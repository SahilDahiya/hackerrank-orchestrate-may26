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
            "Use tools before any grounded reply and inspect the provided support corpus when you need evidence to answer or confirm escalation.",
            instructions,
        )
        self.assertIn(
            "Keep exploration bounded: usually do no more than two searches and two document reads before deciding, unless a retrieved document explicitly points to one more supporting document.",
            instructions,
        )
        self.assertIn(
            "If the ticket is clearly dangerous or outage-like from the request itself, you may escalate without forcing unnecessary tool calls.",
            instructions,
        )
        self.assertIn(
            "After tool-based exploration, if the retrieved support documentation is insufficient for a safe or adequate reply, escalate.",
            instructions,
        )
        self.assertIn("status must be one of: replied, escalated.", instructions)
        self.assertIn(
            "request_type must be one of: product_issue, feature_request, bug, invalid.",
            instructions,
        )
        self.assertIn(
            "response is user-facing and must not mention the corpus, retrieved evidence, or documentation gaps directly.",
            instructions,
        )
        self.assertIn(
            "justification must always cite relevant corpus evidence or explicitly state that the corpus was insufficient.",
            instructions,
        )
        self.assertIn(
            "When evidence supports the answer, justification should name the concrete retrieved sources, preferably with path or breadcrumb references.",
            instructions,
        )
        self.assertIn(
            "Prefer the strongest grounded support-area signal from the retrieved evidence: use Product when it is a clearer grounded label than Area, otherwise use Area.",
            instructions,
        )
        self.assertIn(
            "If no grounded support area applies, return an empty product_area rather than inventing one.",
            instructions,
        )
        self.assertIn(
            "Do not return slash-delimited paths or raw file names as product_area labels.",
            instructions,
        )
        self.assertIn(
            "If the ticket does not contain a real support request, classify it as invalid.",
            instructions,
        )
        self.assertIn(
            "If the request is unrelated to the supported product corpus, do not answer the underlying world-knowledge or off-topic question.",
            instructions,
        )
        self.assertIn(
            "For out-of-scope or non-support conversational requests, usually use status=replied, reply only that the request is out of scope, and prefer product_area=conversation_management.",
            instructions,
        )
        self.assertIn(
            "Do not redirect an invalid, dangerous, or off-topic request to a superficially related supported action just because some keywords overlap.",
            instructions,
        )
        self.assertIn(
            "If the ticket describes an outage, inaccessible service, or a fix-my-account request without strong grounded evidence, escalate instead of inferring a product.",
            instructions,
        )
        self.assertIn(
            "Tickets describing outages, broken pages, or service malfunctions should usually use request_type=bug when grounded by the ticket and evidence.",
            instructions,
        )
        self.assertIn(
            "For tickets about private or sensitive conversation data, prefer a privacy-oriented product_area label when the evidence supports it.",
            instructions,
        )
        self.assertIn(
            "Do not invent paraphrases or collapse exact support-area labels into broader ones.",
            instructions,
        )
        self.assertIn(
            "If a relevant document mentions a prerequisite, limitation, or linked procedure, inspect that supporting procedure with tools before answering.",
            instructions,
        )
        self.assertIn(
            "Prefer reading from the start of the most relevant document before relying on later excerpts so you do not miss top-level notes.",
            instructions,
        )
        self.assertIn(
            "Only state claims, recommendations, tradeoffs, policies, or next steps that are supported by the retrieved corpus evidence.",
            instructions,
        )
        self.assertIn(
            "When the retrieved support documentation explains mechanics, capabilities, or procedures but does not provide decision guidance, summarize only the documented behavior in the response. In the justification, explicitly cite the relevant support documentation or explicitly state that the retrieved support documentation was insufficient to determine the recommendation or tradeoff.",
            instructions,
        )
        self.assertIn(
            "Escalate when the missing evidence makes a safe or adequate reply impossible.",
            instructions,
        )
        self.assertIn(
            "Do not include XML tags, antml tags, parameter wrappers, or markdown field labels inside any output field values. Field values must be plain text only.",
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
