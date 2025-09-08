# -*- coding: utf-8 -*-
"""
make_multi_plots_v2.py — multi-config charts with guards and filters (ruff-clean)

Usage:
  python scripts/make_multi_plots_v2.py --csv experiments/summary.csv --outdir figures --fmt png,svg

Options:
  --calibrations conformal,no_calib  Only include these calibration modes (default: include all)
  --collapse last|median|none        Collapse duplicate (dataset,mode,calibration) rows (default: last)
  --drop-zero-latency / --no-drop-zero-latency  Drop rows with 0 p95 or p99 (default: drop)
  --expect N                         Warn if fewer than N rows after filtering (default: 0)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def ensure_outdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def one_decimal(x: object) -> str:
    try:
        return f"{float(x):.1f}"
    except (TypeError, ValueError):
        return str(x)


def build_labels(df: pd.DataFrame) -> pd.Series:
    cal_col = None
    if "calibration" in df.columns:
        cal_col = "calibration"
    elif "cal" in df.columns:
        cal_col = "cal"

    labels = []
    for _, row in df.iterrows():
        dataset = row.get("dataset", "NA")
        mode = row.get("mode", row.get("model", "NA"))
        cal = row.get(cal_col, "NA") if cal_col else "NA"
        labels.append(f"{dataset}\n{mode}/{cal}")
    return pd.Series(labels, index=df.index)


def collapse(df: pd.DataFrame, how: str) -> pd.DataFrame:
    if how == "none":
        return df

    key_cols = [
        "dataset",
        "mode" if "mode" in df.columns else "model",
        "calibration" if "calibration" in df.columns else "cal",
    ]

    if how == "last":
        # Keep the last occurrence by CSV order
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


def filter_calibrations(df: pd.DataFrame, wanted: list[str]) -> pd.DataFrame:
    if not wanted:
        return df

    cal_col = None
    if "calibration" in df.columns:
        cal_col = "calibration"
    elif "cal" in df.columns:
        cal_col = "cal"

    if not cal_col:
        return df

    return df[df[cal_col].isin(wanted)]


def drop_zero_latency(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["p95_ms", "p99_ms"] if c in df.columns]
    if not cols:
        return df

    mask = np.ones(len(df), dtype=bool)
    for col in cols:
        mask &= df[col].astype(float) > 0.0
    return df[mask]


def smart_order(df: pd.DataFrame) -> pd.DataFrame:
    order_within = [
        ("baseline", "conformal"),
        ("baseline", "no_calib"),
        ("transformer", "conformal"),
        ("transformer", "no_calib"),
    ]

    def key(row: pd.Series) -> tuple[str, int, str, str]:
        dataset = str(row.get("dataset", ""))
        mode = str(row.get("mode", row.get("model", "")))
        cal = str(row.get("calibration", row.get("cal", "")))
        try:
            idx = order_within.index((mode, cal))
        except ValueError:
            idx = 99
        return (dataset, idx, mode, cal)

    df2 = df.copy()
    df2["__key__"] = df2.apply(key, axis=1)
    df2 = df2.sort_values(by="__key__").drop(columns="__key__")
    return df2


def bar_plot(
    df: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    outdir: Path,
    fmts: list[str],
) -> None:
    if metric not in df.columns:
        return

    df2 = smart_order(df.copy())
    labels = build_labels(df2)
    values = df2[metric].astype(float).to_numpy()

    fig, ax = plt.subplots(figsize=(20, 5.5))
    bars = ax.bar(range(len(values)), values)
    ax.set_xticks(range(len(values)))
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.set_ylabel(ylabel)
    ax.set_title(title)

    if values.size:
        ypad = 0.01 * float(np.nanmax(values))
    else:
        ypad = 0.1

    for rect, v in zip(bars, values, strict=False):
        ax.text(
            rect.get_x() + rect.get_width() / 2.0,
            float(v) + ypad,
            one_decimal(v),
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
        suffix = "svg" if ext == "svg" else "png"
        outpath = outdir / f"{stem}.{suffix}"
        fig.savefig(outpath, dpi=None if suffix == "svg" else 200)

    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="experiments/summary.csv")
    parser.add_argument("--outdir", default="figures")
    parser.add_argument("--fmt", default="png,svg")
    parser.add_argument("--calibrations", default="")
    parser.add_argument(
        "--collapse", default="last", choices=["last", "median", "none"]
    )
    parser.add_argument(
        "--drop-zero-latency", dest="drop_zero_latency", action="store_true"
    )
    parser.add_argument(
        "--no-drop-zero-latency", dest="drop_zero_latency", action="store_false"
    )
    parser.set_defaults(drop_zero_latency=True)
    parser.add_argument("--expect", type=int, default=0)
    args = parser.parse_args()

    outdir = ensure_outdir(Path(args.outdir))
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
        wanted = [s.strip() for s in args.calibrations.split(",") if s.strip()]
        df = filter_calibrations(df, wanted)

    if args.drop_zero_latency:
        df = drop_zero_latency(df)

    df = collapse(df, args.collapse)

    if args.expect and len(df) < args.expect:
        print(f"[WARN] Have {len(df)} rows after filtering; expected {args.expect}.")

    metrics: list[tuple[str, str, str]] = []
    if "p95_ms" in df.columns:
        metrics.append(("p95_ms", "p95 latency (ms)", "Latency p95"))
    if "p99_ms" in df.columns:
        metrics.append(("p99_ms", "p99 latency (ms)", "Latency p99"))
    metric_eps = None
    if "eps" in df.columns:
        metric_eps = "eps"
    elif "throughput_eps" in df.columns:
        metric_eps = "throughput_eps"
    if metric_eps:
        metrics.append((metric_eps, "events/s", "Throughput"))

    if not metrics:
        raise SystemExit("No known metrics present.")

    for metric, ylabel, title in metrics:
        bar_plot(df, metric, ylabel, title, outdir, fmts)


if __name__ == "__main__":
    main()
