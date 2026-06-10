from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, DataTable

from filebatch.core.engine import BatchResult
from filebatch.rules.base import RuleResult


class ResultSummary(Vertical):
    DEFAULT_CSS = """
    ResultSummary {
        height: 1fr;
        margin: 0 0 0 0;
        border: round $success;
        Static#result-title {
            text-style: bold;
            margin-bottom: 0;
        }
        DataTable {
            height: 1fr;
        }
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("📊 Results", id="result-title")
        table = DataTable(id="result-table")
        table.add_columns("File", "Rule", "Status", "Message")
        yield table

    def update_result(self, result: BatchResult) -> None:
        table = self.query_one("#result-table", DataTable)
        table.clear()

        for detail in result.details:
            status = "✅" if detail.success else ("⏭️" if detail.skipped else "❌")
            table.add_row(
                detail.file_path.name,
                detail.rule_name,
                status,
                detail.message,
            )

        summary = self.query_one("#result-title", Static)
        summary.update(
            f"📊 Results  |  "
            f"Total: {result.total}  |  "
            f"✅ {result.success}  |  "
            f"❌ {result.failed}  |  "
            f"⏭️ {result.skipped}"
        )

    def append_row(self, detail: RuleResult) -> None:
        table = self.query_one("#result-table", DataTable)
        status = "✅" if detail.success else ("⏭️" if detail.skipped else "❌")
        table.add_row(
            detail.file_path.name,
            detail.rule_name,
            status,
            detail.message,
        )

    def set_summary(self, result: BatchResult) -> None:
        summary = self.query_one("#result-title", Static)
        summary.update(
            f"📊 Results  |  "
            f"Total: {result.total}  |  "
            f"✅ {result.success}  |  "
            f"❌ {result.failed}  |  "
            f"⏭️ {result.skipped}"
        )

    def clear_results(self) -> None:
        table = self.query_one("#result-table", DataTable)
        table.clear()
        summary = self.query_one("#result-title", Static)
        summary.update("📊 Results")
