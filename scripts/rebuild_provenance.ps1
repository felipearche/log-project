# Rebuild docs\PROVENANCE.txt with explicit CSV_ROW blocks (1:1 with experiments\summary.csv)
# PowerShell 5.1-safe; writes UTF-8 (no BOM), LF-only.
# Usage:  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#         .\scripts\rebuild_provenance.ps1

# 0) Find repo root
try { $repo = (git rev-parse --show-toplevel) 2>$null } catch { $repo = "" }
if (-not $repo -or -not (Test-Path $repo)) { $repo = (Get-Location).Path }
Set-Location $repo

# 1) Load CSV
$csvPath = Join-Path $repo "experiments\summary.csv"
if (-not (Test-Path $csvPath)) { throw "Missing $csvPath" }
$rows = Import-Csv -LiteralPath $csvPath
if (-not $rows -or $rows.Count -eq 0) { throw "No data rows in $csvPath" }

# Preserve header order as in the CSV
$headers = @()
foreach ($p in $rows[0].PSObject.Properties) { $headers += $p.Name }

# 2) Build explicit blocks
$lines = New-Object System.Collections.Generic.List[string]
$rowNum = 1
foreach ($row in $rows) {
    $lines.Add("CSV_ROW: $rowNum")
    foreach ($h in $headers) {
        $v = $row.$h
        if ($null -eq $v) { $v = "" }
        # normalize embedded newlines to spaces to keep one key=value per line
        $v = ($v -replace "`r","" -replace "`n"," ")
        $lines.Add("$h=$v")
    }
    $lines.Add("")  # blank line between blocks
    $rowNum += 1
}

# 3) Write UTF-8 (no BOM), LF-only with single final LF
$text = [string]::Join("`n", $lines)
if (-not $text.EndsWith("`n")) { $text += "`n" }
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$outPath = Join-Path $repo "docs\PROVENANCE.txt"
[System.IO.File]::WriteAllText($outPath, $text, $utf8NoBom)
Write-Host ("Wrote PROVENANCE to {0} with {1} rows × {2} fields." -f $outPath, $rows.Count, $headers.Count)
