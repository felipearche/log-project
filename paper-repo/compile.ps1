Param([string]$Main = "log-project-paper.tex")
$ErrorActionPreference = "Stop"
if ($PSScriptRoot) { Set-Location $PSScriptRoot }
if (-not (Test-Path $Main)) { Write-Host "File not found: $Main"; exit 1 }

$basename = [System.IO.Path]::GetFileNameWithoutExtension($Main)

function RunTool {
  param(
    [Parameter(Mandatory=$true)][string]$Exe,
    [Parameter(Mandatory=$true)][string[]]$Args
  )
  Write-Host ">>> $Exe $($Args -join ' ')"
  & $Exe @Args
  if ($LASTEXITCODE -ne 0) { throw "$Exe failed with exit code $LASTEXITCODE" }
}

RunTool -Exe "pdflatex" -Args @("-interaction=nonstopmode","-halt-on-error","-file-line-error",$Main)
if (Test-Path "$basename.aux") { RunTool -Exe "bibtex" -Args @("$basename") } else { Write-Host "Warning: $basename.aux not found; skipping bibtex." }
RunTool -Exe "pdflatex" -Args @("-interaction=nonstopmode","-halt-on-error","-file-line-error",$Main)
RunTool -Exe "pdflatex" -Args @("-interaction=nonstopmode","-halt-on-error","-file-line-error",$Main)

if (Test-Path "$basename.pdf") { Write-Host "Build complete: $basename.pdf" } else { Write-Host "Build finished but $basename.pdf not found." }
