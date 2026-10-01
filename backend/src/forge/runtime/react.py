"""Explicit no-tool planning protocol, without hidden-reasoning requirements."""
import json
import re

from forge.runtime.ports import ContinueAction, FinalAction, ToolAction


class ReActPlanner:
    def prepare(self, instructions: str, tools: tuple[dict, ...] = ()) -> str:
        return instructions + (
            '\n\nReturn a JSON object: {"action":"finish","text":"answer"} '
            'or {"action":"continue","text":"brief next-turn context"}. ' +
            (('Available tools: ' + json.dumps([{'name': t['name'], 'input_schema': t['input_schema']} for t in tools]) + '. Request a native function call or {"action":"tool","name":"tool_name","arguments":{}}. ')
             if tools else 'No tools are available. Do not request tools. ') +
            'No private reasoning or chain of thought is required.'
        )

    def decide(self, response: str) -> FinalAction | ContinueAction | ToolAction:
        try:
            value = json.loads(response)
        except json.JSONDecodeError:
            if response.lstrip().startswith("{") and re.search(r"[\"']?action[\"']?\s*:", response):
                raise ValueError("Invalid planner action") from None
            return FinalAction(response)
        if not isinstance(value, dict) or "action" not in value:
            return FinalAction(response)
        action = value["action"]
        text = value.get("text")
        if action in ("continue", "finish") and isinstance(text, str):
            return ContinueAction(text) if action == "continue" else FinalAction(text)
        name, arguments = value.get("name"), value.get("arguments")
        if action == "tool" and isinstance(name, str) and name.strip() and isinstance(arguments, dict):
            return ToolAction(name, arguments)
        raise ValueError("Invalid planner action")
