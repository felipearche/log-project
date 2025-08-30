# metrics

* TPR@1%FPR: True Positive Rate at a threshold chosen to target FPR~0.01 via the calibrator.
* p95\_ms: 95th percentile of scoring latency (model call only), not including sleep or file I/O.
* eps: events per second = total\_events / wall\_clock\_seconds (full loop).
* CPU\_pct, energy\_J: currently NA; will populate if/when we add psutil/energy meter.
* warmup: events ignored while buffers fill.
* Drift: ADWIN (delta recorded per row); on drift, we reset calibration.
* Determinism: PYTHONHASHSEED set in shell before runs when applicable.
