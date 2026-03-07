"""RAG support — load files / directories and attach content to prompts."""

import os
from typing import Optional

from modules.logger_setup import get_logger

logger = get_logger()

# Extensions treated as plain text
TEXT_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".xml", ".yaml", ".yml",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift",
    ".kt", ".sh", ".bash", ".sql", ".html", ".css", ".toml",
    ".ini", ".cfg", ".conf", ".log", ".rst",
}


class RAGManager:
    def __init__(self):
        self._loaded: dict[str, str] = {}  # path -> content

    def load_path(self, path: str) -> list[str]:
        """
        Load a file or all files in a directory.
        Returns list of successfully loaded paths.
        """
        path = os.path.expanduser(path)
        loaded = []
        if os.path.isfile(path):
            content = self._read_file(path)
            if content is not None:
                self._loaded[path] = content
                loaded.append(path)
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    content = self._read_file(fpath)
                    if content is not None:
                        self._loaded[fpath] = content
                        loaded.append(fpath)
        else:
            logger.warning(f"RAG: path not found: {path}")
        return loaded

    def clear(self) -> None:
        self._loaded.clear()

    def remove(self, path: str) -> bool:
        path = os.path.expanduser(path)
        if path in self._loaded:
            del self._loaded[path]
            return True
        return False

    def list_files(self) -> list[str]:
        return list(self._loaded.keys())

    def has_files(self) -> bool:
        return bool(self._loaded)

    def build_context_block(self) -> str:
        """Return formatted block to prepend to user prompt."""
        if not self._loaded:
            return ""
        parts = ["--- Attached files ---\n"]
        for path, content in self._loaded.items():
            ext = os.path.splitext(path)[1].lower()
            lang = ext.lstrip(".") if ext else "text"
            parts.append(f"### File: {path}\n```{lang}\n{content}\n```\n")
        parts.append("--- End of attached files ---\n")
        return "\n".join(parts)

    def save_to_directory(self, dialog_messages: list[dict], dest_dir: str) -> list[str]:
        """
        Save all code blocks from assistant messages to dest_dir.
        Returns list of saved file paths.
        """
        import re
        os.makedirs(dest_dir, exist_ok=True)
        saved = []
        code_block_re = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
        counter: dict[str, int] = {}
        for msg in dialog_messages:
            if msg.get("role") != "assistant":
                continue
            for match in code_block_re.finditer(msg.get("content", "")):
                lang = match.group(1) or "txt"
                code = match.group(2)
                ext_map = {
                    "python": "py", "py": "py", "javascript": "js",
                    "js": "js", "typescript": "ts", "ts": "ts",
                    "bash": "sh", "shell": "sh", "sh": "sh",
                    "json": "json", "html": "html", "css": "css",
                    "sql": "sql", "yaml": "yaml", "yml": "yaml",
                    "java": "java", "cpp": "cpp", "c": "c",
                    "go": "go", "rust": "rs", "ruby": "rb",
                }
                ext = ext_map.get(lang.lower(), lang.lower() or "txt")
                counter[ext] = counter.get(ext, 0) + 1
                fname = f"code_{counter[ext]}.{ext}"
                fpath = os.path.join(dest_dir, fname)
                with open(fpath, "w", encoding="utf-8") as fh:
                    fh.write(code)
                saved.append(fpath)
        return saved

    def _read_file(self, path: str) -> Optional[str]:
        ext = os.path.splitext(path)[1].lower()
        if ext in TEXT_EXTENSIONS:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                logger.info(f"RAG loaded: {path} ({len(content)} chars)")
                return content
            except Exception as exc:
                logger.warning(f"RAG read error ({path}): {exc}")
                return None
        # Try PDF
        if ext == ".pdf":
            return self._read_pdf(path)
        logger.debug(f"RAG: skipping unsupported file: {path}")
        return None

    def _read_pdf(self, path: str) -> Optional[str]:
        try:
            import pypdf  # type: ignore
            with open(path, "rb") as fh:
                reader = pypdf.PdfReader(fh)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            logger.info(f"RAG loaded PDF: {path}")
            return text
        except ImportError:
            logger.warning("pypdf not installed — skipping PDF file")
        except Exception as exc:
            logger.warning(f"RAG PDF read error: {exc}")
        return None
