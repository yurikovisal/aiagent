"""Tool Registry. Agents may only call tools listed in their `allowed_tools`."""

from __future__ import annotations

from meza.tools.base import Tool

_REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    _REGISTRY[tool.name] = tool
    return tool


def get_tool(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def all_tools() -> list[Tool]:
    return list(_REGISTRY.values())


def manifest() -> list[dict]:
    return [t.to_manifest() for t in all_tools()]


def _bootstrap() -> None:
    if _REGISTRY:
        return
    from meza.tools import defs  # noqa: F401  (import triggers registration)


_bootstrap()
