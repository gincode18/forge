"""Google Gen AI adapter; secrets remain outside persisted run state."""
import base64
import json
import time
from collections.abc import AsyncIterator

from google import genai
from google.genai import errors, types

from forge.runtime.ports import (
    ModelDelta,
    ModelMessage,
    ModelResult,
    ModelUsage,
    ProviderError,
    ToolCall,
)


class _ResponseFailure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


def _check_response(response) -> None:
    feedback = getattr(response, "prompt_feedback", None)
    block = getattr(feedback, "block_reason", None)
    if block and getattr(block, "name", str(block)) != "BLOCKED_REASON_UNSPECIFIED":
        raise _ResponseFailure("blocked_response")
    candidate = response.candidates[0] if response.candidates else None
    reason = getattr(candidate, "finish_reason", None)
    finish = getattr(reason, "name", reason)
    if finish in {"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"}:
        raise _ResponseFailure("blocked_response")
    if finish and finish != "STOP":
        raise _ResponseFailure("incomplete_response")


def _response_failure(error: _ResponseFailure) -> ProviderError:
    messages = {
        "empty_response": "Gemini returned no text",
        "blocked_response": "Gemini response was blocked",
        "incomplete_response": "Gemini response was incomplete",
    }
    return ProviderError("gemini", error.code, messages[error.code])


def _usage(raw) -> ModelUsage | None:
    if raw is None:
        return None
    prompt = raw.prompt_token_count
    candidates = raw.candidates_token_count
    total = raw.total_token_count
    if prompt is None or candidates is None or total is None:
        return None
    output = candidates + (getattr(raw, "thoughts_token_count", None) or 0)
    return ModelUsage(prompt, max(output, total - prompt), total)


def _tool_calls(candidate) -> tuple[ToolCall, ...]:
    calls = []
    for part in (getattr(getattr(candidate, "content", None), "parts", None) or []):
        call = getattr(part, "function_call", None)
        if call is not None:
            signature = getattr(part, 'thought_signature', None)
            calls.append(ToolCall(call.name, dict(call.args or {}), call.id,
                                  base64.b64encode(signature).decode() if signature else None))
    return tuple(calls)


def _metadata(response) -> dict:
    version = getattr(response, "model_version", None)
    return {"model_version": version} if isinstance(version, str) else {}


async def _close_resources(client, owned: bool, source=None) -> bool:
    failed = False
    try:
        try:
            close = getattr(source, "aclose", None)
            if close is not None:
                await close()
        except Exception:  # noqa: BLE001 - cleanup errors can contain credentials.
            failed = True
    finally:
        if owned and client is not None:
            try:
                await client.aio.aclose()
            except Exception:  # noqa: BLE001 - cleanup errors can contain credentials.
                failed = True
            finally:
                try:
                    client.close()
                except Exception:  # noqa: BLE001 - cleanup errors can contain credentials.
                    failed = True
    return failed


