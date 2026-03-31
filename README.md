# ProstorTradeInBot

Telegram-бот для оценки trade-in техники по данным DamProdam.

## Зафиксированные ограничения

- Поддерживаются только: iPhone, MacBook/iMac, Samsung, iPad, Apple Watch.
- Бот считает цену только по Москве.
- Выбор города скрыт от пользователя и не участвует в UX.
- Один источник истины: активный snapshot в PostgreSQL.
- Парсинг: HTML/API first, Playwright only if necessary.

## Текущий этап

Foundation проекта плюс первый рабочий importer DamProdam API и draft snapshot refresh.

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
- Создание draft snapshot через sync service для будущего cron/manual refresh.

## Следующие шаги

- Активировать snapshot и добавить политику версионирования/архивации.
- Построить wizard из active snapshot.
- Подключить реальный price request flow и сохранение лидов.
