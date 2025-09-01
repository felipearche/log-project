## Environment (authoritative via lockfile)

This project’s environment is **pinned** via `env/requirements.lock` and that lockfile is the **single source of truth**. The versions below reflect the current lockfile; if it changes, this document should not be edited manually.

**Pinned packages (from `env/requirements.lock`):**
- numpy==1.26.4
- scipy==1.16.1
- scikit-learn==1.5.2
- matplotlib==3.9.2
- psutil==7.0.0
- river==0.22.0
- joblib==1.5.1
- threadpoolctl==3.6.0
- python-dateutil==2.9.0.post0
- six==1.17.0
- pytz==2025.2 / tzdata==2025.2

**Notes**
- No `pandas` is required or pinned.
- All text files are UTF‑8 (no BOM) with LF and a single trailing newline (enforced by `.editorconfig` and `scripts/normalize_line_endings.ps1`).
- Preferred workflow: Windows PowerShell + Docker. Always mount with `-v "${PWD}:/app"`.
