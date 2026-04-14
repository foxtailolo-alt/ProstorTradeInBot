from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from src.bot.wizard_state import TradeInWizardStates
from src.catalog.service import (
    ActiveSnapshotNotFoundError,
    CatalogError,
    CatalogQuestion,
    CatalogService,
)
from src.lead.service import LeadCaptureRequest, LeadService
from src.pricing.service import PriceQuote, PricingService


def build_router(
    catalog_service: CatalogService,
    pricing_service: PricingService,
    lead_service: LeadService,
) -> Router:
    router = Router(name=__name__)

    @router.message(CommandStart())
    async def handle_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        try:
            overview = await catalog_service.get_active_overview()
        except ActiveSnapshotNotFoundError:
            await message.answer(
                "Сейчас нет активного snapshot для расчета. Попробуйте чуть позже."
            )
            return

        await state.set_state(TradeInWizardStates.selecting_category)
        await state.update_data(snapshot_version=overview.snapshot_version, answers={})
        await message.answer(
            "Выберите категорию устройства.",
            reply_markup=_build_single_column_keyboard(
                [(category.title, f"category:{category.code}") for category in overview.categories]
            ),
        )

    @router.callback_query(
        StateFilter(TradeInWizardStates.selecting_category),
        F.data.startswith("category:"),
    )
    async def handle_category_selection(callback: CallbackQuery, state: FSMContext) -> None:
        snapshot_version = await _get_snapshot_version(state)
        if snapshot_version is None or callback.message is None:
            await _reset_flow(callback, state)
            return

        await _safe_callback_answer(callback)

        category_code = callback.data.split(":", 1)[1]
        try:
            models = await catalog_service.list_models(snapshot_version, category_code)
        except CatalogError:
            await _reset_flow(callback, state)
            return

        if not models:
            await callback.answer("Для этой категории пока нет доступных моделей.", show_alert=True)
            return

        await state.set_state(TradeInWizardStates.selecting_model)
        await state.update_data(
            category_code=category_code,
            device_model_code=None,
            answers={},
            current_question_code=None,
            quoted_price=None,
            contact_name=None,
            contact_value=None,
        )
        await _safe_edit_text(
            callback.message,
            "Выберите модель устройства.",
            reply_markup=_build_single_column_keyboard(
                [(model.title, f"model:{model.code}") for model in models]
            ),
        )

    @router.callback_query(
        StateFilter(TradeInWizardStates.selecting_model),
        F.data.startswith("model:"),
    )
    async def handle_model_selection(callback: CallbackQuery, state: FSMContext) -> None:
        data = await state.get_data()
        snapshot_version = data.get("snapshot_version")
        category_code = data.get("category_code")
        if snapshot_version is None or category_code is None or callback.message is None:
            await _reset_flow(callback, state)
            return

        await _safe_callback_answer(callback)

        model_code = callback.data.split(":", 1)[1]
        await state.update_data(device_model_code=model_code, answers={})
        await _show_next_step(callback.message, state, catalog_service, pricing_service)

    @router.callback_query(
        StateFilter(TradeInWizardStates.answering_question),
        F.data.startswith("answer:"),
    )
    async def handle_question_answer(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.message is None:
            await _reset_flow(callback, state)
            return

        await _safe_callback_answer(callback)

        parts = callback.data.split(":", 2)
        if len(parts) != 3:
            await _safe_callback_answer(callback, "Некорректный ответ.", show_alert=True)
            return

        _, question_code, option_code = parts
        data = await state.get_data()
        current_question_code = data.get("current_question_code")
        if current_question_code != question_code:
            await _safe_callback_answer(
                callback,
                "Этот шаг уже устарел. Продолжайте по актуальному сценарию.",
                show_alert=True,
            )
            return

        answers = dict(data.get("answers", {}))
        answers[question_code] = option_code
        await state.update_data(answers=answers)
        await _show_next_step(callback.message, state, catalog_service, pricing_service)

    @router.message(StateFilter(TradeInWizardStates.waiting_contact_name))
    async def handle_contact_name(message: Message, state: FSMContext) -> None:
        contact_name = (message.text or "").strip()
        if not contact_name:
            await message.answer("Укажите имя или удобное обращение.")
            return

        await state.update_data(contact_name=contact_name)
        await state.set_state(TradeInWizardStates.waiting_contact_value)
        await message.answer(
            "Оставьте телефон или Telegram для связи."
            " Можно нажать кнопку ниже и передать свой номер автоматически.",
            reply_markup=_build_contact_request_keyboard(),
        )

    @router.message(StateFilter(TradeInWizardStates.waiting_contact_value))
    async def handle_contact_value(message: Message, state: FSMContext) -> None:
        if message.contact is not None:
            contact_value = message.contact.phone_number.strip()
        else:
            contact_value = (message.text or "").strip()

        if not contact_value:
            await message.answer(
                "Нужен контакт, чтобы связаться по вашей оценке.",
                reply_markup=_build_contact_request_keyboard(),
            )
            return

        await state.update_data(contact_value=contact_value)
        await state.set_state(TradeInWizardStates.waiting_comment)
        await message.answer(
            "Если хотите, добавьте комментарий к заявке. Если нет, отправьте -",
            reply_markup=ReplyKeyboardRemove(),
        )

    @router.message(StateFilter(TradeInWizardStates.waiting_comment))
    async def handle_comment(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        snapshot_version = data.get("snapshot_version")
        category_code = data.get("category_code")
        model_code = data.get("device_model_code")
        quoted_price = data.get("quoted_price")
        contact_name = data.get("contact_name")
        contact_value = data.get("contact_value")
        answers = dict(data.get("answers", {}))

        if None in {
            snapshot_version,
            category_code,
            model_code,
            quoted_price,
            contact_name,
            contact_value,
        }:
            await state.clear()
            await message.answer("Сценарий прервался. Используйте /start, чтобы начать заново.")
            return

        comment_raw = (message.text or "").strip()
        comment = None if comment_raw in {"", "-", "нет", "пропустить"} else comment_raw

        try:
            await lead_service.capture_lead(
                LeadCaptureRequest(
                    snapshot_version=int(snapshot_version),
                    category_code=str(category_code),
                    device_model_code=str(model_code),
                    quoted_price=int(quoted_price),
                    answers=answers,
                    contact_name=str(contact_name),
                    contact_value=str(contact_value),
                    comment=comment,
                )
            )
        except ValueError:
            await state.clear()
            await message.answer(
                "Не удалось сохранить заявку. Используйте /start и повторите расчет."
            )
            return

        await state.clear()
        await message.answer(
            "Заявка сохранена. Менеджер свяжется с вами по указанному контакту "
            "для подтверждения оценки."
        )

    return router


async def _show_next_step(
    target_message: Message,
    state: FSMContext,
    catalog_service: CatalogService,
    pricing_service: PricingService,
) -> None:
    data = await state.get_data()
    snapshot_version = data.get("snapshot_version")
    category_code = data.get("category_code")
    model_code = data.get("device_model_code")
    answers = dict(data.get("answers", {}))

    if None in {snapshot_version, category_code, model_code}:
        await state.clear()
        await target_message.answer("Сценарий прервался. Используйте /start, чтобы начать заново.")
        return

    try:
        answers, question = await catalog_service.advance_selection(
            int(snapshot_version),
            str(category_code),
            str(model_code),
            answers,
        )
        await state.update_data(answers=answers)
    except CatalogError:
        await state.clear()
        await target_message.answer(
            "Не удалось продолжить расчет. Используйте /start, чтобы начать заново."
        )
        return

    if question is None:
        try:
            quote = await pricing_service.quote(
                int(snapshot_version),
                str(category_code),
                str(model_code),
                answers,
            )
        except ValueError:
            await state.clear()
            await _safe_edit_text(
                target_message,
                "Не удалось корректно рассчитать стоимость для этой конфигурации. "
                "Используйте /start и попробуйте выбрать другой вариант.",
            )
            return
        await state.set_state(TradeInWizardStates.waiting_contact_name)
        await state.update_data(current_question_code=None, quoted_price=quote.amount)
        await _safe_edit_text(target_message, _format_quote_message(quote), reply_markup=None)
        return

    await state.set_state(TradeInWizardStates.answering_question)
    await state.update_data(current_question_code=question.code)
    await _safe_edit_text(
        target_message,
        _format_question_message(question),
        reply_markup=_build_single_column_keyboard(
            [(option.title, f"answer:{question.code}:{option.code}") for option in question.options]
        ),
    )


async def _reset_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _safe_callback_answer(
        callback,
        "Сценарий прервался. Нажмите /start и начните заново.",
        show_alert=True,
    )


async def _get_snapshot_version(state: FSMContext) -> int | None:
    data = await state.get_data()
    value = data.get("snapshot_version")
    return int(value) if value is not None else None


def _format_question_message(question: CatalogQuestion) -> str:
    return f"Шаг {question.step_index}. {question.title}"


def _format_quote_message(quote: PriceQuote) -> str:
    amount_text = f"{quote.amount:,}".replace(",", " ")
    return (
        "Ориентировочная стоимость Вашего устройства "
        f"{quote.device_model_title} - {amount_text} ₽\n\n"
        "Для точной оценки Вашего устройства необходимо провести осмотр в магазине "
        "по адресу ул. Максима Горького 153, график работы с 10:00 до 20:00 каждый день.\n\n"
        "Либо можете оформить заявку и уточнить дополнительные детали у менеджера.\n\n"
        "Как к Вам обращаться?"
    )


def _build_single_column_keyboard(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=callback_data)]
            for text, callback_data in items
        ]
    )


def _build_contact_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Передать мой номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Телефон или Telegram для связи",
    )


async def _safe_callback_answer(
    callback: CallbackQuery,
    text: str | None = None,
    show_alert: bool = False,
) -> None:
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except TelegramBadRequest as exc:
        if "query is too old" not in str(exc).lower() and "query id is invalid" not in str(exc).lower():
            raise


async def _safe_edit_text(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise