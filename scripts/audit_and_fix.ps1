# Audit & (optional) fix helpers for Windows PowerShell
# Run from repo root:  pwsh -NoProfile -File .\scripts\audit_and_fix.ps1
# By default, only audits. Uncomment FIX sections if you want it to modify files in-place.

param(
    [string]$Repo = (Resolve-Path .).Path
)

Write-Host "Repo: $Repo"

# 0) Guard: ensure we're at repo root (expect some sentinel files)
$sentinels = @(".editorconfig",".gitattributes","README.md","CITATION.cff")
$missing = @()
foreach ($s in $sentinels) { if (-not (Test-Path (Join-Path $Repo $s))) { $missing += $s } }
if ($missing.Count -gt 0) {
    Write-Error "Not at repo root? Missing: $($missing -join ', ')"
    exit 2
}

# 1) Verify LF-only and no UTF-8 BOM (non-binary files only)
function Get-TextFiles {
    Get-ChildItem -Path $Repo -Recurse -File |
      Where-Object {
        $bn = $_.Name.ToLowerInvariant()
        -not ($bn -like "*.png" -or $bn -like "*.jpg" -or $bn -like "*.jpeg" -or $bn -like "*.gif" -or $bn -like "*.pdf" -or $bn -like "*.zip")
      }
}
$badCrlf = @()
$badBom  = @()
foreach ($f in Get-TextFiles) {
    $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $badBom += $f.FullName
    }
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    if ($text.Contains("`r`n")) { $badCrlf += $f.FullName }
}
Write-Host "CRLF files: $($badCrlf.Count)"
Write-Host "BOM files:  $($badBom.Count)"

# FIX (optional):
# foreach ($p in $badCrlf) {
#   (Get-Content $p -Raw).Replace("`r`n","`n") | Set-Content -NoNewline -Encoding utf8 $p
# }
# foreach ($p in $badBom) {
#   $bytes = [System.IO.File]::ReadAllBytes($p)
#   [System.IO.File]::WriteAllBytes($p, $bytes[3..($bytes.Length-1)])
# }

# 2) Protected JSONs must be valid and have no final newline
$protected = @(
  "data/mini_tokens.json",
  "data/synth_labels.json",
  "data/synth_tokens.json"
)
foreach ($rel in $protected) {
    $p = Join-Path $Repo $rel
    if (-not (Test-Path $p)) { Write-Error "Missing $rel"; exit 2 }
    $bytes = [System.IO.File]::ReadAllBytes($p)
    try { $null = $ExecutionContext.InvokeCommand.ExpandString([System.Text.Encoding]::UTF8.GetString($bytes)) } catch {}
    if ($bytes.Length -eq 0 -or $bytes[-1] -eq 0x0A -or $bytes[-1] -eq 0x0D) {
        Write-Error "$rel must NOT end with a newline"; exit 2
    }
}

# 3) Run the Python audit (must have Python available)
# python scripts/audit_repo.py
