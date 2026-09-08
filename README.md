# Yandex HA Bridge

Кастомная интеграция для Home Assistant, которая получает устройства Яндекса через официальный API и добавляет выбранные устройства непосредственно в Home Assistant.

## Текущая версия

**0.3.10 — исправление привязки entity и обработки action**

Интеграция работает через Config Flow: OAuth-токен → получение списка устройств → выбор устройств → создание Config Entry в Home Assistant.

Каждое выбранное физическое устройство Яндекса регистрируется в Home Assistant как отдельный **Device**, а поддерживаемые сущности привязываются к этому устройству.

В 0.3.10 `DataUpdateCoordinator` теперь явно получает `ConfigEntry`. Это важно для Home Assistant 2026.8+, где связь entity с Device Registry разрешается только для entity с `unique_id`, загруженной через Config Entry. Также action-запросы больше не переводят весь coordinator в состояние `UpdateFailed`.

## Что исправлено в 0.3.10

- `DataUpdateCoordinator` получает исходный `ConfigEntry` через `config_entry=entry`.
- Исправлена потеря связи `light` entity с Device Registry на Home Assistant 2026.8+.
- Ошибка одного action больше не помечает coordinator как неисправный.
- Пустой список action не отправляется в Yandex API.
- Для HTTP 403 при `POST /v1.0/devices/actions` сохраняется понятная диагностика требования `iot:control`.
- Синхронизированы версии `manifest.json`, `const.py`, App и API User-Agent.

## Важное про HTTP 403

Официальный Yandex Smart Home API разделяет права чтения и управления: `GET /v1.0/user/info` и `GET /v1.0/devices/{device_id}` используют `iot:view`, а `POST /v1.0/devices/actions` использует `iot:control`.

Поэтому токен может успешно показывать устройство, но получать `HTTP 403` при управлении. Это не исправляется кодом интеграции: нужен OAuth-токен с правами `iot:view` и `iot:control`.

Интеграция не выполняет скрытый тестовый action при запуске, чтобы проверять право управления: такой запрос реально меняет состояние устройства.

## Возможности

- OAuth-токен Яндекса.
- Получение списка устройств через официальный API.
- Выбор устройств при установке.
- Изменение списка устройств через Options Flow.
- Регистрация каждого выбранного физического устройства отдельно в Device Registry Home Assistant.
- Управление совместимыми `light`.
- Включение и выключение.
- Яркость.
- RGB/HSV.
- Цветовая температура.
- Периодическое получение состояния.

## Установка

Репозиторий устанавливается через HACS как custom integration.

После установки:

1. Откройте **Настройки → Устройства и службы**.
2. Нажмите **Добавить интеграцию**.
3. Найдите **Yandex HA Bridge**.
4. Введите OAuth-токен Яндекса с правами **`iot:view` и `iot:control`**.
5. Получите список устройств.
6. На первом тесте выберите **одно устройство**.
7. Сохраните Config Entry.
8. Выбранная лампа должна появиться как отдельное устройство, внутри которого находится её `light` entity.

Для изменения выбранных устройств используйте **Настроить / Options**.

## Тестирование после обновления

После установки новой версии рекомендуется удалить старое тестовое устройство и Config Entry, затем добавить интеграцию заново. Это исключает старые записи Entity Registry / Device Registry.

Для лампы ожидается:

- отдельное устройство с именем лампы;
- серийный номер / Yandex device ID;
- раздел **Сущности**, где находится `light.*`;
- в разделе **Управление** должна отображаться световая сущность;
- включение/выключение и остальные доступные возможности должны выполнять action через Yandex API.

## Поддержка света

Используются capabilities Яндекса:

- `devices.capabilities.on_off`
- `devices.capabilities.range` / `brightness`
- `devices.capabilities.color_setting` / `rgb`
- `devices.capabilities.color_setting` / `hsv`
- `devices.capabilities.color_setting` / `temperature_k`

Яркость преобразуется между шкалами Home Assistant `0–255` и Яндекс `0–100`.

## Важно

`Yandex HA Bridge` — отдельная интеграция с доменом `yandex_ha_bridge`. Она не требует удаления или изменения сторонней интеграции `Yandex Smart Home`.

Веб-панель App предназначена только для диагностики и технического обслуживания. Основное создание устройств и сущностей выполняется custom integration через Config Flow.

## Версии

### 0.3.10
- Исправлена передача `ConfigEntry` в `DataUpdateCoordinator`.
- Исправлена привязка entity к Device Registry в Home Assistant 2026.8+.
- Action-ошибки больше не переводят coordinator в `UpdateFailed`.
- Пустые action-запросы не отправляются.
- Улучшена диагностика HTTP 403.

### 0.3.9
- Исправлена привязка `light` entity к устройству.
- Убрана ручная регистрация Device Registry из `__init__.py`.
- `YandexLight` использует `_attr_device_info`.

### 0.3.8
- Исправлен Device Registry.
- Каждая лампа регистрируется как отдельное устройство.
- Обновлены описания интеграции и Config Flow.

### 0.3.7
- Исправлено использование Light API Home Assistant.
- Усилена проверка capabilities перед командами.
- Исправлено создание световых сущностей только для устройств типа `light`.
- Усилены CI-проверки.

### 0.3.6
- Улучшена диагностика `HTTP 403`.
- В API-ошибки добавляются HTTP status, текст ответа и `request_id`.
- Документировано требование `iot:control`.
- Добавлен `User-Agent`.

### 0.3.5
- Исправлен импорт `ATTR_BRIGHTNESS` из `homeassistant.components.light`.
- Исправлена загрузка платформы `light`.
- Добавлена CI-проверка критичного импорта.

### 0.3.4
- Исправлен запуск `DataUpdateCoordinator`.
- Синхронизированы версии App и custom integration.
- Обновлены CI и документация.

### 0.3.3
- Исправлена структура переводов custom integration.
- Добавлены `translations/en.json` и `translations/ru.json`.
- Удалён устаревший `strings.json`.

### 0.3.2
- Синхронизированы версии App, custom integration и исходного кода.
- Удалена устаревшая integration из `custom_components/yandex`.

### 0.3.1
- Интеграция переименована в **Yandex HA Bridge**.
- Используется домен `yandex_ha_bridge`.
- Добавлены Config Flow и Options Flow.
- Добавлена поддержка света, яркости, RGB/HSV и цветовой температуры.

### 0.3.0
- Добавлена стандартная Home Assistant custom integration.
- Config Flow: токен → устройства → выбор.
- Config Entry и Options Flow.
- Добавлена сущность `light`.

### 0.2.x
- Базовое управление и веб-интерфейс выбора устройств.

### 0.1.x
- Авторизация.
- Обнаружение устройств.
- Чтение состояния.

## Разработка и релизы

Версия должна совпадать в `custom_components/yandex_ha_bridge/manifest.json`, `custom_components/yandex_ha_bridge/const.py`, `yandex_ha_bridge/config.yaml`, `custom_components/yandex_ha_bridge/api.py` и `yandex_ha_bridge/app/bridge.py`.

GitHub Actions автоматически проверяет структуру интеграции, версии, Light API imports, Device Registry requirements, собирает `amd64` и `aarch64`, публикует multi-arch manifest и после успешной сборки создаёт tag и GitHub Release.
