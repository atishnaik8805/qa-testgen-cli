import sys
import time

import anthropic

from qa_gen.core.ai.base import AIProvider

_RETRIES = 3
_BACKOFF = [1, 2, 4]


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(
        self,
        system_prompt: str,
        context: str,
        story_prompt: str,
        timeout: int = 60,
    ) -> str:
        last_exc: Exception | None = None
        for attempt, delay in enumerate(_BACKOFF):
            try:
                resp = self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    timeout=timeout,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": context,
                            "cache_control": {"type": "ephemeral"},
                        },
                    ],
                    messages=[{"role": "user", "content": story_prompt}],
                )
                return resp.content[0].text
            except Exception as e:
                last_exc = e
                if attempt < _RETRIES - 1:
                    retry_after = delay
                    if hasattr(e, "response") and e.response is not None:
                        retry_after = int(e.response.headers.get("Retry-After", delay))
                    if "429" in type(e).__name__ or "rate" in str(e).lower():
                        retry_after = max(retry_after, 30)
                    time.sleep(retry_after)

        print(f"AI generation failed after {_RETRIES} attempts: {last_exc}", file=sys.stderr)
        raise SystemExit(4)
