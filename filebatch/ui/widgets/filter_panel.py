from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Input, Static, Checkbox

from filebatch.core.filter import FilterConfig


class FilterPanel(Vertical):
    DEFAULT_CSS = """
    FilterPanel {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
        border: round $primary;
        Static#filter-title {
            text-style: bold;
            margin-bottom: 1;
        }
        Horizontal {
            height: 3;
        }
        Input {
            width: 1fr;
        }
        .filter-label {
            width: 16;
            padding: 0 1 0 0;
            content-align: center middle;
        }
    }
    """

    class FilterChanged(Message):
        def __init__(self, config: FilterConfig) -> None:
            super().__init__()
            self.config = config

    def compose(self) -> ComposeResult:
        yield Static("🔍 File Filters", id="filter-title")
        yield Static("Extensions (comma-sep):")
        yield Input(placeholder=".txt,.md,.py", id="filter-extensions")
        yield Static("Name pattern (glob):")
        yield Input(placeholder="*.txt", id="filter-pattern")
        yield Static("Name regex:")
        yield Input(placeholder="^test_.*\\.py$", id="filter-regex")
        with Horizontal():
            yield Static("Min size (bytes):", classes="filter-label")
            yield Input(placeholder="-1", id="filter-min-size")
        with Horizontal():
            yield Static("Max size (bytes):", classes="filter-label")
            yield Input(placeholder="-1", id="filter-max-size")

    def get_config(self) -> FilterConfig:
        ext_raw = self.query_one("#filter-extensions", Input).value.strip()
        extensions = [e.strip() for e in ext_raw.split(",") if e.strip()] if ext_raw else []
        name_pattern = self.query_one("#filter-pattern", Input).value.strip()
        name_regex = self.query_one("#filter-regex", Input).value.strip()

        min_size = -1
        max_size = -1
        min_raw = self.query_one("#filter-min-size", Input).value.strip()
        max_raw = self.query_one("#filter-max-size", Input).value.strip()
        if min_raw:
            try:
                min_size = int(min_raw)
            except ValueError:
                pass
        if max_raw:
            try:
                max_size = int(max_raw)
            except ValueError:
                pass

        return FilterConfig(
            extensions=extensions,
            name_pattern=name_pattern,
            name_regex=name_regex,
            min_size=min_size,
            max_size=max_size,
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id and event.input.id.startswith("filter-"):
            self.post_message(self.FilterChanged(self.get_config()))
