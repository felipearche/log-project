import csv

EXPECTED_HEADER = [
    "date","commit","dataset","mode","calibration","drift_detector","seed",
    "events","anomalies","drifts","TPR_at_1pct_FPR","p95_ms","p99_ms","eps",
    "CPU_pct","energy_J","calib_target_fpr","calib_window","warmup","adwin_delta",
    "iso_n_estimators","iso_max_samples","iso_random_state","notes",
]

def test_summary_header_exact():
    with open("experiments/summary.csv", newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == EXPECTED_HEADER, f"Header mismatch. Found {header}"
