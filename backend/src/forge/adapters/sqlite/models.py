"""SQLAlchemy records for Forge's local durable state."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class AgentRecord(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    versions: Mapped[list["AgentVersionRecord"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="AgentVersionRecord.version",
    )


class AgentVersionRecord(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version", name="uq_agent_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="RESTRICT"), index=True
    )
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    instructions: Mapped[str] = mapped_column(Text(), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    planner: Mapped[str] = mapped_column(String(80), nullable=False)
    tools: Mapped[list[str]] = mapped_column(JSON(), default=list, nullable=False)
    max_steps: Mapped[int] = mapped_column(Integer(), default=12, nullable=False)
    timeout_seconds: Mapped[float] = mapped_column(
        Float(), default=30, server_default="30", nullable=False
    )
    max_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    max_cost_usd: Mapped[float | None] = mapped_column(Float(), nullable=True)
    max_retries: Mapped[int] = mapped_column(
        Integer(), default=2, server_default="2", nullable=False
    )
    max_output_tokens: Mapped[int] = mapped_column(
        Integer(), default=2048, server_default="2048", nullable=False
    )
    input_cost_per_million: Mapped[float | None] = mapped_column(Float(), nullable=True)
    output_cost_per_million: Mapped[float | None] = mapped_column(
        Float(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    agent: Mapped[AgentRecord] = relationship(back_populates="versions")
    runs: Mapped[list["RunRecord"]] = relationship(back_populates="agent_version")


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_version_id: Mapped[str] = mapped_column(
        ForeignKey("agent_versions.id", ondelete="RESTRICT"), index=True
    )
    input: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    agent_version: Mapped[AgentVersionRecord] = relationship(back_populates="runs")
    events: Mapped[list["EventRecord"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="EventRecord.sequence",
    )
    steps: Mapped[list["StepRecord"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="StepRecord.sequence",
    )


class StepRecord(Base):
    __tablename__ = "steps"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_run_step_sequence"),
        Index("ix_steps_run_created", "run_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer(), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSON(), default=dict, nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer(), default=1, nullable=False)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    run: Mapped[RunRecord] = relationship(back_populates="steps")


class EventRecord(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_run_event_sequence"),
        Index("ix_events_run_created", "run_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer(), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON(), default=dict, nullable=False
    )
    schema_version: Mapped[int] = mapped_column(Integer(), default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    run: Mapped[RunRecord] = relationship(back_populates="events")


class RunCheckpointRecord(Base):
    __tablename__ = 'run_checkpoints'
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id', ondelete='CASCADE'), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON(), nullable=False)


class ApprovalRecord(Base):
    __tablename__ = 'approvals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id', ondelete='CASCADE'))
    step_id: Mapped[str] = mapped_column(ForeignKey('steps.id'))
    tool_name: Mapped[str] = mapped_column(String(80))
    tool_version: Mapped[str] = mapped_column(String(80))
    arguments: Mapped[dict] = mapped_column(JSON())
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArtifactRecord(Base):
    __tablename__ = 'artifacts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id', ondelete='CASCADE'))
    path: Mapped[str] = mapped_column(Text())
    size_bytes: Mapped[int] = mapped_column(Integer())
    media_type: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
