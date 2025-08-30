# src/stream.py
import os, sys, time, json, argparse, csv, subprocess, pathlib, random
import math
from datetime import datetime

# --- Determinism (project canonical) ---
os.environ.setdefault("PYTHONHASHSEED", "20250819")
random.seed(20250819)
try:
    import numpy as np
    np.random.seed(20250819)
except Exception:
    print("[warn] numpy not available; proceeding without np-seeding", file=sys.stderr)

# --- Deps ---
try:
    from river.drift import ADWIN
except ImportError as e:
    raise SystemExit("Missing dependency 'river'. Install with: pip install river") from e

# Optional: sklearn baseline
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Optional: psutil for CPU% sampling
try:
    import psutil
    _PROC = psutil.Process()
    _PROC.cpu_percent(None)  # prime
    PSUTIL_AVAILABLE = True
except Exception:
    _PROC = None
    PSUTIL_AVAILABLE = False

# Conformal calibrator
try:
    from src.calibration import SlidingConformal
except Exception:
    from calibration import SlidingConformal  # fallback when run as a module

# --- Canonical summary schema (24 columns) ---
SUMMARY_HEADER = [
    "date","commit","dataset","mode","calibration","drift_detector","seed",
    "events","anomalies","drifts","TPR_at_1pct_FPR","p95_ms","p99_ms","eps","CPU_pct","energy_J",
    "calib_target_fpr","calib_window","warmup","adwin_delta",
    "iso_n_estimators","iso_max_samples","iso_random_state","notes",
]

# ---------- Helpers ----------

def _fmt(x):
    """CSV formatting: floats to 6 sig figs; NaN -> empty; keep strings/ints as-is."""
    if isinstance(x, float):
        return "" if math.isnan(x) else f"{x:.6g}"
    return str(x)

def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")

def resolve_commit() -> str:
    """Prefer COMMIT env (Docker-friendly), else git short SHA, else 'NA'."""
    env = os.getenv("COMMIT")
    if env:
        return env.strip()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        return out or "NA"
    except Exception:
        return "NA"

def stream_tokens(json_path: str):
    with open(json_path, encoding="utf-8") as f:
        seqs = json.load(f)
    for s in seqs:
        yield " ".join(s)

def load_texts(json_path: str):
    with open(json_path, encoding="utf-8") as f:
        seqs = json.load(f)
    return [" ".join(s) for s in seqs]

def perc(samples, p):
    """Simple percentile with floor index; returns NaN if empty."""
    if not samples:
        return float("nan")
    ys = sorted(samples)
    k = int((p / 100.0) * (len(ys) - 1))
    return float(ys[k])

def tpr_at_fpr(scores, labels, target_fpr=0.01):
    """Compute TPR at fixed FPR using negatives' quantile threshold (higher score = more anomalous)."""
    if labels is None:
        return float("nan"), float("nan")
    if len(scores) != len(labels):
        return float("nan"), float("nan")
    neg = [s for s, y in zip(scores, labels) if int(y) == 0]
    pos = [s for s, y in zip(scores, labels) if int(y) == 1]
    if not neg or not pos:
        return float("nan"), float("nan")
    neg_sorted = sorted(neg)
    # threshold at (1 - target_fpr) quantile of negatives
    k = int((1.0 - target_fpr) * (len(neg_sorted) - 1))
    k = max(0, min(k, len(neg_sorted) - 1))
    thr = float(neg_sorted[k])
    tpr = sum(1 for s in pos if s >= thr) / float(len(pos))
    return float(tpr), thr

# --- Scorers ---

def score_len(s: str) -> float:
    """Cheap heuristic: normalized length (cap at 100 chars)."""
    return min(len(s), 100) / 100.0

