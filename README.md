# log-project  Streaming, Drift-Aware Log Anomaly Detection (Calibrated, Reproducible)

## 0) Overview
A real-time log anomaly detector that:
1) scores each log line with a lightweight baseline (**TF-IDF + IsolationForest**),
2) enforces a target false-positive rate via **Sliding Conformal** (inductive, windowed), and
3) adapts to **drift** using **ADWIN** and **resets the calibrator on detected changes**.

Every run appends **one canonical row** to `experiments/summary.csv` (24-column schema).
Reproducibility pillars: **pinned environment** (`env/requirements.lock`), **Docker parity**, **commit capture** (`COMMIT` env`git` short SHA`NA` fallback), **UTF-8/LF policy**, and **strict provenance** (one block per CSV row).

> Portability: always mount with `-v "${PWD}:/app"` (quoted) so it works even if your path contains spaces.
> TPR formatting: for new rows, record `TPR_at_1pct_FPR` with **four decimals** (e.g., `1.0000`); leave older rows unchanged; use **literal `NA`** for unlabeled datasets.

---

## 1) Quick reproduce (4 commands)

```powershell
# 1) Build the image from this folder
docker build -t log-project:latest .

# 2) Capture commit for results
$env:COMMIT = (git rev-parse --short HEAD).Trim()

# 3) Run the default pipeline (baseline, calibrated)
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest

# 4) Generate figures + README table (inside Docker for deps parity)
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python scripts/make_plots.py --summary experiments/summary.csv
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python scripts/make_readme_table.py --csv experiments/summary.csv --out README_TABLE.txt
```

Output: one new row in `experiments/summary.csv` + one provenance block in `docs/PROVENANCE.txt`.

> Optional: also generate vector figures for docs/slides: add `--svg` to `make_plots.py`. Prefer **PNG** in the repo; generate SVGs on demand (dont commit).

---

## 2) Experiment grid (2x2)

```powershell
$env:COMMIT = (git rev-parse --short HEAD).Trim()

# Calibrated (Sliding Conformal @ 1% target FPR)
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode baseline --data data/synth_tokens.json --labels data/synth_labels.json
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode baseline --data data/mini_tokens.json

# No-calib ablation (fixed threshold)
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode baseline --data data/synth_tokens.json --labels data/synth_labels.json --no_calib
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode baseline --data data/mini_tokens.json --no_calib
```

Each command emits exactly one `CSV_ROW:` and a matching provenance block.

---
### Transformer 22 (adds 4 rows)

```powershell
$env:COMMIT = (git rev-parse --short HEAD).Trim()

# Calibrated (Sliding Conformal @ 1% target FPR)
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode transformer --data data/synth_tokens.json --labels data/synth_labels.json
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode transformer --data data/mini_tokens.json

# No-calib ablation (fixed threshold)
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode transformer --data data/synth_tokens.json --labels data/synth_labels.json --no_calib
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python -m src.stream --mode transformer --data data/mini_tokens.json --no_calib
```

## 3) Results

### 3.1 Table
- Canonical table file: `README_TABLE.txt` (generated below).

