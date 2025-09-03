import csv
import re


def test_p95_le_p99_and_tpr_policy():
    with open("experiments/summary.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows, "experiments/summary.csv is empty"

    hdr = rows[0]
    idx = {name: i for i, name in enumerate(hdr)}

    # Schema guards
    assert len(hdr) == 24, f"Expected 24 columns, found {len(hdr)}"
    required = {"dataset", "mode", "TPR_at_1pct_FPR", "p95_ms", "p99_ms"}
    assert required.issubset(idx), f"Missing required columns: {required - set(idx)}"

    ds_i, tpr_i, p95_i, p99_i = (
        idx["dataset"],
        idx["TPR_at_1pct_FPR"],
        idx["p95_ms"],
        idx["p99_ms"],
    )

    for i, row in enumerate(rows[1:], start=1):
        # p95 <= p99
        p95 = float(row[p95_i])
        p99 = float(row[p99_i])
        assert p95 <= p99 + 1e-9, f"Row {i}: p95_ms={p95} > p99_ms={p99}"

        # TPR formatting policy
        ds = row[ds_i]
        tpr = row[tpr_i]
        if ds == "synth_tokens":
            assert re.fullmatch(r"\d+\.\d{4}", tpr), (
                f"Row {i}: synth_tokens TPR should be 4 decimals, got {tpr!r}"
            )
        elif ds == "mini_tokens":
            assert tpr == "NA", f"Row {i}: mini_tokens TPR should be NA, got {tpr!r}"
