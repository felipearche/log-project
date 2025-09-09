# --- Repo-root detection (robust) ---
if ($PSCommandPath) {
  $ScriptDir = Split-Path -Parent $PSCommandPath
} elseif ($MyInvocation.MyCommand.Path) {
  $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
  # Fallback: assume current dir is repo root and 'scripts' lives under it
  $ScriptDir = Join-Path (Resolve-Path .) 'scripts'
}
$RepoRoot = Split-Path -Parent $ScriptDir
# -----------------------------------
param(
  [string]$CsvPath = "experiments\summary.csv",
  [string]$OutPath = "docs\PROVENANCE.txt"
)
if (!(Test-Path $CsvPath)) { throw "Missing CSV at $CsvPath" }
$rows = Import-Csv -Path $CsvPath
$sb = New-Object System.Text.StringBuilder
foreach ($r in $rows) {
  $dataset = $r.dataset
  $mode = $r.mode
  $cal = if ($r.calibration) { $r.calibration } elseif ($r.cal) { $r.cal } else { "NA" }
  $labels = if ($dataset -eq "synth_tokens") { "--labels data/synth_labels.json" } else { "" }
  $calflag = if ($cal -eq "no_calib") { "--no-calib" } else { "" }
  $cmd = "python -m src.stream --mode $mode --data data/$dataset.json $labels $calflag".Trim()
  $null = $sb.AppendLine("---")
  $null = $sb.AppendLine(("timestamp: {0}" -f $r.date))
  $null = $sb.AppendLine(("commit: {0}" -f $r.commit))
  $null = $sb.AppendLine(("seed: {0}" -f $r.seed))
  $null = $sb.AppendLine(("input: dataset={0}; mode={1}; calibration={2}" -f $dataset,$mode,$cal))
  $null = $sb.AppendLine(("cmd: {0}" -f $cmd))
  $null = $sb.AppendLine(("CSV_ROW: {0}" -f ($r | ConvertTo-Csv -NoTypeInformation -Delimiter ',' | Select-Object -Skip 1)))
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($OutPath, $sb.ToString(), $utf8NoBom)
Write-Host "Wrote $OutPath"
