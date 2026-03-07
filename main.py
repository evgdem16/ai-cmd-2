#!/usr/bin/env python3
"""
LM Chat — Console chat client for LM Studio.
Entry point: python main.py
"""

import os
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings

from modules.api_client import APIClient
from modules.command_handler import CommandHandler
from modules.config_manager import ConfigManager
from modules.console_ui import (
    console,
    print_error,
    print_info,
    print_response_stats,
    print_rule,
    print_welcome,
    stream_and_render,
    print_dialog_history,
)
from modules.dialog_manager import DialogManager
from modules.export_manager import ExportManager
from modules.logger_setup import setup_logger
from modules.rag_manager import RAGManager
from modules.system_prompts_manager import SystemPromptsManager


def _build_prompt(dialog_name: str) -> HTML:
    return HTML(
        f"<ansibrightblue>[{dialog_name}]</ansibrightblue> "
        "<ansiyellow>❯</ansiyellow> "
    )


def _build_bindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add("c-c")
    def _interrupt(event):
        event.app.exit(result=None)

    @kb.add("c-d")
    def _eof(event):
        event.app.exit(result="/exit")

    return kb


def main() -> None:
    # ── config
    cfg = ConfigManager("config.json")

    # ── logger
    setup_logger(cfg.log_file, cfg.log_level)
    from modules.logger_setup import get_logger
    logger = get_logger()
    logger.info("Application started")

    # ── ensure dirs exist
    os.makedirs(cfg.dialogs_dir, exist_ok=True)
    os.makedirs(cfg.exports_dir, exist_ok=True)
    os.makedirs(os.path.dirname(cfg.log_file), exist_ok=True)

    # ── managers
    dm = DialogManager(
        dialogs_dir=cfg.dialogs_dir,
        default_name=cfg.default_dialog_name,
        context_limit=cfg.context_limit,
        display_last_n=cfg.display_last_n,
    )
    spm = SystemPromptsManager(cfg.system_prompts_file)
    rag = RAGManager()
    exp = ExportManager(cfg.exports_dir)

    # ── API client
    try:
        api = APIClient(
            base_url=cfg.base_url,
            api_key=cfg.api_key,
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
        )
    except ImportError: 
        console.print("[bold red]Run: pip install openai[/bold red]")
        sys.exit(1)

    # ── command handler
    handler = CommandHandler(cfg, dm, spm, rag, exp)

    # ── create / open default dialog
    existing = dm.list_dialogs()
    if existing:
        dm.open(existing[0]["name"])
    else:
        name = dm.create()
        dm.open(name)

    # ── welcome banner
    print_welcome(dm.current_name or "dialog")

    # Show recent history
    msgs = dm.get_display_messages(cfg.display_last_n)
    if msgs:
        print_rule("Recent messages")
        print_dialog_history(msgs, cfg.display_last_n)
        print_rule()

    # ── prompt_toolkit session (provides cursor movement + history)
    history = InMemoryHistory()
    session: PromptSession = PromptSession(
        history=history,
        key_bindings=_build_bindings(),
        enable_history_search=False,
        multiline=False,
    )

    # ── main loop
    while True:
        try:
            dialog_label = dm.current_name or "no-dialog"
            if rag.has_files():
                dialog_label += f" +{len(rag.list_files())}f"

            user_input = session.prompt(_build_prompt(dialog_label))
        except KeyboardInterrupt:
            continue
        except EOFError:
            dm.save()
            print_info("Goodbye!")
            break

        if user_input is None or user_input.strip() == "":
            continue

        text = user_input.strip()

        # ── commands
        if handler.is_command(text):
            should_continue = handler.handle(text)
            if not should_continue:
                break
            continue

        # ── chat
        if not dm.current_name:
            name = dm.create()
            dm.open(name)
            print_info(f"Created new dialog: {name}")

        # Build prompt with RAG context
        final_text = text
        if rag.has_files():
            ctx_block = rag.build_context_block()
            final_text = ctx_block + "\n\n" + text

        # Save user message (without RAG context)
        dm.add_user_message(text)

        # Build LLM message list
        context = dm.get_context_messages()
        # Replace last user message content with the RAG-enriched version
        if context and rag.has_files():
            context[-1] = {"role": "user", "content": final_text}

        system_prompt = dm.get_system_prompt()

        logger.info(f"User input: {text[:80]}{'…' if len(text)>80 else ''}")

        # Stream response
        try:
            gen, stats = api.stream_chat(context, system_prompt=system_prompt)
            full_response = stream_and_render(gen)
            print_response_stats(stats)
        except Exception as exc:
            print_error(f"API error: {exc}")
            logger.error(f"API error: {exc}")
            continue

        # Save assistant message
        dm.add_assistant_message(full_response, stats)
        logger.info(f"Response saved. tokens={stats.get('tokens',0)}")


if __name__ == "__main__":
    main()
