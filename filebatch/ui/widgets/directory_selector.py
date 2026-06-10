from __future__ import annotations

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Input, Static, Checkbox


class DirectorySelector(Horizontal):
    DEFAULT_CSS = """
    DirectorySelector {
        height: 3;
        margin: 0 0 1 0;
        Static#dir-label {
            width: auto;
            padding: 0 1;
            content-align: center middle;
        }
        Input#dir-input {
            width: 1fr;
        }
        Button#dir-browse {
            width: auto;
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

    def compose(self) -> ComposeResult:
        yield Static("📁 Directory:", id="dir-label")
        yield Input(placeholder="Enter directory path...", id="dir-input")
        yield Checkbox("Recursive", value=True, id="dir-recursive")
        yield Button("Scan", variant="primary", id="dir-browse")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dir-browse":
            path = self.query_one("#dir-input", Input).value.strip()
            if not path:
                self.query_one("#dir-input", Input).value = str(Path.home())
                path = str(Path.home())
            recursive = self.query_one("#dir-recursive", Checkbox).value
            self.post_message(self.ScanRequested(path, recursive))
            self.post_message(self.DirectoryChanged(path))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "dir-input":
            path = event.value.strip()
            if path:
                recursive = self.query_one("#dir-recursive", Checkbox).value
                self.post_message(self.ScanRequested(path, recursive))
                self.post_message(self.DirectoryChanged(path))

    def set_path(self, path: str) -> None:
        self.query_one("#dir-input", Input).value = path
