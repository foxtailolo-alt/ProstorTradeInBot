# Deployment

Проект рассчитан на деплой на общий Ubuntu VPS без Docker по умолчанию.

## Принципы безопасного деплоя

- Не трогаем существующие проекты до предварительного аудита сервера.
- Используем отдельную директорию проекта, отдельный `.venv`, отдельный `systemd` unit.
- Не ставим глобальные Python-зависимости.
- Секреты храним только в серверном `.env` вне git.
- Перед первым запуском проверяем фактическую загрузку CPU, RAM, диска и существующие процессы.

## Рекомендуемая структура на сервере

```text
/opt/prostor-tradein-bot/app
/opt/prostor-tradein-bot/shared/.env
/opt/prostor-tradein-bot/shared/logs/
```

## Базовый порядок деплоя

1. Скопировать проект в `/opt/prostor-tradein-bot/app`.
2. Создать `python3.12 -m venv /opt/prostor-tradein-bot/app/.venv`.
3. Установить зависимости внутри `.venv`.
4. Подготовить `/opt/prostor-tradein-bot/shared/.env`.
5. Выполнить `alembic upgrade head`.
6. Установить systemd unit из `deploy/systemd/prostor-tradein-bot.service`.
7. Запустить сервис только после server audit.

## Установка SSH-ключа на сервер

Локальный deploy key уже сгенерирован. На сервере нужно один раз выполнить:

```bash
install -d -m 700 /root/.ssh && printf '%s\n' 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILReJf5EIF6ZOL8c10y5pwFWadsJtb7ah+hqfNJ2Icy+ prostor-tradein-bot-deploy-nopass' > /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys && chown -R root:root /root/.ssh && chmod go-w /root
```

После этого подключение должно работать командой:

```bash
ssh prostor-tradein-bot
```

Если ключ не принимается, на сервере нужно сразу проверить:

```bash
ls -ld /root /root/.ssh && ls -l /root/.ssh/authorized_keys && sed -n '1,5p' /root/.ssh/authorized_keys && grep -R "^PermitRootLogin\|^PubkeyAuthentication\|^AuthorizedKeysFile" /etc/ssh/sshd_config /etc/ssh/sshd_config.d 2>/dev/null
```

## Обязательный аудит перед запуском

Запустить:

```bash
bash deploy/scripts/server_audit.sh
```

Если свободной памяти мало, сначала нужно понять нагрузку двух существующих проектов, а не запускать третий сервис вслепую.

## Минимальные ориентиры по ресурсам

- Для самого Telegram-бота без heavy parsing в постоянном фоне обычно достаточно 100-200 MB RAM.
- PostgreSQL может занять еще 150-300 MB в зависимости от конфигурации и общей нагрузки сервера.
- На VPS с 1 GB RAM третий проект возможен только после живой проверки текущего потребления памяти существующими сервисами.
- Если оба существующих проекта уже держат RAM близко к пределу, этот сервер под три проекта небезопасен.

## Секреты

- Bot token хранить только в серверном `.env`.
- После передачи токена в чат безопаснее перевыпустить его в BotFather перед production-деплоем.