param(
    [string]$Repo = "."
)
Set-Location -LiteralPath $Repo
$path = ".gitattributes"
if (-not (Test-Path $path)) { New-Item -ItemType File -Path $path | Out-Null }

$content = Get-Content $path -Raw -ErrorAction SilentlyContinue
$wanted = @(
    "data/mini_tokens.json -text",
    "data/synth_labels.json -text",
    "data/synth_tokens.json -text",
    "*.png binary"
)

$lines = ($content -split "`n") | ForEach-Object { $_.TrimEnd() }
foreach ($w in $wanted) {
    if ($lines -notcontains $w) {
        Add-Content $path $w
        Write-Host "Appended: $w"
    } else {
        Write-Host "Already present: $w"
    }
}
