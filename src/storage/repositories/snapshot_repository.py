from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from src.domain.snapshot_schema import SnapshotSchema
from src.domain.enums import SnapshotStatus
from src.storage.models.snapshot import DeviceModel, Question, QuestionOption, Snapshot, SnapshotCategory


class SnapshotRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_draft_snapshot(self, snapshot_schema: SnapshotSchema) -> Snapshot:
        async with self._session_factory() as session:
            version = await self._get_next_version(session)
            snapshot = Snapshot(
                version=version,
                source_name=snapshot_schema.source_name,
                pricing_city=snapshot_schema.pricing_city,
                status=SnapshotStatus.DRAFT.value,
                imported_at=snapshot_schema.imported_at,
            )

            for category_schema in snapshot_schema.categories:
                category = SnapshotCategory(
                    category_code=category_schema.category_code.value,
                    title=category_schema.title,
                    is_enabled=category_schema.is_enabled,
                    sort_order=category_schema.sort_order,
                )

                category.device_models = [
                    DeviceModel(
                        code=model.code,
                        title=model.title,
                        metadata_json=model.metadata,
                        sort_order=model.sort_order,
                        is_enabled=model.is_enabled,
                    )
                    for model in category_schema.models
                ]

                category.questions = []
                for question_schema in category_schema.questions:
                    question = Question(
                        code=question_schema.code,
                        title=question_schema.title,
                        step_index=question_schema.step_index,
                        question_kind=question_schema.question_kind,
                        branching_rules_json=question_schema.branching_rules,
                        is_required=question_schema.is_required,
                    )
                    question.options = [
                        QuestionOption(
                            code=option.code,
                            title=option.title,
                            pricing_payload_json=option.pricing_payload,
                            sort_order=option.sort_order,
                            is_enabled=option.is_enabled,
                        )
                        for option in question_schema.options
                    ]
                    category.questions.append(question)

                snapshot.categories.append(category)

            session.add(snapshot)
            await session.commit()
            await session.refresh(snapshot)
            return snapshot

    async def get_active_snapshot(self) -> Snapshot | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Snapshot)
                .where(Snapshot.status == SnapshotStatus.ACTIVE.value)
                .options(
                    selectinload(Snapshot.categories).selectinload(SnapshotCategory.device_models),
                    selectinload(Snapshot.categories).selectinload(SnapshotCategory.questions),
                )
            )
            return result.scalar_one_or_none()

    async def list_snapshots(self) -> Sequence[Snapshot]:
        async with self._session_factory() as session:
            result = await session.execute(select(Snapshot).order_by(Snapshot.version.desc()))
            return result.scalars().all()

    async def _get_next_version(self, session: AsyncSession) -> int:
        result = await session.execute(select(Snapshot.version).order_by(Snapshot.version.desc()).limit(1))
        current_version = result.scalar_one_or_none()
        return 1 if current_version is None else current_version + 1
