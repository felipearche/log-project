# -*- coding: utf-8 -*-
"""
make_multi_plots_v2.py â€” multi-config charts with guards and filters

Usage:
  python scripts/make_multi_plots_v2.py --csv experiments/summary.csv --outdir figures --fmt png,svg

Options:
  --calibrations conformal,no_calib  Only include these calibration modes (default: include all)
  --collapse last|median|none        Collapse duplicate (dataset,mode,calibration) rows (default: last)
  --drop-zero-latency / --no-drop-zero-latency  Drop rows with 0 p95 or p99 (default: drop)
  --expect N                         Warn if fewer than N rows after filtering (default: 0)
"""

import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def _ensure_outdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    return p


def _one_decimal(x) -> str:
    try:
        return f"{float(x):.1f}"
    except (TypeError, ValueError):
        return str(x)


def _labels(df: pd.DataFrame) -> pd.Series:
    calcol = (
        "calibration"
        if "calibration" in df.columns
        else ("cal" if "cal" in df.columns else None)
    )
    return df.apply(
        lambda r: f"{r.get('dataset', 'NA')}\n{r.get('mode', r.get('model', 'NA'))}/{r.get(calcol, 'NA') if calcol else 'NA'}",
        axis=1,
    )


def _collapse(df: pd.DataFrame, how: str) -> pd.DataFrame:
    if how == "none":
        return df
    key_cols = [
        "dataset",
        "mode" if "mode" in df.columns else "model",
        "calibration" if "calibration" in df.columns else "cal",
    ]
    if how == "last":
        return df.groupby(key_cols, as_index=False, sort=False).tail(1)
    if how == "median":
        num_cols = [
            c for c in ["p95_ms", "p99_ms", "eps", "throughput_eps"] if c in df.columns
        ]
        agg = {c: "median" for c in num_cols}
        other = [c for c in df.columns if c not in key_cols + num_cols]
        return df.groupby(key_cols, as_index=False).agg(
            {**agg, **{c: "last" for c in other}}
        )
    return df


def _filter_cals(df: pd.DataFrame, wanted: list) -> pd.DataFrame:
    if not wanted:
        return df
    calcol = (
        "calibration"
        if "calibration" in df.columns
        else ("cal" if "cal" in df.columns else None)
    )
    if not calcol:
        return df
    return df[df[calcol].isin(wanted)]


def _drop_zero_latency(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["p95_ms", "p99_ms"] if c in df.columns]
    if not cols:
        return df
    mask = np.ones(len(df), dtype=bool)
    for c in cols:
        mask &= df[c].astype(float) > 0
    return df[mask]


def _smart_order(df: pd.DataFrame) -> pd.DataFrame:
    order_within = [
        ("baseline", "conformal"),
        ("baseline", "no_calib"),
        ("transformer", "conformal"),
        ("transformer", "no_calib"),
    ]

    def key(row):
        ds = str(row.get("dataset", ""))
        md = str(row.get("mode", row.get("model", "")))
        cal = str(row.get("calibration", row.get("cal", "")))
        try:
            wi = order_within.index((md, cal))
        except ValueError:
            wi = 99
        return (ds, wi, md, cal)

    df2 = df.copy()
    df2["__key__"] = df2.apply(key, axis=1)
    df2 = df2.sort_values(by="__key__").drop(columns="__key__")
    return df2


def _bar(df, metric, ylabel, title, outdir, fmts):
    if metric not in df.columns:
        return
    df2 = _smart_order(df.copy())
    lab = _labels(df2)
    vals = df2[metric].astype(float)
    ypad = 0.01 * (np.nanmax(vals) if len(vals) else 1.0)

    fig, ax = plt.subplots(figsize=(20, 5.5))
    bars = ax.bar(range(len(vals)), vals)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(lab, ha="center")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    for r, v in zip(bars, vals):
        ax.text(
            r.get_x() + r.get_width() / 2,
            r.get_height() + ypad,
            _one_decimal(v),
            ha="center",
            va="bottom",
        )
    fig.tight_layout()

    stems = {
        "p95_ms": "latency_p95_ms",
        "p99_ms": "latency_p99_ms",
        "eps": "throughput_eps",
        "throughput_eps": "throughput_eps",
    }
    stem = stems.get(metric, metric)
    for ext in fmts:
        out = outdir / f"{stem}.{('svg' if ext == 'svg' else 'png')}"
        fig.savefig(out, dpi=200 if ext != "svg" else None)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="experiments/summary.csv")
    ap.add_argument("--outdir", default="figures")
    ap.add_argument("--fmt", default="png,svg")
    ap.add_argument("--calibrations", default="")
    ap.add_argument("--collapse", default="last", choices=["last", "median", "none"])
    ap.add_argument(
        "--drop-zero-latency", dest="drop_zero_latency", action="store_true"
    )
    ap.add_argument(
        "--no-drop-zero-latency", dest="drop_zero_latency", action="store_false"
    )
    ap.set_defaults(drop_zero_latency=True)
    ap.add_argument("--expect", type=int, default=0)
    args = ap.parse_args()

    outdir = _ensure_outdir(Path(args.outdir))
    fmts = [s.strip().lower() for s in args.fmt.split(",") if s.strip()]

    df = pd.read_csv(args.csv)
    keep = [
        c
        for c in [
            "dataset",
            "mode",
            "model",
            "calibration",
            "cal",
            "p95_ms",
            "p99_ms",
            "eps",
            "throughput_eps",
        ]
        if c in df.columns
    ]
    df = df[keep].copy()

    if args.calibrations.strip():
        df = _filter_cals(df, [s.strip() for s in args.calibrations.split(",")])

    if args.drop_zero_latency:
        df = _drop_zero_latency(df)

    df = _collapse(df, args.collapse)

    if args.expect and len(df) < args.expect:
        print(f"[WARN] Have {len(df)} rows after filtering; expected {args.expect}.")

    metrics = []
    if "p95_ms" in df.columns:
        metrics.append(("p95_ms", "p95 latency (ms)", "Latency p95"))
    if "p99_ms" in df.columns:
        metrics.append(("p99_ms", "p99 latency (ms)", "Latency p99"))
    metric_eps = (
        "eps"
        if "eps" in df.columns
        else ("throughput_eps" if "throughput_eps" in df.columns else None)
    )
    if metric_eps:
        metrics.append((metric_eps, "events/s", "Throughput"))
    if not metrics:
        raise SystemExit("No known metrics present.")

    for m, y, t in metrics:
        _bar(df, m, y, t, outdir, fmts)


if __name__ == "__main__":
    main()