class BaselineScorer:
    """TF-IDF + IsolationForest anomaly score (higher = more anomalous)."""
    def __init__(self, texts, contamination=0.01, seed=0, min_df=1):
        if not SKLEARN_AVAILABLE:
            raise SystemExit("Missing dependency 'scikit-learn'. Install with: pip install scikit-learn")
        self.vec = TfidfVectorizer(min_df=min_df, max_features=50000)
        X = self.vec.fit_transform(texts)
        # Expose params for logging
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

# --- Summary writer (canonical) ---

def emit_summary_row(*, dataset_path, mode, calibration, drift_detector, seed,
                     events, anomalies, drifts, tpr_at_1pct, p95_ms, p99_ms, eps,
                     CPU_pct="NA", energy_J="NA",
                     calib_target_fpr="NA", calib_window="NA",
                     warmup="NA", adwin_delta="NA",
                     iso_n_estimators="NA", iso_max_samples="NA", iso_random_state="NA",
                     notes="", summary_out=None, print_header=True):
    """Print canonical CSV markers and append one row to the summary file."""
    date = datetime.now().strftime("%Y-%m-%d")
    commit = resolve_commit()
    dataset = pathlib.Path(dataset_path).stem

    row_list = [
        date, commit, dataset, mode, calibration, drift_detector, seed,
        events, anomalies, drifts, tpr_at_1pct, p95_ms, p99_ms, eps, CPU_pct, energy_J,
        calib_target_fpr, calib_window, warmup, adwin_delta,
        iso_n_estimators, iso_max_samples, iso_random_state, notes,
    ]

    header_csv = ",".join(SUMMARY_HEADER)
    row_csv = ",".join(_fmt(v) for v in row_list)

    file_exists = pathlib.Path(summary_out).exists() if summary_out else False
    if print_header and not file_exists:
        print("CSV_HEADER:", header_csv, flush=True)
    print("CSV_ROW:", row_csv, flush=True)

    if summary_out:
        p = pathlib.Path(summary_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not file_exists:
            p.write_text(header_csv + "\n", encoding="utf-8")
        with p.open("a", encoding="utf-8", newline="") as f:
            f.write(row_csv + "\n")

# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synth_tokens.json")
    ap.add_argument("--mode", choices=["len", "baseline", "transformer"], default="baseline",
                    help="Scoring mode: len (cheap heuristic), baseline (TFIDF+IF), transformer (stub)")
    ap.add_argument("--sleep_ms", type=int, default=0, help="sleep between items (ms); 0 for real latency")
    ap.add_argument("--seed", type=int, default=20250819, help="random seed for stochastic components")

    # Labels / per-event export
    ap.add_argument("--labels", type=str, default=None, help="Path to labels json (0/1 per seq)")
    ap.add_argument("--save-scores", type=str, default=None,
                    help="Path to write per-event scores CSV (idx,score,label,flag,thr_stream,lat_ms). Also writes *_drifts.csv")

    # Calibration / drift
    ap.add_argument("--alpha", type=float, default=0.01, help="target FPR for conformal calibration")
    ap.add_argument("--window", type=int, default=5000, help="sliding conformal window size")
    ap.add_argument("--warmup", type=int, default=200, help="samples before thresholding counts")
    ap.add_argument("--no_calib", "--no-calib", dest="no_calib", action="store_true",
                    help="disable conformal; use fixed threshold after warmup")
    ap.add_argument("--adwin-delta", type=float, default=0.002, help="ADWIN delta (drift sensitivity)")

    # Baseline TF-IDF/IF params
    ap.add_argument("--contam", type=float, default=0.01, help="IsolationForest contamination")
    ap.add_argument("--tfidf-min-df", type=int, default=1, help="TfidfVectorizer min_df")

    # Summary output
    ap.add_argument("--summary-out", type=str, default="experiments/summary.csv",
                    help="Path to summary CSV to append")
    ap.add_argument("--no-summary", action="store_true", help="Disable writing to the summary CSV")
    args = ap.parse_args()

    # Seed (python/numpy already set above to canonical); extend here if you add torch/jax later
    random.seed(args.seed)
    try:
        np.random.seed(args.seed)  # safe if numpy present
    except Exception:
        pass

    # Choose scorer
    iso_model = None
    model = None
    if args.mode == "baseline":
        texts = load_texts(args.data)
        bm = BaselineScorer(texts, contamination=args.contam, seed=args.seed, min_df=args.tfidf_min_df)
        iso_model = bm
        scorer = bm.score
    elif args.mode == "len":
        scorer = score_len
    elif args.mode == "transformer":
        from src.transformer import TransformerScorer as _TransformerScorer
        model = _TransformerScorer(embed_dim=32, window=32, decay=0.90, seed=args.seed)
        def scorer(text: str) -> float:
            # Incoming `text` is a whitespace-joined token sequence.
            toks = text.split()
            return model.score_and_update(toks)
    else:
        # Fallback safeguard
        scorer = score_len

    # Conformal calibration (sliding inductive) and drift detector
    calib = SlidingConformal(alpha=args.alpha, window=args.window)
    drift = ADWIN(delta=args.adwin_delta)

    # Optional labels
    labels = None
    if args.labels:
        with open(args.labels, "r", encoding="utf-8") as f:
            labels = json.load(f)
        # basic sanity
        if not isinstance(labels, list):
            print("[warn] labels file is not a list; ignoring labels", file=sys.stderr)
            labels = None

    warm_scores = []
    fixed_thr = None

    lat_s = []
    scores = []
    flags = []
    thr_series = []
    drift_indices = []
    y_true = []

    cpu_samples = []  # <- CPU% sampler
    n_total = 0
    n_anom = 0
    n_drift = 0
    t_start = time.perf_counter()

    calib_n = 0  # count of scores seen by conformal (for warmup gate)

    for i, text in enumerate(stream_tokens(args.data)):
        t0 = time.perf_counter()
        s = scorer(text)
        t1 = time.perf_counter()
        lat_s.append(t1 - t0)
        n_total += 1

        # CPU% sample every 25 events (non-blocking)
        if PSUTIL_AVAILABLE and (i % 25 == 0):
            try:
                cpu_samples.append(_PROC.cpu_percent(None))  # process CPU%
            except Exception:
                pass

        # Warmup collection for fixed threshold path
        if len(warm_scores) < args.warmup:
            warm_scores.append(s)

        is_anom = False

        if args.no_calib:
            # Fixed threshold after warmup based on (1 - alpha) quantile of warm scores
            if fixed_thr is None and len(warm_scores) >= args.warmup:
                arr = sorted(warm_scores)
                k = int((1 - args.alpha) * (len(arr) - 1))
                k = max(0, min(k, len(arr) - 1))
                fixed_thr = float(arr[k])
                print(f"[note] fixed threshold={fixed_thr:.3f} from warmup={len(arr)}")
            thr = fixed_thr if fixed_thr is not None else float("inf")
            if fixed_thr is not None and s > thr:
                is_anom = True
                n_anom += 1
                print(f"[anomaly]#{i} score={s:.3f} thr={thr:.3f} text='{text[:90]}'")
        else:
            # Conformal thresholding
            calib.update(s)
            calib_n += 1
            thr = calib.threshold()
            if calib_n >= args.warmup and s > thr:
                is_anom = True
                n_anom += 1
                print(f"[anomaly]#{i} score={s:.3f} thr={thr:.3f} text='{text[:90]}'")

        # Drift detection & adaptation
        drift.update(s)
        if getattr(drift, "drift_detected", False) or getattr(drift, "change_detected", False):
            n_drift += 1
            drift_indices.append(i)
            # Reset transformer model buffers on drift (regardless of calibration)
            if args.mode == "transformer" and model is not None and hasattr(model, "reset"):
                model.reset()
            if args.no_calib:
                print(f"[drift]#{i} detected (fixed threshold unchanged)")
            else:
                print(f"[drift]#{i} reset conformal window")
                calib.reset()
                drift = ADWIN(delta=args.adwin_delta)

        # Collect per-event series
        scores.append(float(s))
        flags.append(int(is_anom))
        thr_series.append(float(thr))
        if labels is not None and i < len(labels):
            y_true.append(int(labels[i]))

        if args.sleep_ms:
            time.sleep(args.sleep_ms / 1000.0)

    # Metrics
    dt = max(time.perf_counter() - t_start, 1e-12)
    p95 = perc(lat_s, 95) * 1000.0
    p99 = perc(lat_s, 99) * 1000.0
    eps = n_total / dt
    thr_mode = "fixed" if args.no_calib else "conformal"

    # TPR@1%FPR
    tpr1 = float("nan")
    thr_at_1pct = float("nan")
    if labels is not None and len(y_true) == len(scores):
        tpr1, thr_at_1pct = tpr_at_fpr(scores, y_true, target_fpr=0.01)

    # CPU% aggregate
    cpu_pct_val = _mean(cpu_samples) if cpu_samples else float("nan")
    cpu_field = "NA" if math.isnan(cpu_pct_val) else round(cpu_pct_val, 1)

    print(
        f"[summary] total={n_total} anomalies={n_anom} drifts={n_drift} "
        f"p95={p95:.2f}ms p99={p99:.2f}ms throughput={eps:.1f} lines/s threshold={thr_mode}"
    )
    if not math.isnan(tpr1):
        print(f"[metric] TPR@1%FPR={tpr1:.4f} (thr_neg@99th={thr_at_1pct:.4f})")

    # Optional per-event export
    if args.save_scores:
        outp = pathlib.Path(args.save_scores)
        outp.parent.mkdir(parents=True, exist_ok=True)
        with outp.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["idx","score","label","flag","thr_stream","lat_ms"])
            for idx, s in enumerate(scores):
                lab = (y_true[idx] if (labels is not None and idx < len(y_true)) else "")
                lat_ms = lat_s[idx] * 1000.0
                w.writerow([idx, f"{s:.6g}", lab, flags[idx], f"{thr_series[idx]:.6g}", f"{lat_ms:.6g}"])
        # drift indices next to it
        dpath = outp.with_name(outp.stem + "_drifts.csv")
        with dpath.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["idx"])
            for d in drift_indices:
                w.writerow([d])
        print(f"[write] scores -> {outp}")
        print(f"[write] drifts  -> {dpath}")

    # Canonical summary row (reproducible)
    if not args.no_summary:
        calibration_label = "no_calib" if args.no_calib else "conformal"
        base_notes = ("baseline conformal" if (args.mode == "baseline" and not args.no_calib)
                      else ("baseline no-calib" if (args.mode == "baseline" and args.no_calib) else "run"))
        # annotate notes with sampler/energy info
        sampler_note = "cpu_sampler=process_avg" if not isinstance(cpu_field, str) else "cpu_sampler=na"
        notes_final = f"{base_notes};{sampler_note};energy_na"

        emit_summary_row(
            dataset_path=args.data,
            mode=args.mode,
            calibration=calibration_label,
            drift_detector="ADWIN",
            seed=args.seed,
            events=n_total,
            anomalies=n_anom,
            drifts=n_drift,
            tpr_at_1pct=tpr1,   # filled when labels are provided
            p95_ms=p95,
            p99_ms=p99,
            eps=eps,
            CPU_pct=cpu_field,
            energy_J="NA",
            calib_target_fpr=(args.alpha if not args.no_calib else "NA"),
            calib_window=(getattr(calib, "window", args.window) if not args.no_calib else "NA"),
            warmup=args.warmup,
            adwin_delta=args.adwin_delta,
            iso_n_estimators=(getattr(iso_model, "n_estimators", "NA") if iso_model else "NA"),
            iso_max_samples=(getattr(iso_model, "max_samples", "NA") if iso_model else "NA"),
            iso_random_state=(getattr(iso_model, "random_state", "NA") if iso_model else "NA"),
            notes=notes_final,
            summary_out=args.summary_out,
        )
