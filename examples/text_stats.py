"""Conta linhas, palavras e caracteres; --save exporta também um JSON."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--save", action="store_true")
args = parser.parse_args()

text = Path("/input/data.txt").read_text(encoding="utf-8")
stats = {"lines": len(text.splitlines()), "words": len(text.split()), "characters": len(text)}
payload = json.dumps(stats, ensure_ascii=False)
print(payload)
if args.save:
    Path("/output/stats.json").write_text(payload + "\n", encoding="utf-8")
