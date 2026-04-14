# ProstorTradeInBot

Telegram-бот для оценки trade-in техники по данным DamProdam.

## Зафиксированные ограничения

- Поддерживаются только: iPhone, MacBook/iMac, Samsung, iPad, Apple Watch.
- Бот считает цену только по Москве.
- Выбор города скрыт от пользователя и не участвует в UX.
- Один источник истины: активный snapshot в PostgreSQL.
- Парсинг: HTML/API first, Playwright only if necessary.

## Текущий этап

Первый MVP: importer DamProdam API, auto-activated snapshot refresh, snapshot-driven Telegram wizard, live DamProdam pricing и lead capture.

## Быстрый старт

1. Установить Python 3.12.
2. Создать `.env` по примеру `.env.example`.
3. Установить зависимости: `pip install -e .[dev]`.
4. Запустить бота: `prostor-bot`.

## Миграции

- Создать или обновить схему: `alembic upgrade head`.
- Создать новую миграцию после изменения моделей: `alembic revision --autogenerate -m "message"`.

## Деплой

- Инструкции и безопасный shared-VPS baseline: `deploy/README.md`.
- Перед production-запуском обязателен server audit: `deploy/scripts/server_audit.sh`.

## Что уже работает

- Конфиг, запуск и базовый каркас aiogram-приложения.
- PostgreSQL schema для snapshot, вопросов, опций и лидов.
- Импорт 5 категорий из DamProdam API в нормализованный snapshot.
- Refresh через sync service создает новую версию snapshot и автоматически делает ее active.
- Wizard в Telegram строится из active snapshot: категория -> модель -> вопросы -> quote.
- После quote бот собирает контакт и сохраняет lead в PostgreSQL.

## Следующие шаги

- Добавить admin flow и scheduler для контролируемого refresh.
- Усилить UX и branching parity для скрытых шагов DamProdam.
