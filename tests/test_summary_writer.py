import csv
import os


def test_summary_has_24_columns_and_key_fields():
    p = "experiments/summary.csv"
    assert os.path.exists(p), f"Missing {p}"
    with open(p, newline="", encoding="utf-8") as f:
        hdr = next(csv.reader(f))
    assert len(hdr) == 24, f"Expected 24 columns, got {len(hdr)}"
    assert "mode" in hdr and "TPR_at_1pct_FPR" in hdr, "Key columns missing"
