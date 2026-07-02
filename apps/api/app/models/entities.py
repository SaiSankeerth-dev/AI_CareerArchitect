from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="user")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_role: Mapped[str] = mapped_column(String(100))
    # pending | collecting | analyzing | reviewing | applying | done | failed
    status: Mapped[str] = mapped_column(String(30), default="pending")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="runs")
    sources: Mapped[list["ProfileSource"]] = relationship(back_populates="run")
    suggestions: Mapped[list["Suggestion"]] = relationship(back_populates="run")


class ProfileSource(Base):
    __tablename__ = "profile_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    platform: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(1000), default="")
    raw_content: Mapped[str] = mapped_column(Text, default="")
    screenshot_path: Mapped[str] = mapped_column(String(500), default="")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped["AnalysisRun"] = relationship(back_populates="sources")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("profile_sources.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(50))  # text | metadata | item | screenshot
    content: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000), default="")


class UnifiedProfile(Base):
    __tablename__ = "unified_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    agent: Mapped[str] = mapped_column(String(100))
    platform: Mapped[str] = mapped_column(String(50))
    field: Mapped[str] = mapped_column(String(200))
    current: Mapped[str] = mapped_column(Text, default="")
    suggested: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, default="")
    benefit: Mapped[str] = mapped_column(Text, default="")
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    # proposed | validated | rejected | approved | declined | applied | verified
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
    artifact_path: Mapped[str] = mapped_column(String(500), default="")

    run: Mapped["AnalysisRun"] = relationship(back_populates="suggestions")


class CareerReport(Base):
    __tablename__ = "career_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), unique=True, index=True)
    scores: Mapped[dict] = mapped_column(JSON, default=dict)
    gaps: Mapped[dict] = mapped_column(JSON, default=dict)
    roadmap: Mapped[list] = mapped_column(JSON, default=list)
    learning_plan: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
