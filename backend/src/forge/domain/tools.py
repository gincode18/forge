"""Typed capability contracts; independent of HTTP and persistence."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ToolInput(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CalculatorInput(ToolInput):
    expression: str = Field(min_length=1, max_length=256)


class CalculatorOutput(BaseModel):
    value: float


class PathInput(ToolInput):
    path: str = Field(min_length=1, max_length=512)


class WriteInput(PathInput):
    content: str = Field(max_length=32768)


class ReadOutput(BaseModel):
    content: str


class TimeOutput(BaseModel):
    utc: str


class SubprocessInput(ToolInput):
    argv: list[str] = Field(min_length=1, max_length=32)


class SubprocessOutput(BaseModel):
    stdout: str
    stderr: str
    returncode: int


class WriteOutput(BaseModel):
    path: str
    size_bytes: int


@dataclass(frozen=True)
class ToolContext:
    run_id: str
    workspace: Path
    subprocess_allowlist: tuple[tuple[str, ...], ...] = ()


class Tool[InputT: BaseModel, OutputT: BaseModel](Protocol):
    name: str
    version: str
    description: str
    input_model: type[InputT]
    output_model: type[OutputT]
    capabilities: tuple[str, ...]
    risk: str
    timeout_seconds: float
    max_output_bytes: int

    async def execute(self, arguments: InputT, context: ToolContext) -> OutputT: ...


@dataclass(frozen=True)
class PolicyResult:
    decision: Literal['allow', 'deny', 'require_approval']
    reason: str
    tool: Tool[Any, Any] | None = None
    arguments: BaseModel | None = None


class ToolExecutionError(ValueError):
    """Safe runtime-owned error code; no arbitrary tool exception detail."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code.replace('_', ' '))
