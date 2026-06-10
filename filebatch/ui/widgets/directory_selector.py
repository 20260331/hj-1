from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.worker import Worker, get_current_worker
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
    DEFAULT_CSS = """
    DirectorySelector {
        height: auto;
        margin: 0 0 1 0;

        #dir-row {
            height: 3;
        }

        Input#dir-input {
            width: 1fr;
        }

        #btn-row {
            height: 3;
        }

        #btn-row Button {
            margin-left: 1;
        }

        Checkbox#dir-recursive {
            width: auto;
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

    class BrowseRequested(Message):
        def __init__(self) -> None:
            super().__init__()

    def compose(self) -> ComposeResult:
        with Horizontal(id="dir-row"):
            yield Static("Directory:", id="dir-label")
            yield Input(placeholder="Enter directory path...", id="dir-input")
        with Horizontal(id="btn-row"):
            yield Checkbox("Recursive", value=True, id="dir-recursive")
            yield Button("Browse", variant="default", id="btn-browse")
            yield Button("Scan", variant="primary", id="btn-scan")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-scan":
            path = self.query_one("#dir-input", Input).value.strip()
            if not path:
                self.query_one("#dir-input", Input).value = str(Path.home())
                path = str(Path.home())
            recursive = self.query_one("#dir-recursive", Checkbox).value
            self.post_message(self.ScanRequested(path, recursive))
            self.post_message(self.DirectoryChanged(path))
        elif btn_id == "btn-browse":
            self._browse_directory()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "dir-input":
            path = event.value.strip()
            if path:
                recursive = self.query_one("#dir-recursive", Checkbox).value
                self.post_message(self.ScanRequested(path, recursive))
                self.post_message(self.DirectoryChanged(path))

    def _browse_directory(self) -> None:
        self.query_one("#btn-browse", Button).disabled = True
        self.run_worker(self._worker_browse(), exclusive=True, name="browse")

    async def _worker_browse(self) -> None:
        try:
            directory = await asyncio.to_thread(_open_dir_dialog)
            if directory:
                self.query_one("#dir-input", Input).value = directory
                recursive = self.query_one("#dir-recursive", Checkbox).value
                self.post_message(self.ScanRequested(directory, recursive))
                self.post_message(self.DirectoryChanged(directory))
        except Exception:
            pass
        finally:
            try:
                self.query_one("#btn-browse", Button).disabled = False
            except Exception:
                pass

    def set_path(self, path: str) -> None:
        self.query_one("#dir-input", Input).value = path
