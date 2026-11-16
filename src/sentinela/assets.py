"""Resolve project files or their bundled counterparts in an installed package."""
from pathlib import Path


_BUNDLED_ROOT = Path(__file__).with_name("_assets")


def asset_path(root: Path, relative: str) -> Path:
    """Prefer an asset in ``root`` and fall back to the packaged copy."""
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("O caminho do recurso precisa ser relativo ao projeto.")
    local_path = Path(root) / relative_path
    if local_path.is_file():
        return local_path
    return _BUNDLED_ROOT / relative_path
