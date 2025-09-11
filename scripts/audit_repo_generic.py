# ruff: noqa: E501
#!/usr/bin/env python3
"""
Generic repo audit (read-only). Safe to run on any project.
- Validates UTF-8 (no BOM) and LF-only across text files.
- Checks README style nits (bullets end with periods; ASCII '-'; avoid '&'; arrow ASCII fallback).
- Verifies presence & basic content of: LICENSE, CITATION.cff, .editorconfig, .gitattributes, .pre-commit-config.yaml, .github/workflows/*.yml.
- Heuristics for pinned GitHub Actions (commit SHA not version tag), cache-dependency-path, and presence of mypy/pytest/pre-commit in CI.
- If data/HASHES.txt exists, validates 3-field format lines and file existence (size+SHA-256 optional, see STRICT_HASHES).
- Warns on SVGs committed if policy is "prefer PNG".
Usage:  python scripts/audit_repo_generic.py
Exit code: 0 on success, nonzero on hard failures.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys

REPO = pathlib.Path.cwd()

STRICT_HASHES = True  # If True, verify size+SHA256; if False, only format.

BINARY_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".zip",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".mp4",
    ".mov",
    ".avi",
    ".wav",
    ".mp3",
    ".ogg",
    ".woff",
    ".woff2",
    ".ttf",
}


def is_text_file(path: pathlib.Path) -> bool:
    return path.suffix.lower() not in BINARY_EXTS


def read_bytes(p: pathlib.Path) -> bytes:
    return p.read_bytes()


def has_bom(b: bytes) -> bool:
    return b.startswith(b"\xef\xbb\xbf")


def ok(msg):
    print(f"[OK] {msg}")


def warn(msg):
    print(f"[WARN] {msg}")


def fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def check_eol_and_bom():
    bad_bom, bad_crlf = [], []
    for p in REPO.rglob("*"):
        if not p.is_file():
            continue
        if p.name.startswith(".git"):
            continue
        if not is_text_file(p):
            continue
        b = read_bytes(p)
        if has_bom(b):
            bad_bom.append(str(p))
        try:
            s = b.decode("utf-8")
        except UnicodeDecodeError as e:
            fail(f"Non-UTF8 text file: {p} ({e})")
        if "\r" in s:
            bad_crlf.append(str(p))
    if bad_bom:
        warn(f"Files with UTF-8 BOM: {len(bad_bom)} (e.g., {bad_bom[:3]})")
    else:
        ok("UTF-8 without BOM across text files.")
    if bad_crlf:
        warn(f"Files with CRLF: {len(bad_crlf)} (e.g., {bad_crlf[:3]})")
    else:
        ok("LF-only line endings across text files.")


def check_license_and_citation():
    lic = REPO / "LICENSE"
    cit = REPO / "CITATION.cff"
    if lic.exists():
        ok("LICENSE present.")
    else:
        warn("LICENSE missing.")
    if cit.exists():
        txt = cit.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^\s*version\s*:", txt, flags=re.M) and "repository-code:" in txt:
            ok("CITATION.cff has version and repository-code.")
        else:
            warn("CITATION.cff may be missing 'version:' or 'repository-code:'.")
    else:
        warn("CITATION.cff missing.")


def check_editorconfig_gitattributes():
    ec = REPO / ".editorconfig"
    ga = REPO / ".gitattributes"
    if ec.exists():
        txt = ec.read_text(encoding="utf-8", errors="replace")
        if "end_of_line" in txt and "lf" in txt:
            ok(".editorconfig enforces LF.")
        else:
            warn(".editorconfig may not enforce LF.")
        if "insert_final_newline" in txt:
            ok(".editorconfig sets insert_final_newline (verify protected files as needed).")
        else:
            warn(".editorconfig missing insert_final_newline rules (consider per-file exceptions).")
    else:
        warn(".editorconfig missing.")
    if ga.exists():
        txt = ga.read_text(encoding="utf-8", errors="replace")
        if "eol=lf" in txt:
            ok(".gitattributes sets eol=lf.")
        else:
            warn(".gitattributes missing eol=lf rules.")
        if "*.png" in txt and "binary" in txt:
            ok(".gitattributes marks PNG as binary.")
        else:
            warn("Consider marking image formats as binary in .gitattributes.")
    else:
        warn(".gitattributes missing.")


def check_precommit():
    pc = REPO / ".pre-commit-config.yaml"
    if not pc.exists():
        warn("pre-commit not configured (.pre-commit-config.yaml missing).")
        return
    txt = pc.read_text(encoding="utf-8", errors="replace")
    expected = [
        "trailing-whitespace",
        "end-of-file-fixer",
        "mixed-line-ending",
        "ruff",
        "ruff-format",
    ]
    missing = [h for h in expected if h not in txt]
    if missing:
        warn(f"pre-commit: missing hooks {missing}")
    else:
        ok("pre-commit: standard hooks present.")
    if "check_no_bom" in txt or "BOM" in txt:
        ok("pre-commit: BOM guard present.")
    else:
        warn("pre-commit: consider adding a BOM guard for UTF-8 policy.")


def check_ci():
    wf_glob = list((REPO / ".github" / "workflows").glob("*.yml"))
    if not wf_glob:
        warn("No CI workflows found under .github/workflows.")
        return
    pinned_ok = False
    cache_ok = False
    runs_ok = {"mypy": False, "pytest": False, "pre-commit": False}
    for wf in wf_glob:
        txt = wf.read_text(encoding="utf-8", errors="replace")
        # pinned actions heuristic (commit SHAs)
        if re.search(r"uses:\s*actions/[a-zA-Z0-9\-]+@([0-9a-fA-F]{6,})", txt):
            pinned_ok = True
        if "cache-dependency-path" in txt:
            cache_ok = True
        for key in runs_ok:
            if key in txt:
                runs_ok[key] = True
    ok(f"CI workflows present: {len(wf_glob)}")
    if pinned_ok:
        ok("CI: actions appear pinned by commit SHA (heuristic).")
    else:
        warn("CI: actions may not be pinned to commit SHAs.")
    if cache_ok:
        ok("CI: cache-dependency-path found for Python setup.")
    else:
        warn("CI: consider cache-dependency-path for lockfiles.")
    for k, v in runs_ok.items():
        if v:
            ok(f"CI: '{k}' appears in workflow.")
        else:
            warn(f"CI: '{k}' not detected in workflow.")


def check_hashes():
    hf = REPO / "data" / "HASHES.txt"
    if not hf.exists():
        warn("data/HASHES.txt not found (skip).")
        return
    lines = [ln for ln in hf.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    exp = re.compile(r"^(.+?)  (\d+)  ([0-9A-F]{64})$")
    for i, ln in enumerate(lines, 1):
        m = exp.match(ln)
        if not m:
            fail(f"HASHES format error on line {i} (expect 'pathâ â sizeâ â SHA256' with uppercase hex).")
        rel, size_s, hexx = m.groups()
        p = REPO / rel
        if not p.exists():
            fail(f"HASHES path does not exist: {rel}")
        if STRICT_HASHES:
            sz = p.stat().st_size
            if int(size_s) != sz:
                fail(f"Size mismatch for {rel}: {size_s} vs {sz}")
            h = hashlib.sha256(p.read_bytes()).hexdigest().upper()
            if h != hexx:
                fail(f"SHA256 mismatch for {rel}: expected {hexx}, got {h}")
    ok("data/HASHES.txt validates (format + files + sizes + SHA256).")


def check_readme_style():
    rd = REPO / "README.md"
    if not rd.exists():
        warn("README.md missing.")
        return
    txt = rd.read_text(encoding="utf-8", errors="replace")
    # Heuristics
    bullet_lines = [ln for ln in txt.splitlines() if ln.strip().startswith(("-", "*"))]
    no_period = [ln for ln in bullet_lines if not ln.rstrip().endswith((".", ":", ";", ")", "`"))]
    if no_period:
        warn(f"README: {len(no_period)} bullet(s) might not end with a period (style).")
    if "&" in txt:
        warn("README: found '&' in prose; prefer 'and'.")
    if "→" in txt and "(->" not in txt:
        warn("README: uses '→' without ASCII fallback '(->)' nearby.")
    if "—" in txt:
        ok("README: uses long dashes; ensure consistency.")
    if re.search(r"--no[_-]calib", txt):
        ok("README: mentions '--no-calib' flag.")
    # Images
    svgs = list(REPO.rglob("*.svg"))
    if svgs:
        warn(f"SVGs committed ({len(svgs)}). If your policy is 'prefer PNG', consider removing committed SVGs.")
    pngs = list(REPO.rglob("*.png"))
    if pngs:
        ok(f"PNG figures present ({len(pngs)}).")


def main():
    checks = [
        check_eol_and_bom,
        check_license_and_citation,
        check_editorconfig_gitattributes,
        check_precommit,
        check_ci,
        check_hashes,
        check_readme_style,
    ]
    for fn in checks:
        try:
            fn()
        except SystemExit:
            raise
        except Exception as e:
            fail(f"{fn.__name__} crashed: {e}")
    print("\nAll checks completed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
