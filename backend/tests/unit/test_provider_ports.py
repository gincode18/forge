from forge.runtime import ports


def test_streaming_values_extend_legacy_contract_without_shared_metadata():
    assert hasattr(ports, "ModelMessage"), "provider-neutral messages are missing"
    assert ports.ModelMessage("assistant", "hello").text == "hello"
    assert ports.ModelDelta("hello").text == "hello"
    call = ports.ToolCall("lookup", {"q": "hello"}, "call-1")
    result = ports.ModelResult("hello", "fake", "test", tool_calls=(call,))
    assert result.tool_calls == (call,)
    result.metadata["version"] = "test"
    assert ports.ModelResult("", "fake", "test").metadata == {}
    assert ports.ContinueAction("next").text == "next"
    assert ports.ToolAction("lookup", {}).arguments == {}
    assert not ports.ProviderError("fake", "failed", "safe").retryable
    assert ports.ProviderError("fake", "busy", "safe", retryable=True).retryable
    assert hasattr(ports.ModelProvider, "stream")
