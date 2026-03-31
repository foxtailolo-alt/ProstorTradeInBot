from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name=__name__)


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        "Бот запускается. Сейчас готовится foundation для trade-in flow по Москве."
    )
