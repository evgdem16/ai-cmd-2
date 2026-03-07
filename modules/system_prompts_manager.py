"""System prompts management — stored in a single JSON file."""

import json
import os
from datetime import datetime
from typing import Optional

from modules.logger_setup import get_logger

logger = get_logger()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class SystemPromptsManager:
    def __init__(self, file_path: str = "system_prompts.json"):
        self.file_path = file_path
        self._data: dict = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return {"prompts": {}}

    def _save(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)

    def create(self, name: str, content: str) -> bool:
        name = name.strip()
        if name in self._data["prompts"]:
            return False
        self._data["prompts"][name] = {
            "content": content,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self._save()
        logger.info(f"System prompt created: {name}")
        return True

    def update(self, name: str, content: str) -> bool:
        if name not in self._data["prompts"]:
            return False
        self._data["prompts"][name]["content"] = content
        self._data["prompts"][name]["updated_at"] = _now()
        self._save()
        logger.info(f"System prompt updated: {name}")
        return True

    def delete(self, name: str) -> bool:
        if name not in self._data["prompts"]:
            return False
        del self._data["prompts"][name]
        self._save()
        logger.info(f"System prompt deleted: {name}")
        return True

    def get(self, name: str) -> Optional[dict]:
        return self._data["prompts"].get(name)

    def list_prompts(self) -> list[dict]:
        result = []
        for name, info in self._data["prompts"].items():
            result.append({
                "name": name,
                "created_at": info.get("created_at", ""),
                "updated_at": info.get("updated_at", ""),
                "preview": info["content"][:60].replace("\n", " ") + (
                    "…" if len(info["content"]) > 60 else ""
                ),
            })
        return sorted(result, key=lambda p: p["name"])

    def exists(self, name: str) -> bool:
        return name in self._data["prompts"]
