#!/usr/bin/env python3
"""
make_readme_table.py
--------------------
Generates README_TABLE.txt from experiments/summary.csv using a *canonical,
human-facing* ordering:

  dataset:     synth_tokens → mini_tokens → (any others lexicographically)
  mode:        baseline → transformer → (any others lexicographically)
  calibration: conformal → no_calib → (any others lexicographically)

Rules:
- One latest row per (dataset, mode, calibration) tuple (last occurrence wins).
- TPR formatting:
    * synth_* datasets: numeric formatted to 4 decimals if present; otherwise left as-is.
    * mini_* datasets: literal "NA" regardless of underlying value.
- p95_ms / p99_ms / eps: numeric formatted to 1 decimal; non-numeric left as-is.
- Output: UTF-8 (no BOM), LF newlines, trailing newline.
"""

import csv
from pathlib import Path
from collections import OrderedDict

SRC = Path("experiments/summary.csv")
OUT = Path("README_TABLE.txt")

# Canonical human-facing order
DS_ORDER = ["synth_tokens", "mini_tokens"]
MODE_ORDER = ["baseline", "transformer"]
CAL_ORDER = ["conformal", "no_calib"]


def _order_index(value: str, order_list: list[str]) -> tuple[int, str]:
    """
    Produce a sortable key: (primary_index, secondary_lex_key)
    Unknown values get placed after known ones, ordered lexicographically.
    """
    v = (value or "").strip()
    try:
        i = order_list.index(v)
        return (i, "")  # known values keep the given relative order
    except ValueError:
        return (len(order_list), v)  # unknowns sorted after known, lexicographically


def _fmt1(x):
    """Format to 1 decimal if numeric; otherwise return as string unchanged."""
    s = str(x).strip()
    if s == "" or s.upper() == "NA":
        return s or "NA"
    try:
        return f"{float(s):.1f}"
    except Exception:
        return s


def _fmt_tpr(tpr, dataset):
    """
    Format TPR:
    - mini_* datasets => literal 'NA'
    - synth_* datasets => 4 decimals if numeric; otherwise leave as-is (e.g., 'NA')
    """
    ds = str(dataset or "").strip().lower()
    if ds.startswith("mini"):
        return "NA"
    s = str(tpr).strip()
    if s == "" or s.upper() == "NA":
        return "NA" if ds.startswith("synth") else s
    try:
        return f"{float(s):.4f}"
    except Exception:
        return s


def main():
    if not SRC.exists():
        raise SystemExit("ERROR: experiments/summary.csv not found")

    with SRC.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise SystemExit("ERROR: no data rows in summary.csv")

    # Group by (dataset, mode, calibration), keep latest (last occurrence)
    keyed: "OrderedDict[tuple[str,str,str], dict]" = OrderedDict()
    for row in rows:
        key = (row.get("dataset", ""), row.get("mode", ""), row.get("calibration", ""))
        keyed[key] = row  # overwrite => last one wins

    # Sort keys by dataset → mode → calibration using canonical orders
    def sort_key(t):
        ds, md, cal = t
        return (
            _order_index(ds, DS_ORDER),
            _order_index(md, MODE_ORDER),
            _order_index(cal, CAL_ORDER),
        )

    sorted_items = sorted(keyed.items(), key=lambda kv: sort_key(kv[0]))

    # Compose table
    C_TPR = "TPR_at_1pct_FPR"
    C_P95 = "p95_ms"
    C_P99 = "p99_ms"
    C_EPS = "eps"

    header = ["dataset", "mode", "calibration", "TPR@1%FPR", "p95_ms", "p99_ms", "eps"]
    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    for (ds, md, cal), row in sorted_items:
        r = [
            ds,
            md,
            cal,
            _fmt_tpr(row.get(C_TPR, ""), ds),
            _fmt1(row.get(C_P95, "")),
            _fmt1(row.get(C_P99, "")),
            _fmt1(row.get(C_EPS, "")),
        ]
        lines.append("| " + " | ".join(r) + " |")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
