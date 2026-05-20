from pathlib import Path

from .base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, output_dir: Path) -> None:
        self._root = Path(output_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, path: str) -> Path:
        target = (self._root / path).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError(f"Path traversal detected: {path!r}")
        return target

    def write_file(self, path: str, content: str) -> None:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def read_file(self, path: str) -> str:
        target = self._safe_path(path)
        if not target.exists():
            raise FileNotFoundError(f"{target} not found")
        return target.read_text(encoding="utf-8")

    def list_files(self, prefix: str = "") -> list[str]:
        return [
            str(p.relative_to(self._root))
            for p in self._root.rglob("*")
            if p.is_file() and str(p.relative_to(self._root)).startswith(prefix)
        ]

    def delete_file(self, path: str) -> None:
        target = self._safe_path(path)
        try:
            target.unlink()
        except FileNotFoundError:
            pass
