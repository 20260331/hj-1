from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class FileInfo:
    path: Path
    name: str
    suffix: str
    size: int
    is_dir: bool = False

    @classmethod
    def from_path(cls, p: Path) -> FileInfo:
        stat = p.stat()
        return cls(
            path=p,
            name=p.name,
            suffix=p.suffix.lower(),
            size=stat.st_size,
            is_dir=p.is_dir(),
        )


class FileScanner:
    def __init__(self, root: str | Path, recursive: bool = True) -> None:
        self.root = Path(root)
        self.recursive = recursive

    def scan(self) -> list[FileInfo]:
        if not self.root.exists():
            return []
        if not self.root.is_dir():
            return []

        results: list[FileInfo] = []
        if self.recursive:
            for dirpath, _dirnames, filenames in os.walk(self.root):
                for fname in filenames:
                    full = Path(dirpath) / fname
                    try:
                        results.append(FileInfo.from_path(full))
                    except OSError:
                        continue
        else:
            for item in self.root.iterdir():
                if item.is_file():
                    try:
                        results.append(FileInfo.from_path(item))
                    except OSError:
                        continue
        return results
