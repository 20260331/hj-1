from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass

from filebatch.rules.base import Rule, RuleResult
from filebatch.core.scanner import FileInfo


@dataclass
class FindReplaceConfig:
    find_text: str = ""
    replace_text: str = ""
    use_regex: bool = False
    case_sensitive: bool = True
    encoding: str = "utf-8"
    binary_extensions: tuple[str, ...] = (
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
        ".mp3", ".mp4", ".avi", ".mov", ".wav",
        ".zip", ".tar", ".gz", ".rar", ".7z",
        ".exe", ".dll", ".so", ".dylib",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".pyc", ".pyd", ".o", ".obj",
    )


class FindReplaceRule(Rule):
    def __init__(self, config: FindReplaceConfig) -> None:
        self.config = config
        self._compiled: re.Pattern[str] | None = None
        if config.use_regex and config.find_text:
            flags = 0 if config.case_sensitive else re.IGNORECASE
            self._compiled = re.compile(config.find_text, flags)

    @property
    def name(self) -> str:
        return "find_replace"

    def _is_binary(self, info: FileInfo) -> bool:
        return info.suffix.lower() in self.config.binary_extensions

    def apply(self, info: FileInfo, dry_run: bool = False) -> RuleResult:
        cfg = self.config

        if not cfg.find_text:
            return RuleResult(
                file_path=info.path,
                rule_name=self.name,
                skipped=True,
                message="Empty find text",
            )

        if self._is_binary(info):
            return RuleResult(
                file_path=info.path,
                rule_name=self.name,
                skipped=True,
                message="Binary file skipped",
            )

        try:
            content = info.path.read_text(encoding=cfg.encoding)
        except (UnicodeDecodeError, PermissionError) as exc:
            return RuleResult(
                file_path=info.path,
                rule_name=self.name,
                skipped=True,
                message=f"Cannot read: {exc}",
            )

        if cfg.use_regex and self._compiled is not None:
            new_content, count = self._compiled.subn(cfg.replace_text, content)
        else:
            if cfg.case_sensitive:
                count = content.count(cfg.find_text)
                new_content = content.replace(cfg.find_text, cfg.replace_text)
            else:
                pattern = re.compile(re.escape(cfg.find_text), re.IGNORECASE)
                new_content, count = pattern.subn(cfg.replace_text, content)

        if count == 0:
            return RuleResult(
                file_path=info.path,
                rule_name=self.name,
                skipped=True,
                message="No matches found",
            )

        if not dry_run:
            try:
                info.path.write_text(new_content, encoding=cfg.encoding)
            except PermissionError as exc:
                return RuleResult(
                    file_path=info.path,
                    rule_name=self.name,
                    success=False,
                    message=f"Write error: {exc}",
                )

        action = "Would replace" if dry_run else "Replaced"
        return RuleResult(
            file_path=info.path,
            rule_name=self.name,
            success=True,
            message=f"{action} {count} occurrence(s)",
        )
