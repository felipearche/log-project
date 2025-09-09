#!/usr/bin/env python3
import hashlib
import os

FILES = [
    "data/synth_tokens.json",
    "data/mini_tokens.json",
    "data/synth_labels.json",
    "data/raw/mini.log",
]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> None:
    lines = []
    for p in FILES:
        size = os.path.getsize(p)
        digest = sha256(p)
        # Canonical 3-field format: path␠␠size␠␠SHA256 (uppercase), LF
        lines.append(f"{p}  {size}  {digest}")
    data = "\n".join(lines) + "\n"
    os.makedirs("data", exist_ok=True)
    with open("data/HASHES.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    print("Wrote data/HASHES.txt (3-field canonical format)")


if __name__ == "__main__":
    main()
