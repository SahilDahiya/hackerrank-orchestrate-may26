from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

from agent import build_agent_instructions  # noqa: E402
from tool_registry import CANONICAL_TOOL_NAMES, build_canonical_toolset  # noqa: E402


class AgentContractTests(unittest.TestCase):
    def test_build_agent_instructions_includes_locked_prompt_policy(self) -> None:
        instructions = build_agent_instructions()
        self.assertIn("Use only these tools: read, grep, find, ls.", instructions)
        self.assertIn(
            "Always inspect the provided support corpus with tools before answering.",
            instructions,
        )
        self.assertIn("status must be one of: replied, escalated.", instructions)
        self.assertIn(
            "request_type must be one of: product_issue, feature_request, bug, invalid.",
            instructions,
        )
        self.assertIn(
            "justification must cite evidence from the provided corpus or explicitly state that the corpus was insufficient.",
            instructions,
        )

    def test_build_agent_instructions_reflects_requested_tool_subset(self) -> None:
        instructions = build_agent_instructions(("read", "ls"))
        self.assertIn("Use only these tools: read, ls.", instructions)

    def test_build_canonical_toolset_rejects_unknown_tool_names(self) -> None:
        with self.assertRaises(ValueError):
            build_canonical_toolset(("read", "shell"))

    def test_build_canonical_toolset_rejects_duplicate_tool_names(self) -> None:
        with self.assertRaises(ValueError):
            build_canonical_toolset(("read", "read"))

    def test_build_canonical_toolset_rejects_empty_toolset(self) -> None:
        with self.assertRaises(ValueError):
            build_canonical_toolset(())


if __name__ == "__main__":
    unittest.main()
