from __future__ import annotations

from src.lead.service import LeadCaptureRequest, LeadService
from src.storage.models.snapshot import Lead, Snapshot


class StubLeadRepository:
    saved_lead: Lead | None = None

    async def add(self, lead: Lead) -> Lead:
        self.saved_lead = lead
        return lead


class StubSnapshotRepository:
    def __init__(self, snapshot: Snapshot | None) -> None:
        self._snapshot = snapshot

    async def get_snapshot_by_version(self, version: int) -> Snapshot | None:
        if self._snapshot is None:
            return None
        return self._snapshot if self._snapshot.version == version else None


async def test_lead_service_persists_resolved_snapshot_reference() -> None:
    snapshot = Snapshot(
        id="snapshot-1",
        version=8,
        source_name="damprodam_api",
        pricing_city="moscow",
        status="active",
        imported_at=None,
    )
    lead_repository = StubLeadRepository()
    service = LeadService(lead_repository, StubSnapshotRepository(snapshot))

    lead = await service.capture_lead(
        LeadCaptureRequest(
            snapshot_version=8,
            category_code="iphone",
            device_model_code="iphone15",
            quoted_price=45900,
            answers={"memory": "128"},
            contact_name="Ivan",
            contact_value="+79990000000",
            comment="Связаться вечером",
        )
    )

    assert lead.snapshot_id == "snapshot-1"
    assert lead_repository.saved_lead is lead
    assert lead.answers_json == {"memory": "128"}