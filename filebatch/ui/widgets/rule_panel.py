from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Static, Checkbox, Button

from filebatch.rules.find_replace import FindReplaceConfig, FindReplaceRule
from filebatch.rules.rename import RenameConfig, RenameRule
from filebatch.rules.base import Rule


class RulePanel(Vertical):
    DEFAULT_CSS = """
    RulePanel {
        height: auto;
        margin: 0 0 1 0;
        padding: 0 1;
        border: round $accent;
        Static#rule-title {
            text-style: bold;
            margin-bottom: 1;
        }
        Horizontal {
            height: 3;
        }
        Input {
            width: 1fr;
        }
        .rule-label {
            width: 14;
            padding: 0 1 0 0;
            content-align: center middle;
        }
        Button {
            margin: 1 0;
        }
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("⚙️ Batch Rules", id="rule-title")

        yield Static("── Find & Replace ──", id="fr-header")
        with Horizontal():
            yield Static("Find:", classes="rule-label")
            yield Input(placeholder="Text to find", id="fr-find")
        with Horizontal():
            yield Static("Replace:", classes="rule-label")
            yield Input(placeholder="Replacement text", id="fr-replace")
        with Horizontal():
            yield Checkbox("Regex", value=False, id="fr-regex")
            yield Checkbox("Case sensitive", value=True, id="fr-case")
        with Horizontal():
            yield Static("Encoding:", classes="rule-label")
            yield Input(value="utf-8", id="fr-encoding")

        yield Static("── Rename ──", id="rn-header")
        with Horizontal():
            yield Static("Pattern:", classes="rule-label")
            yield Input(placeholder="Pattern to match in filename", id="rn-pattern")
        with Horizontal():
            yield Static("Replace:", classes="rule-label")
            yield Input(placeholder="Replacement for filename", id="rn-replace")
        with Horizontal():
            yield Checkbox("Regex", value=False, id="rn-regex")
            yield Checkbox("Case sensitive", value=True, id="rn-case")

    def build_rules(self) -> list[Rule]:
        rules: list[Rule] = []

        fr_find = self.query_one("#fr-find", Input).value.strip()
        if fr_find:
            fr_config = FindReplaceConfig(
                find_text=fr_find,
                replace_text=self.query_one("#fr-replace", Input).value,
                use_regex=self.query_one("#fr-regex", Checkbox).value,
                case_sensitive=self.query_one("#fr-case", Checkbox).value,
                encoding=self.query_one("#fr-encoding", Input).value.strip() or "utf-8",
            )
            rules.append(FindReplaceRule(fr_config))

        rn_pattern = self.query_one("#rn-pattern", Input).value.strip()
        if rn_pattern:
            rn_config = RenameConfig(
                pattern=rn_pattern,
                replacement=self.query_one("#rn-replace", Input).value,
                use_regex=self.query_one("#rn-regex", Checkbox).value,
                case_sensitive=self.query_one("#rn-case", Checkbox).value,
            )
            rules.append(RenameRule(rn_config))

        return rules
