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


def test_real_sdk_serializes_tool_definitions_and_observations():
    from forge.runtime.ports import ToolCall
    from forge.runtime.tools import ToolRegistry
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        chunk = {'candidates': [{'content': {'role': 'model', 'parts': [{'text': 'done'}]}, 'finishReason': 'STOP'}]}
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=f'data: {json.dumps(chunk)}\n\n')

    async def exercise():
        client = genai.Client(api_key='synthetic-offline-only', vertexai=False, http_options=types.HttpOptions(async_client_args={'transport': httpx.MockTransport(respond)}))
        try:
            return [item async for item in GeminiProvider('offline-model', client=client).stream(
                instructions='use tools', input='calculate', tools=tuple(ToolRegistry().catalog()[:1]),
                messages=(ModelMessage('assistant', '', (ToolCall('calculator', {'expression': '2+2'}, 'c1', 'c3ludGhldGljLXNpZ25hdHVyZQ=='),)),
                          ModelMessage('tool', '{"value":4}', tool_name='calculator', call_id='c1')),
            )]
        finally:
            await client.aio.aclose()
            client.close()
    assert asyncio.run(exercise())[-1].text == 'done'
    request = requests[0]
    assert request['tools'][0]['functionDeclarations'][0]['name'] == 'calculator'
    assert request['contents'][1]['parts'][0]['functionCall']['args'] == {'expression': '2+2'}
    assert request['contents'][1]['parts'][0]['thoughtSignature'] == 'c3ludGhldGljLXNpZ25hdHVyZQ=='
    assert request['contents'][2]['parts'][0]['functionResponse']['response'] == {'value': 4}


def test_gemini_tool_call_retains_opaque_thought_signature():
    from types import SimpleNamespace

    from forge.runtime.gemini import _tool_calls
    call = SimpleNamespace(name='calculator', args={'expression': '2+2'}, id='c1')
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(function_call=call, thought_signature=b'synthetic-signature')]))
    normalized = _tool_calls(candidate)[0]
    assert normalized.thought_signature == 'c3ludGhldGljLXNpZ25hdHVyZQ=='


def test_real_sdk_preserves_multiple_tool_ids_and_order():
    from forge.runtime.ports import ToolCall
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        chunk = {'candidates': [{'content': {'role': 'model', 'parts': [{'text': 'done'}]}, 'finishReason': 'STOP'}]}
        return httpx.Response(200, headers={'content-type': 'text/event-stream'}, content=f'data: {json.dumps(chunk)}\n\n')

    async def exercise():
        client = genai.Client(api_key='synthetic-offline-only', vertexai=False, http_options=types.HttpOptions(async_client_args={'transport': httpx.MockTransport(respond)}))
        try:
            return [item async for item in GeminiProvider('offline-model', client=client).stream(
                instructions='tools', input='original', messages=(
                    ModelMessage('assistant', '', (ToolCall('calculator', {'expression': '1+1'}, 'first'), ToolCall('current_time', {}, 'second'))),
                    ModelMessage('tool', '{"value":2}', tool_name='calculator', call_id='first'),
                    ModelMessage('tool', '{"utc":"synthetic"}', tool_name='current_time', call_id='second'),
                ),
            )]
        finally:
            await client.aio.aclose()
            client.close()

    asyncio.run(exercise())
    contents = requests[0]['contents']
    assert [part['functionCall']['id'] for part in contents[1]['parts']] == ['first', 'second']
    responses = [part['functionResponse'] for content in contents[2:] for part in content['parts']]
    assert [(r['id'], r['name']) for r in responses] == [('first', 'calculator'), ('second', 'current_time')]
    # One chronological response turn for the complete native call batch.
    assert len(contents) == 3
    assert len(contents[2]['parts']) == 2
