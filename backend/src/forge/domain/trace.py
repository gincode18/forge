"""Stable durable identities shared by persisted events and runtime spans."""
import hashlib


def trace_id_for_run(run_id: str) -> str:
    return hashlib.sha256(run_id.encode()).hexdigest()[:32]


def span_id_for_step(step_id: str) -> str:
    return hashlib.sha256(step_id.encode()).hexdigest()[:16]
