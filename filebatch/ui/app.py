from __future__ import annotations

import asyncio
import ctypes
import os
import sys
from pathlib import Path

from textual import constants
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.driver import Driver
from textual.widgets import Header, Footer, Button, Static, ProgressBar
from textual.drivers import win32 as textual_win32
from textual.drivers._writer_thread import WriterThread
from textual.drivers.windows_driver import WindowsDriver

from filebatch.core.scanner import FileScanner, FileInfo
from filebatch.core.filter import FilterEngine, FilterConfig
from filebatch.core.engine import BatchEngine
from filebatch.core.logger import BatchLogger

from filebatch.ui.widgets.directory_selector import DirectorySelector
from filebatch.ui.widgets.filter_panel import FilterPanel
from filebatch.ui.widgets.rule_panel import RulePanel
from filebatch.ui.widgets.log_panel import LogPanel
from filebatch.ui.widgets.result_summary import ResultSummary


def _enable_application_mode_no_quick_edit() -> callable:
    terminal_in = sys.__stdin__
    terminal_out = sys.__stdout__

    current_console_mode_in = textual_win32.get_console_mode(terminal_in)
    current_console_mode_out = textual_win32.get_console_mode(terminal_out)

    def restore() -> None:
        textual_win32.set_console_mode(terminal_in, current_console_mode_in)
        textual_win32.set_console_mode(terminal_out, current_console_mode_out)

    input_mode = (
        current_console_mode_in
        | textual_win32.ENABLE_VIRTUAL_TERMINAL_INPUT
        | textual_win32.ENABLE_EXTENDED_FLAGS
    ) & ~textual_win32.ENABLE_QUICK_EDIT_MODE
    textual_win32.set_console_mode(terminal_in, input_mode)
    textual_win32.set_console_mode(
        terminal_out,
        current_console_mode_out | textual_win32.ENABLE_VIRTUAL_TERMINAL_PROCESSING,
    )
    return restore


