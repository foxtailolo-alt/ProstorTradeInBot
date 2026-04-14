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
            categories.append(
                await self._build_category_schema(category, payload, sort_order=sort_order)
            )

        return SnapshotSchema(
            version=1,
            source_name="damprodam_api",
            pricing_city=self._pricing_city,
            imported_at=datetime.now(tz=UTC),
            categories=tuple(categories),
        )

    async def _build_category_schema(
        self,
        category: SupportedCategory,
        payload: Any,
        *,
        sort_order: int,
    ) -> CategorySchema:
        records = await self._enrich_records(category, self._normalize_records(payload))
        models = tuple(self._build_model_schema(record, index) for index, record in enumerate(records))
        questions = self._build_questions(category, records)

        return CategorySchema(
            category_code=category,
            title=_CATEGORY_TITLES[category],
            models=models,
            questions=questions,
            sort_order=sort_order,
            is_enabled=True,
        )

    async def _enrich_records(
        self,
        category: SupportedCategory,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if category is not SupportedCategory.MAC:
            return records

        return [await self._enrich_mac_record(record) for record in records]

    async def _enrich_mac_record(self, record: dict[str, Any]) -> dict[str, Any]:
        enriched_record = dict(record)
        params = {
            str(group_code): self._clone_group_payload(group_payload)
            for group_code, group_payload in dict(record.get("params", {})).items()
        }
        years = tuple(params.get("year", {}).get("vals", ()))
        model_code = str(record["device_abbr"])

        for year in years:
            payload = await self._api_client.fetch_category_params(
                SupportedCategory.MAC,
                {"models_macbooks": model_code, "year": str(year)},
            )
            group_payloads = payload.get(model_code, {}).get("params", {})
            for group_code, group_payload in group_payloads.items():
                normalized_group_code = str(group_payload.get("group_abbr") or group_code)
                target_group = params.setdefault(
                    normalized_group_code,
                    self._clone_group_payload(group_payload),
                )
                existing_options = OrderedDict(
                    (
                        normalized["code"],
                        normalized,
                    )
                    for normalized in (
                        self._normalize_option(option)
                        for option in target_group.get("vals", ())
                    )
                )
                for option in group_payload.get("vals", ()):
                    normalized = self._normalize_option(option)
                    existing_options.setdefault(normalized["code"], normalized)
                target_group["vals"] = [self._restore_group_option(option) for option in existing_options.values()]

        enriched_record["params"] = params
        return enriched_record

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

    def _build_questions(
        self,
        category: SupportedCategory,
        records: list[dict[str, Any]],
    ) -> tuple[QuestionSchema, ...]:
        grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()

        for record in records:
            model_code = str(record["device_abbr"])
            params = record.get("params", {})

            for fallback_step, (group_code, group_payload) in enumerate(params.items()):
                normalized_group_code = str(group_payload.get("group_abbr") or group_code)
                bucket = grouped.setdefault(
                    normalized_group_code,
                    {
                        "title": str(group_payload.get("group_name") or normalized_group_code),
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

        ordered_group_items = sorted(
            grouped.items(),
            key=lambda item: self._question_sort_key(category, item[0], item[1]),
        )

        questions: list[QuestionSchema] = []
        for step_index, (group_code, bucket) in enumerate(ordered_group_items, start=1):
            ordered_options = self._order_question_options(group_code, bucket["options"].values())
            options = tuple(
                OptionSchema(
                    code=option["code"],
                    title=option["title"],
                    pricing_payload=option["pricing_payload"],
                    sort_order=index,
                    is_enabled=True,
                )
                for index, option in enumerate(ordered_options)
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

        next_step_index = len(questions) + 1
        for static_question in _STATIC_QUESTIONS.get(category, ()):
            questions.append(
                QuestionSchema(
                    code=static_question["code"],
                    title=static_question["title"],
                    step_index=next_step_index,
                    question_kind="single_select",
                    branching_rules={},
                    options=tuple(
                        OptionSchema(
                            code=option["code"],
                            title=option["title"],
                            pricing_payload={},
                            sort_order=index,
                            is_enabled=True,
                        )
                        for index, option in enumerate(static_question["options"])
                    ),
                    is_required=True,
                )
            )
            next_step_index += 1

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
            raw_code = payload.get("abbr", payload.get("name", ""))
            if isinstance(raw_code, bool):
                code = str(raw_code).lower()
            else:
                code = str(raw_code).strip()
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

    @staticmethod
    def _clone_group_payload(payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {"vals": []}
        cloned = dict(payload)
        cloned["vals"] = list(payload.get("vals", ()))
        return cloned

    @staticmethod
    def _restore_group_option(option: dict[str, Any]) -> dict[str, Any]:
        restored = dict(option["pricing_payload"])
        restored["name"] = option["title"]
        restored["abbr"] = option["code"]
        return restored

    @staticmethod
    def _question_sort_key(
        category: SupportedCategory,
        group_code: str,
        bucket: dict[str, Any],
    ) -> tuple[int, int, str]:
        preferred_order = _QUESTION_ORDER_BY_CATEGORY.get(category, ())
        preferred_index = _QUESTION_ORDER_LOOKUP.get(category, {}).get(group_code)
        if preferred_index is not None:
            return (0, preferred_index, group_code)
        return (1, int(bucket["first_seen_step"]), group_code)

    @staticmethod
    def _order_question_options(
        group_code: str,
        options: Any,
    ) -> tuple[dict[str, Any], ...]:
        option_list = tuple(options)
        codes = [str(option["code"]) for option in option_list]

        if option_list and all(code.lstrip("-").isdigit() for code in codes):
            return tuple(sorted(option_list, key=lambda option: int(str(option["code"]))))

        return option_list


_CATEGORY_TITLES: dict[SupportedCategory, str] = {
    SupportedCategory.IPHONE: "iPhone",
    SupportedCategory.MAC: "MacBook/iMac",
    SupportedCategory.SAMSUNG: "Samsung",
    SupportedCategory.IPAD: "iPad",
    SupportedCategory.APPLE_WATCH: "Apple Watch",
}

_QUESTION_ORDER_BY_CATEGORY: dict[SupportedCategory, tuple[str, ...]] = {
    SupportedCategory.MAC: ("year", "cpu", "inches", "memory", "ram"),
}

_QUESTION_ORDER_LOOKUP: dict[SupportedCategory, dict[str, int]] = {
    category: {code: index for index, code in enumerate(order)}
    for category, order in _QUESTION_ORDER_BY_CATEGORY.items()
}

_STATIC_QUESTIONS: dict[SupportedCategory, tuple[dict[str, Any], ...]] = {
    SupportedCategory.IPHONE: (
        {
            "code": "damaged",
            "title": "Все функции работают?",
            "options": (
                {"code": "false", "title": "Все работает"},
                {"code": "true", "title": "Есть неисправности"},
            ),
        },
        {
            "code": "restored_display",
            "title": "Экран менялся?",
            "options": (
                {"code": "0", "title": "Нет"},
                {"code": "1", "title": "Да"},
            ),
        },
        {
            "code": "exterier_condition",
            "title": "Состояние корпуса и экрана",
            "options": (
                {"code": "best", "title": "Как новый"},
                {"code": "well", "title": "Хорошее"},
                {"code": "normal", "title": "Среднее"},
                {"code": "bad", "title": "Плохое"},
            ),
        },
    ),
    SupportedCategory.MAC: (
        {
            "code": "damaged",
            "title": "Есть аппаратные неисправности?",
            "options": (
                {"code": "false", "title": "Нет, все работает"},
                {"code": "true", "title": "Да, есть"},
            ),
        },
    ),
    SupportedCategory.SAMSUNG: (
        {
            "code": "exterier_condition_android",
            "title": "Состояние корпуса и экрана",
            "options": (
                {"code": "best", "title": "Как новый"},
                {"code": "well", "title": "Хорошее"},
                {"code": "normal", "title": "Среднее"},
            ),
        },
    ),
    SupportedCategory.IPAD: (
        {
            "code": "exterier_condition_ipad",
            "title": "Состояние корпуса и экрана",
            "options": (
                {"code": "best", "title": "Как новый"},
                {"code": "well", "title": "Хорошее"},
                {"code": "bad", "title": "Плохое"},
            ),
        },
    ),
    SupportedCategory.APPLE_WATCH: (
        {
            "code": "exterier_condition_watches",
            "title": "Состояние часов",
            "options": (
                {"code": "best", "title": "Как новые"},
                {"code": "normal", "title": "Хорошее"},
                {"code": "scratch", "title": "Много царапин"},
            ),
        },
    ),
}