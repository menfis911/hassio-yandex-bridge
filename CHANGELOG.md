# Changelog

## 0.3.11 — 2026-09-08

### Исправлено
- Исправлена ошибка Home Assistant `Invalid supported_color_modes`.
- Убрана недопустимая комбинация `ColorMode.BRIGHTNESS + ColorMode.COLOR_TEMP`.
- Для диммируемых ламп без цвета используется `ColorMode.BRIGHTNESS`.
- Для ламп с регулировкой цветовой температуры используется `ColorMode.COLOR_TEMP`, который уже включает поддержку яркости.
- Для RGB-ламп используется `ColorMode.RGB`; при наличии цветовой температуры дополнительно используется `ColorMode.COLOR_TEMP`.
- `color_mode` теперь всегда соответствует одному из значений `supported_color_modes`.
- Исправлено падение `light` entity на этапе регистрации, из-за которого Home Assistant показывал устройство с `0 объектов`.

### Причина релиза
На Home Assistant 2026.x проверка Light API строго отклоняет недопустимые комбинации `supported_color_modes`. Предыдущая версия могла сформировать `{BRIGHTNESS, COLOR_TEMP}`, после чего Home Assistant прекращал добавление сущности. В результате Device Registry существовал, но Entity Registry не содержал привязанного объекта.

## 0.3.10 — 2026-09-08

### Исправлено
- `DataUpdateCoordinator` получает исходный `ConfigEntry` через `config_entry=entry`.
- Исправлена передача контекста Config Entry для Device Registry Home Assistant 2026.8+.
- Action-ошибки больше не переводят coordinator в `UpdateFailed`.
- Пустые action-запросы не отправляются.
- Улучшена диагностика HTTP 403 и требования `iot:control`.
