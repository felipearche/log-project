[CmdletBinding()]
param(
  [Parameter()]
  [string]$CsvPath = "experiments\summary.csv",
  [Parameter()]
  [string]$ProvenancePath = "docs\PROVENANCE.txt"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve repo root assuming this script lives in "<repo>\scripts"
$repoRoot = (Get-Item $PSScriptRoot).Parent.FullName
Set-Location $repoRoot

# Resolve absolute paths
$CsvAbs  = Convert-Path (Join-Path $repoRoot $CsvPath)
$ProvAbs = Join-Path $repoRoot $ProvenancePath

if (-not (Test-Path $CsvAbs)) {
  throw "CSV not found at '$CsvAbs'."
}

# Import the CSV
$rows = Import-Csv -Path $CsvAbs

# Build provenance content: one block per row, flattened key=value pairs.
# Date prefix is today's date (yyyy-MM-dd) to keep a chronological paper trail.
$nl = "`n"
$content = New-Object System.Text.StringBuilder

foreach ($row in $rows) {
  $date = (Get-Date).ToString('yyyy-MM-dd')
  $pairs = @()
  foreach ($prop in $row.PSObject.Properties) {
    $name = $prop.Name
    $val  = [string]$prop.Value
    if ($null -eq $val) { $val = "" }
    # Flatten any line breaks inside values
    $val = $val -replace "(\r\n|\r|\n)", " "
    $pairs += ("{0}={1}" -f $name, $val)
  }
  $line = "$date | " + ($pairs -join " | ")
  [void]$content.Append($line + $nl + $nl)  # blank line between blocks
}

# Ensure target directory exists
$provDir = Split-Path -Parent $ProvAbs
if (-not (Test-Path $provDir)) {
  New-Item -ItemType Directory -Force -Path $provDir | Out-Null
}

# Normalize to LF and write UTF-8 (no BOM)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$bytes = $utf8NoBom.GetBytes(($content.ToString()).Replace("`r`n","`n").Replace("`r","`n"))
[IO.File]::WriteAllBytes($ProvAbs, $bytes)

Write-Host "Wrote provenance to $ProvenancePath" -ForegroundColor Green
