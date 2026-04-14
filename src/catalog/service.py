from __future__ import annotations

from dataclasses import dataclass

from src.domain.enums import SupportedCategory
from src.parser.damprodam import DamProdamApiClient
from src.storage.models.snapshot import (
    DeviceModel,
    Question,
    QuestionOption,
    Snapshot,
    SnapshotCategory,
)
from src.storage.repositories.snapshot_repository import SnapshotRepository


class CatalogError(RuntimeError):
    pass


class ActiveSnapshotNotFoundError(CatalogError):
    pass


class SnapshotVersionNotFoundError(CatalogError):
    pass


class CategoryNotFoundError(CatalogError):
    pass


class ModelNotFoundError(CatalogError):
    pass


class OptionNotFoundError(CatalogError):
    pass


@dataclass(slots=True, frozen=True)
class CatalogCategory:
    code: str
    title: str


@dataclass(slots=True, frozen=True)
class CatalogModel:
    code: str
    title: str
    sort_order: int


@dataclass(slots=True, frozen=True)
class CatalogOption:
    code: str
    title: str
    sort_order: int
    pricing_payload: dict


@dataclass(slots=True, frozen=True)
class CatalogQuestion:
    code: str
    title: str
    step_index: int
    options: tuple[CatalogOption, ...]


@dataclass(slots=True, frozen=True)
class CatalogSelectionAnswer:
    question_code: str
    question_title: str
    option_code: str
    option_title: str
    question_step_index: int
    option_sort_order: int
    pricing_payload: dict


@dataclass(slots=True, frozen=True)
class CatalogSelection:
    snapshot_version: int
    category_code: str
    category_title: str
    device_model_code: str
    device_model_title: str
    model_sort_order: int
    model_metadata: dict
    answers: tuple[CatalogSelectionAnswer, ...]


@dataclass(slots=True, frozen=True)
class ActiveCatalogOverview:
    snapshot_version: int
    categories: tuple[CatalogCategory, ...]


