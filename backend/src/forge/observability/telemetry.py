"""Explicit local SDK ownership; no global OTel singleton or network exporter.

Application lifespan owns ``configure_telemetry(console_export=False)`` and calls
``handle.close()`` after draining runtime tasks. Tests override with
``use_provider(handle.provider)``; providers must use ``StepIdGenerator`` when
constructed externally to preserve the durable step identity.
"""
import asyncio
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk.trace.id_generator import RandomIdGenerator
from opentelemetry.sdk.trace.sampling import ALWAYS_ON

from forge.domain.trace import span_id_for_step, trace_id_for_run

_identity: ContextVar[tuple[str, str | None] | None] = ContextVar('forge_span_identity', default=None)
_provider: ContextVar[TracerProvider | None] = ContextVar('forge_telemetry_provider', default=None)
_default_provider: TracerProvider | None = None


class StepIdGenerator(RandomIdGenerator):
    """Supported SDK ID hook scoped only to creation of a Forge boundary."""

    def generate_trace_id(self):
        identity = _identity.get()
        return int(trace_id_for_run(identity[0]), 16) if identity else super().generate_trace_id()

    def generate_span_id(self):
        identity = _identity.get()
        return (int(span_id_for_step(identity[1]), 16)
                if identity and identity[1] else super().generate_span_id())

    def is_trace_id_random(self):
        return False


@dataclass(eq=False)
class TelemetryHandle:
    provider: TracerProvider
    closed: bool = False

    def close(self):
        global _default_provider
        if not self.closed:
            self.closed = True
            _handles.remove(self)
            _default_provider = _handles[-1].provider if _handles else None
            self.provider.shutdown()

    shutdown = close


_handles: list[TelemetryHandle] = []


def configure_telemetry(*, console_export=False):
    """Install an owned local provider. No exporter unless explicitly requested."""
    global _default_provider
    provider = TracerProvider(
        id_generator=StepIdGenerator(), sampler=ALWAYS_ON, shutdown_on_exit=False,
        resource=Resource({'service.name': 'forge-runtime'}),
    )
    if console_export:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    handle = TelemetryHandle(provider)
    _handles.append(handle)
    _default_provider = provider
    return handle


@contextmanager
def use_provider(provider):
    """Task-local injection, restored even on failure; does not own shutdown."""
    token = _provider.set(provider)
    try:
        yield provider
    finally:
        _provider.reset(token)


def safe_code(error):
    """Only normalized codes; never exception messages or dynamic class names."""
    from forge.domain.tools import ToolExecutionError
    from forge.runtime.ports import ProviderError

    if isinstance(error, asyncio.CancelledError):
        return 'cancelled'
    if isinstance(error, TimeoutError):
        return 'timeout'
    if isinstance(error, (ProviderError, ToolExecutionError)):
        # Codes are normalized by adapters; reject arbitrary/custom secret-bearing codes.
        allowed = {'unavailable', 'rate_limited', 'authentication', 'permission_denied',
                   'invalid_request', 'incomplete_response', 'output_limit', 'timeout',
                   'tool_execution_failed', 'provider_error', 'configuration',
                   'invalid_response', 'not_found', 'path_not_allowed'}
        allowed.update({'request_failed', 'cleanup_failed', 'empty_response', 'blocked_response'})
        return error.code if error.code in allowed else 'execution_failed'
    return 'execution_failed'


@dataclass
class Operation:
    outcome: str = 'completed'
    code: str | None = None
    duration_ms: float = 0.0


@contextmanager
def boundary(kind, run_id, step_id, *, child=False, attempt=1, span_key=None):
    """Time the actual invocation; allowlisted attributes only, no exception events."""
    provider = _provider.get() or _default_provider
    tracer = provider.get_tracer('forge.runtime') if provider else trace.NoOpTracer()
    identity = _identity.set((run_id, None if child else span_key or step_id))
    try:
        span = tracer.start_span(
            f'forge.{kind}', context=None if child else Context(),
            attributes={'run_id': run_id, 'step_id': step_id, 'boundary': kind, 'attempt': attempt},
            record_exception=False, set_status_on_exception=False,
        )
    finally:
        _identity.reset(identity)
    operation = Operation()
    started = time.monotonic()
    with trace.use_span(span, end_on_exit=True, record_exception=False, set_status_on_exception=False):
        try:
            yield operation
        except BaseException as error:
            operation.code = safe_code(error)
            operation.outcome = ('cancelled' if isinstance(error, asyncio.CancelledError) else
                                 'timeout' if isinstance(error, TimeoutError) else 'failed')
            raise
        finally:
            operation.duration_ms = (time.monotonic() - started) * 1000
            span.set_attribute('duration_ms', operation.duration_ms)
            span.set_attribute('outcome', operation.outcome)
            if operation.code:
                span.set_attribute('code', operation.code)
            span.set_status(trace.StatusCode.ERROR if operation.outcome in {'failed', 'timeout', 'deny'}
                            else trace.StatusCode.OK)
