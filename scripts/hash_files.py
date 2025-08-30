#!/usr/bin/env python3
import hashlib, os, sys, datetime
FILES = [
    'data/synth_tokens.json',
    'data/mini_tokens.json',
    'data/synth_labels.json',
    'data/raw/mini.log',
]
def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''):
            h.update(chunk)
    return h.hexdigest().upper()
def main():
    today = datetime.date.today().strftime('%Y-%m-%d')
    out = []
    for p in FILES:
        b = os.path.getsize(p)
        s = sha256(p)
        out.append(f"{today} {p} {b} sha256={s}")
    data = "\n".join(out) + "\n"
    os.makedirs('data', exist_ok=True)
    with open('data/HASHES.txt', 'w', encoding='utf-8', newline='\n') as f:
        f.write(data)
    print("Wrote data/HASHES.txt")
if __name__ == '__main__':
    main()
