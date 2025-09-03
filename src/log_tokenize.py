#!/usr/bin/env python3
import re
import json
import argparse
import os
from typing import List

NUM_RE = re.compile(r"\d+")
HEX_RE = re.compile(r"0x[0-9A-Fa-f]+")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def normalize_text(line: str) -> str:
    line = line.rstrip("\n").strip().lower()
    line = HEX_RE.sub("<hex>", line)
    line = IP_RE.sub("<ip>", line)
    line = NUM_RE.sub("<num>", line)
    return line


def to_sequences(in_path: str, out_path: str, max_lines: int = 200000) -> None:
    seqs: List[List[str]] = []
    with open(in_path, "r", encoding="utf-8", errors="strict") as f:
        for i, raw in enumerate(f, 1):
            if i > max_lines:
                break
            norm = normalize_text(raw)
            toks = [t for t in norm.split() if t]
            if toks:
                seqs.append(toks)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    # Protected JSONs must end without a trailing newline
    with open(out_path, "w", encoding="utf-8", newline="") as g:
        json.dump(seqs, g, ensure_ascii=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    ap.add_argument("--max_lines", type=int, default=200000)
    args = ap.parse_args()
    to_sequences(args.in_path, args.out_path, args.max_lines)