class SafeWindowsDriver(WindowsDriver):
    def start_application_mode(self) -> None:
        loop = asyncio.get_running_loop()

        self._restore_console = _enable_application_mode_no_quick_edit()

        self._writer_thread = WriterThread(self._file)
        self._writer_thread.start()

        self.write("\x1b[?1049h")
        self.write("\x1b[?25l")
        self.write("\033[?1004h")
        self.write("\x1b[>1u")
        self.flush()
        self._enable_bracketed_paste()

        self._event_thread = textual_win32.EventMonitor(
            loop, self._app, self.exit_event, self.process_message
        )
        self._event_thread.start()


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
        width: 52;
        min-width: 52;
        height: 1fr;
        overflow-y: auto;
        overflow-x: hidden;
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
        min-height: 3;
        dock: bottom;
        layout: horizontal;
        padding: 0 1;
    }

    #status-text {
        width: 1fr;
        content-align: left middle;
    }

    #progress-bar {
        width: 40;
    }

    #action-buttons {
        width: 1fr;
        height: 3;
        min-height: 3;
        layout: horizontal;
        margin: 1 0 1 0;
    }

    #action-buttons Button {
        margin-right: 1;
        width: auto;
        min-width: 11;
    }

    #file-count {
        color: $text-muted;
        padding: 0 1;
        margin: 0 0 1 0;
        height: 1;
    }

    LogPanel {
        height: 14;
        min-height: 10;
    }

    ResultSummary {
        height: 1fr;
        min-height: 10;
    }
    """

    BINDINGS = [
        ("b", "browse", "Browse"),
        ("q", "quit", "Quit"),
        ("s", "scan", "Scan"),
        ("r", "run_batch", "Run"),
        ("d", "dry_run", "Dry Run"),
        ("c", "clear", "Clear"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._configure_windows_console()
        self._mouse_ui_enabled = self._detect_mouse_ui_enabled()
        self.logger = BatchLogger()
        self._files: list[FileInfo] = []
        self._filtered_files: list[FileInfo] = []
        self._last_scan_path: str | None = None
        self._last_scan_recursive = True
        self._scanning = False

    def _configure_windows_console(self) -> None:
        if not hasattr(ctypes, "windll"):
            return

        kernel32 = ctypes.windll.kernel32
        stdin_handle = kernel32.GetStdHandle(-10)
        if stdin_handle in (0, -1):
            return

        mode = ctypes.c_uint()
        if not kernel32.GetConsoleMode(stdin_handle, ctypes.byref(mode)):
            return

        enable_extended_flags = 0x0080
        enable_quick_edit_mode = 0x0040
        new_mode = (mode.value | enable_extended_flags) & ~enable_quick_edit_mode
        kernel32.SetConsoleMode(stdin_handle, new_mode)

    def _build_driver(
        self, headless: bool, inline: bool, mouse: bool, size: tuple[int, int] | None
    ) -> Driver:
        if sys.platform == "win32" and not headless:
            driver = SafeWindowsDriver(
                self,
                debug=constants.DEBUG,
                mouse=False,
                size=size,
            )
            self._driver = driver
            return driver
        return super()._build_driver(headless=headless, inline=inline, mouse=mouse, size=size)

    def _detect_mouse_ui_enabled(self) -> bool:
        if sys.platform != "win32":
            return True
        return bool(
            os.environ.get("WT_SESSION")
            or os.environ.get("TERM_PROGRAM")
            or os.environ.get("VSCODE_PID")
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main-container"):
            with Vertical(id="left-panel"):
                yield DirectorySelector(show_mouse_actions=self._mouse_ui_enabled)
                yield Static("0 files found", id="file-count")
                yield FilterPanel()
                yield RulePanel()
                if self._mouse_ui_enabled:
                    with Horizontal(id="action-buttons"):
                        yield Button("▶ Run", variant="success", id="btn-run")
                        yield Button("🔍 Dry Run", variant="primary", id="btn-dry")
                        yield Button("🗑 Clear", variant="default", id="btn-clear")
                else:
                    yield Static(
                        "Keyboard mode: B browse, S scan, R run, D dry run, C clear.",
                        id="keyboard-mode-hint",
                    )
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
        try:
            self.query_one(DirectorySelector).set_feedback("")
        except Exception:
            pass
        self._start_scan(event.path, event.recursive)

    def on_directory_selector_scan_validation_failed(
        self, event: DirectorySelector.ScanValidationFailed
    ) -> None:
        self.logger.warning(event.message)
        self._set_status(event.message)
        try:
            self.query_one(DirectorySelector).set_feedback(event.message)
        except Exception:
            pass
        try:
            self.query_one("#dir-input").focus()
        except Exception:
            pass

    def _start_scan(self, path: str, recursive: bool) -> None:
        if self._scanning:
            self.logger.warning("Scan already in progress.")
            self._set_status("Scan already in progress")
            return

        self._set_status(f"Scanning: {path}...")
        self.logger.info(f"Scanning directory: {path} (recursive={recursive})")

        root = Path(path)
        if not root.exists() or not root.is_dir():
            self.logger.error(f"Invalid directory: {path}")
            self._set_status(f"Error: {path} is not a valid directory")
            return

        self._last_scan_path = path
        self._last_scan_recursive = recursive
        self._scanning = True
        self._set_controls_disabled(True)
        self.run_worker(self._scan_worker(root, recursive), exclusive=True, name="scan")

    async def _scan_worker(self, root: Path, recursive: bool) -> None:
        try:
            scanner = FileScanner(root, recursive=recursive)
            files = await asyncio.to_thread(scanner.scan)
            self._files = files
            self.logger.info(f"Found {len(self._files)} files")
            self._apply_filter()
            self._set_status(
                f"Scanned: {len(self._files)} files, {len(self._filtered_files)} matched"
            )
        finally:
            self._scanning = False
            self._set_controls_disabled(False)

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
            path = dir_input.value.strip()
            if not path:
                message = "Enter a directory path or use Browse before scanning."
                self.logger.warning(message)
                self._set_status(message)
                return
            recursive = self.query_one("#dir-recursive").value
            self._start_scan(path, recursive)
        except Exception as exc:
            self.logger.error(f"Scan error: {exc}")

    def action_browse(self) -> None:
        try:
            self.query_one(DirectorySelector)._browse_directory()
        except Exception as exc:
            self.logger.error(f"Browse error: {exc}")

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

        if not dry_run and self._last_scan_path:
            self._refresh_after_batch()
        result_panel.set_summary(result)
        self._set_status(f"Done ({mode}): {result.summary}")

    def _refresh_after_batch(self) -> None:
        root = Path(self._last_scan_path) if self._last_scan_path else None
        if root is None or not root.exists() or not root.is_dir():
            self._files = []
            self._filtered_files = []
            self._update_file_count()
            return

        scanner = FileScanner(root, recursive=self._last_scan_recursive)
        self._files = scanner.scan()
        self._apply_filter()

    def _set_controls_disabled(self, disabled: bool) -> None:
        for control_id in ("#btn-browse", "#btn-scan", "#btn-run", "#btn-dry", "#btn-clear"):
            try:
                self.query_one(control_id, Button).disabled = disabled
            except Exception:
                pass

    def _clear_all(self) -> None:
        if self._scanning:
            self.logger.warning("Cannot clear while a scan is in progress.")
            self._set_status("Wait for the current scan to finish")
            return
        self._files.clear()
        self._filtered_files.clear()
        self._last_scan_path = None
        self._last_scan_recursive = True
        self.logger.clear()
        try:
            self.query_one(DirectorySelector).reset()
            self.query_one(FilterPanel).reset()
            self.query_one(RulePanel).reset()
            self.query_one(LogPanel).clear_log()
            self.query_one(ResultSummary).clear_results()
            self.query_one("#file-count", Static).update("0 files found")
            self._set_progress(0, 100)
        except Exception:
            pass
        self._set_status("Ready")
