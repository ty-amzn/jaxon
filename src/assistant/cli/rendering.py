"""Markdown and code rendering helpers using Rich."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


console = Console()


def render_markdown(text: str) -> Markdown:
    """Create a Rich Markdown renderable."""
    return Markdown(text)


def render_tool_call(name: str, inputs: dict) -> Panel:
    """Render a tool call as a Rich panel."""
    detail_lines = [f"  {k}: {v}" for k, v in inputs.items()]
    detail_text = "\n".join(detail_lines)
    return Panel(
        Text(f"{name}\n{detail_text}"),
        title="[yellow]Tool Call[/yellow]",
        border_style="yellow",
        expand=False,
    )


def render_tool_result(result: str, is_error: bool = False) -> Panel:
    """Render a tool result as a Rich panel."""
    style = "red" if is_error else "green"
    title = "[red]Tool Error[/red]" if is_error else "[green]Tool Result[/green]"
    truncated = result[:2000] + "..." if len(result) > 2000 else result
    return Panel(
        Text(truncated),
        title=title,
        border_style=style,
        expand=False,
    )


def render_permission_request(description: str, category: str) -> Panel:
    """Render a permission approval request."""
    return Panel(
        Text(f"{description}\nCategory: {category}"),
        title="[bold red]Permission Required[/bold red]",
        border_style="red",
        expand=False,
    )
