param(
  [switch]$Build = $false,
  [string]$Seed  = "20250819",
  [string]$Data  = "data/synth_tokens.json",
  [string]$Mode  = "baseline",
  [switch]$NoCalib = $false
)

if ($Build) {
  docker build -t log-project:latest .
}

$commit = (git rev-parse --short HEAD 2>$null); if (-not $commit) { $commit = "NA" }
$env:COMMIT = $commit

# Compose args
$calibArg = $null
if ($NoCalib) { $calibArg = "--no_calib" }

docker run --rm -v "${PWD}:/app" -e COMMIT=$env:COMMIT log-project:latest `
  python src/stream.py `
  --data $Data `
  --mode $Mode `
  --sleep_ms 0 `
  $calibArg

# Append provenance (one block per LAST row appended)
$ts = Get-Date -AsUTC -Format "yyyy-MM-ddTHH:mm:ssZ"
$csv = Get-Content "experiments/summary.csv" -Raw
$csv = $csv -replace "`r`n","`n"
$last = ($csv.Trim().Split("`n") | Select-Object -Last 1)

$block = @"
---
timestamp: $ts
commit: $commit
seed: $Seed
input: $Data
cmd: docker run --rm -v ${PWD}:/app -e COMMIT=$commit log-project:latest python src/stream.py --data $Data --mode $Mode --sleep_ms 0 $calibArg
CSV_ROW: $last
"@

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::AppendAllText("docs/PROVENANCE.txt", ($block -replace "`r`n","`n") + "`n", $utf8NoBom)

Write-Host "[provenance] commit=$commit  seed=$Seed  appended 1 block"
