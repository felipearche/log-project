# Normalizes repository text files to UTF-8 (no BOM) + LF and ensures a trailing newline.
# Excludes canonical binary data artifacts and common noisy dirs.
param(
  [string]$Root = (Get-Location).Path
)

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$excludePatterns = @(
  '^\.git[\\/]', '^\.venv[\\/]', '^__pycache__[\\/]', '^\.pytest_cache[\\/]',
  '^experiments[\\/]logs[\\/]' # logs are optional to keep raw
)

# Treat these four as binary; never normalize them
$binaryData = @(
  'data/synth_tokens.json',
  'data/mini_tokens.json',
  'data/synth_labels.json',
  'data/raw/mini.log'
)

# Helpers
function Is-Excluded($rel) {
  foreach($pat in $excludePatterns){
    if($rel -match $pat){ return $true }
  }
  return $false
}

$changed = @()
$scanned = 0
Get-ChildItem -LiteralPath $Root -Recurse -File | ForEach-Object {
  $abs = $_.FullName
  $rel = [IO.Path]::GetRelativePath($Root, $abs).Replace('\','/')

  if (Is-Excluded $rel) { return }
  if ($binaryData -contains $rel) { return }
  if ($_.Extension -match '^\.(png|jpg|jpeg|gif|svg|ico|pdf|mp4|mov|zip|exe|dll|pyd)$') { return }

  $bytes = [IO.File]::ReadAllBytes($abs)
  $scanned++

  # Try UTF-8 decode; if fails, skip
  try {
    # Strip BOM if present
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
      $bytes = $bytes[3..($bytes.Length-1)]
    }
    $text = [Text.Encoding]::UTF8.GetString($bytes)
  } catch {
    return
  }

  $orig = $text

  # Normalize line endings to LF only
  $text = $text -replace "`r`n","`n" -replace "`r","`n"

  # Ensure single trailing LF
  if (-not $text.EndsWith("`n")) { $text += "`n" }

  if ($text -ne $orig) {
    [IO.File]::WriteAllText($abs, $text, $Utf8NoBom)
    $changed += $rel
  }
}

if ($changed.Count -gt 0) {
  "`nNormalized to UTF-8 (no BOM), LF, with trailing newline for {0} files:" -f $changed.Count | Write-Output
  $changed | ForEach-Object { "  - $_" | Write-Output }
} else {
  "No changes needed. All scanned files are already UTF-8 (no BOM) with LF and trailing newline." | Write-Output
}
