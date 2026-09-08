# Yandex HA Bridge

Кастомная интеграция для Home Assistant, которая получает устройства Яндекса через официальный API Яндекса и добавляет выбранные устройства непосредственно в Home Assistant.

## Текущая версия

**0.3.5 — исправление совместимости light platform с актуальным Home Assistant**

Интеграция работает через Config Flow: OAuth-токен → получение списка устройств → выбор устройств → создание Config Entry в Home Assistant.

Используется уникальный домен `yandex_ha_bridge`, поэтому интеграция может работать одновременно со сторонней интеграцией `yandex_smart_home`.

## Что исправлено в 0.3.5

- Исправлен импорт `ATTR_BRIGHTNESS`: актуальный Home Assistant предоставляет его из `homeassistant.components.light`.
- Исправлена загрузка платформы `light`, из-за которой Config Entry не запускался.
- Добавлена автоматическая проверка этого критичного Home Assistant API-импорта в GitHub Actions.
- Синхронизированы версии App, custom integration и исходного кода: **0.3.5**.

## Возможности 0.3.x

- OAuth-токен Яндекса.
- Получение списка устройств через официальный API.
- Выбор устройств при установке.
- Повторное изменение списка устройств через Options Flow.
- Регистрация выбранных устройств в Home Assistant.
- Управление устройствами типа `light`.
- Включение и выключение.
- Яркость.
- RGB/HSV.
- Цветовая температура.
- Периодическое получение состояния.
- Device Registry Home Assistant.

## Как это работает

```text
        Яндекс Умный дом
               │
               │ официальный API
               ▼
      Yandex HA Bridge API
               │
               ▼
       Home Assistant
               │
               ▼
        Config Entry
               │
               ▼
       выбранные устройства
```

## Установка

Репозиторий устанавливается через HACS как custom integration.

После установки:

1. Откройте **Настройки → Устройства и службы**.
2. Нажмите **Добавить интеграцию**.
3. Найдите **Yandex HA Bridge**.
4. Введите OAuth-токен Яндекса.
5. Получите список устройств.
6. На первом тесте выберите **одно устройство**.
7. Сохраните Config Entry.
8. Перезапустите Home Assistant, если HACS попросит это сделать.

Не удаляйте существующую Config Entry без необходимости. Для изменения выбранных устройств используйте **Настроить / Options**.

## Важно

`Yandex HA Bridge` — отдельная интеграция с доменом `yandex_ha_bridge`. Она не требует удаления или изменения сторонней интеграции `Yandex Smart Home`.

Веб-панель App предназначена для диагностики и технического обслуживания. Основное создание сущностей выполняется custom integration через Config Flow.

## Поддержка света

Для совместимых устройств используются capabilities Яндекса:

- `devices.capabilities.on_off`
- `devices.capabilities.range` / `brightness`
- `devices.capabilities.color_setting` / `rgb`
- `devices.capabilities.color_setting` / `hsv`
- `devices.capabilities.color_setting` / `temperature_k`

Яркость преобразуется между шкалами Home Assistant `0–255` и Яндекс `0–100`.

## Разработка и релизы

Версия должна быть синхронизирована минимум в следующих местах:

- `custom_components/yandex_ha_bridge/manifest.json`
- `yandex_ha_bridge/config.yaml`
- `yandex_ha_bridge/app/bridge.py`
- `yandex_ha_bridge/CHANGELOG.md`

GitHub Actions выполняет validation, собирает `amd64` и `aarch64`, публикует multi-arch manifest и после успешной сборки создаёт соответствующие tag и GitHub Release.
