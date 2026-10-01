"""Explicit built-in registry. Restrictions reduce accidents, not a sandbox."""
import ast
import asyncio
import operator
import os
import signal
import stat
from collections.abc import Iterable
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forge.domain.tools import (
    CalculatorInput,
    CalculatorOutput,
    PathInput,
    ReadOutput,
    SubprocessInput,
    SubprocessOutput,
    TimeOutput,
    Tool,
    ToolContext,
    ToolExecutionError,
    ToolInput,
    WriteInput,
    WriteOutput,
)

WARNING = 'Local restrictions are not a sandbox or security boundary.'


class Calculator:
    name = 'calculator'
    version = '1'
    description = 'Evaluate bounded arithmetic (no code execution).'
    input_model = CalculatorInput
    output_model = CalculatorOutput
    capabilities = ('calculate',)
    risk = 'low'
    timeout_seconds = 1.0
    max_output_bytes = 4096

    async def execute(self, arguments: CalculatorInput, context: ToolContext) -> CalculatorOutput:
        operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                      ast.Div: operator.truediv, ast.Mod: operator.mod}

        def evaluate(node):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                return node.value
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = evaluate(node.operand)
                return -value if isinstance(node.op, ast.USub) else value
            if isinstance(node, ast.BinOp) and type(node.op) in operations:
                return operations[type(node.op)](evaluate(node.left), evaluate(node.right))
            raise ValueError('unsupported arithmetic')

        tree = ast.parse(arguments.expression, mode='eval')
        if len(list(ast.walk(tree))) > 64:
            raise ValueError('expression too complex')
        value = evaluate(tree.body)
        if abs(value) > 1e100:
            raise ValueError('result too large')
        return CalculatorOutput(value=value)


