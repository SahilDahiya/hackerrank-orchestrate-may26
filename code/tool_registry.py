from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_ai import FunctionToolset, RunContext, Tool

from corpus import (
    Breadcrumbs,
    breadcrumb_for_slice,
    iter_text_files,
    match_find_pattern,
    read_utf8_lines,
    relative_data_path,
    render_breadcrumb_block,
    resolve_data_path,
    strip_frontmatter,
)
from schemas import TicketDeps

CANONICAL_TOOL_NAMES = ("read", "grep", "find", "ls")

READ_MAX_LINES = 200
GREP_MAX_MATCHES = 20
GREP_CONTEXT_RADIUS = 1


def _render_ls_entries(entries: list[Path]) -> str:
    if not entries:
        return "(empty)"
    rendered: list[str] = []
    for entry in sorted(entries, key=lambda item: item.name.lower()):
        suffix = "/" if entry.is_dir() else ""
        rendered.append(f"{entry.name}{suffix}")
    return "\n".join(rendered)


def _render_find_results(*, data_root: Path, matches: list[Path]) -> str:
    if not matches:
        return "No matches found."
    return "\n".join(relative_data_path(data_root=data_root, path=path) for path in matches)


def _compile_pattern(pattern: str, *, literal: bool, ignore_case: bool) -> re.Pattern[str]:
    flags = re.IGNORECASE if ignore_case else 0
    source = re.escape(pattern) if literal else pattern
    return re.compile(source, flags)


def _excerpt_bounds(match_indexes: list[int], total_lines: int) -> tuple[int, int]:
    start = max(0, min(match_indexes) - GREP_CONTEXT_RADIUS)
    end = min(total_lines, max(match_indexes) + GREP_CONTEXT_RADIUS + 1)
    return start, end


def _render_grep_group(
    *,
    data_root: Path,
    path: Path,
    lines: list[str],
    match_indexes: list[int],
) -> str:
    start, end = _excerpt_bounds(match_indexes, len(lines))
    excerpt_lines = []
    for line_number in range(start, end):
        prefix = f"{line_number + 1}: "
        excerpt_lines.append(prefix + lines[line_number])
    breadcrumbs = breadcrumb_for_slice(
        data_root=data_root,
        path=path,
        lines=lines,
        start_index=match_indexes[0],
    )
    return render_breadcrumb_block(
        breadcrumbs=breadcrumbs,
        body="\n".join(excerpt_lines),
    )


def read(
    ctx: RunContext[TicketDeps],
    path: Annotated[str, Field(min_length=1)],
    offset: Annotated[int | None, Field(ge=1)] = None,
    limit: Annotated[int | None, Field(ge=1)] = None,
) -> str:
    """Read a UTF-8 text file with optional line slicing."""

    resolved = resolve_data_path(data_root=ctx.deps.data_root, tool_path=path)
    if not resolved.is_file():
        raise ValueError(f"path is not a file: {path}")

    lines = strip_frontmatter(read_utf8_lines(resolved))
    start_index = (offset - 1) if offset is not None else 0
    if not lines and offset not in (None, 1):
        raise ValueError(f"offset {offset} is beyond end of file")
    if start_index >= len(lines) and lines:
        raise ValueError(f"offset {offset} is beyond end of file")

    selected = lines[start_index:]
    effective_limit = min(limit if limit is not None else READ_MAX_LINES, READ_MAX_LINES)
    selected = selected[:effective_limit]
    body = "\n".join(selected)
    breadcrumbs = breadcrumb_for_slice(
        data_root=ctx.deps.data_root,
        path=resolved,
        lines=lines,
        start_index=start_index,
    )
    rendered = render_breadcrumb_block(breadcrumbs=breadcrumbs, body=body)
    if start_index + len(selected) < len(lines):
        next_offset = start_index + len(selected) + 1
        rendered += (
            f"\n\n[Showing lines {start_index + 1}-{start_index + len(selected)} "
            f"of {len(lines)}. Use offset={next_offset} to continue.]"
        )
    return rendered


