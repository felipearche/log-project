# src/transformer.py
# UTF-8 (no BOM), LF line endings, trailing newline

from __future__ import annotations

from typing import Iterable, List, Deque
from collections import deque
import hashlib
import math

import numpy as np


__all__ = ["TransformerScorer"]


class TransformerScorer:
    """
    CPU-only micro-transformer-style scorer for streaming anomaly detection.

    Design goals
    ------------
    - Deterministic: results depend only on inputs + seed (20250819 default).
    - Edge-feasible: pure NumPy, no heavy DL deps or GPU needed.
    - Streaming: maintains a causal context of the last `window` token embeddings.
    - Orientation: higher raw score => more anomalous (compatible with SlidingConformal at 1% FPR).
    - Resettable: call `reset()` on ADWIN-detected drift.

    Scoring
    -------
    1) Build a context vector as an exponentially-decayed mean of prior token embeddings.
    2) For the current line's tokens, compute cosine distance (1 - cos_sim) to the context.
    3) Return the mean distance in [0, 1] (clamped). Update context AFTER scoring.

    Inputs
    ------
    - tokens: iterable of pre-tokenized strings (lowercase; mask <num>/<ip>/<hex>).
      Empty token lists return 0.0.
    """

    def __init__(
        self,
        embed_dim: int = 32,
        window: int = 32,
        decay: float = 0.90,
        seed: int = 20250819,
    ) -> None:
        if not isinstance(embed_dim, int) or embed_dim <= 0:
            raise ValueError("embed_dim must be a positive integer")
        if not isinstance(window, int) or window <= 0:
            raise ValueError("window must be a positive integer")
        if not (0.0 < float(decay) < 1.0):
            raise ValueError("decay must be in (0,1)")
        self.embed_dim = int(embed_dim)
        self.window = int(window)
        self.decay = float(decay)
        self.seed = int(seed)
        self._buf: Deque[np.ndarray] = deque(maxlen=self.window)

    # ---- Public API (used by stream.py) ------------------------------------

    def reset(self) -> None:
        """Clear all contextual state (call this on ADWIN drift)."""
        self._buf.clear()

    def score_and_update(self, tokens: Iterable[str]) -> float:
        """
        Compute raw anomaly score for a line (higher = more anomalous),
        then update the internal context with the line's tokens.
        """
        toks = list(tokens) if tokens is not None else []
        score = self._score(toks)
        for t in toks:
            self._buf.append(self._embed(t))
        return float(score)

    # ---- Internals ----------------------------------------------------------

    def _score(self, tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        if not self._buf:
            # No context yet -> neutral score (avoid cold-start spikes).
            return 0.0

        ctx = self._context_vector()
        dists = []
        for tok in tokens:
            e = self._embed(tok)
            sim = float(np.dot(ctx, e))  # in [-1, 1]
            if sim > 1.0:
                sim = 1.0
            elif sim < -1.0:
                sim = -1.0
            d = 1.0 - sim  # 0 identical .. 2 opposite
            dists.append(d)

        # Mean distance; clamp to [0,1] for stability.
        score = float(np.mean(dists))
        if not math.isfinite(score):
            score = 0.0
        return max(0.0, min(1.0, score))

    def _context_vector(self) -> np.ndarray:
        """
        Exponentially decayed mean over the buffer (more recent => higher weight).
        """
        n = len(self._buf)
        if n == 0:
            return self._unit(np.zeros(self.embed_dim, dtype=np.float32))
        # Right side of deque is most recent; assign ages 1..n (oldest->newest)
        weights = np.array(
            [self.decay ** (n - i) for i in range(1, n + 1)], dtype=np.float32
        )
        weights_sum = float(weights.sum())
        if weights_sum <= 0.0 or not math.isfinite(weights_sum):
            weights = np.ones(n, dtype=np.float32) / float(n)
        else:
            weights /= weights_sum
        stacked = np.stack(list(self._buf), axis=0)  # [n, D]
        ctx = (weights[:, None] * stacked).sum(axis=0)
        return self._unit(ctx)

    def _embed(self, token: str) -> np.ndarray:
        """
        Deterministic per-token embedding derived from SHA-256 (no global vocab).
        """
        # Stable 64-bit seed from token + base seed ensures reproducibility.
        h = hashlib.sha256((token + "::" + str(self.seed)).encode("utf-8")).digest()
        subseed = int.from_bytes(h[:8], "big", signed=False)
        rng = np.random.default_rng(subseed)
        v = rng.standard_normal(self.embed_dim, dtype=np.float32)
        return self._unit(v)

    @staticmethod
    def _unit(v: np.ndarray) -> np.ndarray:
        n = float(np.linalg.norm(v))
        if n <= 0.0 or not math.isfinite(n):
            return np.zeros_like(v, dtype=np.float32)
        return (v / n).astype(np.float32)
