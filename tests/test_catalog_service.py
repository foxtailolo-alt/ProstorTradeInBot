from __future__ import annotations

from collections.abc import Mapping

from src.catalog.service import ActiveSnapshotNotFoundError, CatalogService
from src.domain.enums import SupportedCategory
from src.storage.models.snapshot import (
    DeviceModel,
    Question,
    QuestionOption,
    Snapshot,
    SnapshotCategory,
)


class StubSnapshotRepository:
    def __init__(
        self,
        active_snapshot: Snapshot | None,
        versioned_snapshot: Snapshot | None,
    ) -> None:
        self._active_snapshot = active_snapshot
        self._versioned_snapshot = versioned_snapshot

    async def get_active_snapshot(self) -> Snapshot | None:
        return self._active_snapshot

    async def get_snapshot_by_version(self, version: int) -> Snapshot | None:
        if self._versioned_snapshot is None:
            return None
        return self._versioned_snapshot if self._versioned_snapshot.version == version else None


def _build_snapshot() -> Snapshot:
    snapshot = Snapshot(
        id="snapshot-1",
        version=3,
        source_name="damprodam_api",
        pricing_city="moscow",
        status="active",
        imported_at=None,
    )
    category = SnapshotCategory(
        category_code="iphone",
        title="iPhone",
        sort_order=0,
        is_enabled=True,
    )
    category.device_models = [
        DeviceModel(
            code="iphone15",
            title="iPhone 15",
            sort_order=0,
            is_enabled=True,
            metadata_json={},
        ),
        DeviceModel(
            code="iphone14",
            title="iPhone 14",
            sort_order=1,
            is_enabled=True,
            metadata_json={},
        ),
    ]
    memory_question = Question(
        code="memory",
        title="Память",
        step_index=1,
        question_kind="single_select",
        branching_rules_json={
            "model_option_map": {"iphone15": ["128", "256"], "iphone14": ["128"]}
        },
        is_required=True,
    )
    memory_question.options = [
        QuestionOption(
            code="128",
            title="128 ГБ",
            sort_order=0,
            is_enabled=True,
            pricing_payload_json={},
        ),
        QuestionOption(
            code="256",
            title="256 ГБ",
            sort_order=1,
            is_enabled=True,
            pricing_payload_json={},
        ),
    ]
    condition_question = Question(
        code="condition",
        title="Состояние",
        step_index=2,
        question_kind="single_select",
        branching_rules_json={},
        is_required=True,
    )
    condition_question.options = [
        QuestionOption(
            code="perfect",
            title="Как новый",
            sort_order=0,
            is_enabled=True,
            pricing_payload_json={"bonus": 2000},
        ),
        QuestionOption(
            code="good",
            title="Хорошее",
            sort_order=1,
            is_enabled=True,
            pricing_payload_json={},
        ),
    ]
    category.questions = [memory_question, condition_question]
    snapshot.categories = [category]
    return snapshot


async def test_catalog_service_requires_active_snapshot() -> None:
    service = CatalogService(StubSnapshotRepository(active_snapshot=None, versioned_snapshot=None))

    try:
        await service.get_active_overview()
    except ActiveSnapshotNotFoundError:
        pass
    else:
        raise AssertionError("Expected ActiveSnapshotNotFoundError")


async def test_catalog_service_filters_model_specific_options() -> None:
    snapshot = _build_snapshot()
    service = CatalogService(
        StubSnapshotRepository(active_snapshot=snapshot, versioned_snapshot=snapshot)
    )

    overview = await service.get_active_overview()
    models = await service.list_models(overview.snapshot_version, "iphone")
    answers, question = await service.advance_selection(
        overview.snapshot_version,
        "iphone",
        "iphone14",
        {},
    )

    assert [model.code for model in models] == ["iphone15", "iphone14"]
    assert answers == {"memory": "128"}
    assert question is not None
    assert question.code == "condition"
    assert [option.code for option in question.options] == ["perfect", "good"]


async def test_catalog_service_resolves_selection_details() -> None:
    snapshot = _build_snapshot()
    service = CatalogService(
        StubSnapshotRepository(active_snapshot=snapshot, versioned_snapshot=snapshot)
    )

    selection = await service.resolve_selection(
        snapshot_version=3,
        category_code="iphone",
        model_code="iphone15",
        answers={"memory": "256", "condition": "perfect"},
    )

    assert selection.device_model_title == "iPhone 15"
    assert [answer.option_code for answer in selection.answers] == ["256", "perfect"]
    assert selection.answers[1].pricing_payload == {"bonus": 2000}