def grep(
    ctx: RunContext[TicketDeps],
    pattern: Annotated[str, Field(min_length=1)],
    path: Annotated[str | None, Field(min_length=1)] = None,
    ignore_case: bool = False,
    literal: bool = False,
    limit: Annotated[int, Field(ge=1)] = GREP_MAX_MATCHES,
) -> str:
    """Search corpus files for matching lines and return grouped evidence blocks."""

    search_root = resolve_data_path(data_root=ctx.deps.data_root, tool_path=path)
    files = [search_root] if search_root.is_file() else iter_text_files(search_root)
    regex = _compile_pattern(pattern, literal=literal, ignore_case=ignore_case)

    grouped_matches: dict[Path, list[int]] = defaultdict(list)
    match_count = 0
    for file_path in files:
        try:
            lines = strip_frontmatter(read_utf8_lines(file_path))
        except UnicodeDecodeError:
            continue
        for line_index, line in enumerate(lines):
            if regex.search(line):
                grouped_matches[file_path].append(line_index)
                match_count += 1
                if match_count >= limit:
                    break
        if match_count >= limit:
            break

    if not grouped_matches:
        return "No matches found."

    blocks = []
    for file_path, match_indexes in grouped_matches.items():
        lines = strip_frontmatter(read_utf8_lines(file_path))
        blocks.append(
            _render_grep_group(
                data_root=ctx.deps.data_root,
                path=file_path,
                lines=lines,
                match_indexes=match_indexes,
            )
        )
    output = "\n\n---\n\n".join(blocks)
    if match_count >= limit:
        output += (
            f"\n\n[Showing up to {limit} matches. Narrow the pattern or path for more precise results.]"
        )
    return output


def find(
    ctx: RunContext[TicketDeps],
    pattern: Annotated[str, Field(min_length=1)],
    path: Annotated[str | None, Field(min_length=1)] = None,
) -> str:
    """Find matching files by glob-like pattern under the data root."""

    search_root = resolve_data_path(data_root=ctx.deps.data_root, tool_path=path)
    files = iter_text_files(search_root) if search_root.is_dir() else [search_root]
    matches = match_find_pattern(files, pattern)
    return _render_find_results(data_root=ctx.deps.data_root, matches=matches)


def ls(
    ctx: RunContext[TicketDeps],
    path: Annotated[str | None, Field(min_length=1)] = None,
) -> str:
    """List a directory under the data root."""

    resolved = resolve_data_path(data_root=ctx.deps.data_root, tool_path=path)
    if not resolved.is_dir():
        raise ValueError(f"path is not a directory: {path}")
    return _render_ls_entries(list(resolved.iterdir()))


READ_TOOL = Tool(
    read,
    takes_ctx=True,
    name="read",
    strict=True,
    sequential=False,
)
GREP_TOOL = Tool(
    grep,
    takes_ctx=True,
    name="grep",
    strict=True,
    sequential=False,
)
FIND_TOOL = Tool(
    find,
    takes_ctx=True,
    name="find",
    strict=True,
    sequential=False,
)
LS_TOOL = Tool(
    ls,
    takes_ctx=True,
    name="ls",
    strict=True,
    sequential=False,
)

TOOLS_BY_NAME = {
    "read": READ_TOOL,
    "grep": GREP_TOOL,
    "find": FIND_TOOL,
    "ls": LS_TOOL,
}


def build_canonical_toolset(
    tool_names: Sequence[str] = CANONICAL_TOOL_NAMES,
) -> FunctionToolset[TicketDeps]:
    resolved_tools = []
    seen_names: set[str] = set()
    for tool_name in tool_names:
        if tool_name in seen_names:
            raise ValueError(f"duplicate tool name: {tool_name}")
        seen_names.add(tool_name)
        try:
            resolved_tools.append(TOOLS_BY_NAME[tool_name])
        except KeyError as error:
            raise ValueError(f"unknown canonical tool: {tool_name}") from error
    return FunctionToolset[TicketDeps](resolved_tools, strict=True)
