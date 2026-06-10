from __future__ import annotations

import enum
import datetime
from dataclasses import dataclass
from typing import Callable


class LogLevel(enum.IntEnum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


@dataclass
class LogEntry:
    timestamp: datetime.datetime
    level: LogLevel
    message: str

    @property
    def formatted(self) -> str:
        ts = self.timestamp.strftime("%H:%M:%S")
        prefix = {
            LogLevel.DEBUG: "DBG",
            LogLevel.INFO: "INF",
            LogLevel.WARNING: "WRN",
            LogLevel.ERROR: "ERR",
        }[self.level]
        return f"[{ts}] [{prefix}] {self.message}"


class BatchLogger:
    def __init__(self, level: LogLevel = LogLevel.DEBUG) -> None:
        self.level = level
        self.entries: list[LogEntry] = []
        self._on_entry: Callable[[LogEntry], None] | None = None

    def on_entry(self, callback: Callable[[LogEntry], None]) -> None:
        self._on_entry = callback

    def _log(self, level: LogLevel, message: str) -> None:
        if level < self.level:
            return
        entry = LogEntry(
            timestamp=datetime.datetime.now(),
            level=level,
            message=message,
        )
        self.entries.append(entry)
        if self._on_entry:
            self._on_entry(entry)

    def debug(self, message: str) -> None:
        self._log(LogLevel.DEBUG, message)

    def info(self, message: str) -> None:
        self._log(LogLevel.INFO, message)

    def warning(self, message: str) -> None:
        self._log(LogLevel.WARNING, message)

    def error(self, message: str) -> None:
        self._log(LogLevel.ERROR, message)

    def clear(self) -> None:
        self.entries.clear()

    def get_formatted(self) -> list[str]:
        return [e.formatted for e in self.entries]
