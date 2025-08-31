.PHONY: tokenize baseline hashes all
PY := python

tokenize:
	$(PY) src/log_tokenize.py --in data/raw/mini.log --out data/mini_tokens.json --max_lines 10000

baseline:
	$(PY) src/stream.py --data data/synth_tokens.json --mode baseline --sleep_ms 0 --summary-out experiments/summary.csv

hashes:
	$(PY) scripts/hash_files.py

all: tokenize baseline