class StubDamProdamApiClient:
    async def fetch_category_params(
        self,
        category: SupportedCategory,
        payload: Mapping[str, str],
    ) -> dict[str, dict]:
        assert category is SupportedCategory.MAC
        year = payload.get("year")
        cpu = payload.get("cpu")
        inches = payload.get("inches")
        memory = payload.get("memory")

        params: dict[str, dict] = {
            "year": {"vals": ["2023"]},
            "cpu": {"vals": ["m3"]},
            "inches": {"vals": ["14", "16"] if cpu == "m3" else ["14"]},
            "memory": {"vals": ["512"] if inches == "16" else ["256", "512"]},
            "ram": {"vals": ["18"] if memory == "512" else ["8", "18"]},
            "touch_bar": {"vals": ["false"]},
        }
        if year == "2023":
            params.pop("year")
        if cpu == "m3":
            params.pop("cpu")
        if inches is not None:
            params.pop("inches", None)
        if memory is not None:
            params.pop("memory", None)
        if inches == "16":
            params["is_retina"] = {"vals": [True]}
        return {"mbp14": {"params": params}}

    async def fetch_buyout_price(
        self,
        category: SupportedCategory,
        payload: Mapping[str, str],
    ) -> dict[str, int]:
        assert category is SupportedCategory.MAC
        return {"counted_price": 50000}


class StubMacCpuOrderingApiClient:
    async def fetch_category_params(
        self,
        category: SupportedCategory,
        payload: Mapping[str, str],
    ) -> dict[str, dict]:
        assert category is SupportedCategory.MAC
        return {
            "macbookpro": {
                "params": {
                    "cpu": {
                        "vals": [
                            {"name": "Apple M2 Max", "abbr": "applem2max"},
                            {"name": "Apple M2 Pro", "abbr": "applem2pro"},
                            {"name": "Apple M3", "abbr": "applem3"},
                            {"name": "Apple M3 Pro", "abbr": "applem3pro"},
                        ]
                    }
                }
            }
        }

    async def fetch_buyout_price(
        self,
        category: SupportedCategory,
        payload: Mapping[str, str],
    ) -> dict[str, int]:
        assert category is SupportedCategory.MAC
        return {"counted_price": 50000}


class StubMacAirViabilityApiClient:
    async def fetch_category_params(
        self,
        category: SupportedCategory,
        payload: Mapping[str, str],
    ) -> dict[str, dict]:
        assert category is SupportedCategory.MAC
        params = {
            "year": {"vals": ["2017"]},
            "inches": {"vals": ["13"]},
            "memory": {"vals": ["128"]},
            "ram": {"vals": ["8"]},
            "touch_bar": {"vals": ["no"]},
            "is_retina": {"vals": [True, False]},
        }

        if payload.get("year") == "2017":
            params.pop("year", None)
        if payload.get("inches") == "13":
            params.pop("inches", None)
        if payload.get("memory") == "128":
            params.pop("memory", None)
        if payload.get("ram") == "8":
            params.pop("ram", None)
        if payload.get("touch_bar") == "no":
            params.pop("touch_bar", None)
        if payload.get("is_retina") in {"true", "false"}:
            params.pop("is_retina", None)

        return {"macbookair": {"params": params}}

    async def fetch_buyout_price(
        self,
        category: SupportedCategory,
        payload: Mapping[str, str],
    ) -> dict[str, int]:
        assert category is SupportedCategory.MAC
        if payload.get("is_retina") == "false":
            return {"counted_price": 12000}
        raise ValueError("invalid configuration")


def _build_mac_snapshot() -> Snapshot:
    snapshot = Snapshot(
        id="snapshot-mac",
        version=4,
        source_name="damprodam_api",
        pricing_city="moscow",
        status="active",
        imported_at=None,
    )
    category = SnapshotCategory(
        category_code="mac",
        title="MacBook/iMac",
        sort_order=0,
        is_enabled=True,
    )
    category.device_models = [
        DeviceModel(
            code="mbp14",
            title="MacBook Pro 14",
            sort_order=0,
            is_enabled=True,
            metadata_json={},
        )
    ]

    def question(code: str, step_index: int, options: list[str]) -> Question:
        item = Question(
            code=code,
            title=code,
            step_index=step_index,
            question_kind="single_select",
            branching_rules_json={"model_option_map": {"mbp14": options}},
            is_required=True,
        )
        item.options = [
            QuestionOption(
                code=option,
                title=option,
                sort_order=index,
                is_enabled=True,
                pricing_payload_json={},
            )
            for index, option in enumerate(options)
        ]
        return item

    category.questions = [
        question("year", 1, ["2023"]),
        question("cpu", 2, ["m3"]),
        question("inches", 3, ["14", "16"]),
        question("memory", 4, ["256", "512"]),
        question("ram", 5, ["8", "18"]),
        question("touch_bar", 6, ["false"]),
        question("is_retina", 7, ["true"]),
    ]
    snapshot.categories = [category]
    return snapshot


def _build_macbookpro_cpu_snapshot() -> Snapshot:
    snapshot = Snapshot(
        id="snapshot-mbp-cpu",
        version=5,
        source_name="damprodam_api",
        pricing_city="moscow",
        status="active",
        imported_at=None,
    )
    category = SnapshotCategory(
        category_code="mac",
        title="MacBook/iMac",
        sort_order=0,
        is_enabled=True,
    )
    category.device_models = [
        DeviceModel(
            code="macbookpro",
            title="MacBook Pro",
            sort_order=0,
            is_enabled=True,
            metadata_json={},
        )
    ]
    cpu_question = Question(
        code="cpu",
        title="Процессор",
        step_index=2,
        question_kind="single_select",
        branching_rules_json={
            "model_option_map": {
                "macbookpro": ["applem3", "applem2max", "applem2pro", "applem3pro"]
            }
        },
        is_required=True,
    )
    cpu_question.options = [
        QuestionOption(
            code=code,
            title=code,
            sort_order=index,
            is_enabled=True,
            pricing_payload_json={},
        )
        for index, code in enumerate(["applem3", "applem2max", "applem2pro", "applem3pro"])
    ]
    category.questions = [cpu_question]
    snapshot.categories = [category]
    return snapshot


