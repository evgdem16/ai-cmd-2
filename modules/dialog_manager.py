"""Dialog management: create, open, switch, delete, list, search, save."""

import json
import os
import re
from datetime import datetime
from typing import Optional

from modules.logger_setup import get_logger

logger = get_logger()

# Fields that must NOT be sent to the LLM
_DEBUG_KEYS = {"_debug", "_stats", "id", "timestamp"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class DialogManager:
    def __init__(self, dialogs_dir: str, default_name: str = "dialog",
                 context_limit: int = -1, display_last_n: int = 10):
        self.dialogs_dir = dialogs_dir
        self.default_name = default_name
        self.context_limit = context_limit
        self.display_last_n = display_last_n

        os.makedirs(self.dialogs_dir, exist_ok=True)

        self.current_dialog: Optional[dict] = None
        self.current_name: Optional[str] = None

    def _path(self, name: str) -> str:
        return os.path.join(self.dialogs_dir, f"{name}.json")

    def _exists(self, name: str) -> bool:
        return os.path.exists(self._path(name))

    def create(self, name: Optional[str] = None) -> str:
        """Create a new dialog. Returns the actual name used."""
        if not name:
            name = self._unique_name(self.default_name)
        else:
            name = self._sanitise(name)
            if self._exists(name):
                name = self._unique_name(name)

        dialog = {
            "name": name,
            "created_at": _now(),
            "updated_at": _now(),
            "system_prompt": None,
            "messages": [],
            "_stats": {
                "total_tokens": 0,
                "total_messages": 0,
                "total_response_time": 0.0,
            },
        }
        self._write(name, dialog)
        logger.info(f"Created dialog: {name}")
        return name

    def open(self, name: str) -> bool:
        """Load a dialog as the current one. Returns True on success."""
        name = self._sanitise(name)
        if not self._exists(name):
            return False
        self.current_dialog = self._read(name)
        self.current_name = name
        logger.info(f"Opened dialog: {name}")
        return True

    def switch(self, name: str) -> bool:
        """Alias for open — ensures current context is saved first."""
        if self.current_dialog and self.current_name:
            self.save()
        return self.open(name)

    def save(self) -> None:
        if self.current_dialog and self.current_name:
            self.current_dialog["updated_at"] = _now()
            self._write(self.current_name, self.current_dialog)

    def delete(self, name: str) -> bool:
        name = self._sanitise(name)
        path = self._path(name)
        if os.path.exists(path):
            os.remove(path)
            if self.current_name == name:
                self.current_dialog = None
                self.current_name = None
            logger.info(f"Deleted dialog: {name}")
            return True
        return False

    def list_dialogs(self) -> list[dict]:
        """Return metadata for all dialogs sorted by update time."""
        result = []
        for fname in os.listdir(self.dialogs_dir):
            if fname.endswith(".json"):
                try:
                    dialog = self._read(fname[:-5])
                    result.append({
                        "name": dialog["name"],
                        "created_at": dialog.get("created_at", ""),
                        "updated_at": dialog.get("updated_at", ""),
                        "messages": len(dialog.get("messages", [])),
                        "active": dialog["name"] == self.current_name,
                    })
                except Exception:
                    pass
        result.sort(key=lambda d: d["updated_at"], reverse=True)
        return result

    def search(self, query: str) -> list[dict]:
        """Search for query across all dialogs. Returns match snippets."""
        query_lower = query.lower()
        results = []
        for fname in os.listdir(self.dialogs_dir):
            if not fname.endswith(".json"):
                continue
            try:
                dialog = self._read(fname[:-5])
                for msg in dialog.get("messages", []):
                    content = msg.get("content", "")
                    if query_lower in content.lower():
                        idx = content.lower().find(query_lower)
                        snippet = content[max(0, idx - 40): idx + 80].replace("\n", " ")
                        results.append({
                            "dialog": dialog["name"],
                            "role": msg.get("role", "?"),
                            "timestamp": msg.get("timestamp", ""),
                            "snippet": f"…{snippet}…",
                        })
            except Exception:
                pass
        return results

    def add_user_message(self, content: str) -> None:
        if self.current_dialog is None:
            raise RuntimeError("No active dialog")
        msg_id = len(self.current_dialog["messages"]) + 1
        self.current_dialog["messages"].append({
            "id": msg_id,
            "role": "user",
            "content": content,
            "timestamp": _now(),
            "_debug": {"tokens": None, "response_time": None},
        })
        self.current_dialog["_stats"]["total_messages"] += 1
        self.save()

    def add_assistant_message(self, content: str, stats: dict) -> None:
        if self.current_dialog is None:
            raise RuntimeError("No active dialog")
        msg_id = len(self.current_dialog["messages"]) + 1
        self.current_dialog["messages"].append({
            "id": msg_id,
            "role": "assistant",
            "content": content,
            "timestamp": _now(),
            "_debug": {
                "tokens": stats.get("tokens", 0),
                "response_time": stats.get("response_time", 0),
            },
        })
        s = self.current_dialog["_stats"]
        s["total_messages"] += 1
        s["total_tokens"] += stats.get("tokens", 0)
        s["total_response_time"] = round(
            s["total_response_time"] + stats.get("response_time", 0), 3
        )
        self.save()

    def get_context_messages(self) -> list[dict]:
        """Return messages in LLM-safe format (no _debug / _stats)."""
        if not self.current_dialog:
            return []
        msgs = self.current_dialog.get("messages", [])

        limit = self.context_limit
        if limit == 0:
            return []
        if limit > 0:
            msgs = msgs[-limit:]

        return [{"role": m["role"], "content": m["content"]} for m in msgs]

    def get_display_messages(self, n: Optional[int] = None) -> list[dict]:
        """Return last n messages for display (or all if n is None)."""
        if not self.current_dialog:
            return []
        msgs = self.current_dialog.get("messages", [])
        count = n if n is not None else self.display_last_n
        return msgs[-count:] if count > 0 else msgs

    def set_system_prompt(self, prompt_text: Optional[str]) -> None:
        if self.current_dialog is not None:
            self.current_dialog["system_prompt"] = prompt_text
            self.save()

    def get_system_prompt(self) -> Optional[str]:
        if self.current_dialog:
            return self.current_dialog.get("system_prompt")
        return None

    def get_stats(self) -> dict:
        if not self.current_dialog:
            return {}
        return dict(self.current_dialog.get("_stats", {}))

    def _read(self, name: str) -> dict:
        with open(self._path(name), "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write(self, name: str, data: dict) -> None:
        with open(self._path(name), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    def _sanitise(self, name: str) -> str:
        return re.sub(r"[^\w\-]", "_", name).strip("_") or "dialog"

    def _unique_name(self, base: str) -> str:
        if not self._exists(base):
            return base
        i = 1
        while self._exists(f"{base}_{i}"):
            i += 1
        return f"{base}_{i}"
