def test_calibration_docstring_ascii_and_phrase():
    txt = open("src/calibration.py", encoding="utf-8").read()
    assert "Sliding-window conformal" in txt
    assert all(ord(c) < 128 for c in txt), "Non-ASCII found in calibration.py"
