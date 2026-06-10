from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable

from filebatch.core.scanner import FileInfo
from filebatch.rules.base import Rule, RuleResult
from filebatch.core.logger import BatchLogger


@dataclass
class BatchResult:
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    details: list[RuleResult] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return (
            f"Total: {self.total} | "
            f"Success: {self.success} | "
            f"Failed: {self.failed} | "
            f"Skipped: {self.skipped}"
        )


class BatchEngine:
    def __init__(self, logger: BatchLogger | None = None) -> None:
        self.logger = logger or BatchLogger()
        self._on_progress: Callable[[int, int, FileInfo], None] | None = None
        self._on_result: Callable[[RuleResult], None] | None = None

    def on_progress(self, callback: Callable[[int, int, FileInfo], None]) -> None:
        self._on_progress = callback

    def on_result(self, callback: Callable[[RuleResult], None]) -> None:
        self._on_result = callback

    def execute(self, files: list[FileInfo], rules: list[Rule], dry_run: bool = False) -> BatchResult:
        result = BatchResult(total=len(files))
        self.logger.info(f"Batch started: {len(files)} files, {len(rules)} rules, dry_run={dry_run}")

        for idx, info in enumerate(files):
            if self._on_progress:
                self._on_progress(idx + 1, len(files), info)

            for rule in rules:
                try:
                    rule_result = rule.apply(info, dry_run=dry_run)
                    result.details.append(rule_result)

                    if rule_result.skipped:
                        result.skipped += 1
                        self.logger.debug(f"Skipped: {info.name} ({rule.name})")
                    elif rule_result.success:
                        result.success += 1
                        self.logger.info(f"OK: {info.name} -> {rule_result.message}")
                    else:
                        result.failed += 1
                        self.logger.error(f"FAIL: {info.name} ({rule.name}): {rule_result.message}")

                    if self._on_result:
                        self._on_result(rule_result)

                except Exception as exc:
                    result.failed += 1
                    err_result = RuleResult(
                        file_path=info.path,
                        rule_name=rule.name,
                        success=False,
                        message=str(exc),
                    )
                    result.details.append(err_result)
                    self.logger.error(f"ERROR: {info.name} ({rule.name}): {exc}")
                    if self._on_result:
                        self._on_result(err_result)

        self.logger.info(f"Batch finished: {result.summary}")
        return result
