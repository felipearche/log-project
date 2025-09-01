import re
import hashlib
from pathlib import Path

HASHES = Path("data/HASHES.txt")


def test_hashes_format_and_crypto():
    assert HASHES.exists(), "data/HASHES.txt not found"
    lines = [
        line for line in HASHES.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    # exactly four lines
    assert len(lines) == 4, f"Expected 4 lines, got {len(lines)}"
    # two spaces + UPPERCASE HEX; exact four expected paths (any order)
    pat = re.compile(
        r"^(\d{4}-\d{2}-\d{2})\s{2}(\S+)\s{2}(\d+)\s{2}sha256=([0-9A-F]{64})\s*$"
    )
    expected = {
        "data/synth_tokens.json",
        "data/mini_tokens.json",
        "data/synth_labels.json",
        "data/raw/mini.log",
    }
    seen = set()
    for i, line in enumerate(lines, start=1):
        m = pat.match(line)
        assert m, f"Line {i} fails format (two spaces or HEX case?): {line!r}"
        _date, path, size_s, hex_upper = m.groups()
        seen.add(path)
        # verify file exists and size matches
        fp = Path(path)
        assert fp.exists(), f"Missing file referenced by HASHES: {path}"
        actual_size = fp.stat().st_size
        assert int(size_s) == actual_size, (
            f"Size mismatch for {path}: {size_s} vs {actual_size}"
        )
        # verify SHA-256 matches and is uppercase in file
        h = hashlib.sha256(fp.read_bytes()).hexdigest().upper()
        assert hex_upper == h, f"SHA mismatch for {path}: {hex_upper} vs {h}"
    assert seen == expected, (
        f"Paths mismatch.\nExpected: {sorted(expected)}\nSeen: {sorted(seen)}"
    )
