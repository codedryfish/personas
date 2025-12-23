"""Simulation-related ORM models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from persona_sim.db.base import Base


class SimulationStatus(StrEnum):
    """Lifecycle status for a simulation run."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationRun(Base):
    """Primary record for a simulation run."""

    __tablename__ = "simulation_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    scenario_json: Mapped[str] = mapped_column(Text, nullable=False)
    personas_json: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[SimulationStatus] = mapped_column(
        Enum(SimulationStatus, native_enum=False), nullable=False, default=SimulationStatus.CREATED
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)

    transcript_events: Mapped[List["TranscriptEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    evaluation_report: Mapped[Optional["EvaluationReport"]] = relationship(
        back_populates="run", uselist=False, cascade="all, delete-orphan"
    )


class TranscriptEvent(Base):
    """Logged event associated with a simulation run."""

    __tablename__ = "transcript_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulation_runs.run_id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[str] = mapped_column(String(50), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    run: Mapped[SimulationRun] = relationship(back_populates="transcript_events")


class EvaluationReport(Base):
    """Evaluation report tied to a simulation run."""

    __tablename__ = "evaluation_reports"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulation_runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[SimulationRun] = relationship(back_populates="evaluation_report")