def _build_macbookair_retina_snapshot() -> Snapshot:
    snapshot = Snapshot(
        id="snapshot-mba-retina",
        version=6,
        source_name="damprodam_api",
        pricing_city="moscow",
        status="active",
        imported_at=None,
    )
    category = SnapshotCategory(
        category_code="mac",
        title="MacBook/iMac",
        sort_order=0,
        is_enabled=True,
    )
    category.device_models = [
        DeviceModel(
            code="macbookair",
            title="MacBook Air",
            sort_order=0,
            is_enabled=True,
            metadata_json={},
        )
    ]

    def question(code: str, step_index: int, options: list[str]) -> Question:
        item = Question(
            code=code,
            title=code,
            step_index=step_index,
            question_kind="single_select",
            branching_rules_json={"model_option_map": {"macbookair": options}},
            is_required=True,
        )
        item.options = [
            QuestionOption(
                code=option,
                title=option,
                sort_order=index,
                is_enabled=True,
                pricing_payload_json={},
            )
            for index, option in enumerate(options)
        ]
        return item

    category.questions = [
        question("year", 1, ["2017"]),
        question("inches", 2, ["13"]),
        question("memory", 3, ["128"]),
        question("ram", 4, ["8"]),
        question("touch_bar", 5, ["no"]),
        question("is_retina", 6, ["true", "false"]),
        question("cpu", 7, ["intel", "applem1"]),
        question("damaged", 8, ["false", "true"]),
    ]
    snapshot.categories = [category]
    return snapshot


async def test_catalog_service_auto_skips_single_option_mac_questions() -> None:
    snapshot = _build_mac_snapshot()
    service = CatalogService(
        StubSnapshotRepository(active_snapshot=snapshot, versioned_snapshot=snapshot),
        StubDamProdamApiClient(),
    )

    answers, question = await service.advance_selection(4, "mac", "mbp14", {})

    assert answers == {"year": "2023", "cpu": "m3"}
    assert question is not None
    assert question.code == "inches"
    assert [option.code for option in question.options] == ["14", "16"]


async def test_catalog_service_mac_options_follow_previous_answers() -> None:
    snapshot = _build_mac_snapshot()
    service = CatalogService(
        StubSnapshotRepository(active_snapshot=snapshot, versioned_snapshot=snapshot),
        StubDamProdamApiClient(),
    )

    answers, question = await service.advance_selection(
        4,
        "mac",
        "mbp14",
        {"year": "2023", "cpu": "m3", "inches": "16"},
    )

    assert question is None
    assert answers == {
        "year": "2023",
        "cpu": "m3",
        "inches": "16",
        "memory": "512",
        "ram": "18",
        "touch_bar": "false",
        "is_retina": "true",
    }

    selection = await service.resolve_selection(
        4,
        "mac",
        "mbp14",
        {"year": "2023", "cpu": "m3", "inches": "16", "memory": "512"},
    )

    assert {answer.question_code: answer.option_code for answer in selection.answers} == {
        "year": "2023",
        "cpu": "m3",
        "inches": "16",
        "memory": "512",
        "ram": "18",
        "touch_bar": "false",
        "is_retina": "true",
    }


async def test_catalog_service_uses_live_cpu_option_order() -> None:
    snapshot = _build_macbookpro_cpu_snapshot()
    service = CatalogService(
        StubSnapshotRepository(active_snapshot=snapshot, versioned_snapshot=snapshot),
        StubMacCpuOrderingApiClient(),
    )

    answers, question = await service.advance_selection(5, "mac", "macbookpro", {"year": "2023"})

    assert answers == {"year": "2023"}
    assert question is not None
    assert question.code == "cpu"
    assert [option.code for option in question.options] == [
        "applem2max",
        "applem2pro",
        "applem3",
        "applem3pro",
    ]


async def test_catalog_service_filters_invalid_late_mac_options() -> None:
    snapshot = _build_macbookair_retina_snapshot()
    service = CatalogService(
        StubSnapshotRepository(active_snapshot=snapshot, versioned_snapshot=snapshot),
        StubMacAirViabilityApiClient(),
    )

    answers, question = await service.advance_selection(
        6,
        "mac",
        "macbookair",
        {
            "year": "2017",
            "inches": "13",
            "memory": "128",
            "ram": "8",
            "touch_bar": "no",
        },
    )

    assert answers == {
        "year": "2017",
        "inches": "13",
        "memory": "128",
        "ram": "8",
        "touch_bar": "no",
        "is_retina": "false",
    }
    assert question is not None
    assert question.code == "damaged"