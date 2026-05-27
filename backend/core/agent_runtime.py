from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agent_framework import FunctionTool

from core.config import Settings


@dataclass
class AgentRuntime:
    """Microsoft Agent Framework runtime for the RFP pipeline."""

    settings: Settings
    tools: list[FunctionTool] = field(default_factory=list)

    def register_tools(self, tools: list[FunctionTool]) -> None:
        self.tools.extend(tools)


def make_tool(
    func: Callable[..., Any],
    *,
    name: str,
    description: str = "",
) -> FunctionTool:
    return FunctionTool(name=name, description=description, func=func)


async def build_agent_runtime(settings: Settings) -> AgentRuntime:
    """Bootstrap the Microsoft Agent Framework runtime on app startup."""
    return AgentRuntime(settings=settings)
