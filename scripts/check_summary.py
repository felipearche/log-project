import csv, sys
from pathlib import Path

p = Path("experiments/summary.csv")
if not p.exists():
    sys.exit("ERROR: experiments/summary.csv not found.")

with p.open("r", encoding="utf-8", newline="") as f:
    rows = list(csv.reader(f))
if not rows:
    sys.exit("ERROR: summary.csv is empty.")

hdr = rows[0]
if len(hdr) != 24:
    sys.exit(f"ERROR: Expected 24 columns, got {len(hdr)}")

if "mode" not in hdr or "calibration" not in hdr:
    sys.exit("ERROR: Missing 'mode' or 'calibration' column.")

# Locate p95/p99/tpr/data columns
def find_col(want):
    for c in hdr:
        if c.lower() == want.lower():
            return c
    return None

p95c = find_col("p95_ms")
p99c = find_col("p99_ms")
tprc = find_col("TPR_at_1pct_FPR")
datc = find_col("data") or find_col("dataset")

if not (p95c and p99c):
    sys.exit("ERROR: Could not find p95_ms and/or p99_ms columns.")

if not (tprc and datc):
    sys.exit("ERROR: Missing TPR_at_1pct_FPR or data/dataset column.")

bad_p = []
bad_tpr = []
for i, r in enumerate(rows[1:], start=2):
    # p95 <= p99
    try:
        p95 = float(r[hdr.index(p95c)])
        p99 = float(r[hdr.index(p99c)])
        if p95 > p99:
            bad_p.append(i)
    except:
        pass

    # TPR policy
    tpr = r[hdr.index(tprc)].strip()
    ds  = r[hdr.index(datc)]
    if tpr.upper() == "NA":
        if "mini_tokens" not in ds:
            bad_tpr.append(f"line {i}: NA only allowed for mini_tokens (got {ds})")
    else:
        try:
            float(tpr)
        except:
            bad_tpr.append(f"line {i}: TPR must be numeric or NA")
        else:
            if "synth_tokens" in ds and "." in tpr:
                frac = tpr.split(".", 1)[1]
                if len(frac) != 4:
                    bad_tpr.append(f"line {i}: TPR for synth_tokens must have 4 decimals (got {tpr})")

if bad_p:
    sys.exit("ERROR: p95_ms > p99_ms at " + ", ".join(map(str, bad_p)))
if bad_tpr:
    sys.exit("ERROR: TPR policy issues:\n- " + "\n- ".join(bad_tpr))

print("OK: summary.csv passed all checks.")