class CatalogService:
    _MAC_DYNAMIC_QUESTION_CODES = {
        "year",
        "cpu",
        "inches",
        "memory",
        "ram",
        "touch_bar",
        "is_retina",
    }

    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        api_client: DamProdamApiClient | None = None,
    ) -> None:
        self._snapshot_repository = snapshot_repository
        self._api_client = api_client

    async def get_active_overview(self) -> ActiveCatalogOverview:
        snapshot = await self._snapshot_repository.get_active_snapshot()
        if snapshot is None:
            raise ActiveSnapshotNotFoundError("No active snapshot is available.")

        return ActiveCatalogOverview(
            snapshot_version=snapshot.version,
            categories=self._build_categories(snapshot.categories),
        )

    async def list_models(
        self,
        snapshot_version: int,
        category_code: str,
    ) -> tuple[CatalogModel, ...]:
        category = await self._get_category(snapshot_version, category_code)
        models = [
            CatalogModel(code=model.code, title=model.title, sort_order=model.sort_order)
            for model in sorted(category.device_models, key=lambda item: item.sort_order)
            if model.is_enabled
        ]
        return tuple(models)

    async def get_next_question(
        self,
        snapshot_version: int,
        category_code: str,
        model_code: str,
        answers: dict[str, str],
    ) -> CatalogQuestion | None:
        _, question = await self.advance_selection(
            snapshot_version,
            category_code,
            model_code,
            answers,
        )
        return question

    async def advance_selection(
        self,
        snapshot_version: int,
        category_code: str,
        model_code: str,
        answers: dict[str, str],
    ) -> tuple[dict[str, str], CatalogQuestion | None]:
        category = await self._get_category(snapshot_version, category_code)
        model = self._get_model(category, model_code)
        resolved_answers = dict(answers)
        live_params = await self._get_dynamic_params(category.category_code, model, resolved_answers)

        for question in self._iter_enabled_questions(category):
            if question.code in resolved_answers:
                continue

            options = self._build_question_options(question, model_code, live_params)
            options = await self._filter_mac_viable_options(
                category,
                model,
                question,
                resolved_answers,
                options,
            )
            if not options:
                continue

            if len(options) == 1:
                resolved_answers[question.code] = options[0].code
                live_params = await self._get_dynamic_params(
                    category.category_code,
                    model,
                    resolved_answers,
                )
                continue

            return resolved_answers, CatalogQuestion(
                code=question.code,
                title=question.title,
                step_index=question.step_index,
                options=options,
            )

        return resolved_answers, None

    async def resolve_selection(
        self,
        snapshot_version: int,
        category_code: str,
        model_code: str,
        answers: dict[str, str],
    ) -> CatalogSelection:
        snapshot = await self._get_snapshot(snapshot_version)
        category = self._get_category_from_snapshot(snapshot, category_code)
        model = self._get_model(category, model_code)
        resolved_input_answers, _ = await self.advance_selection(
            snapshot_version,
            category_code,
            model_code,
            answers,
        )

        resolved_answers: list[CatalogSelectionAnswer] = []
        for question in self._iter_enabled_questions(category):
            option_code = resolved_input_answers.get(question.code)
            if option_code is None:
                continue

            option = self._get_option(question, model_code, option_code)
            resolved_answers.append(
                CatalogSelectionAnswer(
                    question_code=question.code,
                    question_title=question.title,
                    option_code=option.code,
                    option_title=option.title,
                    question_step_index=question.step_index,
                    option_sort_order=option.sort_order,
                    pricing_payload=dict(option.pricing_payload_json),
                )
            )

        return CatalogSelection(
            snapshot_version=snapshot.version,
            category_code=category.category_code,
            category_title=category.title,
            device_model_code=model.code,
            device_model_title=model.title,
            model_sort_order=model.sort_order,
            model_metadata=dict(model.metadata_json),
            answers=tuple(resolved_answers),
        )

    async def _get_snapshot(self, snapshot_version: int) -> Snapshot:
        snapshot = await self._snapshot_repository.get_snapshot_by_version(snapshot_version)
        if snapshot is None:
            raise SnapshotVersionNotFoundError(
                f"Snapshot version '{snapshot_version}' does not exist."
            )
        return snapshot

    async def _get_category(self, snapshot_version: int, category_code: str) -> SnapshotCategory:
        snapshot = await self._get_snapshot(snapshot_version)
        return self._get_category_from_snapshot(snapshot, category_code)

    def _get_category_from_snapshot(
        self,
        snapshot: Snapshot,
        category_code: str,
    ) -> SnapshotCategory:
        for category in sorted(snapshot.categories, key=lambda item: item.sort_order):
            if category.category_code == category_code and category.is_enabled:
                return category
        raise CategoryNotFoundError(f"Category '{category_code}' is not available.")

    @staticmethod
    def _get_model(category: SnapshotCategory, model_code: str) -> DeviceModel:
        for model in sorted(category.device_models, key=lambda item: item.sort_order):
            if model.code == model_code and model.is_enabled:
                return model
        raise ModelNotFoundError(f"Model '{model_code}' is not available.")

    def _get_option(self, question: Question, model_code: str, option_code: str) -> QuestionOption:
        for option in self._get_available_options(question, model_code):
            if option.code == option_code:
                return option
        raise OptionNotFoundError(
            f"Option '{option_code}' is not available for question '{question.code}'."
        )

    @staticmethod
    def _build_categories(categories: list[SnapshotCategory]) -> tuple[CatalogCategory, ...]:
        return tuple(
            CatalogCategory(code=category.category_code, title=category.title)
            for category in sorted(categories, key=lambda item: item.sort_order)
            if category.is_enabled
        )

    def _build_question_options(
        self,
        question: Question,
        model_code: str,
        live_params: dict[str, dict] | None = None,
    ) -> tuple[CatalogOption, ...]:
        options = [
            CatalogOption(
                code=option.code,
                title=option.title,
                sort_order=option.sort_order,
                pricing_payload=dict(option.pricing_payload_json),
            )
            for option in self._get_available_options(question, model_code)
        ]
        if live_params is None:
            return tuple(options)

        live_group = live_params.get(question.code)
        if live_group is None:
            if question.code in self._MAC_DYNAMIC_QUESTION_CODES:
                return ()
            return tuple(options)

        option_by_code = {option.code: option for option in options}
        ordered_live_options: list[CatalogOption] = []
        for live_option in live_group.get("vals", []):
            live_code = self._extract_live_option_code(live_option)
            if live_code is None:
                continue
            snapshot_option = option_by_code.get(live_code)
            if snapshot_option is None:
                continue
            ordered_live_options.append(snapshot_option)
        return tuple(ordered_live_options)

    @staticmethod
    def _iter_enabled_questions(category: SnapshotCategory) -> tuple[Question, ...]:
        return tuple(sorted(category.questions, key=lambda item: item.step_index))

    @staticmethod
    def _get_available_options(
        question: Question,
        model_code: str,
        live_params: dict[str, dict] | None = None,
    ) -> tuple[QuestionOption, ...]:
        model_option_map = question.branching_rules_json.get("model_option_map", {})
        allowed_codes = model_option_map.get(model_code)
        options = [
            option
            for option in sorted(question.options, key=lambda item: item.sort_order)
            if option.is_enabled
        ]
        if live_params is not None:
            live_group = live_params.get(question.code)
            if live_group is None:
                return ()
            live_codes = {
                CatalogService._extract_live_option_code(option)
                for option in live_group.get("vals", [])
            }
            live_codes.discard(None)
            options = [option for option in options if option.code in live_codes]
        if allowed_codes is None:
            return tuple(options)
        allowed_lookup = set(allowed_codes)
        return tuple(option for option in options if option.code in allowed_lookup)

    async def _get_dynamic_params(
        self,
        category_code: str,
        model: DeviceModel,
        answers: dict[str, str],
    ) -> dict[str, dict] | None:
        if self._api_client is None or category_code != SupportedCategory.MAC.value:
            return None

        payload = {
            "models_macbooks": model.code,
            "year": answers.get("year"),
            "cpu": answers.get("cpu"),
            "inches": answers.get("inches"),
            "memory": answers.get("memory"),
            "ram": answers.get("ram"),
            "touch_bar": answers.get("touch_bar"),
            "is_retina": self._normalize_bool_answer(answers.get("is_retina")),
            "damaged": answers.get("damaged"),
        }
        params = await self._api_client.fetch_category_params(
            SupportedCategory.MAC,
            {key: value for key, value in payload.items() if value is not None},
        )
        return params.get(model.code, {}).get("params", {})

    async def _filter_mac_viable_options(
        self,
        category: SnapshotCategory,
        model: DeviceModel,
        question: Question,
        answers: dict[str, str],
        options: tuple[CatalogOption, ...],
    ) -> tuple[CatalogOption, ...]:
        if (
            self._api_client is None
            or category.category_code != SupportedCategory.MAC.value
            or question.code not in self._MAC_DYNAMIC_QUESTION_CODES
            or len(options) <= 1
        ):
            return options

        viable_options: list[CatalogOption] = []
        for option in options:
            if await self._is_mac_option_viable(category, model, question, answers, option):
                viable_options.append(option)

        return tuple(viable_options) if viable_options else options

    async def _is_mac_option_viable(
        self,
        category: SnapshotCategory,
        model: DeviceModel,
        question: Question,
        answers: dict[str, str],
        option: CatalogOption,
    ) -> bool:
        candidate_answers = dict(answers)
        candidate_answers[question.code] = option.code
        candidate_answers, live_params = await self._auto_fill_mac_dynamic_answers(
            category,
            model,
            candidate_answers,
        )

        later_dynamic_questions = [
            item
            for item in self._iter_enabled_questions(category)
            if item.step_index > question.step_index
            and item.code in self._MAC_DYNAMIC_QUESTION_CODES
            and item.code not in candidate_answers
        ]
        if any(self._build_question_options(item, model.code, live_params) for item in later_dynamic_questions):
            return True

        payload = {
            "models_macbooks": model.code,
            "year": candidate_answers.get("year"),
            "cpu": candidate_answers.get("cpu"),
            "inches": candidate_answers.get("inches"),
            "memory": candidate_answers.get("memory"),
            "ram": candidate_answers.get("ram"),
            "touch_bar": candidate_answers.get("touch_bar"),
            "is_retina": self._normalize_bool_answer(candidate_answers.get("is_retina")),
            "damaged": candidate_answers.get("damaged", "false"),
        }
        try:
            response = await self._api_client.fetch_buyout_price(
                SupportedCategory.MAC,
                {key: value for key, value in payload.items() if value is not None},
            )
        except Exception:
            return False

        return response.get("counted_price") is not None

    async def _auto_fill_mac_dynamic_answers(
        self,
        category: SnapshotCategory,
        model: DeviceModel,
        answers: dict[str, str],
    ) -> tuple[dict[str, str], dict[str, dict] | None]:
        resolved_answers = dict(answers)
        live_params = await self._get_dynamic_params(category.category_code, model, resolved_answers)

        for question in self._iter_enabled_questions(category):
            if question.code in resolved_answers or question.code not in self._MAC_DYNAMIC_QUESTION_CODES:
                continue

            options = self._build_question_options(question, model.code, live_params)
            if len(options) != 1:
                continue

            resolved_answers[question.code] = options[0].code
            live_params = await self._get_dynamic_params(
                category.category_code,
                model,
                resolved_answers,
            )

        return resolved_answers, live_params

    @staticmethod
    def _extract_live_option_code(option: object) -> str | None:
        if isinstance(option, dict):
            raw_code = option.get("abbr", option.get("name"))
        else:
            raw_code = option
        if raw_code in (None, ""):
            return None
        if isinstance(raw_code, bool):
            return str(raw_code).lower()
        return str(raw_code)

    @staticmethod
    def _normalize_bool_answer(value: str | None) -> str | None:
        if value is None:
            return None
        if value in {"True", "true"}:
            return "true"
        if value in {"False", "false"}:
            return "false"
        return value