"""Fail-closed capability authorization before every tool boundary."""
from pathlib import Path

from forge.domain.tools import PolicyResult, ToolContext
from forge.runtime.ports import ToolCall
from forge.runtime.tools import ToolRegistry, scoped_path


class ToolPolicy:
    def evaluate(self, call: ToolCall, enabled: tuple[str, ...], registry: ToolRegistry,
                 context: ToolContext) -> PolicyResult:
        tool = next((tool for key in enabled if (tool := registry.get(key)) is not None and tool.name == call.name), None)
        if tool is None:
            return PolicyResult('deny', 'disabled_or_unknown')
        try:
            arguments = tool.input_model.model_validate(call.arguments)
            if call.name == 'subprocess':
                scoped_path(context.workspace, '__scope_probe__')
            if hasattr(arguments, 'path'):
                scoped_path(context.workspace, arguments.path)
            if call.name == 'subprocess' and (
                tuple(arguments.argv) not in context.subprocess_allowlist
                or not Path(arguments.argv[0]).is_absolute()
            ):
                return PolicyResult('deny', 'command_not_allowlisted', tool)
        except (ValueError, OSError):
            return PolicyResult('deny', 'invalid_arguments_or_scope', tool)
        if tool.risk == 'sensitive':
            return PolicyResult('require_approval', 'sensitive_capability', tool, arguments)
        return PolicyResult('allow', 'enabled', tool, arguments)
