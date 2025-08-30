# rebuild_provenance.ps1 (v2) — canonical 1:1 provenance from experiments/summary.csv
# Policy: one block per CSV data row; keys ordered: timestamp, commit, seed, input, cmd, CSV_ROW
# - CSV_ROW must be UPPERCASE and contain the EXACT CSV row string
# - UTF-8 (no BOM), LF newlines, trailing LF at EOF
# Usage (repo root):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   pwsh -NoProfile -File .\scripts\rebuild_provenance.ps1

$ErrorActionPreference = "Stop"

# 0) Paths
$csvPath = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\experiments\summary.csv')
$provOut = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\data') | ForEach-Object { Join-Path $_ 'PROVENANCE.txt' }

if (-not (Test-Path $csvPath)) {
  throw "Missing experiments/summary.csv at $csvPath"
}

# 1) Read raw text to preserve exact row strings; normalize newlines to LF
$raw = Get-Content -Raw -LiteralPath $csvPath
$raw = $raw -replace "`r`n","`n" -replace "`r","`n"
$lines = $raw -split "`n"
if ($lines.Count -lt 2) { throw "summary.csv has no data rows" }

$header  = $lines[0]
$dataRaw = @()
for ($i=1; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -ne "") { $dataRaw += $lines[$i] }
}

# 2) Parse CSV objects (matching the normalized text)
$rows = $raw | ConvertFrom-Csv

if ($rows.Count -ne $dataRaw.Count) {
  Write-Host "WARNING: Parsed rows ($($rows.Count)) != raw rows ($($dataRaw.Count)). Proceeding by index." -ForegroundColor Yellow
}

# 3) Build blocks
$blocks = New-Object System.Collections.Generic.List[string]
for ($i=0; $i -lt $rows.Count; $i++) {
  $r = $rows[$i]
  $rawLine = $dataRaw[$i]

  $ts = if ($r.PSObject.Properties.Name -contains 'date' -and $r.date) { $r.date } else { (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK") }
  $commit = if ($r.PSObject.Properties.Name -contains 'commit' -and $r.commit) { $r.commit } else { "NA" }
  $seed   = if ($r.PSObject.Properties.Name -contains 'seed'   -and $r.seed)   { $r.seed }   else { "NA" }
  $dataset = if ($r.PSObject.Properties.Name -contains 'dataset') { $r.dataset } else { "NA" }
  $mode    = if ($r.PSObject.Properties.Name -contains 'mode')    { $r.mode }    else { "NA" }
  $cal     = if ($r.PSObject.Properties.Name -contains 'calibration') { $r.calibration } else { "NA" }

  $blockLines = @(
    '---',
    "timestamp: $ts",
    "commit: $commit",
    "seed: $seed",
    "input: dataset=$dataset; mode=$mode; calibration=$cal",
    "cmd: NA (backfilled)",
    "CSV_ROW: $rawLine"
  )
  $blocks.Add( ($blockLines -join "`n") )
}

# 4) Write file: UTF-8 (no BOM), LF, with trailing LF
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($provOut, ($blocks -join "`n") + "`n", $utf8NoBom)

Write-Host "Wrote $provOut" -ForegroundColor Green

# 5) Post-check
$provCsvRows = (Select-String -Path $provOut -Pattern '^CSV_ROW:' | Measure-Object).Count
Write-Host "Post-check: CSV rows=$($rows.Count); PROVENANCE CSV_ROW=$provCsvRows" -ForegroundColor Cyan
