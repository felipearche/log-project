import sys, csv, io
path = sys.argv[1] if len(sys.argv) > 1 else "experiments/summary.csv"
with open(path, "r", encoding="utf-8") as f:
    rows = list(csv.reader(f))
if not rows or len(rows) < 2:
    sys.exit(0)
header = rows[0]
try:
    tpr_idx = header.index("TPR_at_1pct_FPR")
except ValueError:
    sys.exit(0)
last = rows[-1]
val = (last[tpr_idx] or "").strip()
if val and val.upper() != "NA":
    try:
        last[tpr_idx] = f"{float(val):.4f}"
    except ValueError:
        pass
buf = io.StringIO()
w = csv.writer(buf, lineterminator="\n")
w.writerows(rows)
with open(path, "wb") as f:
    f.write(buf.getvalue().encode("utf-8"))
