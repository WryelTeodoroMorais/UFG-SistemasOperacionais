"""Gravação de artefatos JSON sem sobrescrever arquivos existentes."""
import json
from pathlib import Path


def check_destination(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    if not path.parent.is_dir():
        raise ValueError("A pasta de destino deve existir")


def write_json(path: Path, data: dict) -> None:
    payload = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(payload)
