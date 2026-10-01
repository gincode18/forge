from dataclasses import asdict

from forge.runtime.ports import ModelResult, ToolCall


def test_normalized_result_persists_ordered_text_and_tool_content_blocks():
    result = ModelResult("Hello", "fake", "test", tool_calls=(ToolCall("lookup", {"q": "x"}, "call-1"),))
    assert "content_blocks" in asdict(result), "Normalized content blocks are missing"
    assert asdict(result)["content_blocks"] == (
        {"type": "text", "text": "Hello"},
        {"type": "tool_call", "tool_call": {"name": "lookup", "arguments": {"q": "x"}, "id": "call-1", "thought_signature": None}},
    )


def test_tool_only_result_has_no_fabricated_empty_text_block():
    result = ModelResult("", "fake", "test", tool_calls=(ToolCall("lookup", {}),))
    assert "content_blocks" in asdict(result), "Normalized content blocks are missing"
    assert len(asdict(result)["content_blocks"]) == 1
    assert asdict(result)["content_blocks"][0]["type"] == "tool_call"
