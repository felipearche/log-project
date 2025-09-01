import csv
import sys
from pathlib import Path

CSV_PATH = Path("experiments/summary.csv")


def main() -> None:
    rows = list(csv.reader(CSV_PATH.open(encoding="utf-8", newline="")))
    if not rows:
        sys.exit("ERROR: experiments/summary.csv is empty")

    hdr = rows[0]
    required = [
        "dataset",
        "mode",
        "calibration",
        "TPR_at_1pct_FPR",
        "p95_ms",
        "p99_ms",
        "eps",
    ]
    for col in required:
        if col not in hdr:
            sys.exit(f"ERROR: missing column {col!r} in header")

    idx = {name: i for i, name in enumerate(hdr)}
    bad_p = []
    bad_tpr = []

    for i, r in enumerate(rows[1:], start=2):
        # p95 <= p99
        try:
            p95 = float(r[idx["p95_ms"]])
            p99 = float(r[idx["p99_ms"]])
        except Exception:
            bad_p.append(i)
        else:
            if p95 > p99:
                bad_p.append(i)

        # TPR policy
        tpr = r[idx["TPR_at_1pct_FPR"]].strip()
        ds = r[idx["dataset"]]

        if tpr.upper() == "NA":
            if "mini_tokens" not in ds:
                bad_tpr.append(f"line {i}: TPR must be numeric for {ds}")
        else:
            try:
                float(tpr)
            except Exception:
                bad_tpr.append(f"line {i}: TPR must be numeric or NA")
            else:
                if "synth_tokens" in ds and "." in tpr:
                    frac = tpr.split(".", 1)[1]
                    if len(frac) != 4:
                        bad_tpr.append(
                            f"line {i}: TPR for synth_tokens must have 4 decimals (got {tpr})"
                        )

    if bad_p:
        sys.exit(
            "ERROR: p95_ms > p99_ms or non-numeric at lines "
            + ", ".join(map(str, bad_p))
        )
    if bad_tpr:
        sys.exit("ERROR: TPR policy violations: " + "; ".join(bad_tpr))

    print("OK")


if __name__ == "__main__":
    main()
