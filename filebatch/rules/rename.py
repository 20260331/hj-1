from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass

from filebatch.rules.base import Rule, RuleResult
from filebatch.core.scanner import FileInfo


@dataclass
class RenameConfig:
    pattern: str = ""
    replacement: str = ""
    use_regex: bool = False
    case_sensitive: bool = True
    preview_only: bool = False


class RenameRule(Rule):
    def __init__(self, config: RenameConfig) -> None:
        self.config = config
        self._compiled: re.Pattern[str] | None = None
        if config.use_regex and config.pattern:
            flags = 0 if config.case_sensitive else re.IGNORECASE
            self._compiled = re.compile(config.pattern, flags)

    @property
    def name(self) -> str:
        return "rename"

    def _compute_new_name(self, info: FileInfo) -> tuple[str, bool]:
        cfg = self.config
        old_name = info.name

        if not cfg.pattern:
            return old_name, False

        if cfg.use_regex and self._compiled is not None:
            new_name = self._compiled.sub(cfg.replacement, old_name)
        else:
            if cfg.case_sensitive:
                new_name = old_name.replace(cfg.pattern, cfg.replacement)
            else:
                pattern = re.compile(re.escape(cfg.pattern), re.IGNORECASE)
                new_name = pattern.sub(cfg.replacement, old_name)

        return new_name, new_name != old_name

    def apply(self, info: FileInfo, dry_run: bool = False) -> RuleResult:
        new_name, changed = self._compute_new_name(info)

        if not changed:
            return RuleResult(
                file_path=info.path,
                rule_name=self.name,
                skipped=True,
                message="Name unchanged",
            )

        new_path = info.path.parent / new_name

        if new_path.exists():
            return RuleResult(
                file_path=info.path,
                rule_name=self.name,
                success=False,
                message=f"Target already exists: {new_name}",
            )

        if dry_run:
            return RuleResult(
                file_path=info.path,
                rule_name=self.name,
                success=True,
                message=f"Would rename to: {new_name}",
            )

        try:
            info.path.rename(new_path)
        except OSError as exc:
            return RuleResult(
                file_path=info.path,
                rule_name=self.name,
                success=False,
                message=f"Rename error: {exc}",
            )

        return RuleResult(
            file_path=info.path,
            rule_name=self.name,
            success=True,
            message=f"Renamed to: {new_name}",
        )
