from __future__ import annotations

import re
from fnmatch import fnmatch
from dataclasses import dataclass, field
from filebatch.core.scanner import FileInfo


@dataclass
class FilterConfig:
    extensions: list[str] = field(default_factory=list)
    name_pattern: str = ""
    name_regex: str = ""
    min_size: int = -1
    max_size: int = -1


class FilterEngine:
    def __init__(self, config: FilterConfig) -> None:
        self.config = config
        self._compiled_regex: re.Pattern[str] | None = None
        if config.name_regex:
            self._compiled_regex = re.compile(config.name_regex)

    def match(self, info: FileInfo) -> bool:
        cfg = self.config

        if cfg.extensions:
            if info.suffix.lower() not in [e.lower() if e.startswith(".") else f".{e.lower()}" for e in cfg.extensions]:
                return False

        if cfg.name_pattern:
            if not fnmatch(info.name, cfg.name_pattern):
                return False

        if self._compiled_regex is not None:
            if not self._compiled_regex.search(info.name):
                return False

        if cfg.min_size >= 0 and info.size < cfg.min_size:
            return False

        if cfg.max_size >= 0 and info.size > cfg.max_size:
            return False

        return True

    def apply(self, files: list[FileInfo]) -> list[FileInfo]:
        return [f for f in files if self.match(f)]
