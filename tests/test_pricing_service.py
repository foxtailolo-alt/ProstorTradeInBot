from __future__ import annotations

from collections.abc import Mapping

from src.catalog.service import CatalogSelection, CatalogSelectionAnswer
from src.domain.enums import SupportedCategory
from src.pricing.service import PricingService


class StubCatalogService:
    async def resolve_selection(
        self,
        snapshot_version: int,
        category_code: str,
        model_code: str,
        answers: dict[str, str],
    ) -> CatalogSelection:
        return CatalogSelection(
            snapshot_version=snapshot_version,
            category_code=category_code,
            category_title="iPhone",
            device_model_code=model_code,
            device_model_title="iPhone 15",
            model_sort_order=1,
            model_metadata={},
            answers=(
                CatalogSelectionAnswer(
                    question_code="memory",
                    question_title="Память",
                    option_code="128",
                    option_title="128 ГБ",
                    question_step_index=1,
                    option_sort_order=0,
                    pricing_payload={},
                ),
                CatalogSelectionAnswer(
                    question_code="damaged",
                    question_title="Все функции работают?",
                    option_code="false",
                    option_title="Все работает",
                    question_step_index=2,
                    option_sort_order=0,
                    pricing_payload={},
                ),
                CatalogSelectionAnswer(
                    question_code="restored_display",
                    question_title="Экран менялся?",
                    option_code="0",
                    option_title="Нет",
                    question_step_index=3,
                    option_sort_order=0,
                    pricing_payload={},
                ),
                CatalogSelectionAnswer(
                    question_code="exterier_condition",
                    question_title="Состояние корпуса и экрана",
                    option_code="best",
                    option_title="Как новый",
                    question_step_index=4,
                    option_sort_order=0,
                    pricing_payload={},
                ),
            ),
        )


class StubDamProdamApiClient:
    async def fetch_buyout_price(
        self,
        category: SupportedCategory,
        payload: Mapping[str, str],
    ) -> dict[str, int]:
        assert category is SupportedCategory.IPHONE
        assert payload == {
            "models_iphones": "iphone15",
            "memory": "128",
            "equipment_iphone": "zero",
            "restored_display": "0",
            "exterier_condition": "best",
            "damaged": "false",
        }
        return {"counted_price": 86000, "bonus_for_use": 2000}


class StubMacCatalogService:
    async def resolve_selection(
        self,
        snapshot_version: int,
        category_code: str,
        model_code: str,
        answers: dict[str, str],
    ) -> CatalogSelection:
        return CatalogSelection(
            snapshot_version=snapshot_version,
            category_code=category_code,
            category_title="Mac",
            device_model_code=model_code,
            device_model_title="MacBook Air",
            model_sort_order=1,
            model_metadata={},
            answers=(
                CatalogSelectionAnswer(
                    question_code="year",
                    question_title="Год",
                    option_code="2017",
                    option_title="2017",
                    question_step_index=1,
                    option_sort_order=0,
                    pricing_payload={},
                ),
                CatalogSelectionAnswer(
                    question_code="inches",
                    question_title="Диагональ",
                    option_code="13",
                    option_title="13",
                    question_step_index=2,
                    option_sort_order=0,
                    pricing_payload={},
                ),
                CatalogSelectionAnswer(
                    question_code="memory",
                    question_title="Память",
                    option_code="128",
                    option_title="128",
                    question_step_index=3,
                    option_sort_order=0,
                    pricing_payload={},
                ),
                CatalogSelectionAnswer(
                    question_code="ram",
                    question_title="RAM",
                    option_code="8",
                    option_title="8",
                    question_step_index=4,
                    option_sort_order=0,
                    pricing_payload={},
                ),
                CatalogSelectionAnswer(
                    question_code="touch_bar",
                    question_title="Touch Bar",
                    option_code="no",
                    option_title="Нет",
                    question_step_index=5,
                    option_sort_order=0,
                    pricing_payload={},
                ),
                CatalogSelectionAnswer(
                    question_code="is_retina",
                    question_title="Retina",
                    option_code="false",
                    option_title="Нет",
                    question_step_index=6,
                    option_sort_order=0,
                    pricing_payload={},
                ),
                CatalogSelectionAnswer(
                    question_code="damaged",
                    question_title="Все функции работают?",
                    option_code="false",
                    option_title="Все работает",
                    question_step_index=7,
                    option_sort_order=0,
                    pricing_payload={},
                ),
            ),
        )


class StubMacMinPriceApiClient:
    async def fetch_buyout_price(
        self,
        category: SupportedCategory,
        payload: Mapping[str, str],
    ) -> dict[str, int]:
        assert category is SupportedCategory.MAC
        return {"min_price": 10000, "max_price": 22000}

    async def fetch_category_params(
        self,
        category: SupportedCategory,
        payload: Mapping[str, str],
    ) -> dict[str, dict]:
        assert category is SupportedCategory.MAC
        return {"macbookair": {"params": {}}}


async def test_pricing_service_builds_deterministic_quote() -> None:
    service = PricingService(StubCatalogService(), StubDamProdamApiClient())

    quote = await service.quote(
        5,
        "iphone",
        "iphone15",
        {
            "memory": "128",
            "damaged": "false",
            "restored_display": "0",
            "exterier_condition": "best",
        },
    )

    assert quote.amount == 86000
    assert quote.trace[0].amount == 86000
    assert quote.trace[1].amount == 2000


async def test_pricing_service_rejects_mac_range_only_response() -> None:
    service = PricingService(StubMacCatalogService(), StubMacMinPriceApiClient())

    try:
        await service.quote(6, "mac", "macbookair", {})
    except ValueError as exc:
        assert str(exc) == "DamProdam pricing returned no candidates."
    else:
        raise AssertionError("Expected ValueError for Mac range-only pricing response")