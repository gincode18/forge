from forge.domain.tools import ToolContext
from forge.runtime.tools import ToolRegistry


def test_policy_returns_typed_approval_and_cannot_approve_traversal(tmp_path):
    from forge.runtime.policy import ToolPolicy
    from forge.runtime.ports import ToolCall
    policy = ToolPolicy()
    registry = ToolRegistry()
    context = ToolContext('test', tmp_path)
    result = policy.evaluate(ToolCall('filesystem_write', {'path': 'answer.txt', 'content': 'safe'}), ('filesystem_write@1',), registry, context)
    assert result.decision == 'require_approval'
    assert result.arguments.content == 'safe'
    result = policy.evaluate(ToolCall('filesystem_write', {'path': '../answer.txt', 'content': 'unsafe'}), ('filesystem_write@1',), registry, context)
    assert result.decision == 'deny'
