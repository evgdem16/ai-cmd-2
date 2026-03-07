import time
from typing import Generator, Iterator, Optional

from modules.logger_setup import get_logger

logger = get_logger()


class APIClient:
    def __init__(self, base_url: str, api_key: str, model: str,
                 max_tokens: int = 2048, temperature: float = 0.7):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=f"{self.base_url}/v1",
                api_key=self.api_key,
            )
            logger.info(f"API client initialised: {self.base_url}")
        except ImportError:
            logger.error("openai package is not installed. Run: pip install openai")
            raise

    def stream_chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> tuple[Generator[str, None, None], dict]:
        """
        Returns (token_generator, stats_dict).
        stats_dict is filled after the generator is exhausted.
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        stats: dict = {"tokens": 0, "response_time": 0.0, "error": None}
        start = time.time()

        try:
            logger.info(f"Sending {len(full_messages)} messages to LLM (model={self.model})")
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True,
            )

            def _generate() -> Iterator[str]:
                total_chunks = 0
                try:
                    for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            total_chunks += len(delta.content.split())
                            yield delta.content
                    stats["response_time"] = round(time.time() - start, 3)
                    try:
                        if chunk.usage:
                            stats["tokens"] = chunk.usage.completion_tokens or 0
                    except Exception:
                        stats["tokens"] = total_chunks
                    logger.info(
                        f"Stream complete: {stats['tokens']} tokens, "
                        f"{stats['response_time']}s"
                    )
                except Exception as exc:
                    err_msg = str(exc)
                    yield f"\n[API error: {err_msg}]"

            return _generate(), stats

        except Exception as exc:
            err_msg = str(exc)
            base_url = self.base_url
            def _error_gen():
                yield f"[Connection error: {err_msg}]\n... {base_url}"

            return _error_gen(), stats

    def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> tuple[str, dict]:
        """Non-streaming call. Returns (full_text, stats)."""
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        stats: dict = {"tokens": 0, "response_time": 0.0, "error": None}
        start = time.time()
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False,
            )
            stats["response_time"] = round(time.time() - start, 3)
            content = response.choices[0].message.content or ""
            if response.usage:
                stats["tokens"] = response.usage.completion_tokens or 0
            return content, stats
        except Exception as exc:
            stats["error"] = str(exc)
            logger.error(f"Non-stream API call failed: {exc}")
            return f"[Error: {exc}]", stats
