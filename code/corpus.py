from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path


FRONTMATTER_BOUNDARY = "---"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass(frozen=True)
class Breadcrumbs:
    path: str
    title: str | None
    section: str | None


class CorpusPathError(ValueError):
    """Raised when a tool path escapes the configured data root."""


def resolve_data_path(*, data_root: Path, tool_path: str | None) -> Path:
    base = data_root.resolve()
    if tool_path is None or tool_path == "":
        return base
    candidate = (base / tool_path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as error:
        raise CorpusPathError(
            f"path {tool_path!r} is outside the allowed data root"
        ) from error
    return candidate


def relative_data_path(*, data_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(data_root.resolve()))


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.name.startswith("."):
            files.append(path)
    return files


def match_find_pattern(paths: list[Path], pattern: str) -> list[Path]:
    return [path for path in paths if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(str(path), pattern)]


def read_utf8_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def read_utf8_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_title(lines: list[str]) -> str | None:
    in_frontmatter = False
    title_value: str | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if index == 0 and stripped == FRONTMATTER_BOUNDARY:
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == FRONTMATTER_BOUNDARY:
                break
            if stripped.startswith("title:"):
                value = stripped.split(":", 1)[1].strip().strip('"')
                if value:
                    title_value = value
        match = HEADING_RE.match(line)
        if match and match.group(1) == "#":
            return match.group(2).strip()
    return title_value


def strip_frontmatter(lines: list[str]) -> list[str]:
    if not lines or lines[0].strip() != FRONTMATTER_BOUNDARY:
        return lines
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_BOUNDARY:
            return lines[index + 1 :]
    return lines


def extract_section_for_line(lines: list[str], line_index: int) -> str | None:
    for reverse_index in range(min(line_index, len(lines) - 1), -1, -1):
        match = HEADING_RE.match(lines[reverse_index])
        if not match:
            continue
        level = len(match.group(1))
        if level >= 2:
            return match.group(2).strip()
    return None


def breadcrumb_for_slice(
    *,
    data_root: Path,
    path: Path,
    lines: list[str],
    start_index: int = 0,
) -> Breadcrumbs:
    return Breadcrumbs(
        path=relative_data_path(data_root=data_root, path=path),
        title=extract_title(lines),
        section=extract_section_for_line(lines, start_index),
    )


def render_breadcrumb_block(
    *,
    breadcrumbs: Breadcrumbs,
    body: str,
) -> str:
    header_lines = [f"Path: {breadcrumbs.path}"]
    if breadcrumbs.title:
        header_lines.append(f"Title: {breadcrumbs.title}")
    if breadcrumbs.section:
        header_lines.append(f"Section: {breadcrumbs.section}")
    body_text = body.strip("\n")
    if not body_text:
        return "\n".join(header_lines)
    return "\n".join([*header_lines, "", body_text])
