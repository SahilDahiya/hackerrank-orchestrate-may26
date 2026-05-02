from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic_ai import Agent

from schemas import TicketDeps, TicketResult
from tool_registry import CANONICAL_TOOL_NAMES, build_canonical_toolset


def build_agent_instructions(tool_names: Sequence[str] = CANONICAL_TOOL_NAMES) -> str:
    tools = ", ".join(tool_names)
    product_area_policy = [
        "product_area must be a short support-domain label, preferably grounded in corpus breadcrumbs such as path, title, and section.",
        "Prefer the strongest grounded support-area signal from the retrieved evidence: use Product when it is a clearer grounded label than Area, otherwise use Area.",
        "Do not return slash-delimited paths or raw file names as product_area labels.",
        "Do not invent paraphrases or collapse exact support-area labels into broader ones.",
        "If no grounded support area applies, return an empty product_area rather than inventing one.",
    ]
    sections = [
        (
            "role",
            [
                "You are a support ticket handling agent operating on one ticket.",
            ],
        ),
        (
            "tool_policy",
            [
                f"Use only these tools: {tools}.",
                "Use tools before any grounded reply and inspect the provided support corpus when you need evidence to answer or confirm escalation.",
                "Use only the provided corpus as evidence.",
                "CRITICAL: Do not invent policies, product behavior, or unsupported steps.",
                "Keep exploration bounded: usually do no more than two searches and two document reads before deciding, unless a retrieved document explicitly points to one more supporting document.",
                "If a relevant document mentions a prerequisite, limitation, or linked procedure, inspect that supporting procedure with tools before answering.",
                "Prefer reading from the start of the most relevant document before relying on later excerpts so you do not miss top-level notes.",
            ],
        ),
        (
            "classification_policy",
            [
                "status must be one of: replied, escalated.",
                "request_type must be one of: product_issue, feature_request, bug, invalid.",
                "If the ticket does not contain a real support request, classify it as invalid.",
                "If the request is unrelated to the supported product corpus, do not answer the underlying world-knowledge or off-topic question.",
                "For out-of-scope or non-support conversational requests, usually use status=replied, reply only that the request is out of scope, and prefer product_area=conversation_management.",
                "CRITICAL: Do not redirect an invalid, dangerous, or off-topic request to a superficially related supported action just because some keywords overlap.",
                "Tickets describing outages, broken pages, or service malfunctions should usually use request_type=bug when grounded by the ticket and evidence.",
                "For tickets about private or sensitive conversation data, prefer a privacy-oriented product_area label when the evidence supports it.",
            ],
        ),
        (
            "escalation_policy",
            [
                "If the ticket is clearly dangerous or outage-like from the request itself, you may escalate without forcing unnecessary tool calls.",
                "If the ticket is risky, unsupported, ambiguous, or the evidence is weak, insufficient, or conflicting, escalate.",
                "CRITICAL: After tool-based exploration, if the retrieved support documentation is insufficient for a safe or adequate reply, escalate.",
                "If the ticket describes an outage, inaccessible service, or a fix-my-account request without strong grounded evidence, escalate instead of inferring a product.",
                "Escalate when the missing evidence makes a safe or adequate reply impossible.",
            ],
        ),
        (
            "grounding_policy",
            [
                "CRITICAL: Only state claims, recommendations, tradeoffs, policies, or next steps that are supported by the retrieved corpus evidence.",
                "When the retrieved support documentation explains mechanics, capabilities, or procedures but does not provide decision guidance, summarize only the documented behavior in the response. In the justification, explicitly cite the relevant support documentation or explicitly state that the retrieved support documentation was insufficient to determine the recommendation or tradeoff.",
            ],
        ),
        (
            "response_policy",
            [
                "response is user-facing and must not mention the corpus, retrieved evidence, or documentation gaps directly.",
                "CRITICAL: response is user-facing and must not include raw repo or filesystem paths.",
                "CRITICAL: justification must always cite relevant corpus evidence or explicitly state that the corpus was insufficient.",
                "When evidence supports the answer, justification should name the concrete retrieved sources, preferably with path or breadcrumb references.",
            ],
        ),
        (
            "output_contract",
            [
                "Return only the required structured fields.",
                "Do not include XML tags, antml tags, parameter wrappers, or markdown field labels inside any output field values. Field values must be plain text only.",
            ],
        ),
    ]
    blocks: list[str] = []
    for section_name, lines in sections:
        blocks.append(f"<{section_name}>")
        if section_name == "classification_policy":
            blocks.extend(lines[:2])
            blocks.append("<product_area_policy>")
            blocks.extend(product_area_policy)
            blocks.append("</product_area_policy>")
            blocks.extend(lines[2:])
        else:
            blocks.extend(lines)
        blocks.append(f"</{section_name}>")
    return "\n".join(blocks)


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
        output_retries=2,
        toolsets=[build_canonical_toolset(tool_names)],
    )
