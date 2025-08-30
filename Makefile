.PHONY: synth tokenize baseline all
PY := python

synth:
	$(PY) data/make_synth.py --n 2000 --anom_ratio 0.03 --seed 20250819 --tokens_out data/synth_tokens.json --labels_out data/synth_labels.json

tokenize:
	$(PY) src/log_tokenize.py --in data/raw/mini.log --out data/mini_tokens.json --max_lines 10000

baseline:
	$(PY) src/stream.py --data data/synth_tokens.json --mode baseline --sleep_ms 0 --summary-out experiments/summary.csv

hashes:
	python scripts/hash_files.py


all: synth tokenize baseline
