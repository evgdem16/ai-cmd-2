"""Parse and dispatch /commands."""

import os
import shlex
from typing import Optional

from modules.console_ui import (
    console,
    print_dialog_history,
    print_dialog_list,
    print_error,
    print_info,
    print_response_stats,
    print_rule,
    print_search_results,
    print_stats,
    print_success,
    print_system_prompt_list,
    print_warning,
    stream_and_render,
)
from modules.logger_setup import get_logger

logger = get_logger()

HELP_TEXT = """
[bold blue]Available commands[/bold blue]

[bold cyan]Dialog management[/bold cyan]
  [yellow]/new <name>[/yellow]           Create a new dialog (optional name)
  [yellow]/open <name>[/yellow]          Open an existing dialog
  [yellow]/switch <name>[/yellow]        Switch to another dialog (saves current)
  [yellow]/list[/yellow]                 List all dialogs
  [yellow]/delete <name>[/yellow]        Delete a dialog
  [yellow]/search <query>[/yellow]       Search through all dialog history
  [yellow]/history <n>[/yellow]          Show last N messages in current dialog
  [yellow]/stats[/yellow]                Show statistics for current dialog

[bold cyan]System prompts[/bold cyan]
  [yellow]/sp list[/yellow]              List all system prompts
  [yellow]/sp new <name>[/yellow]        Create a new system prompt (opens editor)
  [yellow]/sp edit <name>[/yellow]       Edit an existing system prompt
  [yellow]/sp delete <name>[/yellow]     Delete a system prompt
  [yellow]/sp show <name>[/yellow]       Show system prompt content
  [yellow]/sp apply <name>[/yellow]      Apply prompt to current dialog
  [yellow]/sp clear[/yellow]             Remove system prompt from current dialog
  [yellow]/sp current[/yellow]           Show currently applied system prompt

[bold cyan]RAG (file context)[/bold cyan]
  [yellow]/rag load <path>[/yellow]      Load file or directory into context
  [yellow]/rag list[/yellow]             Show loaded files
  [yellow]/rag clear[/yellow]            Clear all loaded files
  [yellow]/rag remove <path>[/yellow]    Remove a specific loaded file
  [yellow]/rag save <dir>[/yellow]       Save code blocks from dialog to directory

[bold cyan]Export[/bold cyan]
  [yellow]/export html <path>[/yellow]   Export dialog to HTML
  [yellow]/export pdf <path>[/yellow]    Export dialog to PDF
  [yellow]/export doc <path>[/yellow]    Export dialog to DOCX

[bold cyan]Interface[/bold cyan]
  [yellow]/clear[/yellow]                Clear the terminal screen
  [yellow]/help[/yellow]                 Show this help
  [yellow]/exit[/yellow] or [yellow]/quit[/yellow]        Exit the application

[dim]Tip: Press ↑ / ↓ to navigate input history. ← / → move cursor.[/dim]
"""


