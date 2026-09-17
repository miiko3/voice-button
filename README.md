# Voice Button

Голосовая диктовка для Windows. Зажмите `Ctrl + Win + Alt`, говорите — текст распознаётся offline (Vosk) и вводится в активное поле (туда, где стоит курсор). Во время записи снизу по центру появляется полупрозрачная капсула с анимацией уровня голоса.

## Установка

Скачайте `VoiceButton.exe` из последнего [Release](https://github.com/miiko3/voice-button/releases) и запустите. Модель распознавания уже встроена — интернет не нужен.

## Использование

1. Запустите `VoiceButton.exe`.
2. Поставьте курсор в поле, куда нужно ввести текст (браузер, редактор, чат).
3. Зажмите и удерживайте `Ctrl + Win + Alt`, говорите.
4. Отпустите — текст распознается и введётся в это поле.

Если микрофон недоступен или распознавание не удалось — капсула покажет ошибку.

## Настройка

Через переменные окружения:

| Переменная | Значение по умолчанию | Описание |
|---|---|---|
| `VOICE_BUTTON_MODEL` | `vosk-model-small-ru-0.22` | Папка модели Vosk (или имя папки в `models/`) |

## Разработка

```powershell
pip install -r requirements.txt -r requirements-dev.txt
# модель для локального запуска/тестов
curl.exe -L -o model.zip https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
Expand-Archive model.zip -DestinationPath .\models
python -m pytest -v
```

## Сборка exe

```powershell
pip install pyinstaller
curl.exe -L -o model.zip https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
Expand-Archive model.zip -DestinationPath .\models
pyinstaller --noconfirm --clean voicebutton.spec
```

Результат в `dist/VoiceButton.exe`. Сборка и публикация Release выполняются автоматически через GitHub Actions при пуше в `main`.