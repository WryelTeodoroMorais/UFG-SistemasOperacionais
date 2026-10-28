from pathlib import Path

source = Path("/input/data.txt").read_text(encoding="utf-8")
Path("/output/result.txt").write_text(source.upper(), encoding="utf-8")
print(f"Caracteres processados: {len(source)}")
