"""Exercise the real Google SDK wire serialization without network or credentials."""
import asyncio
import json

import httpx
from google import genai
from google.genai import types

from forge.runtime.gemini import GeminiProvider
from forge.runtime.ports import ModelDelta, ModelMessage


def test_real_sdk_stream_preserves_chronological_context():
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        chunks = [
            {"candidates": [{"content": {"role": "model", "parts": [{"text": "Hello "}]}}]},
            {"candidates": [{"content": {"role": "model", "parts": [{"text": "world"}]}, "finishReason": "STOP"}],
             "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2, "totalTokenCount": 7},
             "responseId": "offline-response", "modelVersion": "offline-model"},
        ]
        body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    async def exercise():
        client = genai.Client(api_key="synthetic-offline-only", vertexai=False, http_options=types.HttpOptions(
            async_client_args={"transport": httpx.MockTransport(respond)},
        ))
        try:
            return [item async for item in GeminiProvider("offline-model", client=client).stream(
                instructions="Be brief", input="Original question",
                messages=(ModelMessage("assistant", "Prior answer"), ModelMessage("user", "Continue")),
                max_output_tokens=20,
            )]
        finally:
            await client.aio.aclose()
            client.close()

    results = asyncio.run(exercise())
    assert results[:-1] == [ModelDelta("Hello "), ModelDelta("world")]
    assert results[-1].text == "Hello world"
    assert results[-1].usage.total_tokens == 7
    assert results[-1].request_id == "offline-response"
    assert len(requests) == 1
    assert [(c["role"], c["parts"][0]["text"]) for c in requests[0]["contents"]] == [
        ("user", "Original question"), ("model", "Prior answer"), ("user", "Continue"),
    ]
    assert requests[0]["generationConfig"]["maxOutputTokens"] == 20
