from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass


@dataclass
class RuleResult:
    file_path: Path
    rule_name: str
    success: bool = False
    skipped: bool = False
    message: str = ""


class Rule(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def apply(self, info, dry_run: bool = False) -> RuleResult: ...