class GeminiProvider:
    def __init__(self, model: str, *, api_key: str | None = None, client: genai.Client | None = None):
        if client is None and not api_key:
            raise ValueError("GEMINI_API_KEY is required to run Gemini agents")
        self.model = model
        self._client = client
        self._api_key = api_key

    async def stream(
        self, *, instructions: str, input: str,
        messages: tuple[ModelMessage, ...] = (), max_output_tokens: int = 2048,
        tools: tuple[dict, ...] = (),
    ) -> AsyncIterator[ModelDelta | ModelResult]:
        started = time.monotonic()
        client = self._client
        owned = client is None
        source = None
        succeeded = False
        try:
            client = client if client is not None else genai.Client(
                api_key=self._api_key, vertexai=False
            )
            contents = [types.Content(role="user", parts=[types.Part(text=input)])]
            for message in messages:
                parts = [types.Part(text=message.text)] if message.text else []
                if message.role == 'tool':
                    parts = [types.Part(function_response=types.FunctionResponse(
                        name=message.tool_name, id=message.call_id, response=json.loads(message.text),
                    ))]
                else:
                    parts.extend(types.Part(function_call=types.FunctionCall(name=call.name, args=call.arguments, id=call.id),
                                            thought_signature=base64.b64decode(call.thought_signature) if call.thought_signature else None) for call in message.tool_calls)
                if (message.role == 'tool' and contents[-1].role == 'user'
                        and all(part.function_response is not None for part in contents[-1].parts)):
                    contents[-1].parts.extend(parts)
                else:
                    contents.append(types.Content(role='model' if message.role == 'assistant' else 'user', parts=parts))
            generate_stream = getattr(client.aio.models, "generate_content_stream", None)
            config = types.GenerateContentConfig(
                system_instruction=instructions, max_output_tokens=max_output_tokens,
                tools=[types.Tool(function_declarations=[types.FunctionDeclaration(
                    name=tool['name'], description=tool['description'], parameters_json_schema=tool['input_schema'],
                ) for tool in tools])] if tools else None,
            )
            if generate_stream is not None:
                source = await generate_stream(model=self.model, contents=contents, config=config)
            else:
                # Legacy offline SDK doubles have completion only. Real SDKs use
                # the awaited async streaming iterator above.
                async def completion_chunks():
                    yield await client.aio.models.generate_content(
                        model=self.model, contents=contents if messages else input, config=config,
                    )
                source = completion_chunks()
            text = ""
            usage = None
            finish = None
            request_id = None
            tool_calls = []
            metadata = {}
            async for response in source:
                _check_response(response)
                delta = response.text
                if delta:
                    text += delta
                    yield ModelDelta(delta)
                if response.usage_metadata:
                    usage = _usage(response.usage_metadata)
                candidate = response.candidates[0] if response.candidates else None
                if candidate and candidate.finish_reason:
                    finish = candidate.finish_reason.name
                request_id = response.response_id or request_id
                tool_calls.extend(_tool_calls(candidate))
                metadata.update(_metadata(response))
            if not text and not tool_calls:
                raise _ResponseFailure("empty_response")
            if generate_stream is not None and finish != "STOP":
                raise _ResponseFailure("incomplete_response")
            result = ModelResult(
                text, "gemini", self.model, finish_reason=finish, usage=usage,
                request_id=request_id, latency_ms=round((time.monotonic() - started) * 1000, 3),
                tool_calls=tuple(tool_calls), metadata=metadata,
            )
            succeeded = True
        except _ResponseFailure as error:
            raise _response_failure(error) from None
        except Exception as error:  # noqa: BLE001 - untrusted SDK details can contain credentials.
            retryable = isinstance(error, errors.APIError) and (error.code == 429 or 500 <= error.code < 600)
            raise ProviderError("gemini", "request_failed", "Gemini request failed", retryable=retryable) from None
        finally:
            failed = await _close_resources(client, owned, source)
            if failed and succeeded:
                raise ProviderError("gemini", "cleanup_failed", "Gemini cleanup failed") from None
        yield result

    async def complete(self, *, instructions: str, input: str) -> ModelResult:
        started = time.monotonic()
        owned = self._client is None
        client = self._client
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
            _check_response(response)
            text = response.text or ""
            candidate = response.candidates[0] if response.candidates else None
            tool_calls = _tool_calls(candidate)
            if not text and not tool_calls:
                raise _ResponseFailure("empty_response")
            usage = response.usage_metadata
            finish = candidate.finish_reason if candidate else None
            result = ModelResult(
                text=text,
                provider="gemini",
                model=self.model,
                finish_reason=finish.name if finish else None,
                usage=_usage(usage),
                tool_calls=tool_calls, metadata=_metadata(response),
                request_id=response.response_id,
                latency_ms=round((time.monotonic() - started) * 1000, 3),
            )
            succeeded = True
            return result
        except _ResponseFailure as error:
            raise _response_failure(error) from None
        except Exception as error:  # noqa: BLE001 - SDK exception text is untrusted secret-bearing data.
            # SDK errors may include credentials in transport/response details.
            # Suppress the raw chain as well as replacing the public message.
            retryable = isinstance(error, errors.APIError) and (error.code == 429 or 500 <= error.code < 600)
            raise ProviderError("gemini", "request_failed", "Gemini request failed", retryable=retryable) from None
        finally:
            failed = await _close_resources(client, owned)
            # Never mask a safe failure, cancellation, or an enclosing timeout.
            if failed and succeeded:
                raise ProviderError("gemini", "cleanup_failed", "Gemini cleanup failed") from None
