# datasets

## schema (v1)
- file format: JSON array of sequences; each sequence is a list of strings (tokens)
- special tokens: <num>=\d+, <ip>=\b\d{1,3}(\.\d{1,3}){3}\b, <hex>=0x[0-9a-fA-F]+
- encoding: UTF-8 (no BOM); EOL = LF

### example
```json
[
  ["servicea","info","user","<num>","connected","from","<hex>"],
  ["auth","info","login","user","<num>","from","<ip>"]
]
```

### synth_tokens.json
- path: data/synth_tokens.json
- sequences: 2000
- size (bytes): 137400
- sha256: 8AF36305BB4FA61486322BFAFE148F6481C7FF1772C081F3E9590FB5C79E6600
- note: Provided artifact for experiments; do not regenerate as part of README steps.

### synth_labels.json
- path: data/synth_labels.json
- items: 2000 (binary 0/1 labels)
- size (bytes): 6000
- sha256: 814DA8A6BAB57EC08702DDC0EFFAC7AFDC88868B4C2EE4C6087C735FB22EDADA
- note: Provided artifact aligned with `synth_tokens.json`.

### mini_tokens.json
- path: data/mini_tokens.json
- sequences: 5
- total tokens: 43
- size (bytes): 533
- sha256: 3CA2BCE42228159B81E5B2255B6BC352819B22FFA74BBD4F78AC82F00A2E1263
- generation (local): `python src/log_tokenize.py --in data/raw/mini.log --out data/mini_tokens.json --max_lines 10000`
- generation (docker): `docker run --rm -v "${PWD}:/app" log-project:latest python src/log_tokenize.py --in data/raw/mini.log --out data/mini_tokens.json --max_lines 10000`
- tokenizer: lowercase + masks `<num>` `<ip>` `<hex>`

### raw/mini.log
- path: data/raw/mini.log
- lines: 5
- size (bytes): 310
- sha256: F5953777A9A84819D55964E5772792CE8819A3FED1E0365FA279EB53F6496FB4
- encoding: UTF-8; EOL=LF
