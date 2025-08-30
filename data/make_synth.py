import argparse
import json
import os
import random
from typing import List, Tuple

TEMPLATES = [
    "serviceA INFO user <num> connected from <hex>",
    "serviceB WARN disk <num> nearing capacity",
    "serviceC ERROR timeout after <num> ms",
    "auth INFO login user <num> from <ip>",
]

ANOMALIES = [
    "serviceC ERROR kernel panic code <hex>",
    "serviceB CRITICAL RAID failure device <num>",
    "serviceA ALERT unauthorized root access from <hex>",
    "auth ALERT brute force attempt from <ip>",
]


def tok(s: str) -> List[str]:
    """Lowercase + whitespace split (keeps <num>/<ip>/<hex> placeholders)."""
    return s.lower().strip().split()


def generate(n: int, anom_ratio: float, seed: int) -> Tuple[List[List[str]], List[int]]:
    """
    Generate exactly k anomalies and n-k normal sequences, then shuffle.
    Returns (tokens, labels) where labels are 1 for anomaly, 0 for normal.
    """
    if n <= 0:
        return [], []

    # Clamp ratio and compute exact anomaly count
    anom_ratio = max(0.0, min(1.0, anom_ratio))
    k = int(n * anom_ratio)

    rng = random.Random(seed)

    # Sample sequences from the template pools
    normals = [tok(rng.choice(TEMPLATES)) for _ in range(n - k)]
    anoms = [tok(rng.choice(ANOMALIES)) for _ in range(k)]

    seqs = normals + anoms
    labels = [0] * (n - k) + [1] * k

    # Deterministic shuffle
    idx = list(range(n))
    rng.shuffle(idx)

    tokens_out = [seqs[i] for i in idx]
    labels_out = [labels[i] for i in idx]
    return tokens_out, labels_out


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic synthetic log generator")
    ap.add_argument("--n", type=int, default=2000, help="number of sequences")
    ap.add_argument("--anom_ratio", type=float, default=0.03, help="fraction of anomalies (0..1)")
    ap.add_argument("--seed", type=int, default=20250819, help="PRNG seed")
    ap.add_argument("--tokens_out", default="data/synth_tokens.json", help="output path for tokens JSON")
    ap.add_argument("--labels_out", default="data/synth_labels.json", help="output path for labels JSON")
    args = ap.parse_args()

    tokens, labels = generate(args.n, args.anom_ratio, args.seed)

    # Ensure output dirs exist
    for p in (args.tokens_out, args.labels_out):
        out_dir = os.path.dirname(p) or "data"
        os.makedirs(out_dir, exist_ok=True)

    # Write files (UTF-8, newline at EOF)
    with open(args.tokens_out, "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False)
        f.write("\n")
    with open(args.labels_out, "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False)
        f.write("\n")

    # Console summary
    total = len(labels)
    anoms = sum(labels)
    print(
        f"wrote: {args.tokens_out} (n={total}, anomalies={anoms}, "
        f"anom_ratio~={anoms/total if total else 0:.4f})"
    )
    print(f"wrote: {args.labels_out}")


if __name__ == "__main__":
    main()
