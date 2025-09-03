#!/usr/bin/env python3
import sys
from pathlib import Path

BOM = b"\xef\xbb\xbf"


def has_bom(path: Path) -> bool:
    try:
        b = path.read_bytes()
    except Exception:
        return False
    return b.startswith(BOM)


def main(argv: list[str]) -> int:
    bad: list[str] = []
    for arg in argv[1:]:
        p = Path(arg)
        if p.is_file() and has_bom(p):
            bad.append(str(p))
    if bad:
        sys.stderr.write("UTF-8 BOM detected in:\n" + "\n".join(bad) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