```powershell
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python scripts/make_readme_table.py --csv experiments/summary.csv --out README_TABLE.txt

# (Optional) normalize 'nan'  'NA' if any appear in the Markdown table output
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$content   = (Get-Content README_TABLE.txt -Raw) -replace '\bnan\b','NA'
[IO.File]::WriteAllText('README_TABLE.txt', $content + "`n", $utf8NoBom)
```

> The generator shows the **latest row per (dataset, mode, calibration)**. TPR is formatted to **4 decimals**; p95/p99/eps to **1 decimal**; any textual `nan` is rendered as **NA**.

### 3.2 Figures

```powershell
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python scripts/make_plots.py --summary experiments/summary.csv
```

Embed examples (the plotting script writes to `figures/`):
```markdown
![Latency p95](figures/latency_p95_ms.png)
![Latency p99](figures/latency_p99_ms.png)
![Throughput (eps)](figures/throughput_eps.png)
```

**Takeaway:** Sliding Conformal at 1% target FPR yields higher, stable TPR at the same FPR; ADWIN resets maintain alignment under drift.

---

## 4) Datasets & hashes (canonical)
Track every dataset in three places:

1. Tokenized logs live in `data/*.json`. See **`docs/DATASETS.md`** for schema, sizes, counts, and SHA-256.
2. **Policy:** `data/HASHES.txt` lists `YYYY-MM-DD  data/<path>  <bytes>  sha256=<HEX>` for each tracked artifact (UTF-8 **no BOM**, **LF**). Exactly **4 entries** are expected.
3. `docs/PROVENANCE.txt`  one block per run, containing the **verbatim** `CSV_ROW:`.

- **Scope clarification (2025-09-03):** `data/` now contains **artifact data only**.
  Non-artifacts were relocated (`data/make_synth.py``scripts/`, `data/PROVENANCE.txt``docs/PROVENANCE.txt`, `data/DATASETS.md``docs/DATASETS.md`). `data/HASHES.txt` covers only artifact JSON/log files; docs/scripts are excluded.

**Regenerate hashes (preferred):**
```powershell
docker run --rm -v "${PWD}:/app" log-project:latest python scripts/hash_files.py
```

**Example entries (update if files change):**
```
2025-08-29  data/synth_tokens.json  137400  sha256=8AF36305BB4FA61486322BFAFE148F6481C7FF1772C081F3E9590FB5C79E6600
2025-08-29  data/mini_tokens.json  533  sha256=3CA2BCE42228159B81E5B2255B6BC352819B22FFA74BBD4F78AC82F00A2E1263
2025-08-29  data/synth_labels.json  6000  sha256=814DA8A6BAB57EC08702DDC0EFFAC7AFDC88868B4C2EE4C6087C735FB22EDADA
2025-08-29  data/raw/mini.log  310  sha256=F5953777A9A84819D55964E5772792CE8819A3FED1E0365FA279EB53F6496FB4
```

---

## 5) Provenance policy (strict)

### Format-only maintenance (history)

We enforce a 1:1 mapping between rows in `experiments/summary.csv` and blocks in `docs/PROVENANCE.txt`.

Each block includes: ISO date, commit short SHA, seed, input dataset, exact Docker command (with `--labels` for `synth_tokens` and `--no_calib` for ablations), and the **full `CSV_ROW:`**. All text files are **UTF-8 (no BOM)** with **LF** line endings.

**Rebuild provenance:**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\scripts\rebuild_provenance.ps1
type .\docs\PROVENANCE.txt
```

**Verify 1:1 mapping (strict):**
```powershell
$rows = (Get-Content experiments\summary.csv | Measure-Object -Line).Lines - 1
$provCsvRows = (Select-String -Path docs\PROVENANCE.txt -Pattern '^CSV_ROW:' | Measure-Object).Count
if ($rows -ne $provCsvRows) { throw "Provenance mismatch: CSV=$rows PROVENANCE=$provCsvRows" }
```

**CI checks:** equal counts (rows vs blocks), quoted mount path (`-v "${PWD}:/app"`), `CSV_ROW:` exactness (uppercase label), single trailing newline.

---

## 6) Canonical results schema (24 columns)
Policy: no blank cellsuse `NA` when not applicable. `TPR_at_1pct_FPR` is numeric for labeled datasets and the literal `NA` for unlabeled.

Header (first line of `experiments/summary.csv`):
```
date,commit,dataset,mode,calibration,drift_detector,seed,events,anomalies,drifts,TPR_at_1pct_FPR,p95_ms,p99_ms,eps,CPU_pct,energy_J,calib_target_fpr,calib_window,warmup,adwin_delta,iso_n_estimators,iso_max_samples,iso_random_state,notes
```
- `energy_J` is **NA** on this hardware.
- **Formatting policy:** for new rows, prefer fixed-point **4 decimals** for TPR (e.g., `1.0000`); do **not** rewrite previous rows.
- `notes` may include: `baseline conformal;cpu_sampler=process_avg;energy_na`.

---

- **Note:** When `mode=transformer`, `iso_n_estimators`, `iso_max_samples`, and `iso_random_state` are recorded as **NA**.

## 7) Running the pipeline (CLI)
**Flags (most common):**
```
--data PATH                  # tokens JSON
--labels PATH                # optional labels JSON for TPR metric
--alpha 0.01      # default 1% (alpha)
--window 5000          # sliding window size
--warmup 200                 # warmup events
--no_calib                   # disable conformal (ablation)
--adwin-delta 0.002          # drift sensitivity
--save-scores PATH           # per-event scores CSV (optional)
--summary-out experiments/summary.csv
--seed 20250819
--sleep_ms 0
```
**Drift handling:** On ADWIN change  increment drift count, call `calib.reset()`, continue.
For unlabeled datasets, `TPR_at_1pct_FPR` is the literal `NA`. CPU metric: `CPU_pct` is the mean **process** CPU%.

---

## 8) Tokenizer (deterministic)
- Lowercase
- Special tokens: `<hex>` (`0x[0-9A-Fa-f]+`), `<ip>` (IPv4), `<num>` (`\d+`)
- Encoding: **UTF-8 (no BOM)**; input logs and token JSON are UTF-8.

Recreate tokens from raw:
```powershell
docker run --rm -v "${PWD}:/app" log-project:latest `
  python src/log_tokenize.py --in data/raw/mini.log --out data/mini_tokens.json
```

---

## 9) Determinism & seeds
- Canonical seed: **20250819** (experiments + synthesis).
- Python hashing determinism (optional):
```powershell
$env:PYTHONHASHSEED = "0"
```
- Two identical commands should yield identical `CSV_ROW` values except timestamp/commit.

---

## 10) Environment & build (pinned)
- `env/requirements.lock` pins exact versions (e.g., `numpy 1.26.4`, `scipy 1.16.1`, `scikit-learn 1.5.2`, `psutil 7.0.0`, `matplotlib`, etc.).
- Dockerfile installs only from the lockfile; `CMD` runs the default pipeline.

Record actual versions from the built image:
```powershell
docker run --rm -v "${PWD}:/app" log-project:latest `
  python scripts/print_versions.py
```

---

## 11) Encoding & EOL policy

- All tracked text files are **UTF-8 (no BOM)** with **LF** line endings, and each file ends with a **single trailing newline**.
- Enforced by the checked-in **`.gitattributes`** (authoritative). An `.editorconfig` is **optional** and may be added locally as an editor hint.
- Repo can be normalized with `git add --renormalize .` after setting the policy.

`.gitattributes` (excerpt):
```
* text=auto eol=lf
*.png binary
data/synth_tokens.json -text
data/mini_tokens.json  -text
data/synth_labels.json -text
data/raw/mini.log     -text
```

**Normalize now (one-time):**
```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/normalize_line_endings.ps1 -Path .
```

**Ignores for reproducibility:**
```
.venv/
__pycache__/
.pytest_cache/
experiments/logs/
_audited/
fsck.txt
*.bak
```

---

## 12) Testing
Covers:
- Tokenizer masking and lowercase
- Summary schema (24 columns; p95_ms  p99_ms)
- Calibration docs / ASCII
- Drift  conformal reset (smoke)
- Determinism (smoke)

```powershell
docker build -t log-project:latest .
docker run --rm -v "${PWD}:/app" log-project:latest `
  sh -lc 'python -m pip install --quiet pytest==8.3.3 && python -m pytest -q'
```

**Local venv (Windows):**
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r env/requirements.lock
python -m pip install pytest==8.3.3
python -m pytest -q
```

---

## 13) Release (tag + zip + hashes + provenance)

**Note:** Release zips must exclude **.venv/**, **experiments/logs/**, **.pytest_cache/**, **__pycache__/**, and the **.git/** folder.

**Use the script (Windows / PowerShell):**
```powershell
# Create the release zip + write dist/HASHES.txt and dist/PROVENANCE.txt
pwsh -NoProfile -File .\scripts\make_release.ps1

# Verify contents and hashes
Get-ChildItem -Recurse release\ | Select-Object FullName,Length
Get-Content release\HASHES.txt
Get-Content release\PROVENANCE.txt
```

**Policy:** Model artifacts and release hashes/provenance live under `dist/`.
Do **not** add model files or release hashes to `data/HASHES.txt` (that file must list only the four canonical data artifacts).

---

## 14) Fresh-clone reproducibility check
```powershell
cd ..
git clone https://github.com/felipearche/log-project log-project-fresh
cd log-project-fresh
docker build -t log-project:latest .
$env:COMMIT = (git rev-parse --short HEAD).Trim()
docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest
```

Verify: one new CSV row + matching provenance block.

---

## 15) Metrics (definitions)
- **TPR_at_1pct_FPR**  TPR computed at the score threshold set by the 99th percentile of negatives (target FPR=1%).
- **p95_ms**, **p99_ms**  end-to-end per-event latency percentiles.
- **eps**  throughput, events per second.
- **CPU_pct**  process average CPU% during the run.
- **drifts**  ADWIN change detections (each triggers `calib.reset()`).

---

## 16) Motivation & impact
- **Reliability under drift:** Sliding Conformal + ADWIN maintain a stable operating point (1% FPR) in streaming settings.
- **Systems + ML:** We report latency (p95/p99), throughput (eps), and CPU% to demonstrate edge feasibility.
- **Reproducibility culture:** Docker, pinned env, dataset hashes, strict provenance, and encoding/EOL policy.

---

## 17) System & benchmark environment (recorded)
(Example capture; see `experiments/environment_snapshot.md` in this repo for the current machine.)

**CPU**
AMD Ryzen 7 5800HS with Radeon Graphics  8 cores / 16 threads

**Memory**
TotalPhysicalMemoryBytes15.41 GB

**OS**
Windows 11 Home (build 26100)

**Docker**
Client: 28.3.2  Server: 28.3.2  Docker Desktop 4.44.3

**Image Python/libs**
python==3.11.9; numpy==1.26.4; scikit-learn==1.5.2; matplotlib==3.9.2; psutil==7.0.0; scipy==1.16.1

> Note: All throughput/latency numbers in this README were measured on the above machine unless noted.

---

## 18) Data ethics & privacy

- Logs can contain sensitive data (PII, secrets). The tokenizer masks `0x` (as `<hex>`), IPv4 addresses (`<ip>`), and integers (`\d+`), but **this is not a full PII scrubber**.
- Before committing new datasets:
  - Remove or redact user identifiers, secrets/keys, tokens.
  - Prefer synthetic or anonymized logs for public sharing.
  - Document any remaining sensitive fields in `docs/DATASETS.md`.

---

## 19) Extending the project

**Add a dataset**
1. Place tokenized JSON in `data/NAME_tokens.json`. Optional labels: `data/NAME_labels.json`.
2. Update hashes: `docker run --rm -v "${PWD}:/app" log-project:latest python scripts/hash_files.py` (commits `data/HASHES.txt`).
3. Run the pipeline and commit the new summary/provenance.

**Add a model/detector**
1. Implement under `src/` (e.g., `src/detectors/my_detector.py`).
2. Register CLI options in `src/stream.py`.
3. Include any new hyperparams in the summary CSV and provenance block.
4. Add tests in `tests/` and update Â§7 flags if needed.

**Add a drift detector**
- Ensure a **reset hook** is called to flush conformal history on drift.

---

## 20) CI suggestion (GitHub Actions)

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - run: docker build -t log-project:latest .
      - run: docker run --rm -v "${{ github.workspace }}:/app" log-project:latest \
               sh -lc 'python -m pip install --quiet pytest==8.3.3 && python -m pytest -q'
      - run: docker run --rm -v "${{ github.workspace }}:/app" log-project:latest \
               python - << 'PY'
import csv, sys
expected = ["date","commit","dataset","mode","calibration","drift_detector","seed","events","anomalies","drifts","TPR_at_1pct_FPR","p95_ms","p99_ms","eps","CPU_pct","energy_J","calib_target_fpr","calib_window","warmup","adwin_delta","iso_n_estimators","iso_max_samples","iso_random_state","notes"]
with open("experiments/summary.csv", newline="", encoding="utf-8") as f:
    r = csv.reader(f)
    hdr = next(r, [])
    if hdr != expected:
        print("Header mismatch:", hdr, file=sys.stderr)
        sys.exit(1)
print("summary.csv header OK")
PY
```

---

## 21) Troubleshooting

- **Plots script expects only `summary.csv`:** If you see references to `--scores`, update to the latest `scripts/make_plots.py` (figures are derived from `experiments/summary.csv` only).
- **`AttributeError: 'SlidingConformal' object has no attribute 'size'`:** Update to the latest code (the calibrator implements `size()` for compatibility with `src/stream.py`).

Other common issues:
- **Docker mount issues on Windows**  Always quote the mount: `-v "${PWD}:/app"`.
- **Table shows `nan`**  Regenerate the table (see Â§3.1); the generator renders textual `nan` as `NA`.
- **TPR formatting varies (`1` vs `1.0000`)**  Use `scripts/normalize_tpr_lastrow.py` after runs; dont rewrite historical rows.
- **CRLF vs LF / missing final newline**  `scripts/normalize_line_endings.ps1` fixes this across the repo.
- **PowerShell 5.1 vs 7**  Scripts are 5.1-compatible; prefer **pwsh 7+** for consistency.

---

## 22) License & citation

This project is licensed under the **MIT License**. See [LICENSE](LICENSE).

**How to cite:**
Felipe Arche. *log-project: Streaming, Drift-Aware Log Anomaly Detection (Calibrated, Reproducible).* 2025. Git repository.

See also `CITATION.cff` for a machine-readable citation.

### Repository link
- Replace every `https://github.com/felipearche/log-project` with your **actual** HTTPS repo URL.
- Set the same URL in `CITATION.cff`:
```yaml
repository-code: https://github.com/felipearche/log-project
```

---

## Maintenance summaries (latest)

- **2025-08-31**: Encoding/EOL compliance - Added a single trailing LF to `scripts/make_release.ps1` to conform to the repo policy (UTF8 no BOM, LF, single trailing newline). See Â§11 for the policy and normalization script.; CPU_pct backfill (historic) - Backfilled two early `CPU_pct` blanks to the literal `NA` in `experiments/summary.csv` for full-column coverage and clarity. Immediately rebuilt `docs/PROVENANCE.txt` to preserve the strict 1:1 mapping with `CSV_ROW:` lines (postcheck: CSV rows=26; PROVENANCE CSV_ROW=26).; Tests - Post-change test suite: 4 passed.
- **2025-08-30**: TPR formatting policy enforced - `TPR_at_1pct_FPR` is four decimals for `synth_tokens` (e.g., `1.0000`) and the literal `NA` for `mini_tokens`. See the experiment schema and the table generator script.; Provenance 1:1 rebuilt - `docs/PROVENANCE.txt` now has exactly one `CSV_ROW:` per row in `experiments/summary.csv` (counts match). A `notes:` line was added to the latest block documenting this maintenance.; README table regenerated - `README_TABLE.txt` reflects the latest row per (dataset, mode, calibration) with canonical formatting (TPR 4dp, p95/p99/eps 1dp, `NA` where applicable).
- **2025-09-03**: Repository hygiene & provenance scope  Moved non-artifacts out of `data/` (scripts`scripts/`, docs`docs/`); updated references to `docs/PROVENANCE.txt`; added `.gitattributes` (LF policy; keep protected JSONs byte-exact); ignored `.ruff_cache/` in `.gitignore`. Provenance 1:1 mapping unchanged; metrics unchanged.
- **2025-09-03**: **Assets & attributes**
  - Normalized 3 SVGs in `figures/` (CRLFâ†’LF; stripped trailing whitespace; UTFâ€‘8 no BOM; single final LF).
  - Updated `.gitattributes` to mark `*.png` as **binary** (prevents EOL normalization and diffs on images); normalized `.gitattributes` to **LF**.
  - Added a dated PROVENANCE note recording the actual Docker base image and the above maintenance.
  - Hooks: all passing; tests: unchanged; metrics/results: unchanged.
- **2025-09-03** (IST): **Green build** & repo hygiene
  - Fixed mid-token splits in `src/stream.py`, `src/calibration.py`, `src/log_tokenize.py`, and `scripts/make_plots.py`.
  - Corrected summary writing in `src/stream.py`: **TPR** now formatted to **4 decimals or `NA`**; **anomalies** column now records `n_anom` (previously mis-written).
  - Enforced **LF** line endings across the tree; removed **UTFâ€‘8 BOM** from `.pre-commit-config.yaml`; widened local **BOM guard** to include `ya?ml`.
  - Re-generated `experiments/summary.csv` **with labels** for `synth_tokens`; `p95 <= p99` and TPR formatting policy satisfied.
  - **Pre-commit:** all hooks pass; **tests:** 6 passed (`pytest==8.3.3`).
  - **Policy reminders:** three protected JSONs (`data/mini_tokens.json`, `data/synth_labels.json`, `data/synth_tokens.json`) remain byte-identical with **no trailing newline**; `data/HASHES.txt` unchanged (4 lines, uppercase `sha256=...`).

---

## Release Packaging (Reproducible)

To produce a clean source archive (no caches, no `.git`):

```powershell
git archive --format=zip -o log-project-src.zip HEAD
```

Policy recap: UTF-8 **without BOM**, **LF-only** line endings; a single final LF on text files.
Exceptions: `data/mini_tokens.json`, `data/synth_labels.json`, `data/synth_tokens.json` must **not** end with a newline.
