from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

from src.domain.enums import SupportedCategory
from src.domain.snapshot_schema import CategorySchema, DeviceModelSchema, OptionSchema, QuestionSchema, SnapshotSchema
from src.parser.contracts import SnapshotImporter
from src.parser.damprodam.api import DamProdamApiClient


class DamProdamSnapshotImporter(SnapshotImporter):
    def __init__(self, api_client: DamProdamApiClient, *, pricing_city: str = "moscow") -> None:
        self._api_client = api_client
        self._pricing_city = pricing_city

    async def import_snapshot(self) -> SnapshotSchema:
        categories: list[CategorySchema] = []

        for sort_order, category in enumerate(SupportedCategory):
            payload = await self._api_client.fetch_category_params(category)
            categories.append(self._build_category_schema(category, payload, sort_order=sort_order))

        return SnapshotSchema(
            version=1,
            source_name="damprodam_api",
            pricing_city=self._pricing_city,
            imported_at=datetime.now(tz=UTC),
            categories=tuple(categories),
        )

    def _build_category_schema(
        self,
        category: SupportedCategory,
        payload: Any,
        *,
        sort_order: int,
    ) -> CategorySchema:
        records = self._normalize_records(payload)
        models = tuple(self._build_model_schema(record, index) for index, record in enumerate(records))
        questions = self._build_questions(records)

        return CategorySchema(
            category_code=category,
            title=_CATEGORY_TITLES[category],
            models=models,
            questions=questions,
            sort_order=sort_order,
            is_enabled=True,
        )

    def _build_model_schema(self, record: dict[str, Any], sort_order: int) -> DeviceModelSchema:
        code = str(record["device_abbr"])
        title = str(record["device_name"])
        metadata = {
            "source_seq_position": record.get("seq_position"),
            "model_series": record.get("model_series"),
            "params": record.get("params", {}),
        }

        return DeviceModelSchema(
            code=code,
            title=title,
            metadata=metadata,
            sort_order=sort_order,
            is_enabled=True,
        )

    def _build_questions(self, records: list[dict[str, Any]]) -> tuple[QuestionSchema, ...]:
        grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()

        for record in records:
            model_code = str(record["device_abbr"])
            params = record.get("params", {})

            for fallback_step, (group_code, group_payload) in enumerate(params.items()):
                bucket = grouped.setdefault(
                    group_code,
                    {
                        "title": str(group_payload.get("group_name") or group_code),
                        "model_option_map": {},
                        "options": OrderedDict(),
                        "first_seen_step": len(grouped) + fallback_step,
                    },
                )
                options = tuple(group_payload.get("vals", ()))
                bucket["model_option_map"][model_code] = []

                for option in options:
                    normalized = self._normalize_option(option)
                    bucket["model_option_map"][model_code].append(normalized["code"])
                    bucket["options"].setdefault(normalized["code"], normalized)

        questions: list[QuestionSchema] = []
        for step_index, (group_code, bucket) in enumerate(grouped.items(), start=1):
            options = tuple(
                OptionSchema(
                    code=option["code"],
                    title=option["title"],
                    pricing_payload=option["pricing_payload"],
                    sort_order=index,
                    is_enabled=True,
                )
                for index, option in enumerate(bucket["options"].values())
            )
            questions.append(
                QuestionSchema(
                    code=group_code,
                    title=bucket["title"],
                    step_index=step_index,
                    question_kind="single_select",
                    branching_rules={
                        "model_option_map": bucket["model_option_map"],
                    },
                    options=options,
                    is_required=True,
                )
            )

        return tuple(questions)

    def _normalize_records(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            records = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            records = [item for item in payload.values() if isinstance(item, dict)]
        else:
            raise TypeError("Unexpected params payload type")

        return sorted(
            records,
            key=lambda item: (
                -(item.get("seq_position") or 0),
                str(item.get("device_name") or item.get("device_abbr") or ""),
            ),
        )

    def _normalize_option(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            code = str(payload.get("abbr", payload.get("name", ""))).strip()
            title = str(payload.get("name", payload.get("abbr", ""))).strip()
            pricing_payload = {
                key: value
                for key, value in payload.items()
                if key not in {"name", "abbr"}
            }
            return {
                "code": code,
                "title": title,
                "pricing_payload": pricing_payload,
            }

        code = str(payload).strip()
        return {
            "code": code,
            "title": code,
            "pricing_payload": {},
        }


_CATEGORY_TITLES: dict[SupportedCategory, str] = {
    SupportedCategory.IPHONE: "iPhone",
    SupportedCategory.MAC: "MacBook/iMac",
    SupportedCategory.SAMSUNG: "Samsung",
    SupportedCategory.IPAD: "iPad",
    SupportedCategory.APPLE_WATCH: "Apple Watch",
}