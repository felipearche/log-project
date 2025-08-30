import sys, csv, io
p = sys.argv[1] if len(sys.argv) > 1 else "experiments/summary.csv"
with open(p, "r", encoding="utf-8") as f:
    rows = list(csv.reader(f))
if not rows: sys.exit(0)
hdr = rows[0]
try:
    i = hdr.index("TPR_at_1pct_FPR")
except ValueError:
    sys.exit(0)
for r in rows[1:]:
    if i < len(r):
        if (r[i] is None) or (str(r[i]).strip() == ""):
            r[i] = "NA"
buf = io.StringIO()
csv.writer(buf, lineterminator="\n").writerows(rows)
with open(p, "wb") as f:
    f.write(buf.getvalue().encode("utf-8"))
