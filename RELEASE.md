# Releases

**Goal:** Create a clean, tagged zip and record its **own** hash + provenance under `dist/`.
**Do _not_ modify `data/HASHES.txt`** (that file lists only the four dataset artifacts).

> Windows PowerShell; run from repo root.

---

## 1) Pre-flight
```powershell
cd C:\Users\felip\log-project
git status
```
Ensure there are **no uncommitted changes**.

## 2) Choose a version tag
```powershell
$ver = "v0.9"  # e.g., v0.9, v1.0
git tag -l
```
Pick a new tag name (do not re-use an existing one).

## 3) Create the zip (exclude .venv/, experiments/logs/, caches, figures, and .git/)
```powershell
$name   = "log-project-$ver.zip"
$outdir = "dist"
mkdir -Force $outdir | Out-Null

# Create a staging copy excluding heavy/cached folders
$excludes = @(
  ".venv", "experiments\logs", ".pytest_cache", "__pycache__", ".git", ".ruff_cache", "figures"
)
$staging = Join-Path $outdir "staging"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
robocopy . $staging /MIR /XD $($excludes -join " ")

# Zip the staging tree
$zip = Join-Path $outdir $name
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zip -CompressionLevel Optimal -Force

# Clean staging
Remove-Item -Recurse -Force $staging
```

## 4) Compute hash and write release provenance
```powershell
$zip    = Join-Path $outdir $name
$sha    = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToUpper()
$ts     = Get-Date -AsUTC -Format "yyyy-MM-ddTHH:mm:ssZ"
$enc    = New-Object System.Text.UTF8Encoding($false)
$commit = (git rev-parse --short HEAD 2>$null); if (-not $commit) { $commit = "NA" }

if (-not (Test-Path "dist\PROVENANCE.txt")) {
  New-Item -ItemType File -Path "dist\PROVENANCE.txt" -Force | Out-Null
}

$blk = @"
---
timestamp: $ts
tag: $ver
commit: $commit
artifact: $zip
hash: sha256=$sha
"@

[IO.File]::AppendAllText("dist\PROVENANCE.txt", ($blk -replace "`r`n","`n") + "`n", $enc)
Write-Host "Release hash: sha256=$sha"
```

## 5) (Optional) push tag
```powershell
git tag $ver
git push origin $ver
```

## 6) Verify outputs
```powershell
Get-ChildItem -Recurse dist\ | Select-Object FullName,Length
Get-Content dist\PROVENANCE.txt
```
