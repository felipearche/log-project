BUILD INSTRUCTIONS (Windows PowerShell 5.1)

From this folder:
  powershell -NoProfile -ExecutionPolicy Bypass -File ".\compile.ps1" -Main "log-project-paper.tex"

Or compile without the script:
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error log-project-paper.tex
  bibtex   log-project-paper
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error log-project-paper.tex
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error log-project-paper.tex
  ii .\log-project-paper.pdf

Notes:
- Title/author/body preserved; only preamble hygiene changed (geometry/hyperref).
- Exactly one geometry line kept (first seen), reinserted after \documentclass.
- A single hyperref + well-formed hypersetup inserted (colorlinks + PDF metadata).
- \emergencystretch=3em added after \begin{document}.
- One \balance inserted after final section before bibliography.
- Clean artifacts: .\clean.ps1
