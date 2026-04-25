import sys
import time

from google import genai
from google.genai import types

from qa_gen.core.ai.base import AIProvider

_RETRIES = 3
_BACKOFF = [1, 2, 4]


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(
        self,
        system_prompt: str,
        context: str,
        story_prompt: str,
        timeout: int = 60,
    ) -> str:
        system_instruction = system_prompt + "\n\n" + context
        last_exc: Exception | None = None
        for attempt, delay in enumerate(_BACKOFF):
            try:
                resp = self._client.models.generate_content(
                    model=self._model,
                    contents=[story_prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        max_output_tokens=4096,
                    ),
                )
                return resp.text
            except Exception as e:
                last_exc = e
                if attempt < _RETRIES - 1:
                    retry_after = delay
                    if "429" in str(e) or "quota" in str(e).lower():
                        retry_after = 30
                    time.sleep(retry_after)

        print(f"AI generation failed after {_RETRIES} attempts: {last_exc}", file=sys.stderr)
        raise SystemExit(4)
