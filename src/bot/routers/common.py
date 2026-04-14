from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name=__name__)


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(
        "Используйте /start, чтобы выбрать категорию, модель и получить оценку trade-in по Москве."
    )


@router.message()
async def handle_unknown(message: Message) -> None:
    await message.answer("Используйте /start, чтобы начать новый расчет, или /help для подсказки.")
