from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual import events
from textual.message import Message
from textual.widgets import Button, Input, Static, Checkbox


def _open_dir_dialog() -> str:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        directory = filedialog.askdirectory(parent=root)
    finally:
        root.destroy()
    return directory if directory else ""


class DirectorySelector(Vertical):
    def __init__(self, *, show_mouse_actions: bool = True) -> None:
        super().__init__()
        self.show_mouse_actions = show_mouse_actions

    DEFAULT_CSS = """
    DirectorySelector {
        height: 10;
        margin: 0 0 1 0;
        padding: 0 0;

        Horizontal {
            width: 1fr;
        }

        #dir-row {
            height: 3;
        }

        Static#dir-label {
            width: 11;
            content-align: center middle;
            text-style: bold;
        }

        Input#dir-input {
            width: 1fr;
        }

        #btn-row {
            height: 3;
        }

        #dir-feedback {
            height: 2;
            color: $warning;
            padding: 0 1;
        }

        #dir-hint {
            height: 2;
            color: $text-muted;
            padding: 0 1;
        }

        Checkbox#dir-recursive {
            width: 13;
            content-align: left middle;
        }

        #btn-row Button {
            width: auto;
            min-width: 10;
        }

        Button#btn-browse {
            margin-left: 1;
        }

        Button#btn-scan {
            margin-left: 1;
        }
    }
    """

    class DirectoryChanged(Message):
        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

    class ScanRequested(Message):
        def __init__(self, path: str, recursive: bool) -> None:
            super().__init__()
            self.path = path
            self.recursive = recursive

    class ScanValidationFailed(Message):
        def __init__(self, message: str) -> None:
            super().__init__()
            self.message = message

    def compose(self) -> ComposeResult:
        with Horizontal(id="dir-row"):
            yield Static("Dir:", id="dir-label")
            yield Input(placeholder="C:\\path\\to\\folder", id="dir-input")
        with Horizontal(id="btn-row"):
            yield Checkbox("Recursive", value=True, id="dir-recursive")
            if self.show_mouse_actions:
                yield Button("Browse", variant="default", id="btn-browse")
                yield Button("Scan", variant="primary", id="btn-scan")
        hint = (
            "Hint: type a path or use Browse, then press Enter / S to scan."
            if self.show_mouse_actions
            else "Keyboard mode: type a path, press Enter / S to scan, B to browse."
        )
        yield Static(hint, id="dir-hint")
        yield Static("", id="dir-feedback")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self.show_mouse_actions:
            return
        btn_id = event.button.id
        if btn_id == "btn-scan":
            self._trigger_scan()
        elif btn_id == "btn-browse":
            self._browse_directory()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if not self.show_mouse_actions:
            return
        if not event.widget or getattr(event.widget, "id", None) != "btn-scan":
            return
        if self.query_one("#dir-input", Input).value.strip():
            return

        self.post_message(
            self.ScanValidationFailed("Choose a directory to scan or click Browse.")
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "dir-input":
            self._trigger_scan()

    def _trigger_scan(self) -> None:
        path = self.query_one("#dir-input", Input).value.strip()
        if not path:
            self.post_message(
                self.ScanValidationFailed("Choose a directory to scan or click Browse.")
            )
            return
        recursive = self.query_one("#dir-recursive", Checkbox).value
        self.post_message(self.ScanRequested(path, recursive))
        self.post_message(self.DirectoryChanged(path))

    def _browse_directory(self) -> None:
        if self.show_mouse_actions:
            self.query_one("#btn-browse", Button).disabled = True
            self.query_one("#btn-scan", Button).disabled = True
        self.run_worker(self._worker_browse(), exclusive=True, name="browse")

    async def _worker_browse(self) -> None:
        try:
            directory = await asyncio.to_thread(_open_dir_dialog)
            if directory:
                self.set_feedback("")
                self.query_one("#dir-input", Input).value = directory
                recursive = self.query_one("#dir-recursive", Checkbox).value
                self.post_message(self.ScanRequested(directory, recursive))
                self.post_message(self.DirectoryChanged(directory))
            else:
                self.set_feedback("Choose a directory to scan.")
        except Exception:
            pass
        finally:
            try:
                if self.show_mouse_actions:
                    self.query_one("#btn-browse", Button).disabled = False
                    self.query_one("#btn-scan", Button).disabled = False
            except Exception:
                pass

    def set_path(self, path: str) -> None:
        self.query_one("#dir-input", Input).value = path

    def reset(self) -> None:
        self.query_one("#dir-input", Input).value = ""
        self.query_one("#dir-recursive", Checkbox).value = True
        self.set_feedback("")

    def set_feedback(self, message: str) -> None:
        self.query_one("#dir-feedback", Static).update(message)
