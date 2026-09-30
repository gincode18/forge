"""Google Gen AI adapter; secrets remain outside persisted run state."""
import time

from google import genai
from google.genai import types

from forge.runtime.ports import ModelResult, ModelUsage, ProviderError


class GeminiProvider:
    def __init__(self, model: str, *, api_key: str | None = None, client: genai.Client | None = None):
        if client is None and not api_key:
            raise ValueError("GEMINI_API_KEY is required to run Gemini agents")
        self.model = model
        self._client = client
        self._api_key = api_key

    async def complete(self, *, instructions: str, input: str) -> ModelResult:
        started = time.monotonic()
        owned = self._client is None
        client = self._client
        empty_response = False
        succeeded = False
        try:
            client = client if client is not None else genai.Client(
                api_key=self._api_key, vertexai=False
            )
            response = await client.aio.models.generate_content(
                model=self.model,
                contents=input,
                config=types.GenerateContentConfig(system_instruction=instructions),
            )
            text = response.text
            if not text:
                empty_response = True
                raise ProviderError("gemini", "empty_response", "Gemini returned no text")
            usage = response.usage_metadata
            candidate = response.candidates[0] if response.candidates else None
            finish = candidate.finish_reason if candidate else None
            result = ModelResult(
                text=text,
                provider="gemini",
                model=self.model,
                finish_reason=finish.name if finish else None,
                usage=ModelUsage(
                    input_tokens=usage.prompt_token_count or 0,
                    output_tokens=usage.candidates_token_count or 0,
                    total_tokens=usage.total_token_count or 0,
                ) if usage else None,
                request_id=response.response_id,
                latency_ms=round((time.monotonic() - started) * 1000, 3),
            )
            succeeded = True
            return result
        except Exception:  # noqa: BLE001 - SDK exception text is untrusted secret-bearing data.
            # SDK errors may include credentials in transport/response details.
            # Suppress the raw chain as well as replacing the public message.
            if empty_response:
                raise ProviderError("gemini", "empty_response", "Gemini returned no text") from None
            raise ProviderError("gemini", "request_failed", "Gemini request failed") from None
        finally:
            if owned and client is not None:
                cleanup_failed = False
                try:
                    await client.aio.aclose()
                except Exception:  # noqa: BLE001 - SDK errors may contain credentials.
                    cleanup_failed = True
                finally:
                    # Close the sync half even if async cleanup fails or is cancelled.
                    try:
                        client.close()
                    except Exception:  # noqa: BLE001 - SDK exception text is untrusted secret-bearing data.
                        cleanup_failed = True
                # Cleanup must not mask a safe request failure, empty response, or
                # cancellation (including an enclosing asyncio timeout).
                if cleanup_failed and succeeded:
                    raise ProviderError("gemini", "cleanup_failed", "Gemini cleanup failed") from None
