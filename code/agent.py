from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic_ai import Agent

from schemas import TicketDeps, TicketResult
from tool_registry import CANONICAL_TOOL_NAMES, build_canonical_toolset


def build_agent_instructions(tool_names: Sequence[str] = CANONICAL_TOOL_NAMES) -> str:
    tools = ", ".join(tool_names)
    return "\n".join(
        [
            "You are a support ticket handling agent operating on one ticket.",
            f"Use only these tools: {tools}.",
            "Always inspect the provided support corpus with tools before answering.",
            "Use only the provided corpus as evidence.",
            "Do not invent policies, product behavior, or unsupported steps.",
            "If the ticket is risky, unsupported, ambiguous, or the evidence is weak, insufficient, or conflicting, escalate.",
            "status must be one of: replied, escalated.",
            "request_type must be one of: product_issue, feature_request, bug, invalid.",
            "product_area must be a short support-domain label, preferably grounded in corpus breadcrumbs such as path, title, and section.",
            "response is user-facing and must not include raw repo or filesystem paths.",
            "justification must cite evidence from the provided corpus or explicitly state that the corpus was insufficient.",
            "Return only the required structured fields.",
        ]
    )


def build_canonical_agent(
    *,
    model: Any,
    tool_names: Sequence[str] = CANONICAL_TOOL_NAMES,
) -> Agent[TicketDeps, TicketResult]:
    return Agent(
        model,
        output_type=TicketResult,
        instructions=build_agent_instructions(tool_names),
        deps_type=TicketDeps,
        toolsets=[build_canonical_toolset(tool_names)],
    )
