from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums import SnapshotStatus, SupportedCategory
from src.storage.models.base import Base
from src.storage.models.mixins import TimestampMixin


class Snapshot(TimestampMixin, Base):
    __tablename__ = "snapshots"
    __table_args__ = (
        UniqueConstraint("version", name="uq_snapshots_version"),
        Index("ix_snapshots_status", "status"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pricing_city: Mapped[str] = mapped_column(String(32), nullable=False, default="moscow")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=SnapshotStatus.DRAFT.value)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    categories: Mapped[list[SnapshotCategory]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")
    leads: Mapped[list[Lead]] = relationship(back_populates="snapshot")


class SnapshotCategory(TimestampMixin, Base):
    __tablename__ = "snapshot_categories"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "category_code", name="uq_snapshot_categories_snapshot_id_category_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False)
    category_code: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    snapshot: Mapped[Snapshot] = relationship(back_populates="categories")
    device_models: Mapped[list[DeviceModel]] = relationship(back_populates="category", cascade="all, delete-orphan")
    questions: Mapped[list[Question]] = relationship(back_populates="category", cascade="all, delete-orphan")


class DeviceModel(TimestampMixin, Base):
    __tablename__ = "device_models"
    __table_args__ = (
        UniqueConstraint("category_id", "code", name="uq_device_models_category_id_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("snapshot_categories.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    category: Mapped[SnapshotCategory] = relationship(back_populates="device_models")


class Question(TimestampMixin, Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("category_id", "code", name="uq_questions_category_id_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("snapshot_categories.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="single_select")
    branching_rules_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_required: Mapped[bool] = mapped_column(default=True, nullable=False)

    category: Mapped[SnapshotCategory] = relationship(back_populates="questions")
    options: Mapped[list[QuestionOption]] = relationship(back_populates="question", cascade="all, delete-orphan")


class QuestionOption(TimestampMixin, Base):
    __tablename__ = "question_options"
    __table_args__ = (
        UniqueConstraint("question_id", "code", name="uq_question_options_question_id_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    pricing_payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    question: Mapped[Question] = relationship(back_populates="options")


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_snapshot_id", "snapshot_id"),
        Index("ix_leads_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("snapshots.id", ondelete="RESTRICT"), nullable=False)
    category_code: Mapped[str] = mapped_column(String(32), nullable=False)
    device_model_code: Mapped[str] = mapped_column(String(128), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_value: Mapped[str] = mapped_column(String(120), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    quoted_price: Mapped[int] = mapped_column(Integer, nullable=False)
    answers_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    snapshot: Mapped[Snapshot] = relationship(back_populates="leads")


SUPPORTED_CATEGORY_CODES = {item.value for item in SupportedCategory}
