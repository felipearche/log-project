$patterns = @("*.aux","*.bbl","*.blg","*.out","*.toc","*.lof","*.lot","*.fls","*.fdb_latexmk","*.synctex.gz","*.log","*.bcf","*.run.xml","*.xdv","*.nav","*.snm","*.vrb",".DS_Store","Thumbs.db","__MACOSX")
foreach ($pat in $patterns) { Get-ChildItem -Path . -Filter $pat -File -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "Removing $($_.FullName)"; Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue } }
Write-Host "Clean complete."
