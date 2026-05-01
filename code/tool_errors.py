from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic_ai.toolsets import WrapperToolset


class ToolOperationalError(Exception):
    """Expected tool-domain failure that should be shown to the model."""


class ToolPathError(ToolOperationalError):
    """Path or filesystem failure caused by tool input or target state."""


class ToolEncodingError(ToolOperationalError):
    """File content could not be interpreted as expected text."""


@dataclass
class ErrorWrappingToolset(WrapperToolset[Any]):
    async def call_tool(self, name, tool_args, ctx, tool):
        try:
            return await super().call_tool(name, tool_args, ctx, tool)
        except ToolOperationalError as error:
            return {
                "ok": False,
                "error_type": type(error).__name__,
                "message": str(error),
            }


__all__ = [
    "ErrorWrappingToolset",
    "ToolEncodingError",
    "ToolOperationalError",
    "ToolPathError",
]
