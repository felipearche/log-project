# HOWTO — Figures & Provenance
_Last updated: 2025-09-08 23:22:41_

This HOWTO documents how to regenerate the **multi‑config figures** and maintain a strict **1:1 paper trail** between `experiments/summary.csv` and `docs/PROVENANCE.txt`.

---

## 1) Prerequisites
- Docker installed (or a local Python 3.11 env that matches the lockfiles).
- From repo root: `docker build -t log-project:latest .`
- Capture commit short SHA (for provenance):
  ```powershell
  $env:COMMIT = (git rev-parse --short HEAD).Trim()
  ```

---

## 2) Run the experiment grid (2×2 × calibration = 8 rows)
The commands below append **one** row per run to `experiments/summary.csv` and **one** block to `docs/PROVENANCE.txt`.

### Baseline — calibrated (Sliding Conformal @ 1% FPR)
```powershell
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode baseline --data data/synth_tokens.json --labels data/synth_labels.json

docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode baseline --data data/mini_tokens.json
```

### Baseline — no‑calib (ablation)
```powershell
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode baseline --data data/synth_tokens.json --labels data/synth_labels.json --no-calib

docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode baseline --data data/mini_tokens.json --no-calib
```

### Transformer — calibrated
```powershell
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode transformer --data data/synth_tokens.json --labels data/synth_labels.json

docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode transformer --data data/mini_tokens.json
```

### Transformer — no‑calib (ablation)
```powershell
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode transformer --data data/synth_tokens.json --labels data/synth_labels.json --no-calib

docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode transformer --data data/mini_tokens.json --no-calib
```

**Sanity check (rows):**
```powershell
$rows = (Get-Content .\experiments\summary.csv | Select-Object -Skip 1).Count
"Rows (excluding header): $rows"   # expect â‰¥ 8
```

---

## 3) Generate the multi‑config figures
The repository provides a duplicate‑aware, ruff‑clean plotter: `scripts/make_multi_plots_v2.py`.

### Calibrated‑only (recommended for README)
```powershell
python scripts\make_multi_plots_v2.py --csv experiments\summary.csv --outdir figures --fmt png,svg --calibrations conformal --expect 4
```

### Full ablation set (calibrated + no‑calib)
```powershell
python scripts\make_multi_plots_v2.py --csv experiments\summary.csv --outdir figuresblations --fmt png,svg --expect 8
```

**Notes**
- Collapses duplicate (dataset, mode, calibration) combos (default: **last**) â†’ use `--collapse median` to aggregate repeats.
- Drops rows with `p95_ms==0` or `p99_ms==0` by default â†’ pass `--no-drop-zero-latency` to keep them.
- X‑labels are `dataset` on line 1 and `mode/calibration` on line 2.
- Output files: `figures/latency_p95_ms.(png|svg)`, `figures/latency_p99_ms.(png|svg)`, `figures/throughput_eps.(png|svg)`.

---

## 4) Rebuild provenance strictly from CSV
If in doubt, rebuild the file to guarantee **1:1** mapping and exact `CSV_ROW:` capture.

```powershell
# Bypass policy for this run only, and rebuild
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts
ebuild_provenance.ps1 `
  -CsvPath experiments\summary.csv `
  -OutPath docs\PROVENANCE.txt
```

**Verify counts:**
```powershell
$csvRows = (Get-Content .\experiments\summary.csv | Select-Object -Skip 1).Count
$provRows = (Select-String -Path .\docs\PROVENANCE.txt -SimpleMatch 'CSV_ROW:').Count
"CSV rows: $csvRows ; PROVENANCE CSV_ROW: $provRows"
```

---

## 5) Commit workflow
```powershell
pre-commit run -a
mypy src
pytest -q

git add experiments\summary.csv figures\ docs\ scriptsgit commit -m "experiments: add full grid; figures: multi-config; provenance: rebuild 1:1"
git push
```

---

## 6) Troubleshooting
- **PowerShell policy**: use `-ExecutionPolicy Bypass` or `Set-ExecutionPolicy -Scope Process Bypass` for one-shot runs; `Unblock-File` if needed.
- **SVGs modified by hooks**: run `git add -A` then `pre-commit run -a` again (hooks normalize line endings/whitespace).
- **Mixed OS environments**: prefer LF line endings; the repo enforces UTF‑8 (no BOM), LF‑only.
