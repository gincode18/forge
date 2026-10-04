"""Real SDK spans, owned lifecycle, deterministic correlation, and safe failures."""
import asyncio
import hashlib

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_owned_provider_exports_real_deterministic_spans_without_global_mutation():
    from forge.observability import telemetry

    global_provider = trace.get_tracer_provider()
    exporter = InMemorySpanExporter()
    handle = telemetry.configure_telemetry()
    handle.provider.add_span_processor(SimpleSpanProcessor(exporter))
    with telemetry.use_provider(handle.provider), telemetry.boundary('model', 'run-a', 'step-a') as operation:
        assert exporter.get_finished_spans() == ()
        operation.outcome = 'completed'
    span, = exporter.get_finished_spans()
    assert isinstance(span, ReadableSpan)
    assert span.context.trace_id == int(hashlib.sha256(b'run-a').hexdigest()[:32], 16)
    assert span.context.span_id == int(hashlib.sha256(b'step-a').hexdigest()[:16], 16)
    assert span.attributes['run_id'] == 'run-a'
    assert span.attributes['step_id'] == 'step-a'
    assert span.attributes['outcome'] == 'completed'
    assert span.attributes['duration_ms'] >= 0
    assert span.end_time >= span.start_time
    assert trace.get_tracer_provider() is global_provider
    handle.close()
    handle.close()


@pytest.mark.parametrize('error,outcome', [(RuntimeError('SYNTHETIC-SECRET'), 'failed'),
                                          (TimeoutError('SYNTHETIC-SECRET'), 'timeout'),
                                          (asyncio.CancelledError('SYNTHETIC-SECRET'), 'cancelled')])
def test_boundary_never_exports_exception_text_or_events(error, outcome):
    from forge.observability import telemetry

    exporter = InMemorySpanExporter()
    handle = telemetry.configure_telemetry()
    handle.provider.add_span_processor(SimpleSpanProcessor(exporter))
    with (telemetry.use_provider(handle.provider), pytest.raises(type(error)),
          telemetry.boundary('model', 'run-a', 'step-a')):
        raise error
    span, = exporter.get_finished_spans()
    assert span.attributes['outcome'] == outcome
    assert span.events == ()
    assert 'SYNTHETIC' not in span.to_json()
    assert span.status.description is None
    handle.close()


def test_policy_is_child_of_tool_with_separate_identity():
    from forge.observability import telemetry

    exporter = InMemorySpanExporter()
    handle = telemetry.configure_telemetry()
    handle.provider.add_span_processor(SimpleSpanProcessor(exporter))
    with (telemetry.use_provider(handle.provider), telemetry.boundary('tool', 'run-a', 'step-a'),
          telemetry.boundary('policy', 'run-a', 'step-a', child=True) as policy):
        policy.outcome = 'deny'
    policy_span, tool_span = exporter.get_finished_spans()
    assert policy_span.parent.span_id == tool_span.context.span_id
    assert policy_span.context.span_id != tool_span.context.span_id
    assert policy_span.context.trace_id == tool_span.context.trace_id
    assert policy_span.attributes['step_id'] == 'step-a'
    handle.close()


def test_closing_nested_handles_out_of_order_never_restores_a_shutdown_provider():
    from forge.observability import telemetry

    baseline = telemetry._default_provider
    first = telemetry.configure_telemetry()
    second = telemetry.configure_telemetry()
    first.close()
    second.close()
    assert telemetry._default_provider is baseline


def test_task_local_provider_overrides_restore_without_cross_task_pollution():
    from forge.observability import telemetry

    first = telemetry.configure_telemetry()
    second = telemetry.configure_telemetry()
    exports = [InMemorySpanExporter(), InMemorySpanExporter()]
    for handle, exporter in zip([first, second], exports, strict=True):
        handle.provider.add_span_processor(SimpleSpanProcessor(exporter))

    async def operation(handle, name):
        with telemetry.use_provider(handle.provider):
            await asyncio.sleep(0)
            with telemetry.boundary('model', name, name):
                await asyncio.sleep(0)

    async def run():
        await asyncio.gather(operation(first, 'first'), operation(second, 'second'))

    asyncio.run(run())
    assert [s.attributes['run_id'] for s in exports[0].get_finished_spans()] == ['first']
    assert [s.attributes['run_id'] for s in exports[1].get_finished_spans()] == ['second']
    second.close()
    first.close()
