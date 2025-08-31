param(
  [string]$OutDir = "release",
  [switch]$IncludeGitTrackedOnly = $true
)

$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$short = (& git rev-parse --short HEAD) 2>$null; if (-not $short) { $short = "NA" }
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipName = "log-project-$stamp-$short.zip"
$out = Join-Path $root $OutDir
$tmp = Join-Path $env:TEMP ("log-project-release-" + [guid]::NewGuid().ToString("N"))

New-Item -Force -ItemType Directory -Path $out | Out-Null
New-Item -Force -ItemType Directory -Path $tmp | Out-Null

# choose file list
if ($IncludeGitTrackedOnly) {
  $files = (& git ls-files) -split "`n"
} else {
  $files = Get-ChildItem -Recurse -File | % { $_.FullName.Substring($root.Length+1) }
}

# exclusions (even if tracked)
$excludePatterns = @(
  '^\.git/', '^\.venv/', '^__pycache__/', '^\.pytest_cache/',
  '^experiments/logs/', '^release/', '^\.git_corrupt_backup/'
)
$files = $files | ? { $_ -ne '' } | % { $_ -replace '\\','/' } |
         ? { $fp = $_; -not ($excludePatterns | % { if ($fp -match $_) { $true } } | Where-Object { $_ }) }

# copy preserving structure
foreach ($rel in $files) {
  $src = Join-Path $root $rel
  $dst = Join-Path $tmp $rel
  $dir = Split-Path $dst -Parent
  if (-not (Test-Path $dir)) { New-Item -Force -ItemType Directory -Path $dir | Out-Null }
  Copy-Item -Force $src $dst
}

# create zip
$zipPath = Join-Path $out $zipName
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item -Recurse -Force $tmp

# hashes & provenance
$hash = (Get-FileHash -Algorithm SHA256 $zipPath).Hash.ToUpper()
$bytes = (Get-Item $zipPath).Length
$today = (Get-Date).ToString('yyyy-MM-dd')

$hashesTxt = Join-Path $out 'HASHES.txt'
$provTxt = Join-Path $out 'PROVENANCE.txt'

$hashLine = "$today  release/$zipName  $bytes  sha256=$hash"
$prov = @()
$prov += "---"
$prov += "timestamp: $(Get-Date -Format s)Z"
$prov += "commit: $short"
$prov += "input: repo snapshot (git tracked files; excludes venv/caches/logs)"
$prov += "cmd: scripts/make_release.ps1"
$prov += "output: release/$zipName"
$prov += "sha256: $hash"
$prov += "notes: created zip with exclusions; metrics and source unchanged."
$prov += ""

Add-Content -Path $hashesTxt -Value $hashLine
Add-Content -Path $provTxt -Value ($prov -join "`n")

Write-Host "Release created:" $zipPath
Write-Host "SHA256:" $hash
