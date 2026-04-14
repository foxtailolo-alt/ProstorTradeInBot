from src.bot.routers.wizard import _build_contact_request_keyboard, _format_quote_message
from src.pricing.service import PriceQuote, PriceTraceEntry


def test_quote_message_hides_internal_pricing_details() -> None:
    message = _format_quote_message(
        PriceQuote(
            snapshot_version=1,
            category_code="iphone",
            category_title="iPhone",
            device_model_code="iphone15pro",
            device_model_title="iPhone 15 Pro",
            amount=42000,
            trace=(
                PriceTraceEntry(label="Оценка DamProdam", amount=42000),
                PriceTraceEntry(label="Бонус при покупке у партнера", amount=2000),
            ),
        )
    )

    assert message == (
        "Ориентировочная стоимость Вашего устройства iPhone 15 Pro - 42 000 ₽\n\n"
        "Для точной оценки Вашего устройства необходимо провести осмотр в магазине "
        "по адресу ул. Максима Горького 153, график работы с 10:00 до 20:00 каждый день.\n\n"
        "Либо можете оформить заявку и уточнить дополнительные детали у менеджера.\n\n"
        "Как к Вам обращаться?"
    )


def test_contact_keyboard_requests_user_phone() -> None:
    keyboard = _build_contact_request_keyboard()

    assert keyboard.resize_keyboard is True
    assert keyboard.one_time_keyboard is True
    assert keyboard.keyboard[0][0].text == "Передать мой номер"
    assert keyboard.keyboard[0][0].request_contact is True