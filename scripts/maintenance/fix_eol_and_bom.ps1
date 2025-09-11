# Fix LF and BOM across text files (skip protected JSONs)
param(
    [string]$Repo = "."
)
Set-Location -LiteralPath $Repo

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$patterns = @("*.py","*.md","*.yml","*.yaml","*.txt","*.toml","*.ini","*.ps1","*.cfg","*.csv","*.gitignore","*.gitattributes","*Makefile","Dockerfile","CITATION.cff",".editorconfig",".pre-commit-config.yaml","ruff.toml","mypy.ini","README","README.md")
$exclude = @("data/mini_tokens.json","data/synth_labels.json","data/synth_tokens.json")

$files = New-Object System.Collections.Generic.List[System.String]
foreach ($pat in $patterns) {
    Get-ChildItem -Recurse -File -Include $pat | ForEach-Object {
        $rel = $_.FullName.Substring((Get-Location).Path.Length + 1).Replace("\","/")
        if ($exclude -contains $rel) { return }
        $files.Add($_.FullName)
    }
}

foreach ($f in $files) {
    $bytes = [IO.File]::ReadAllBytes($f)
    # Strip UTF-8 BOM if present
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $bytes = $bytes[3..($bytes.Length-1)]
    }
    $text = [Text.Encoding]::UTF8.GetString($bytes)
    # Normalize CRLF and CR to LF
    $text = $text -replace "`r`n","`n"
    $text = $text -replace "`r","`n"
    # Write back UTF-8 (no BOM)
    [IO.File]::WriteAllText($f, $text, $utf8NoBom)
}
Write-Host "Normalized $($files.Count) files to UTF-8 (no BOM) with LF endings." -ForegroundColor Green
