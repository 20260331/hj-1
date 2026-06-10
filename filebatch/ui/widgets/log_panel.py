from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog, Static

from filebatch.core.logger import LogEntry, LogLevel


class LogPanel(Vertical):
    DEFAULT_CSS = """
    LogPanel {
        height: 1fr;
        margin: 0 0 0 0;
        border: round $warning;
        Static#log-title {
            text-style: bold;
            margin-bottom: 0;
        }
        RichLog {
            height: 1fr;
        }
    }
    """

    LEVEL_STYLES = {
        LogLevel.DEBUG: "dim",
        LogLevel.INFO: "",
        LogLevel.WARNING: "yellow",
        LogLevel.ERROR: "bold red",
    }

    def compose(self) -> ComposeResult:
        yield Static("📋 Log", id="log-title")
        yield RichLog(id="log-content", highlight=True, markup=True)

    def append(self, entry: LogEntry) -> None:
        log = self.query_one("#log-content", RichLog)
        style = self.LEVEL_STYLES.get(entry.level, "")
        ts = entry.timestamp.strftime("%H:%M:%S")
        prefix = {
            LogLevel.DEBUG: "DBG",
            LogLevel.INFO: "INF",
            LogLevel.WARNING: "WRN",
            LogLevel.ERROR: "ERR",
        }[entry.level]
        if style:
            log.write(f"[{ts}] [{prefix}] [{style}]{entry.message}[/{style}]")
        else:
            log.write(f"[{ts}] [{prefix}] {entry.message}")

    def clear_log(self) -> None:
        self.query_one("#log-content", RichLog).clear()
