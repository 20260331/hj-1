from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Static, ProgressBar

from filebatch.core.scanner import FileScanner, FileInfo
from filebatch.core.filter import FilterEngine, FilterConfig
from filebatch.core.engine import BatchEngine, BatchResult
from filebatch.core.logger import BatchLogger
from filebatch.rules.base import Rule

from filebatch.ui.widgets.directory_selector import DirectorySelector
from filebatch.ui.widgets.filter_panel import FilterPanel
from filebatch.ui.widgets.rule_panel import RulePanel
from filebatch.ui.widgets.log_panel import LogPanel
from filebatch.ui.widgets.result_summary import ResultSummary


class FileBatchApp(App):
    TITLE = "FileBatch - File Batch Processing Tool"
    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        height: 1fr;
        layout: horizontal;
    }

    #left-panel {
        width: 38;
        height: 1fr;
        overflow-y: auto;
        border: none;
        padding: 0 1;
    }

    #right-panel {
        width: 1fr;
        height: 1fr;
        layout: vertical;
        padding: 0 1;
    }

    #bottom-bar {
        height: 3;
        layout: horizontal;
        padding: 0 1;
    }

    #status-text {
        width: 1fr;
        content-align: center middle;
    }

    #progress-bar {
        width: 1fr;
    }

    #action-buttons {
        width: auto;
        height: 3;
        layout: horizontal;
    }

    #action-buttons Button {
        margin-left: 1;
    }

    #file-count {
        color: $text-muted;
        padding: 0 1;
        margin-bottom: 1;
    }

    LogPanel {
        height: 12;
    }

    ResultSummary {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "scan", "Scan"),
        ("r", "run_batch", "Run"),
        ("d", "dry_run", "Dry Run"),
        ("c", "clear", "Clear"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.logger = BatchLogger()
        self._files: list[FileInfo] = []
        self._filtered_files: list[FileInfo] = []
        self._scanning = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            with Vertical(id="left-panel"):
                yield DirectorySelector()
                yield Static("0 files found", id="file-count")
                yield FilterPanel()
                yield RulePanel()
                with Horizontal(id="action-buttons"):
                    yield Button("▶ Run", variant="success", id="btn-run")
                    yield Button("🔍 Dry Run", variant="primary", id="btn-dry")
                    yield Button("🗑 Clear", variant="default", id="btn-clear")
            with Vertical(id="right-panel"):
                yield LogPanel()
                yield ResultSummary()
        with Horizontal(id="bottom-bar"):
            yield Static("Ready", id="status-text")
            yield ProgressBar(total=100, id="progress-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.logger.on_entry(self._on_log_entry)

    def _on_log_entry(self, entry) -> None:
        try:
            log_panel = self.query_one(LogPanel)
            log_panel.append(entry)
        except Exception:
            pass

    def _set_status(self, text: str) -> None:
        try:
            self.query_one("#status-text", Static).update(text)
        except Exception:
            pass

    def _set_progress(self, current: int, total: int) -> None:
        try:
            bar = self.query_one("#progress-bar", ProgressBar)
            bar.update(total=total, progress=current)
        except Exception:
            pass

    def _update_file_count(self) -> None:
        try:
            self.query_one("#file-count", Static).update(
                f"{len(self._filtered_files)} files matched "
                f"(of {len(self._files)} scanned)"
            )
        except Exception:
            pass

    def on_directory_selector_scan_requested(self, event: DirectorySelector.ScanRequested) -> None:
        self._do_scan(event.path, event.recursive)

    def _do_scan(self, path: str, recursive: bool) -> None:
        self._set_status(f"Scanning: {path}...")
        self.logger.info(f"Scanning directory: {path} (recursive={recursive})")

        root = Path(path)
        if not root.exists() or not root.is_dir():
            self.logger.error(f"Invalid directory: {path}")
            self._set_status(f"Error: {path} is not a valid directory")
            return

        scanner = FileScanner(root, recursive=recursive)
        self._files = scanner.scan()
        self.logger.info(f"Found {len(self._files)} files")

        self._apply_filter()
        self._set_status(f"Scanned: {len(self._files)} files, {len(self._filtered_files)} matched")

    def on_filter_panel_filter_changed(self, event: FilterPanel.FilterChanged) -> None:
        self._apply_filter()

    def _apply_filter(self) -> None:
        try:
            filter_panel = self.query_one(FilterPanel)
            config = filter_panel.get_config()
        except Exception:
            config = FilterConfig()

        engine = FilterEngine(config)
        self._filtered_files = engine.apply(self._files)
        self._update_file_count()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-run":
            self._run_batch(dry_run=False)
        elif btn_id == "btn-dry":
            self._run_batch(dry_run=True)
        elif btn_id == "btn-clear":
            self._clear_all()

    def action_scan(self) -> None:
        try:
            dir_input = self.query_one("#dir-input")
            path = dir_input.value.strip() or str(Path.home())
            recursive = self.query_one("#dir-recursive").value
            self._do_scan(path, recursive)
        except Exception as exc:
            self.logger.error(f"Scan error: {exc}")

    def action_run_batch(self) -> None:
        self._run_batch(dry_run=False)

    def action_dry_run(self) -> None:
        self._run_batch(dry_run=True)

    def action_clear(self) -> None:
        self._clear_all()

    def _run_batch(self, dry_run: bool) -> None:
        if not self._filtered_files:
            self.logger.warning("No files to process. Scan a directory first.")
            self._set_status("No files to process")
            return

        try:
            rule_panel = self.query_one(RulePanel)
            rules = rule_panel.build_rules()
        except Exception as exc:
            self.logger.error(f"Failed to build rules: {exc}")
            return

        if not rules:
            self.logger.warning("No rules configured. Configure at least one rule.")
            self._set_status("No rules configured")
            return

        result_panel = self.query_one(ResultSummary)
        result_panel.clear_results()

        mode = "DRY RUN" if dry_run else "LIVE"
        self._set_status(f"Running ({mode})...")
        self._set_progress(0, len(self._filtered_files))

        batch_engine = BatchEngine(logger=self.logger)

        def on_progress(current: int, total: int, info: FileInfo) -> None:
            self._set_progress(current, total)
            self._set_status(f"Processing ({mode}): {current}/{total} - {info.name}")

        def on_result(rule_result) -> None:
            try:
                result_panel.append_row(rule_result)
            except Exception:
                pass

        batch_engine.on_progress(on_progress)
        batch_engine.on_result(on_result)

        result = batch_engine.execute(self._filtered_files, rules, dry_run=dry_run)

        result_panel.set_summary(result)
        self._set_status(f"Done ({mode}): {result.summary}")

    def _clear_all(self) -> None:
        self._files.clear()
        self._filtered_files.clear()
        self.logger.clear()
        try:
            self.query_one(LogPanel).clear_log()
            self.query_one(ResultSummary).clear_results()
            self.query_one("#file-count", Static).update("0 files found")
            self._set_progress(0, 100)
        except Exception:
            pass
        self._set_status("Ready")
