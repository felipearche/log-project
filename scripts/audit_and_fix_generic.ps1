# Generic audit & (optional) fix helpers (Windows PowerShell)
# Usage: pwsh -NoProfile -File .\scripts\audit_and_fix_generic.ps1
param([string]$Repo = (Resolve-Path .).Path)

Write-Host "Repo: $Repo"

# Sentinel check
$sentinels = @(".gitattributes",".editorconfig","README.md")
$missing = @()
foreach ($s in $sentinels) { if (-not (Test-Path (Join-Path $Repo $s))) { $missing += $s } }
if ($missing.Count -gt 0) { Write-Warning "Not at repo root? Missing: $($missing -join ', ')" }

# Scan BOM & CRLF
function Get-TextFiles {
  Get-ChildItem -Path $Repo -Recurse -File | Where-Object {
    $ext = [IO.Path]::GetExtension($_.FullName).ToLowerInvariant()
    -not @(".png",".jpg",".jpeg",".gif",".pdf",".zip",".gz",".bz2",".xz",".7z",".mp4",".mov",".avi",".wav",".mp3",".ogg",".woff",".woff2",".ttf") -contains $ext
  }
}
$badBom = @(); $badCrlf = @()
foreach ($f in Get-TextFiles) {
  $bytes = [IO.File]::ReadAllBytes($f.FullName)
  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) { $badBom += $f.FullName }
  $txt = [Text.Encoding]::UTF8.GetString($bytes)
  if ($txt.Contains("`r")) { $badCrlf += $f.FullName }
}
Write-Host "BOM files: $($badBom.Count)"
Write-Host "CRLF files: $($badCrlf.Count)"

# Optional FIXES (uncomment to apply)
# foreach ($p in $badBom) {
#   $bytes = [IO.File]::ReadAllBytes($p)
#   [IO.File]::WriteAllBytes($p, $bytes[3..($bytes.Length-1)])
# }
# foreach ($p in $badCrlf) {
#   (Get-Content $p -Raw) -replace "`r`n","`n" | Set-Content -NoNewline -Encoding utf8 $p
# }

Write-Host "Done."
