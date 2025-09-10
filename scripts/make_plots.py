#!/usr/bin/env python3
import argparse
import csv
import os
from collections import OrderedDict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

DS_ORDER = ["synth_tokens", "mini_tokens"]
MODE_ORDER = ["baseline", "transformer"]
CAL_ORDER = ["conformal", "no_calib"]


def parse_args():
    p = argparse.ArgumentParser(description="Generate figures from experiments/summary.csv")
    p.add_argument("--summary", default="experiments/summary.csv", help="Path to summary.csv")
    p.add_argument("--outdir", default="figures", help="Output directory for PNGs/SVGs")
    p.add_argument("--spacing", type=float, default=1.22, help="Horizontal spacing between bars")
    p.add_argument("--svg", action="store_true", help="Also write .svg files alongside .png")
    return p.parse_args()


def read_latest_groups(summary_path):
    groups = OrderedDict()
    with open(summary_path, encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        idx = {name: i for i, name in enumerate(header)}
        required = ["dataset", "mode", "calibration", "p95_ms", "p99_ms", "eps"]
        for col in required:
            if col not in idx:
                raise SystemExit(f"[ERROR] Missing required column in summary.csv: {col}")
        for row in r:
            key = (row[idx["dataset"]], row[idx["mode"]], row[idx["calibration"]])
            groups[key] = row  # keep latest per group (last wins)
    return groups, header


def order_keys(keys):
    def rank(v, lst):
        return lst.index(v) if v in lst else len(lst)

    return sorted(
        keys,
        key=lambda k: (
            rank(k[0], DS_ORDER),
            rank(k[1], MODE_ORDER),
            rank(k[2], CAL_ORDER),
        ),
    )


def to_float(x):
    try:
        return float(x)
    except Exception:
        return None


def eps_formatter(y, _pos):
    return f"{y:,.0f}"


def draw(metric, ylabel, groups, idx, outpng, spacing=1.22, also_svg=False):
    keys = order_keys(list(groups.keys()))
    labels, values = [], []
    for ds, mode, cal in keys:
        v = to_float(groups[(ds, mode, cal)][idx[metric]])
        if v is None:  # skip NA
            continue
        labels.append(f"{ds}\n{mode}/{cal}")
        values.append(v)
    if not values:
        print(f"[WARN] No numeric values for {metric}; skipping {outpng}")
        return

    os.makedirs(os.path.dirname(outpng), exist_ok=True)

    n = len(values)
    xs = [i * spacing for i in range(n)]
    width = 0.62

    fig, ax = plt.subplots(figsize=(max(6.0, 1.2 * n), 4.0), dpi=120)
    bars = ax.bar(xs, values, width=width)

    for spine in ["top", "right"]:
        s = ax.spines[spine]
        s.set_visible(True)
        s.set_linewidth(1.2)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, linestyle="--", alpha=0.35)

    ax.set_ylabel(ylabel)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.tick_params(axis="x", pad=12)

    if metric == "eps":
        ax.yaxis.set_major_formatter(FuncFormatter(eps_formatter))
    else:
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.1f}"))

    ymax = max(values) if values else 1.0
    ax.set_ylim(0, ymax * 1.15)

    for b, v in zip(bars, values, strict=False):
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() * 1.01,
            f"{v:.1f}",
            ha="center",
            va="bottom",
            fontsize=11,
        )

    fig.tight_layout()
    fig.savefig(outpng)
    if also_svg:
        fig.savefig(os.path.splitext(outpng)[0] + ".svg")
    plt.close(fig)


def main():
    args = parse_args()
    groups, header = read_latest_groups(args.summary)
    idx = {name: i for i, name in enumerate(header)}

    draw(
        "p95_ms",
        "p95 latency (ms)",
        groups,
        idx,
        os.path.join(args.outdir, "latency_p95_ms.png"),
        spacing=args.spacing,
        also_svg=args.svg,
    )
    draw(
        "p99_ms",
        "p99 latency (ms)",
        groups,
        idx,
        os.path.join(args.outdir, "latency_p99_ms.png"),
        spacing=args.spacing,
        also_svg=args.svg,
    )
    draw(
        "eps",
        "events/s",
        groups,
        idx,
        os.path.join(args.outdir, "throughput_eps.png"),
        spacing=args.spacing,
        also_svg=args.svg,
    )


if __name__ == "__main__":
    main()
