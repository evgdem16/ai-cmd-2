"""Console UI — rich output, syntax highlighting, streaming display."""

from typing import Generator, Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

console = Console(highlight=True)


_ROLE_STYLE = {
    "user":      "bold cyan",
    "assistant": "bold green",
    "system":    "bold yellow",
}
_ROLE_LABEL = {
    "user":      "You",
    "assistant": "Assistant",
    "system":    "System",
}


def print_message(msg: dict, show_ts: bool = True) -> None:
    role = msg.get("role", "user")
    content = msg.get("content", "")
    ts = msg.get("timestamp", "")
    style = _ROLE_STYLE.get(role, "white")
    label = _ROLE_LABEL.get(role, role.upper())

    header = f"[{style}]{label}[/{style}]"
    if show_ts and ts:
        header += f"  [dim]{ts}[/dim]"

    console.print()
    console.print(header)
    console.print(Markdown(content))


def print_dialog_history(messages: list[dict], n: Optional[int] = None) -> None:
    if not messages:
        console.print("[dim]  (no messages yet)[/dim]")
        return
    subset = messages[-n:] if n else messages
    for msg in subset:
        print_message(msg)


def stream_and_render(generator: Generator[str, None, None]) -> str:
    """
    Stream tokens live with markdown rendering.
    Returns the full accumulated text.
    """
    full_text = ""
    console.print()
    console.print("[bold green]Assistant[/bold green]")

    with Live("", console=console, refresh_per_second=8,
              vertical_overflow="visible") as live:
        for chunk in generator:
            full_text += chunk
            live.update(Markdown(full_text + " ▌"))

        live.update(Markdown(full_text))

    console.print()
    return full_text


def print_stats(stats: dict, dialog_name: Optional[str] = None) -> None:
    title = f"📊 Statistics — {dialog_name}" if dialog_name else "📊 Statistics"
    table = Table(title=title, box=box.ROUNDED, style="dim",
                  title_style="bold blue")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    table.add_row("Total messages", str(stats.get("total_messages", 0)))
    table.add_row("Total tokens", str(stats.get("total_tokens", 0)))
    table.add_row("Total response time",
                  f"{stats.get('total_response_time', 0):.2f}s")

    msg_count = stats.get("total_messages", 0)
    if msg_count:
        avg_tokens = stats.get("total_tokens", 0) / max(msg_count // 2, 1)
        avg_time = stats.get("total_response_time", 0) / max(msg_count // 2, 1)
        table.add_row("Avg tokens / response", f"{avg_tokens:.0f}")
        table.add_row("Avg response time", f"{avg_time:.2f}s")

    console.print(table)


def print_response_stats(stats: dict) -> None:
    if stats.get("error"):
        console.print(f"[red]⚠ {stats['error']}[/red]")
        return
    parts = []
    if stats.get("tokens"):
        parts.append(f"tokens: [cyan]{stats['tokens']}[/cyan]")
    if stats.get("response_time"):
        parts.append(f"time: [cyan]{stats['response_time']:.2f}s[/cyan]")
    if parts:
        console.print(f"[dim]  {' │ '.join(parts)}[/dim]")


def print_dialog_list(dialogs: list[dict]) -> None:
    if not dialogs:
        console.print("[dim]No dialogs found.[/dim]")
        return
    table = Table(title="Dialogs", box=box.ROUNDED, title_style="bold blue")
    table.add_column("", width=2)
    table.add_column("Name", style="cyan")
    table.add_column("Messages", justify="right")
    table.add_column("Updated at", style="dim")

    for d in dialogs:
        marker = "▶" if d.get("active") else " "
        style = "bold" if d.get("active") else ""
        table.add_row(marker, d["name"], str(d["messages"]),
                      d.get("updated_at", ""), style=style)
    console.print(table)


def print_system_prompt_list(prompts: list[dict]) -> None:
    if not prompts:
        console.print("[dim]No system prompts saved.[/dim]")
        return
    table = Table(title="System Prompts", box=box.ROUNDED, title_style="bold yellow")
    table.add_column("Name", style="yellow")
    table.add_column("Preview")
    table.add_column("Updated at", style="dim")
    for p in prompts:
        table.add_row(p["name"], p["preview"], p.get("updated_at", ""))
    console.print(table)


def print_search_results(results: list[dict], query: str) -> None:
    if not results:
        console.print(f"[dim]No results for '[yellow]{query}[/yellow]'.[/dim]")
        return
    console.print(f"\n[bold]Search results for '[yellow]{query}[/yellow]':[/bold]")
    for r in results:
        snippet = r.get("snippet", "")
        # Highlight query in snippet
        hi = snippet.replace(query, f"[bold yellow]{query}[/bold yellow]")
        console.print(
            f"  [cyan]{r['dialog']}[/cyan] › [dim]{r['role']}[/dim] "
            f"[dim]{r.get('timestamp','')}[/dim]\n  {hi}\n"
        )


def print_rule(title: str = "") -> None:
    console.print(Rule(title, style="dim"))


def print_error(msg: str) -> None:
    console.print(f"[bold red]✗ {msg}[/bold red]")


def print_success(msg: str) -> None:
    console.print(f"[bold green]✓ {msg}[/bold green]")


def print_info(msg: str) -> None:
    console.print(f"[dim]{msg}[/dim]")


def print_warning(msg: str) -> None:
    console.print(f"[bold yellow]⚠ {msg}[/bold yellow]")


def print_welcome(dialog_name: str) -> None:
    panel = Panel(
        "[bold]LM Studio Chat[/bold]\n"
        "[dim]Type your message and press Enter.\n"
        "Use [cyan]/help[/cyan] to see all available commands.[/dim]",
        title="[bold blue]Welcome[/bold blue]",
        border_style="blue",
    )
    console.print(panel)
    console.print(f"[dim]Active dialog:[/dim] [cyan]{dialog_name}[/cyan]\n")
