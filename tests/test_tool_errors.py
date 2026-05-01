from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from pydantic_ai import RunContext  # noqa: E402
from pydantic_ai.models.test import TestModel  # noqa: E402
from pydantic_ai.usage import RunUsage  # noqa: E402

from schemas import TicketDeps  # noqa: E402
from tool_registry import build_canonical_toolset  # noqa: E402


class ToolErrorWrappingTests(unittest.TestCase):
    def test_expected_tool_misuse_becomes_model_visible_error_result(self) -> None:
        ctx = RunContext(
            deps=TicketDeps(
                data_root=Path("data").resolve(),
                ticket_id="ticket-1",
                company="Claude",
            ),
            model=TestModel(),
            usage=RunUsage(),
        )
        toolset = build_canonical_toolset()
        tools = asyncio.run(toolset.get_tools(ctx))
        result = asyncio.run(toolset.call_tool("ls", {"path": "claude/index.md"}, ctx, tools["ls"]))

        self.assertEqual(result["ok"], False)
        self.assertEqual(result["error_type"], "ToolPathError")
        self.assertIn("path is not a directory", result["message"])


if __name__ == "__main__":
    unittest.main()
