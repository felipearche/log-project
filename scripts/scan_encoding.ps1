Param()
Get-ChildItem -Recurse -File | ForEach-Object {
  $p = $_.FullName
  if ($p -match '\.(md|txt|py|ps1|yml|yaml|json|csv|lock|cfg|ini|toml|dockerignore|gitattributes|gitignore|Dockerfile)$' -or
      (Split-Path -Leaf $p) -eq 'Dockerfile') {
    $bytes = [IO.File]::ReadAllBytes($p)
    $hasBOM = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    $crlf = $text -match "`r`n"
    $endsLF = ($bytes.Length -gt 0 -and $bytes[$bytes.Length-1] -eq 0x0A)
    "{0}`tUTF8_no_BOM={1}`tCRLF={2}`ttrailing_LF={3}" -f $p, (-not $hasBOM), $crlf, $endsLF
  }
}
