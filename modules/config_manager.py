"""Configuration manager — loads and provides access to config.json."""

import json
import os
from typing import Any

DEFAULT_CONFIG: dict = {
    "lm_studio": {
        "base_url": "http://localhost:1234",
        "api_key": "lm-studio",
        "model": "local-model",
        "max_tokens": 2048,
        "temperature": 0.7,
        "stream": True,
    },
    "dialogs": {
        "directory": "dialogs",
        "default_name": "dialog",
        "context_limit": -1,
        "display_last_n": 10,
    },
    "system_prompts_file": "system_prompts.json",
    "exports_directory": "exports",
    "logs": {
        "file": "logs/app.log",
        "level": "INFO",
    },
}


class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            # Merge with defaults so new keys are always present
            return self._deep_merge(DEFAULT_CONFIG, loaded)
        self._save(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def _save(self, cfg: dict) -> None:
        with open(self.config_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = dict(base)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = ConfigManager._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    def get(self, *keys: str, default: Any = None) -> Any:
        node = self.config
        for key in keys:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    @property
    def base_url(self) -> str:
        return self.get("lm_studio", "base_url", default="http://localhost:1234")

    @property
    def api_key(self) -> str:
        return self.get("lm_studio", "api_key", default="lm-studio")

    @property
    def model(self) -> str:
        return self.get("lm_studio", "model", default="local-model")

    @property
    def max_tokens(self) -> int:
        return int(self.get("lm_studio", "max_tokens", default=2048))

    @property
    def temperature(self) -> float:
        return float(self.get("lm_studio", "temperature", default=0.7))

    @property
    def dialogs_dir(self) -> str:
        return self.get("dialogs", "directory", default="dialogs")

    @property
    def default_dialog_name(self) -> str:
        return self.get("dialogs", "default_name", default="dialog")

    @property
    def context_limit(self) -> int:
        return int(self.get("dialogs", "context_limit", default=-1))

    @property
    def display_last_n(self) -> int:
        return int(self.get("dialogs", "display_last_n", default=10))

    @property
    def system_prompts_file(self) -> str:
        return self.get("system_prompts_file", default="system_prompts.json")

    @property
    def exports_dir(self) -> str:
        return self.get("exports_directory", default="exports")

    @property
    def log_file(self) -> str:
        return self.get("logs", "file", default="logs/app.log")

    @property
    def log_level(self) -> str:
        return self.get("logs", "level", default="INFO")
