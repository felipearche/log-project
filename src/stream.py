#!/usr/bin/env python3
import os
import sys
import time
import json
import argparse
import subprocess
import pathlib
import random
import math
from datetime import datetime

os.environ.setdefault("PYTHONHASHSEED", "20250819")
random.seed(20250819)
try:
    import numpy as np  # type: ignore

    np.random.seed(20250819)
except Exception:
    print("[warn] numpy not available; proceeding without np-seeding", file=sys.stderr)

try:
    from river.drift import ADWIN  # type: ignore
except Exception:

    class ADWIN:  # minimal fallback; never signals drift
        def __init__(self, delta: float = 0.002):
            self.delta = float(delta)
            self.drift_detected = False
            self.change_detected = False

        def update(self, _x: float):
            self.drift_detected = False
            self.change_detected = False


try:
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
    from sklearn.ensemble import IsolationForest  # type: ignore

    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

try:
    import psutil  # type: ignore

    _PROC = psutil.Process()
    _PROC.cpu_percent(None)
    PSUTIL_AVAILABLE = True
except Exception:
    _PROC = None
    PSUTIL_AVAILABLE = False

try:
    from src.calibration import SlidingConformal
except Exception:
    from calibration import SlidingConformal  # type: ignore

SUMMARY_HEADER = [
    "date",
    "commit",
    "dataset",
    "mode",
    "calibration",
    "drift_detector",
    "seed",
    "events",
    "anomalies",
    "drifts",
    "TPR_at_1pct_FPR",
    "p95_ms",
    "p99_ms",
    "eps",
    "CPU_pct",
    "energy_J",
    "calib_target_fpr",
    "calib_window",
    "warmup",
    "adwin_delta",
    "iso_n_estimators",
    "iso_max_samples",
    "iso_random_state",
    "notes",
]


def _fmt(x):
    if isinstance(x, float):
        return "" if math.isnan(x) else f"{x:.6g}"
    return str(x)


def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def resolve_commit() -> str:
    env = os.getenv("COMMIT")
    if env:
        return env.strip()
    try:
        out = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode("utf-8")
            .strip()
        )
        return out or "NA"
    except Exception:
        return "NA"


def stream_tokens(json_path: str):
    with open(json_path, encoding="utf-8") as f:
        j = json.load(f)
    return [" ".join(seq) for seq in j]  # list[list[str]] -> list[str]


def perc(samples, p):
    if not samples:
        return float("nan")
    ys = sorted(samples)
    k = int((p / 100.0) * (len(ys) - 1))
    return float(ys[k])


def tpr_at_fpr(scores, labels, target_fpr=0.01):
    if labels is None or len(scores) != len(labels):
        return float("nan"), float("nan")
    neg = [s for s, y in zip(scores, labels) if int(y) == 0]
    pos = [s for s, y in zip(scores, labels) if int(y) == 1]
    if not neg or not pos:
        return float("nan"), float("nan")
    neg_sorted = sorted(neg)
    k = int((1.0 - target_fpr) * (len(neg_sorted) - 1))
    k = max(0, min(k, len(neg_sorted) - 1))
    thr = float(neg_sorted[k])
    tpr = sum(1 for s in pos if s >= thr) / float(len(pos))
    return float(tpr), thr


def score_len(text: str) -> float:
    # simple monotone proxy: longer line -> higher anomaly
    return float(len(text))


class BaselineScorer:
    """TF-IDF + IsolationForest anomaly score (higher = more anomalous)."""

    def __init__(self, texts, contamination=0.01, seed=0, min_df=1):
        if not SKLEARN_AVAILABLE:
            raise SystemExit(
                "Missing dependency 'scikit-learn'. Install with: pip install scikit-learn"
            )
        self.vec = TfidfVectorizer(min_df=min_df, max_features=50000)
        X = self.vec.fit_transform(texts)
        self.n_estimators = 200
        self.max_samples = "auto"
        self.random_state = seed
        self.clf = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=contamination,
            random_state=seed,
        ).fit(X)

    def score(self, text: str) -> float:
        X = self.vec.transform([text])
        return float(-self.clf.score_samples(X)[0])  # higher = more anomalous


