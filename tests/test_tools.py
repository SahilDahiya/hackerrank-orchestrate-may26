from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from schemas import TicketDeps  # noqa: E402
from tool_registry import find, grep, ls, read  # noqa: E402


class ToolContractTests(unittest.TestCase):
    def setUp(self) -> None:
        deps = TicketDeps(
            data_root=Path("data").resolve(),
            ticket_id="ticket-1",
            company="Claude",
        )
        self.ctx = SimpleNamespace(deps=deps)

    def test_ls_defaults_to_data_root(self) -> None:
        result = ls(self.ctx)
        self.assertIn("claude/", result)
        self.assertIn("hackerrank/", result)
        self.assertIn("visa/", result)

    def test_find_returns_matching_paths_only(self) -> None:
        result = find(self.ctx, pattern="*claude-code-faq*", path="claude")
        self.assertIn("claude/claude-code/12386420-claude-code-faq.md", result)
        self.assertNotIn("Title:", result)

    def test_read_renders_breadcrumb_header_and_continuation_hint(self) -> None:
        result = read(
            self.ctx,
            path="claude/claude-code/12386420-claude-code-faq.md",
            limit=5,
        )
        self.assertIn("Path: claude/claude-code/12386420-claude-code-faq.md", result)
        self.assertIn("Title: Claude Code FAQ", result)
        self.assertIn("[Showing lines 1-5", result)

    def test_grep_groups_file_matches_into_breadcrumbed_evidence_block(self) -> None:
        result = grep(
            self.ctx,
            pattern="single sign-on",
            path="claude/claude-code",
            ignore_case=True,
            limit=3,
        )
        self.assertIn("Path: claude/claude-code/12386420-claude-code-faq.md", result)
        self.assertIn("Section: How do I set up single sign-on (SSO) for Claude Code?", result)
        self.assertIn("8: ## How do I set up single sign-on (SSO) for Claude Code?", result)

    def test_tools_reject_paths_outside_data_root(self) -> None:
        with self.assertRaises(ValueError):
            read(self.ctx, path="../README.md")
        with self.assertRaises(ValueError):
            grep(self.ctx, pattern="Claude", path="../")
        with self.assertRaises(ValueError):
            find(self.ctx, pattern="*.md", path="../")
        with self.assertRaises(ValueError):
            ls(self.ctx, path="../")

    def test_read_rejects_offset_beyond_end_of_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            empty_file = tmp_root / "empty.md"
            empty_file.write_text("", encoding="utf-8")
            ctx = SimpleNamespace(
                deps=TicketDeps(
                    data_root=tmp_root.resolve(),
                    ticket_id="ticket-empty",
                    company="Claude",
                )
            )
            with self.assertRaises(ValueError):
                read(ctx, path="empty.md", offset=2)

    def test_grep_limit_notice_is_emitted_when_limit_is_hit(self) -> None:
        result = grep(
            self.ctx,
            pattern="Claude Code",
            path="claude/claude-code/12386420-claude-code-faq.md",
            limit=1,
        )
        self.assertIn("[Showing up to 1 matches.", result)
        self.assertEqual(result.count("Path: claude/claude-code/12386420-claude-code-faq.md"), 1)


if __name__ == "__main__":
    unittest.main()