def scoped_path(workspace: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('unsafe path')
    if any(parent.is_symlink() for parent in (workspace, *workspace.parents)):
        raise ValueError('unsafe workspace')
    root = workspace.resolve()
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError('symlinks are not allowed')
    if not current.resolve().is_relative_to(root):
        raise ValueError('unsafe path')
    if current.exists():
        if not current.is_file():
            raise ValueError('only regular files are allowed')
        if current.stat().st_nlink > 1:
            raise ValueError('hardlinks are not allowed')
    return current


@contextmanager
def open_scoped_file(workspace: Path, value: str, *, write: bool = False):
    """POSIX descriptor walk: never follow a swapped directory or file symlink.

    This does not isolate against hostile directory renames or newly added hardlinks.
    """
    scoped_path(workspace, value)
    root = workspace.absolute()
    if '..' in root.parts:
        raise ValueError('unsafe workspace')
    relative = Path(value)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    with ExitStack() as stack:
        directory = os.open(root.anchor, directory_flags)
        stack.callback(os.close, directory)
        # Open every workspace ancestor too; opening just the root still follows
        # symlinks in its ancestors. Only create directories inside the workspace.
        parts = [(part, False) for part in root.parts[1:]]
        parts += [(part, write) for part in relative.parts[:-1]]
        for part, create in parts:
            try:
                child = os.open(part, directory_flags, dir_fd=directory)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, mode=0o700, dir_fd=directory)
                except FileExistsError:
                    pass
                child = os.open(part, directory_flags, dir_fd=directory)
            stack.callback(os.close, child)
            directory = child
        flags = os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        flags |= (os.O_WRONLY | os.O_CREAT) if write else os.O_RDONLY
        descriptor = os.open(relative.name, flags, mode=0o600, dir_fd=directory)
        with os.fdopen(descriptor, 'wb' if write else 'rb') as file:
            metadata = os.fstat(file.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError('only regular files are allowed')
            if metadata.st_nlink > 1:
                raise ValueError('hardlinks are not allowed')
            # Never use O_TRUNC before validating the opened inode.
            if write:
                os.ftruncate(file.fileno(), 0)
            yield file


class FilesystemRead:
    name = 'filesystem_read'
    version = '1'
    description = 'Read a bounded UTF-8 file in the run workspace.'
    input_model = PathInput
    output_model = ReadOutput
    capabilities = ('workspace.read',)
    risk = 'low'
    timeout_seconds = 2.0
    max_output_bytes = 65536

    async def execute(self, arguments: PathInput, context: ToolContext) -> ReadOutput:
        with open_scoped_file(context.workspace, arguments.path) as source:
            data = source.read(32769)
        if len(data) > 32768:
            raise ValueError('file too large')
        return ReadOutput(content=data.decode('utf-8'))


class FilesystemWrite:
    name = 'filesystem_write'
    version = '1'
    description = 'Write a bounded UTF-8 file in the run workspace (approval required).'
    input_model = WriteInput
    output_model = WriteOutput
    capabilities = ('workspace.write',)
    risk = 'sensitive'
    timeout_seconds = 2.0
    max_output_bytes = 65536

    async def execute(self, arguments: WriteInput, context: ToolContext) -> WriteOutput:
        data = arguments.content.encode('utf-8')
        if len(data) > 32768:
            raise ValueError('file too large')
        with open_scoped_file(context.workspace, arguments.path, write=True) as destination:
            destination.write(data)
        return WriteOutput(path=arguments.path, size_bytes=len(data))


class CurrentTime:
    name = 'current_time'
    version = '1'
    description = 'Read the current UTC time.'
    input_model = ToolInput
    output_model = TimeOutput
    capabilities = ('clock.read',)
    risk = 'low'
    timeout_seconds = 1.0
    max_output_bytes = 4096

    async def execute(self, arguments: ToolInput, context: ToolContext) -> TimeOutput:
        return TimeOutput(utc=datetime.now(UTC).isoformat())


class Subprocess:
    name = 'subprocess'
    version = '1'
    description = 'Run operator-allowlisted exact argv locally. NOT a sandbox.'
    input_model = SubprocessInput
    output_model = SubprocessOutput
    capabilities = ('process.execute',)
    risk = 'sensitive'
    timeout_seconds = 5.0
    max_output_bytes = 65536

    async def execute(self, arguments: SubprocessInput, context: ToolContext) -> SubprocessOutput:
        if tuple(arguments.argv) not in context.subprocess_allowlist or not Path(arguments.argv[0]).is_absolute():
            raise ValueError('command not allowlisted')
        scoped_path(context.workspace, '__scope_probe__')
        process = await asyncio.create_subprocess_exec(*arguments.argv, cwd=context.workspace,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': str(context.workspace)},
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, start_new_session=True)
        used = 0

        async def read(pipe):
            nonlocal used
            chunks = []
            while chunk := await pipe.read(4096):
                used += len(chunk)
                if used > self.max_output_bytes:
                    raise ToolExecutionError('output_limit')
                chunks.append(chunk)
            return b''.join(chunks)

        readers = [asyncio.create_task(read(process.stdout)), asyncio.create_task(read(process.stderr))]
        try:
            async with asyncio.timeout(self.timeout_seconds):
                stdout, stderr = await asyncio.gather(*readers)
                await process.wait()
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            for reader in readers:
                reader.cancel()
            await asyncio.gather(*readers, return_exceptions=True)
            await process.wait()
        return SubprocessOutput(stdout=stdout.decode('utf-8', errors='replace'),
                                stderr=stderr.decode('utf-8', errors='replace'), returncode=process.returncode)


class ToolRegistry:
    def __init__(self, tools: Iterable[Tool[Any, Any]] | None = None):
        self._tools: dict[str, Tool[Any, Any]] = {}
        for tool in tools if tools is not None else [Calculator(), CurrentTime(), FilesystemRead(), FilesystemWrite(), Subprocess()]:
            key = f'{tool.name}@{tool.version}'
            if key in self._tools:
                raise ValueError('duplicate tool version')
            self._tools[key] = tool

    def get(self, key: str) -> Tool[Any, Any] | None:
        return self._tools.get(key)

    def catalog(self):
        return [{'name': t.name, 'version': t.version, 'key': key, 'description': t.description,
                 'input_schema': t.input_model.model_json_schema(),
                 'output_schema': t.output_model.model_json_schema(),
                 'capabilities': list(t.capabilities), 'risk': t.risk,
                 'timeout_seconds': t.timeout_seconds, 'max_output_bytes': t.max_output_bytes,
                 'default_policy': 'allow' if t.risk == 'low' else 'require_approval',
                 'security_warning': WARNING} for key, t in self._tools.items()]
