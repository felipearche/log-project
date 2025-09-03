# -*- coding: utf-8 -*-
from pathlib import Path
import re
import hashlib

HASHES = Path("data/HASHES.txt")


def test_hashes_format_and_crypto():
    assert HASHES.exists(), "data/HASHES.txt not found"
    lines = [ln for ln in HASHES.read_text(encoding="utf-8").splitlines() if ln.strip()]
    # exactly four lines
    assert len(lines) == 4, f"Expected 4 lines, got {len(lines)}"

    # Accept canonical 3-field or legacy 4-field with date + sha256=
    pat3 = re.compile(r"^(\S+)\s{2}(\d+)\s{2}([0-9A-F]{64})$")
    pat4 = re.compile(
        r"^\d{4}-\d{2}-\d{2}\s{2}(\S+)\s{2}(\d+)\s{2}sha256=([0-9A-F]{64})$"
    )

    expected = {
        "data/synth_tokens.json",
        "data/mini_tokens.json",
        "data/synth_labels.json",
        "data/raw/mini.log",
    }
    seen = set()

    for line in lines:
        m = pat3.match(line) or pat4.match(line)
        assert m, f"Bad line: {line!r}"
        path, size_s, sha_declared = m.groups()
        size_declared = int(size_s)

        p = Path(path)
        assert p.exists(), f"Missing file: {path}"
        data = p.read_bytes()

        assert len(data) == size_declared, (
            f"Size mismatch for {path}: actual {len(data)} vs declared {size_declared}"
        )
        sha_actual = hashlib.sha256(data).hexdigest().upper()
        assert sha_actual == sha_declared, (
            f"SHA mismatch for {path}: {sha_actual} vs {sha_declared}"
        )
        seen.add(path)

    assert seen == expected, f"Unexpected paths: {seen ^ expected}"
