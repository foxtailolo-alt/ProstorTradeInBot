from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any

from src.catalog.service import CatalogSelection, CatalogService
from src.domain.enums import SupportedCategory
from src.parser.damprodam import DamProdamApiClient


@dataclass(slots=True, frozen=True)
class PriceTraceEntry:
    label: str
    amount: int


@dataclass(slots=True, frozen=True)
class PriceQuote:
    snapshot_version: int
    category_code: str
    category_title: str
    device_model_code: str
    device_model_title: str
    amount: int
    trace: tuple[PriceTraceEntry, ...]


class PricingService:
    def __init__(
        self,
        catalog_service: CatalogService,
        api_client: DamProdamApiClient,
    ) -> None:
        self._catalog_service = catalog_service
        self._api_client = api_client

    async def quote(
        self,
        snapshot_version: int,
        category_code: str,
        device_model_code: str,
        answers: dict[str, str],
    ) -> PriceQuote:
        selection = await self._catalog_service.resolve_selection(
            snapshot_version,
            category_code,
            device_model_code,
            answers,
        )
        candidates = await self._quote_candidates(selection)
        if not candidates:
            raise ValueError("DamProdam pricing returned no candidates.")

        min_amount = min(candidate["amount"] for candidate in candidates)
        max_amount = max(candidate["amount"] for candidate in candidates)
        final_amount = min_amount
        trace = [
            PriceTraceEntry(label="Оценка DamProdam", amount=final_amount),
        ]

        if len(candidates) > 1 or min_amount != max_amount:
            trace.append(
                PriceTraceEntry(
                    label=f"Диапазон сценариев {min_amount}-{max_amount} ₽",
                    amount=max_amount - min_amount,
                )
            )

        bonus_amounts = [candidate["bonus"] for candidate in candidates if candidate["bonus"]]
        if bonus_amounts:
            trace.append(
                PriceTraceEntry(
                    label="Бонус при покупке у партнера",
                    amount=int(mean(bonus_amounts)),
                )
            )

        screen_fines = [candidate["screen_fine"] for candidate in candidates if candidate["screen_fine"]]
        if screen_fines:
            trace.append(
                PriceTraceEntry(
                    label="Штраф за замененный экран",
                    amount=-max(screen_fines),
                )
            )

        return PriceQuote(
            snapshot_version=selection.snapshot_version,
            category_code=selection.category_code,
            category_title=selection.category_title,
            device_model_code=selection.device_model_code,
            device_model_title=selection.device_model_title,
            amount=final_amount,
            trace=tuple(trace),
        )

    async def _quote_candidates(self, selection: CatalogSelection) -> list[dict[str, int]]:
        category = SupportedCategory(selection.category_code)
        base_payload = self._build_buyout_payload(selection)
        candidate_payloads = await self._expand_candidate_payloads(category, base_payload)

        candidates: list[dict[str, int]] = []
        for payload in candidate_payloads:
            try:
                response = await self._api_client.fetch_buyout_price(category, payload)
            except Exception:
                continue

            amount = self._extract_amount(response, category)
            if amount is None:
                continue
            candidates.append(
                {
                    "amount": amount,
                    "bonus": int(response.get("bonus_for_use") or 0),
                    "screen_fine": int(response.get("restored_display_iphone_fine") or 0),
                }
            )

        return candidates

    def _build_buyout_payload(self, selection: CatalogSelection) -> dict[str, Any]:
        answers = {answer.question_code: answer.option_code for answer in selection.answers}
        payload: dict[str, Any]

        if selection.category_code == SupportedCategory.IPHONE.value:
            payload = {
                "models_iphones": selection.device_model_code,
                "memory": answers.get("memory"),
                "equipment_iphone": "zero",
                "restored_display": answers.get("restored_display"),
                "exterier_condition": answers.get("exterier_condition"),
                "damaged": answers.get("damaged"),
            }
            model_series = selection.model_metadata.get("model_series")
            if model_series:
                payload["model_series"] = model_series
            return payload

        if selection.category_code == SupportedCategory.MAC.value:
            return {
                "models_macbooks": selection.device_model_code,
                "year": answers.get("year"),
                "memory": answers.get("memory"),
                "inches": answers.get("inches"),
                "cpu": answers.get("cpu"),
                "touch_bar": answers.get("touch_bar"),
                "is_retina": self._normalize_bool_answer(answers.get("is_retina")),
                "ram": answers.get("ram"),
                "damaged": answers.get("damaged"),
            }

        if selection.category_code == SupportedCategory.SAMSUNG.value:
            payload = {
                "vendor": "samsung",
                "models_android": selection.device_model_code,
                "memory": answers.get("memory"),
                "exterier_condition_android": answers.get("exterier_condition_android"),
            }
            model_series = selection.model_metadata.get("model_series")
            if model_series:
                payload["model_series"] = model_series
            return payload

        if selection.category_code == SupportedCategory.IPAD.value:
            return {
                "models_ipads": selection.device_model_code,
                "memory": answers.get("memory"),
                "cellular": answers.get("cellular"),
                "exterier_condition_ipad": answers.get("exterier_condition_ipad"),
                "equipment_ipad": "zero",
            }

        return {
            "models_watches": selection.device_model_code,
            "size_mm": answers.get("size_mm"),
            "exterier_condition_watches": answers.get("exterier_condition_watches"),
            "equipment_watches": "zero",
        }

    async def _expand_candidate_payloads(
        self,
        category: SupportedCategory,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if category is not SupportedCategory.MAC or payload.get("cpu"):
            return [payload]

        params_payload = {key: value for key, value in payload.items() if key != "cpu" and value is not None}
        params = await self._api_client.fetch_category_params(category, params_payload)
        model_params = params.get(payload["models_macbooks"], {}).get("params", {})
        cpu_values = model_params.get("cpu", {}).get("vals", [])
        cpu_codes = [
            self._extract_option_code(option)
            for option in cpu_values
            if self._extract_option_code(option)
        ]
        if not cpu_codes:
            return [payload]

        return [dict(payload, cpu=cpu_code) for cpu_code in cpu_codes]

    @staticmethod
    def _extract_amount(
        response: dict[str, Any],
        category: SupportedCategory,
    ) -> int | None:
        counted_price = response.get("counted_price")
        if counted_price is not None:
            return int(counted_price)

        if category is SupportedCategory.MAC:
            return None

        min_price = response.get("min_price")
        if min_price is not None:
            return int(min_price)

        max_price = response.get("max_price")
        if max_price is not None:
            return int(max_price)

        raise ValueError("DamProdam response does not contain a price.")

    @staticmethod
    def _normalize_bool_answer(value: str | None) -> str | None:
        if value is None:
            return None
        if value in {"True", "true"}:
            return "true"
        if value in {"False", "false"}:
            return "false"
        return value

    @staticmethod
    def _extract_option_code(option: Any) -> str | None:
        if isinstance(option, dict):
            raw_code = option.get("abbr", option.get("name"))
        else:
            raw_code = option

        if raw_code in (None, ""):
            return None
        if isinstance(raw_code, bool):
            return str(raw_code).lower()
        return str(raw_code)