class CommandHandler:
    def __init__(self, config, dialog_manager, sp_manager, rag_manager, export_manager):
        self.cfg = config
        self.dm = dialog_manager
        self.spm = sp_manager
        self.rag = rag_manager
        self.exp = export_manager

    def is_command(self, text: str) -> bool:
        return text.strip().startswith("/")

    def handle(self, raw: str) -> bool:
        """
        Parse and execute a command.
        Returns True if the app should continue, False to exit.
        """
        raw = raw.strip()
        try:
            parts = shlex.split(raw)
        except ValueError:
            parts = raw.split()

        if not parts:
            return True

        cmd = parts[0].lower()
        args = parts[1:]

        # ── exit
        if cmd in ("/exit", "/quit"):
            self.dm.save()
            print_info("Goodbye! Context saved.")
            return False

        # ── help
        if cmd == "/help":
            console.print(HELP_TEXT)
            return True

        # ── clear
        if cmd == "/clear":
            os.system("cls" if os.name == "nt" else "clear")
            return True

        # ── stats
        if cmd == "/stats":
            if not self.dm.current_name:
                print_error("No active dialog.")
            else:
                print_stats(self.dm.get_stats(), self.dm.current_name)
            return True

        # ── dialog commands
        if cmd == "/new":
            name = args[0] if args else None
            actual = self.dm.create(name)
            self.dm.open(actual)
            print_success(f"Created and switched to dialog: [cyan]{actual}[/cyan]")
            return True

        if cmd == "/open":
            if not args:
                print_error("Usage: /open <name>"); return True
            if self.dm.open(args[0]):
                print_success(f"Opened dialog: [cyan]{args[0]}[/cyan]")
                print_rule(args[0])
                msgs = self.dm.get_display_messages(self.cfg.display_last_n)
                print_dialog_history(msgs)
            else:
                print_error(f"Dialog not found: {args[0]}")
            return True

        if cmd == "/switch":
            if not args:
                print_error("Usage: /switch <name>"); return True
            if self.dm.switch(args[0]):
                print_success(f"Switched to dialog: [cyan]{args[0]}[/cyan]")
                print_rule(args[0])
                msgs = self.dm.get_display_messages(self.cfg.display_last_n)
                print_dialog_history(msgs)
            else:
                print_error(f"Dialog not found: {args[0]}")
            return True

        if cmd == "/list":
            print_dialog_list(self.dm.list_dialogs())
            return True

        if cmd == "/delete":
            if not args:
                print_error("Usage: /delete <name>"); return True
            if self.dm.delete(args[0]):
                print_success(f"Deleted dialog: {args[0]}")
            else:
                print_error(f"Dialog not found: {args[0]}")
            return True

        if cmd == "/search":
            if not args:
                print_error("Usage: /search <query>"); return True
            query = " ".join(args)
            results = self.dm.search(query)
            print_search_results(results, query)
            return True

        if cmd == "/history":
            n = int(args[0]) if args and args[0].isdigit() else self.cfg.display_last_n
            if not self.dm.current_name:
                print_error("No active dialog."); return True
            msgs = self.dm.get_display_messages(n)
            print_rule(f"{self.dm.current_name} — last {n}")
            print_dialog_history(msgs)
            return True

        # ── system prompts  /sp <sub> ...
        if cmd == "/sp":
            return self._handle_sp(args)

        # ── RAG  /rag <sub> ...
        if cmd == "/rag":
            return self._handle_rag(args)

        # ── export  /export <fmt> [path]
        if cmd == "/export":
            return self._handle_export(args)

        print_warning(f"Unknown command: {cmd}  (try /help)")
        return True

    def _handle_sp(self, args: list[str]) -> bool:
        if not args:
            print_error("Usage: /sp <list|new|edit|delete|show|apply|clear|current>")
            return True
        sub = args[0].lower()
        name = args[1] if len(args) > 1 else None

        if sub == "list":
            print_system_prompt_list(self.spm.list_prompts())

        elif sub == "new":
            if not name:
                print_error("Usage: /sp new <name>"); return True
            content = self._multiline_input(f"Enter system prompt for '{name}'")
            if content:
                if self.spm.create(name, content):
                    print_success(f"System prompt '{name}' created.")
                else:
                    print_warning(f"Prompt '{name}' already exists. Use /sp edit to update.")
            else:
                print_warning("Aborted — empty content.")

        elif sub == "edit":
            if not name:
                print_error("Usage: /sp edit <name>"); return True
            if not self.spm.exists(name):
                print_error(f"Prompt '{name}' not found."); return True
            existing = self.spm.get(name)["content"]
            print_info(f"Current content:\n{existing}\n")
            content = self._multiline_input(f"New content for '{name}' (leave blank to cancel)")
            if content:
                self.spm.update(name, content)
                print_success(f"System prompt '{name}' updated.")
            else:
                print_warning("Aborted — no changes made.")

        elif sub == "delete":
            if not name:
                print_error("Usage: /sp delete <name>"); return True
            if self.spm.delete(name):
                print_success(f"System prompt '{name}' deleted.")
            else:
                print_error(f"Prompt '{name}' not found.")

        elif sub == "show":
            if not name:
                print_error("Usage: /sp show <name>"); return True
            p = self.spm.get(name)
            if not p:
                print_error(f"Prompt '{name}' not found."); return True
            console.print(f"[bold yellow]{name}[/bold yellow]")
            console.print(f"[dim]Created: {p.get('created_at','')}  "
                          f"Updated: {p.get('updated_at','')}[/dim]")
            console.print(p["content"])

        elif sub == "apply":
            if not name:
                print_error("Usage: /sp apply <name>"); return True
            if not self.dm.current_name:
                print_error("No active dialog."); return True
            p = self.spm.get(name)
            if not p:
                print_error(f"Prompt '{name}' not found."); return True
            self.dm.set_system_prompt(p["content"])
            print_success(f"System prompt '{name}' applied to dialog "
                          f"[cyan]{self.dm.current_name}[/cyan].")

        elif sub == "clear":
            if not self.dm.current_name:
                print_error("No active dialog."); return True
            self.dm.set_system_prompt(None)
            print_success("System prompt cleared for current dialog.")

        elif sub == "current":
            sp = self.dm.get_system_prompt()
            if sp:
                console.print("[bold yellow]Active system prompt:[/bold yellow]")
                console.print(sp)
            else:
                print_info("No system prompt applied to current dialog.")
        else:
            print_warning(f"Unknown /sp sub-command: {sub}")
        return True

    def _handle_rag(self, args: list[str]) -> bool:
        if not args:
            print_error("Usage: /rag <load|list|clear|remove|save>"); return True
        sub = args[0].lower()

        if sub == "load":
            if len(args) < 2:
                print_error("Usage: /rag load <path>"); return True
            path = " ".join(args[1:])
            loaded = self.rag.load_path(path)
            if loaded:
                for p in loaded:
                    print_success(f"Loaded: {p}")
            else:
                print_error(f"No files loaded from: {path}")

        elif sub == "list":
            files = self.rag.list_files()
            if files:
                console.print("[bold]Loaded RAG files:[/bold]")
                for f in files:
                    print_info(f"  {f}")
            else:
                print_info("No files loaded.")

        elif sub == "clear":
            self.rag.clear()
            print_success("RAG context cleared.")

        elif sub == "remove":
            if len(args) < 2:
                print_error("Usage: /rag remove <path>"); return True
            path = " ".join(args[1:])
            if self.rag.remove(path):
                print_success(f"Removed: {path}")
            else:
                print_error(f"Not loaded: {path}")

        elif sub == "save":
            if len(args) < 2:
                print_error("Usage: /rag save <directory>"); return True
            dest = " ".join(args[1:])
            if not self.dm.current_name:
                print_error("No active dialog."); return True
            msgs = self.dm.current_dialog.get("messages", [])
            saved = self.rag.save_to_directory(msgs, dest)
            if saved:
                for p in saved:
                    print_success(f"Saved: {p}")
            else:
                print_warning("No code blocks found in the dialog.")
        else:
            print_warning(f"Unknown /rag sub-command: {sub}")
        return True

    def _handle_export(self, args: list[str]) -> bool:
        if not args:
            print_error("Usage: /export <html|pdf|doc> [path]"); return True
        if not self.dm.current_name or not self.dm.current_dialog:
            print_error("No active dialog."); return True

        fmt = args[0].lower()
        dest = " ".join(args[1:]) or None
        dialog = self.dm.current_dialog

        try:
            if fmt == "html":
                path = self.exp.export_html(dialog, dest)
            elif fmt == "pdf":
                path = self.exp.export_pdf(dialog, dest)
            elif fmt in ("doc", "docx"):
                path = self.exp.export_docx(dialog, dest)
            else:
                print_error(f"Unknown format: {fmt}  (html / pdf / doc)")
                return True
            print_success(f"Exported to: [cyan]{path}[/cyan]")
        except Exception as exc:
            print_error(f"Export failed: {exc}")
        return True

    def _multiline_input(self, prompt: str) -> str:
        """Simple multi-line input; end with a line containing only '.' """
        console.print(f"[dim]{prompt}[/dim]")
        console.print("[dim](Enter text. Finish with a single '.' on a line)[/dim]")
        lines = []
        while True:
            try:
                line = input()
            except (EOFError, KeyboardInterrupt):
                return ""
            if line == ".":
                break
            lines.append(line)
        return "\n".join(lines)
