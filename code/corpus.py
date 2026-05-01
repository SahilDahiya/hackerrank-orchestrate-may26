from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path


FRONTMATTER_BOUNDARY = "---"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
CORPUS_ROOT_DIRS = {"claude", "hackerrank", "visa"}


@dataclass(frozen=True)
class Breadcrumbs:
    path: str
    area: str | None
    product: str | None
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


def extract_product_heading_for_line(
    lines: list[str],
    line_index: int,
    *,
    title: str | None,
) -> str | None:
    for reverse_index in range(min(line_index, len(lines) - 1), -1, -1):
        match = HEADING_RE.match(lines[reverse_index])
        if not match:
            continue
        if match.group(1) != "#":
            continue
        heading = match.group(2).strip()
        if title and heading == title:
            continue
        return _slug_to_label(heading)
    return None


def breadcrumb_for_slice(
    *,
    data_root: Path,
    path: Path,
    lines: list[str],
    start_index: int = 0,
) -> Breadcrumbs:
    relative_path = relative_data_path(data_root=data_root, path=path)
    area = derive_area_label(relative_path)
    title = extract_title(lines)
    return Breadcrumbs(
        path=relative_path,
        area=area,
        product=extract_product_heading_for_line(lines, start_index, title=title),
        title=title,
        section=extract_section_for_line(lines, start_index),
    )


def render_breadcrumb_block(
    *,
    breadcrumbs: Breadcrumbs,
    body: str,
) -> str:
    header_lines = [f"Path: {breadcrumbs.path}"]
    if breadcrumbs.area:
        header_lines.append(f"Area: {breadcrumbs.area}")
    if breadcrumbs.product:
        header_lines.append(f"Product: {breadcrumbs.product}")
    if breadcrumbs.title:
        header_lines.append(f"Title: {breadcrumbs.title}")
    if breadcrumbs.section:
        header_lines.append(f"Section: {breadcrumbs.section}")
    body_text = body.strip("\n")
    if not body_text:
        return "\n".join(header_lines)
    return "\n".join([*header_lines, "", body_text])


def _slug_to_label(value: str) -> str:
    stem = Path(value).stem
    cleaned = stem.strip().lower().replace("-", "_").replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "general_support"


def derive_area_label(relative_path: str) -> str | None:
    parts = Path(relative_path).parts
    if not parts:
        return None

    if parts[0] == "hackerrank":
        if len(parts) >= 2:
            return _slug_to_label(parts[1])
        return "hackerrank"

    if parts[0] == "screen":
        return "screen"

    if parts[0] == "hackerrank_community":
        return "community"

    if parts[0] == "claude":
        if len(parts) >= 3 and parts[1] == "claude":
            return _slug_to_label(parts[2])
        if len(parts) >= 2:
            return _slug_to_label(parts[1])
        return "claude"

    if parts[0] in {"account-management", "conversation-management"}:
        return _slug_to_label(parts[0])

    if parts[0] == "visa":
        if len(parts) == 2 and parts[1] == "support.md":
            return "general_support"
        if len(parts) >= 4 and parts[1:4] == ("support", "consumer", "travelers-cheques.md"):
            return "travel_support"
        if len(parts) >= 4 and parts[1:4] == ("support", "consumer", "travel-support.md"):
            return "travel_support"
        if len(parts) >= 2:
            return _slug_to_label(parts[1])
        return "visa"

    if parts[0] == "support":
        if len(parts) == 1:
            return "general_support"
        if len(parts) >= 2 and parts[1] == "consumer":
            if len(parts) >= 3 and parts[2] in {"travelers-cheques.md", "travel-support.md"}:
                return "travel_support"
            return "general_support"
        return "general_support"

    return _slug_to_label(parts[0])
