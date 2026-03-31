from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.storage.models.snapshot import Lead


class LeadRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(self, lead: Lead) -> Lead:
        async with self._session_factory() as session:
            session.add(lead)
            await session.commit()
            await session.refresh(lead)
            return lead
