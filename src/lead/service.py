from __future__ import annotations

from dataclasses import dataclass

from src.storage.models.snapshot import Lead
from src.storage.repositories.lead_repository import LeadRepository
from src.storage.repositories.snapshot_repository import SnapshotRepository


@dataclass(slots=True, frozen=True)
class LeadCaptureRequest:
    snapshot_version: int
    category_code: str
    device_model_code: str
    quoted_price: int
    answers: dict[str, str]
    contact_name: str
    contact_value: str
    comment: str | None = None


class LeadService:
    def __init__(
        self,
        lead_repository: LeadRepository,
        snapshot_repository: SnapshotRepository,
    ) -> None:
        self._lead_repository = lead_repository
        self._snapshot_repository = snapshot_repository

    async def capture_lead(self, request: LeadCaptureRequest) -> Lead:
        snapshot = await self._snapshot_repository.get_snapshot_by_version(request.snapshot_version)
        if snapshot is None:
            raise ValueError(f"Snapshot version '{request.snapshot_version}' does not exist.")

        lead = Lead(
            snapshot_id=snapshot.id,
            category_code=request.category_code,
            device_model_code=request.device_model_code,
            contact_name=request.contact_name,
            contact_value=request.contact_value,
            comment=request.comment,
            quoted_price=request.quoted_price,
            answers_json=dict(request.answers),
        )
        return await self._lead_repository.add(lead)