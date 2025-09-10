# ruff: noqa: E501
#!/usr/bin/env python3
"""
Audit the repository for provenance, hygiene, and reproducibility guarantees.
- Header-aware CSV vs PROVENANCE check
- Typing: fail() -> NoReturn; regex match assertions for mypy
Run from repo root:  python scripts/audit_repo.py
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import pathlib
import re
import sys
from typing import NoReturn

REPO_ROOT = pathlib.Path.cwd()

# Policy
PROTECTED_JSONS = [
    "data/mini_tokens.json",
    "data/synth_labels.json",
    "data/synth_tokens.json",
]
HASHES_FILE = "data/HASHES.txt"
SUMMARY_CSV = "experiments/summary.csv"
PROVENANCE = "docs/PROVENANCE.txt"
CITATION = "CITATION.cff"
EDITORCONFIG = ".editorconfig"
GITATTR = ".gitattributes"
CI_YML = ".github/workflows/ci.yml"
PRECOMMIT = ".pre-commit-config.yaml"


def fail(msg: str) -> NoReturn:
    print(f"[FAIL] {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def path(p: str) -> pathlib.Path:
    return REPO_ROOT / p


def read_bytes(p: pathlib.Path) -> bytes:
    try:
        return p.read_bytes()
    except FileNotFoundError:
        fail(f"Missing file: {p}")


def has_bom(b: bytes) -> bool:
    return b.startswith(b"\xef\xbb\xbf")


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def detect_summary_header(rows: list[list[str]]) -> int:
    """Return the index of the first data row (0 if no header)."""
    if not rows:
        return 0
    header = rows[0]
    header_text = ",".join([c.strip().lower() for c in header])
    header_like = any(
        k in header_text
        for k in [
            "dataset",
            "mode",
            "calibration",
            "tpr_at_1pct_fpr",
            "commit",
            "run_id",
            "timestamp",
        ]
    )
    nonnum = 0
    for c in header:
        s = c.strip()
        if not s:
            nonnum += 1
            continue
        try:
            float(s)
        except ValueError:
            nonnum += 1
    if header_like or nonnum >= max(3, len(header) // 2):
        return 1
    return 0


def count_summary_data_rows() -> int:
    p = path(SUMMARY_CSV)
    b = read_bytes(p)
    if has_bom(b):
        fail("experiments/summary.csv has a BOM.")
    txt = b.decode("utf-8")
    rdr = csv.reader(io.StringIO(txt))
    rows = list(rdr)
    if not rows:
        fail("experiments/summary.csv is empty.")
    start_idx = detect_summary_header(rows)
    return max(0, len(rows) - start_idx)


def check_protected_jsons() -> None:
    for rel in PROTECTED_JSONS:
        f = path(rel)
        b = read_bytes(f)
        if has_bom(b):
            fail(f"{rel} has a UTF-8 BOM; must be UTF-8 without BOM.")
        try:
            json.loads(b.decode("utf-8"))
        except Exception as e:
            fail(f"{rel} is not valid JSON: {e}")
        if len(b) == 0 or b[-1] in (0x0A, 0x0D):
            fail(f"{rel} must NOT end with a newline (byte-exact policy).")
    ok("Protected JSONs: valid UTF-8 (no BOM), valid JSON, and no final newline.")


def check_hashes() -> None:
    p = path(HASHES_FILE)
    b = read_bytes(p)
    if has_bom(b):
        fail("data/HASHES.txt has a BOM.")
    text = b.decode("utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        fail("data/HASHES.txt is empty.")
    exp_three_fields = re.compile(r"^(.+?)  (\d+)  ([0-9A-F]{64})$")
    for i, ln in enumerate(lines, 1):
        m = exp_three_fields.match(ln)
        if not m:
            fail(f"HASHES format error on line {i}: expected 'pathÃ¢ÂÂ Ã¢ÂÂ sizeÃ¢ÂÂ Ã¢ÂÂ SHA256' with uppercase hex.")
        assert m is not None
        rel_path, size_s, hexx = m.groups()
        f = path(rel_path)
        if not f.exists():
            fail(f"HASHES path does not exist: {rel_path}")
        size = int(size_s)
        stat_size = f.stat().st_size
        if size != stat_size:
            fail(f"Size mismatch for {rel_path}: expected {size}, actual {stat_size}.")
        calc = sha256_file(f)
        if calc != hexx:
            fail(f"SHA256 mismatch for {rel_path}: expected {hexx}, actual {calc}.")
    ok("data/HASHES.txt: three-field, uppercase SHA-256, sizes and digests match.")


def check_summary_csv() -> None:
    p = path(SUMMARY_CSV)
    b = read_bytes(p)
    if has_bom(b):
        fail("experiments/summary.csv has a BOM.")
    txt = b.decode("utf-8")
    rdr = csv.reader(io.StringIO(txt))
    rows = list(rdr)
    if not rows:
        fail("experiments/summary.csv is empty.")
    start_idx = detect_summary_header(rows)
    for i, row in enumerate(rows[start_idx:], start_idx + 1):
        if len(row) != 24:
            fail(f"Row {i} in experiments/summary.csv does not have 24 columns (has {len(row)}).")
    ok("experiments/summary.csv: 24 columns per data row.")


def check_provenance_blocks() -> None:
    data_rows = count_summary_data_rows()
    p = path(PROVENANCE)
    b = read_bytes(p)
    if has_bom(b):
        fail("docs/PROVENANCE.txt has a BOM.")
    txt = b.decode("utf-8")
    blocks = len(re.findall(r"^CSV_ROW:", txt, flags=re.M))
    if data_rows and blocks < data_rows:
        fail(f"docs/PROVENANCE.txt: found {blocks} CSV_ROW blocks, but {data_rows} data rows in summary.")
    ok(f"docs/PROVENANCE.txt: CSV_ROW blocks present (>= {data_rows} data rows).")


def check_editorconfig() -> None:
    p = path(EDITORCONFIG)
    txt = read_bytes(p).decode("utf-8")
    if "insert_final_newline = false" not in txt and "insert_final_newline=false" not in txt:
        warn(".editorconfig: missing insert_final_newline=false for protected JSONs.")
    if "end_of_line = lf" not in txt and "end_of_line=lf" not in txt:
        warn(".editorconfig: missing end_of_line=lf (LF-only policy).")
    ok(".editorconfig present.")


def check_gitattributes() -> None:
    p = path(GITATTR)
    txt = read_bytes(p).decode("utf-8")
    if "eol=lf" not in txt:
        warn(".gitattributes: missing eol=lf rule(s).")
    ok(".gitattributes present.")


def check_citation() -> None:
    p = path(CITATION)
    txt = read_bytes(p).decode("utf-8")
    if "repository-code:" not in txt:
        fail("CITATION.cff missing 'repository-code:'")
    if re.search(r"^\s*version\s*:", txt, flags=re.M) is None:
        fail("CITATION.cff missing 'version:'")
    ok("CITATION.cff includes repository-code and version.")


def check_ci() -> None:
    p = path(CI_YML)
    txt = read_bytes(p).decode("utf-8")
    if not re.search(r"uses:\s*actions/checkout@([0-9a-fA-F]{6,})", txt):
        warn("CI: actions/checkout may not be pinned to a commit SHA.")
    if not re.search(r"uses:\s*actions/setup-python@([0-9a-fA-F]{6,})", txt):
        warn("CI: actions/setup-python may not be pinned to a commit SHA.")
    if "cache-dependency-path" not in txt:
        warn("CI: actions/setup-python is missing cache-dependency-path for lockfiles.")
    if "mypy" not in txt:
        warn("CI: mypy not detected.")
    if "pytest" not in txt:
        warn("CI: pytest not detected.")
    ok("CI workflow present.")


def check_precommit() -> None:
    p = path(PRECOMMIT)
    txt = read_bytes(p).decode("utf-8")
    expected = [
        "trailing-whitespace",
        "end-of-file-fixer",
        "mixed-line-ending",
        "ruff",
        "ruff-format",
    ]
    for rule in expected:
        if rule not in txt:
            warn(f"pre-commit: missing hook '{rule}'.")
    if "check_no_bom.py" not in txt and "BOM" not in txt:
        warn("pre-commit: BOM guard not found (UTF-8 no BOM policy).")
    ok(".pre-commit-config.yaml present.")


def check_figures() -> None:
    figs = [
        "figures/latency_p95_ms.png",
        "figures/latency_p99_ms.png",
        "figures/throughput_eps.png",
    ]
    missing = [f for f in figs if not path(f).exists()]
    if missing:
        warn("Figures not found: " + ", ".join(missing))
    else:
        ok("Figures present (PNG).")


def main() -> None:
    checks = [
        check_protected_jsons,
        check_hashes,
        check_summary_csv,
        check_provenance_blocks,
        check_editorconfig,
        check_gitattributes,
        check_citation,
        check_ci,
        check_precommit,
        check_figures,
    ]
    for fn in checks:
        try:
            fn()
        except SystemExit:
            raise
        except Exception as e:
            fail(f"{fn.__name__} crashed: {e}")
    print("\nAll checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