def emit_summary_row(
    *,
    dataset_path,
    mode,
    calibration,
    drift_detector,
    seed,
    events,
    anomalies,
    drifts,
    tpr_str,
    p95_ms,
    p99_ms,
    eps,
    CPU_pct,
    energy_J,
    calib_target_fpr,
    calib_window,
    warmup,
    adwin_delta,
    iso_n_estimators,
    iso_max_samples,
    iso_random_state,
    notes,
    summary_out,
):
    date_s = datetime.utcnow().strftime("%Y-%m-%d")
    row_list = [
        date_s,
        resolve_commit(),
        pathlib.Path(dataset_path).name.replace(".json", ""),
        mode,
        calibration,
        drift_detector,
        seed,
        events,
        anomalies,
        drifts,
        tpr_str,
        p95_ms,
        p99_ms,
        eps,
        CPU_pct,
        energy_J,
        calib_target_fpr,
        calib_window,
        warmup,
        adwin_delta,
        iso_n_estimators,
        iso_max_samples,
        iso_random_state,
        notes,
    ]
    header_csv = ",".join(SUMMARY_HEADER)
    row_csv = ",".join(_fmt(v) for v in row_list)
    file_exists = pathlib.Path(summary_out).exists() if summary_out else False
    if not file_exists:
        pathlib.Path(summary_out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(summary_out).write_text(header_csv + "\n", encoding="utf-8")
    with open(summary_out, "a", encoding="utf-8", newline="") as f:
        f.write(row_csv + "\n")


def main():
    ap = argparse.ArgumentParser(
        description="Stream log tokens and compute anomaly metrics"
    )
    ap.add_argument(
        "--data",
        default="data/synth_tokens.json",
        help="Path to tokenized JSON (list[list[str]])",
    )
    ap.add_argument("--mode", choices=["baseline", "transformer"], default="baseline")
    ap.add_argument(
        "--sleep_ms",
        type=int,
        default=0,
        help="sleep per event (ms) to simulate streaming",
    )
    ap.add_argument(
        "--summary-out", dest="summary_out", default="experiments/summary.csv"
    )
    ap.add_argument("--seed", type=int, default=20250819)
    ap.add_argument(
        "--labels", default="", help="Optional labels JSON path (list[int])"
    )
    ap.add_argument(
        "--alpha", type=float, default=0.01, help="target FPR for conformal calibration"
    )
    ap.add_argument(
        "--window", type=int, default=5000, help="sliding conformal window size"
    )
    ap.add_argument(
        "--warmup", type=int, default=200, help="samples before thresholding counts"
    )
    ap.add_argument(
        "--no-calib",
        dest="no_calib",
        action="store_true",
        help="disable conformal; use fixed threshold after warmup",
    )
    ap.add_argument(
        "--adwin-delta",
        type=float,
        default=0.002,
        help="ADWIN delta (drift sensitivity)",
    )
    ap.add_argument(
        "--contam", type=float, default=0.01, help="IsolationForest contamination"
    )
    ap.add_argument(
        "--tfidf-min-df", type=int, default=1, help="TfidfVectorizer min_df"
    )
    ap.add_argument(
        "--save-scores", default="", help="Optional path to save per-event scores CSV"
    )
    args = ap.parse_args()

    random.seed(args.seed)

    texts = stream_tokens(args.data)
    scorer = None
    iso_model = None
    if args.mode == "baseline":
        if SKLEARN_AVAILABLE:
            iso_model = BaselineScorer(
                texts,
                contamination=args.contam,
                seed=args.seed,
                min_df=args.tfidf_min_df,
            )
            scorer = iso_model.score
        else:
            scorer = score_len
    else:
        scorer = score_len  # placeholder for transformer path

    calibration_label = "no_calib" if args.no_calib else "conformal"
    calib = SlidingConformal(alpha=args.alpha, window=args.window)
    drift = ADWIN(delta=args.adwin_delta)

    labels = None
    if args.labels:
        try:
            with open(args.labels, "r", encoding="utf-8") as f:
                labels = json.load(f)
        except Exception:
            labels = None

    lat_s = []
    scores = []
    y_true = []
    cpu_samples = []
    n_anom = 0
    n_drift = 0

    fixed_thr = None
    warm_scores = []

    for i, text in enumerate(texts, start=1):
        t0 = time.perf_counter()
        s = scorer(text)
        t1 = time.perf_counter()
        lat_s.append(t1 - t0)
        scores.append(s)

        if labels is not None and i - 1 < len(labels):
            y_true.append(int(labels[i - 1]))

        if PSUTIL_AVAILABLE and _PROC is not None and (i % 50 == 0):
            try:
                cpu_samples.append(_PROC.cpu_percent(None))
            except Exception:
                pass

        if args.no_calib:
            warm_scores.append(s)
            if fixed_thr is None and len(warm_scores) >= args.warmup:
                arr = sorted(warm_scores)
                k = int((1 - args.alpha) * (len(arr) - 1))
                k = max(0, min(k, len(arr) - 1))
                fixed_thr = float(arr[k])
            thr = fixed_thr if fixed_thr is not None else float("inf")
            is_anom = fixed_thr is not None and s > thr
        else:
            calib.update(s)
            thr = calib.threshold()
            is_anom = len(scores) >= args.warmup and s > thr

        drift.update(s)
        if getattr(drift, "drift_detected", False) or getattr(
            drift, "change_detected", False
        ):
            n_drift += 1
            calib.reset()  # reset calibration on drift

        if is_anom:
            n_anom += 1

        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    n_total = len(scores)
    p95 = perc(lat_s, 95) * 1000.0 if lat_s else float("nan")
    p99 = perc(lat_s, 99) * 1000.0 if lat_s else float("nan")
    eps = (n_total / sum(lat_s)) if lat_s and sum(lat_s) > 0 else float("nan")

    tpr1 = float("nan")
    if labels is not None and len(y_true) == len(scores):
        tpr1, _thr = tpr_at_fpr(scores, y_true, target_fpr=0.01)
    tpr_str = (
        f"{tpr1:.4f}" if (isinstance(tpr1, float) and not math.isnan(tpr1)) else "NA"
    )

    cpu_pct_val = _mean(cpu_samples) if cpu_samples else float("nan")
    cpu_field = "NA" if math.isnan(cpu_pct_val) else round(cpu_pct_val, 1)

    notes = f"{args.mode} {calibration_label};cpu_sampler={'process_avg' if PSUTIL_AVAILABLE else 'na'};energy_na"

    emit_summary_row(
        dataset_path=args.data,
        mode=args.mode,
        calibration=calibration_label,
        drift_detector="ADWIN",
        seed=args.seed,
        events=n_total,
        anomalies=n_anom,
        drifts=n_drift,
        tpr_str=tpr_str,
        p95_ms=p95,
        p99_ms=p99,
        eps=eps,
        CPU_pct=cpu_field,
        energy_J="NA",
        calib_target_fpr=(args.alpha if not args.no_calib else "NA"),
        calib_window=(calib.window if not args.no_calib else "NA"),
        warmup=args.warmup,
        adwin_delta=args.adwin_delta,
        iso_n_estimators=(
            getattr(iso_model, "n_estimators", "NA") if iso_model else "NA"
        ),
        iso_max_samples=(
            getattr(iso_model, "max_samples", "NA") if iso_model else "NA"
        ),
        iso_random_state=(
            getattr(iso_model, "random_state", "NA") if iso_model else "NA"
        ),
        notes=notes,
        summary_out=args.summary_out,
    )


if __name__ == "__main__":
    main()
