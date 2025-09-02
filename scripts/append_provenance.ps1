param(
  [Parameter(Mandatory=$true)][string]$Data,
  [Parameter(Mandatory=$true)][string]$Cmd,
  [Parameter(Mandatory=$true)][string]$Notes
)

$ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
$commit = (git rev-parse --short HEAD 2>$null); if (-not $commit) { $commit = "NA" }

# Take the last *actual* summary row appended to experiments\summary.csv
$csvRow = (Get-Content experiments\summary.csv | Select-Object -Last 1)

$block = @"
$ts | commit $commit | seed=20250819
input: $Data
cmd: $Cmd
output: experiments/summary.csv (appended 1 row)
notes: $Notes
CSV_ROW: $csvRow
---
"@

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::AppendAllText("docs\PROVENANCE.txt", $block, $utf8NoBom)
Write-Host "Appended provenance block." -ForegroundColor Green
