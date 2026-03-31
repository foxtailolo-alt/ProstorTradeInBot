# Data Contract v0

Дата фиксации: 2026-03-31
Статус: Draft

## Цель

Описать единый внутренний контракт, от которого будут зависеть parser, pricing engine, wizard и lead storage.

## Инварианты

- Один источник истины: active snapshot в PostgreSQL.
- Все пользовательские шаги строятся из snapshot.
- Все расчеты строятся из snapshot.
- Город не является пользовательским полем.
- В pricing context всегда используется `moscow`.
- Snapshot append-only по версиям: новый импорт создает новую версию, активируется только после проверки.

## Сущности

### Snapshot
- `id`
- `version`
- `source_name`
- `pricing_city`
- `status`: `draft | active | archived`
- `imported_at`
- `created_at`
- `updated_at`

### SnapshotCategory
- `id`
- `snapshot_id`
- `category_code`
- `title`
- `is_enabled`
- `sort_order`

### DeviceModel
- `id`
- `category_id`
- `code`
- `title`
- `metadata_json`
- `sort_order`
- `is_enabled`

### Question
- `id`
- `category_id`
- `code`
- `title`
- `step_index`
- `question_kind`
- `branching_rules_json`
- `is_required`

### QuestionOption
- `id`
- `question_id`
- `code`
- `title`
- `pricing_payload_json`
- `sort_order`
- `is_enabled`

### Lead
- `id`
- `snapshot_id`
- `category_code`
- `device_model_code`
- `contact_name`
- `contact_value`
- `comment`
- `quoted_price`
- `answers_json`
- `created_at`
- `updated_at`

## Контракт parser -> snapshot

Parser обязан:
- сохранять только поддерживаемые категории;
- записывать `pricing_city = moscow`;
- нормализовать тексты и коды опций;
- сохранять ветвления в `branching_rules_json`;
- сохранять ценовые артефакты в `pricing_payload_json`;
- не перезаписывать active snapshot напрямую;
- создавать новую snapshot version на каждый import run.

## Контракт wizard -> snapshot

Wizard обязан:
- читать только active snapshot;
- хранить в user state только `snapshot_version`, `category_code`, `device_model_code`, выбранные `option_code`;
- строить кнопки и тексты из snapshot;
- не содержать захардкоженных вопросников по категориям.

## Контракт pricing -> snapshot

Pricing engine обязан:
- принимать `snapshot_version`, `category_code`, `device_model_code`, выбранные ответы;
- работать только в московском контексте;
- поддерживать минимум 3 режима: direct formula, table lookup, rule adjustments;
- возвращать итоговую цену и объяснимый trace для диагностики.

## Контракт bot -> lead storage

После расчета бот сохраняет:
- snapshot version;
- category code;
- device model code;
- answers snapshot;
- quoted price;
- контактные данные;
- optional comment.

## Открытые вопросы Sprint 0

- Где точно находятся скрытые вопросы для iPhone, MacBook/iMac и Samsung.
- Есть ли hidden API для финальной цены.
- Какие поля реально влияют на цену, а какие только на lead qualification.
- В каком виде сайт хранит price modifiers: формула, lookup tables, server response или комбинированная логика.
