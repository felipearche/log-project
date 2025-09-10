import json
import os


def test_mini_tokens_exists_and_has_masks():
    p = "data/mini_tokens.json"
    assert os.path.exists(p), f"Missing {p}"
    j = json.load(open(p, encoding="utf-8"))
    assert isinstance(j, list) and all(isinstance(x, list) for x in j)
    flat = " ".join(t for seq in j for t in seq)
    assert any(tok in flat for tok in ("<num>", "<ip>", "<hex>")), "No canonical masks found"
