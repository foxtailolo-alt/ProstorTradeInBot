from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.domain.enums import SupportedCategory
from src.domain.snapshot_schema import CategorySchema, SnapshotSchema


@dataclass(slots=True, frozen=True)
class ExtractorContext:
    category: SupportedCategory
    pricing_city: str = "moscow"


class CategoryExtractor(Protocol):
    async def extract(self, context: ExtractorContext) -> CategorySchema:
        ...


class SnapshotImporter(Protocol):
    async def import_snapshot(self) -> SnapshotSchema:
        ...
