from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.enums import SupportedCategory


@dataclass(slots=True, frozen=True)
class OptionSchema:
    code: str
    title: str
    pricing_payload: dict = field(default_factory=dict)
    sort_order: int = 0
    is_enabled: bool = True


@dataclass(slots=True, frozen=True)
class QuestionSchema:
    code: str
    title: str
    step_index: int
    question_kind: str = "single_select"
    branching_rules: dict = field(default_factory=dict)
    options: tuple[OptionSchema, ...] = ()
    is_required: bool = True


@dataclass(slots=True, frozen=True)
class DeviceModelSchema:
    code: str
    title: str
    metadata: dict = field(default_factory=dict)
    sort_order: int = 0
    is_enabled: bool = True


@dataclass(slots=True, frozen=True)
class CategorySchema:
    category_code: SupportedCategory
    title: str
    models: tuple[DeviceModelSchema, ...]
    questions: tuple[QuestionSchema, ...]
    sort_order: int = 0
    is_enabled: bool = True


@dataclass(slots=True, frozen=True)
class SnapshotSchema:
    version: int
    source_name: str
    pricing_city: str
    imported_at: datetime
    categories: tuple[CategorySchema, ...]
