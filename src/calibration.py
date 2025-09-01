"""
Sliding-window conformal calibration for streaming anomaly scores.

- Threshold targets ~1% FPR over a recent window.
- On ADWIN drift: call `calib.reset()` to clear calibration state.
- ASCII-only text to avoid encoding issues.
"""

from collections import deque
from typing import Iterable, Deque, List


class SlidingConformal:
    """
    Sliding-window inductive conformal calibrator for streaming anomaly scores.
    Maintains the last `window` scores. `threshold()` returns the
    (1-alpha) empirical quantile. Call `reset()` on drift.
    """

    def __init__(self, alpha: float = 0.01, window: int = 500):
        if not (0.0 < alpha < 1.0):
            raise ValueError("alpha must be in (0,1)")
        if window <= 0:
            raise ValueError("window must be > 0")
        self.alpha = float(alpha)
        self._buf: Deque[float] = deque(maxlen=int(window))

    def update(self, score: float) -> None:
        try:
            s = float(score)
        except Exception as e:
            raise ValueError(f"score must be float-like, got {score!r}") from e
        self._buf.append(s)

    def extend(self, scores: Iterable[float]) -> None:
        for s in scores:
            self.update(float(s))

    def reset(self) -> None:
        self._buf.clear()

    @property
    def window(self) -> int:
        return self._buf.maxlen or 0

    def threshold(self) -> float:
        n = len(self._buf)
        if n == 0:
            return float("inf")  # no anomalies until warmup filled
        # empirical quantile index (1-alpha)
        k = max(1, int(round((1.0 - self.alpha) * n)))
        arr: List[float] = sorted(self._buf)
        return arr[k - 1]
