import uuid
from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    Boolean,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Index,
    func,
    literal_column,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, now


def uid():
    return str(uuid.uuid4())


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class User(Record, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)


class Session(Record, Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True))


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)


class Context(Record, Base):
    __tablename__ = "contexts"
    body: Mapped[dict] = mapped_column(JSONB, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class Configuration(Base):
    __tablename__ = "configuration"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)


class Connection(Record, Base):
    __tablename__ = "connections"
    provider: Mapped[str] = mapped_column(String(30), unique=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    encrypted: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="no_comprobada")
    detail: Mapped[str] = mapped_column(Text, default="")
    checked_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Idea(Record, Base):
    __tablename__ = "ideas"
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    angle: Mapped[str] = mapped_column(Text, default="")
    topic: Mapped[str] = mapped_column(String(100), default="")
    content_type: Mapped[str] = mapped_column(String(100), default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    project_connection: Mapped[str] = mapped_column(Text, default="")
    origin: Mapped[str] = mapped_column(String(30), default="automatico")
    original_input: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="pendiente")
    discard_reason: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    current_news: Mapped[bool] = mapped_column(Boolean, default=False)
    relations: Mapped[list] = mapped_column(JSONB, default=list)
    signals: Mapped[list] = mapped_column(JSONB, default=list)
    context_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        Index(
            "ideas_search",
            literal_column(
                "to_tsvector('spanish'::regconfig, (((((title::text || ' '::text) || summary) || ' '::text) || angle) || ' '::text) || topic::text)"
            ),
            postgresql_using="gin",
        ),
    )


class Publication(Record, Base):
    __tablename__ = "publications"
    idea_id: Mapped[str | None] = mapped_column(
        ForeignKey("ideas.id"), unique=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(300))
    wp_status: Mapped[str] = mapped_column(String(40), default="local")
    li_status: Mapped[str] = mapped_column(String(40), default="local")
    wp_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    li_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str] = mapped_column(Text, default="")
    url_history: Mapped[list] = mapped_column(JSONB, default=list)
    remote_modified: Mapped[str] = mapped_column(String(100), default="")
    remote_fingerprint: Mapped[str] = mapped_column(String(64), default="")
    external_change: Mapped[bool] = mapped_column(Boolean, default=False)
    public_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    current_wp: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_li: Mapped[str | None] = mapped_column(String(36), nullable=True)
    best_wp: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sent_wp: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sent_li: Mapped[str | None] = mapped_column(String(36), nullable=True)
    li_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    file_id: Mapped[str | None] = mapped_column(ForeignKey("files.id"), nullable=True)
    confirmations: Mapped[dict] = mapped_column(JSONB, default=dict)
    synced_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __table_args__ = (
        Index(
            "publications_search",
            func.to_tsvector(literal_column("'spanish'"), title),
            postgresql_using="gin",
        ),
    )


class Version(Record, Base):
    __tablename__ = "versions"
    publication_id: Mapped[str] = mapped_column(
        ForeignKey("publications.id"), index=True
    )
    channel: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(100))
    data: Mapped[dict] = mapped_column(JSONB)
    fingerprint: Mapped[str] = mapped_column(String(64))
    based_on: Mapped[str | None] = mapped_column(
        ForeignKey("versions.id"), nullable=True
    )
    context_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)


class Evaluation(Record, Base):
    __tablename__ = "evaluations"
    version_id: Mapped[str] = mapped_column(ForeignKey("versions.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    evaluator: Mapped[str] = mapped_column(String(100))
    score: Mapped[int] = mapped_column(Integer)
    result: Mapped[dict] = mapped_column(JSONB)
    editorial: Mapped[dict] = mapped_column(JSONB, default=dict)


class Source(Record, Base):
    __tablename__ = "sources"
    idea_id: Mapped[str | None] = mapped_column(ForeignKey("ideas.id"), nullable=True)
    publication_id: Mapped[str | None] = mapped_column(
        ForeignKey("publications.id"), nullable=True
    )
    version_id: Mapped[str | None] = mapped_column(
        ForeignKey("versions.id"), nullable=True
    )
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, default="")
    excerpt: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consulted_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)


class File(Record, Base):
    __tablename__ = "files"
    path: Mapped[str] = mapped_column(Text)
    mime: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    alt: Mapped[str] = mapped_column(Text, default="")
    wp_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_uncertain: Mapped[bool] = mapped_column(Boolean, default=False)


class Metric(Record, Base):
    __tablename__ = "metrics"
    publication_id: Mapped[str | None] = mapped_column(
        ForeignKey("publications.id"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(30))
    period_start: Mapped[str] = mapped_column(String(10))
    period_end: Mapped[str] = mapped_column(String(10))
    dimensions: Mapped[dict] = mapped_column(JSONB)
    values: Mapped[dict] = mapped_column(JSONB)
    quality: Mapped[str] = mapped_column(String(40))
    __table_args__ = (
        UniqueConstraint(
            "provider", "period_start", "period_end", "publication_id", "dimensions"
        ),
    )


class AnalyticsRow(Record, Base):
    __tablename__ = "analytics_rows"
    provider: Mapped[str] = mapped_column(String(30))
    property: Mapped[str] = mapped_column(Text)
    dataset: Mapped[str] = mapped_column(String(20))
    day: Mapped[str] = mapped_column(String(10), index=True)
    dimensions: Mapped[dict] = mapped_column(JSONB)
    values: Mapped[dict] = mapped_column(JSONB)
    quality: Mapped[str] = mapped_column(String(40))
    __table_args__ = (
        UniqueConstraint("provider", "property", "dataset", "day", "dimensions"),
    )


class AnalyticsBatch(Record, Base):
    __tablename__ = "analytics_batches"
    provider: Mapped[str] = mapped_column(String(30))
    property: Mapped[str] = mapped_column(Text)
    dataset: Mapped[str] = mapped_column(String(20))
    start: Mapped[str] = mapped_column(String(10))
    end: Mapped[str] = mapped_column(String(10))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB)
    rows: Mapped[int] = mapped_column(Integer)


class Job(Record, Base):
    __tablename__ = "jobs"
    kind: Mapped[str] = mapped_column(String(40))
    active_key: Mapped[str | None] = mapped_column(
        String(120), unique=True, nullable=True
    )
    parameters: Mapped[dict] = mapped_column(JSONB)
    selection: Mapped[dict] = mapped_column(JSONB, default=dict)
    context_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    state: Mapped[str] = mapped_column(String(30), default="pendiente")
    phase: Mapped[str] = mapped_column(String(120), default="En cola")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    checkpoints: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[dict] = mapped_column(JSONB, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lease_until: Mapped[object | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    heartbeat: Mapped[object | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    available_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=now)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (Index("jobs_claim", "state", "available_at", "lease_until"),)


class AICall(Record, Base):
    __tablename__ = "ai_calls"
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    phase: Mapped[str] = mapped_column(String(100))
    usage: Mapped[dict] = mapped_column(JSONB, default=dict)
    rates: Mapped[dict] = mapped_column(JSONB, default=dict)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    estimated_cost: Mapped[object | None] = mapped_column(Numeric(16, 8), nullable=True)
    calculated_cost: Mapped[object | None] = mapped_column(
        Numeric(16, 8), nullable=True
    )
    uncertain: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="enviada")


class Notification(Record, Base):
    __tablename__ = "notifications"
    message: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(30), default="info")
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class OAuthState(Record, Base):
    __tablename__ = "oauth_states"
    state_hash: Mapped[str] = mapped_column(String(64), unique=True)
    provider: Mapped[str] = mapped_column(String(30))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True))
