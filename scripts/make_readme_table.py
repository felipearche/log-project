import csv
from pathlib import Path
from collections import OrderedDict

SRC = Path("experiments/summary.csv")
OUT = Path("README_TABLE.txt")

def fmt1(x):
    try:
        return f"{float(x):.1f}"
    except Exception:
        return str(x)

def fmt_tpr(tpr, dataset):
    ds = str(dataset).strip()
    if ds.startswith("mini"):
        return "NA"
    try:
        # normalize to 4 decimals
        return f"{float(tpr):.4f}"
    except Exception:
        return str(tpr)

if not SRC.exists():
    raise SystemExit("ERROR: experiments/summary.csv not found")

rows = list(csv.DictReader(SRC.open("r", encoding="utf-8", newline="")))
if not rows:
    raise SystemExit("ERROR: no data rows in summary.csv")

# Group by (dataset, mode, calibration) and keep latest (last occurrence)
keyed = OrderedDict()
for row in rows:
    key = (row.get("dataset",""), row.get("mode",""), row.get("calibration",""))
    keyed[key] = row  # overwrite => last one wins

# Compose table
C_TPR = "TPR_at_1pct_FPR"
C_P95 = "p95_ms"
C_P99 = "p99_ms"
C_EPS = "eps"

table = []
header = ["dataset","mode","calibration","TPR@1%FPR","p95_ms","p99_ms","eps"]
table.append("| " + " | ".join(header) + "|")
table.append("|" + "|".join(["---"]*len(header)) + "|")

for (ds, md, cal), row in keyed.items():
    r = [
        ds, md, cal,
        fmt_tpr(row.get(C_TPR,""), ds),
        fmt1(row.get(C_P95,"")),
        fmt1(row.get(C_P99,"")),
        fmt1(row.get(C_EPS,"")),
    ]
    table.append("| " + " | ".join(r) + "|")

OUT.write_text("\n".join(table) + "\n", encoding="utf-8")
print(f"Wrote {OUT}")
