import importlib.util

import pytest


@pytest.mark.parametrize("response", [
    '{"action":"continue"}', '{"action":"finish","text":42}',
    '{"action":"tool","name":"x","arguments":[]}',
    '{"action":"tool","name":"","arguments":{}}',
    '{"action":"unknown"}', '{"action":"finish","text":"x"',
    "{'action':'finish','text':'x'}", "{action: 'continue', text: 'x'}",
])
def test_malformed_explicit_action_fails_without_echoing_response(response):
    from forge.runtime.react import ReActPlanner

    with pytest.raises(ValueError, match="Invalid planner action") as caught:
        ReActPlanner().decide(response)
    assert response not in str(caught.value)

from forge.runtime.ports import ContinueAction, FinalAction, ToolAction


def test_react_decides_explicit_actions_and_legacy_text():
    assert importlib.util.find_spec("forge.runtime.react") is not None, "ReAct planner is missing"
    from forge.runtime.react import ReActPlanner

    planner = ReActPlanner()
    assert planner.decide("ordinary answer") == FinalAction("ordinary answer")
    assert planner.decide('{"action":"continue","text":"next turn"}') == ContinueAction("next turn")
    assert planner.decide('{"action":"finish","text":"answer"}') == FinalAction("answer")
    assert planner.decide('{"action":"tool","name":"lookup","arguments":{"q":"x"}}') == ToolAction("lookup", {"q": "x"})
    prompt = planner.prepare("Be brief")
    assert prompt.startswith("Be brief")
    assert "JSON" in prompt and "continue" in prompt and "finish" in prompt
    assert "No tools" in prompt
