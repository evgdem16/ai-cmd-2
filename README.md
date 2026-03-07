# 💬 LM Chat

**LM Chat** — многофункциональный консольный чат-клиент для [LM Studio](https://lmstudio.ai/) с поддержкой потокового вывода, управления диалогами, системных промтов, RAG-контекста, экспорта и подсветки синтаксиса.

---

## ✨ Возможности

| Категория | Функции |
|-----------|---------|
| **Интерфейс** | Потоковый вывод токенов в реальном времени, Markdown + подсветка синтаксиса кода, перемещение курсора (← →), история ввода (↑ ↓) |
| **Диалоги** | Создание, переключение, удаление, просмотр списка, поиск по истории, автосохранение |
| **Контекст** | Настраиваемый лимит сообщений в контексте, хранение в отдельных JSON-файлах |
| **Системные промты** | Создание, редактирование, применение к диалогу, хранение в JSON |
| **RAG** | Загрузка файлов и директорий в контекст, сохранение блоков кода из диалога |
| **Экспорт** | HTML, PDF, DOCX |
| **Статистика** | Токены, время ответа, общая статистика диалога |
| **Логирование** | Полные логи в файл |

---

## 🛠 Установка

### Требования
- Python 3.11+
- [LM Studio](https://lmstudio.ai/) с запущенным локальным сервером

### Шаги

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/youruser/lm-chat.git
cd lm-chat

# 2. Создайте виртуальное окружение (рекомендуется)
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Запустите LM Studio и включите локальный сервер
#    (вкладка "Local Server" → Start Server)

# 5. Запустите чат
python main.py
```

---

## ⚙️ Конфигурация (`config.json`)

```json
{
  "lm_studio": {
    "base_url": "http://localhost:1234",   // URL LM Studio сервера
    "api_key": "lm-studio",               // Любая строка (LM Studio её игнорирует)
    "model": "local-model",               // Идентификатор модели (из LM Studio)
    "max_tokens": 2048,                    // Максимум токенов в ответе
    "temperature": 0.7,                    // Температура (0.0–2.0)
    "stream": true                         // Потоковый вывод
  },
  "dialogs": {
    "directory": "dialogs",               // Папка для хранения диалогов
    "default_name": "dialog",             // Имя по умолчанию для нового диалога
    "context_limit": -1,                  // -1=весь контекст, 0=без контекста, N=последние N
    "display_last_n": 10                  // Сколько сообщений показывать при переключении
  },
  "system_prompts_file": "system_prompts.json",  // Файл системных промтов
  "exports_directory": "exports",                 // Папка для экспортов
  "logs": {
    "file": "logs/app.log",              // Файл логов
    "level": "INFO"                       // Уровень логирования (DEBUG/INFO/WARNING/ERROR)
  }
}
```

### Параметр `context_limit`

| Значение | Поведение |
|----------|-----------|
| `-1` | Передаётся **весь** контекст диалога |
| `0` | Контекст **не передаётся** (только текущее сообщение) |
| `N > 0` | Передаются последние **N** сообщений |

---

## 🗂 Структура проекта

```
lm_chat/
├── main.py                      # Точка входа
├── config.json                  # Конфигурация
├── requirements.txt
├── system_prompts.json          # Системные промты (создаётся автоматически)
├── modules/
│   ├── api_client.py            # Клиент LM Studio API
│   ├── config_manager.py        # Загрузка конфига
│   ├── dialog_manager.py        # Управление диалогами
│   ├── system_prompts_manager.py# Управление системными промтами
│   ├── rag_manager.py           # RAG: загрузка файлов в контекст
│   ├── export_manager.py        # Экспорт HTML/PDF/DOCX
│   ├── console_ui.py            # Rich-интерфейс, подсветка, стриминг
│   ├── command_handler.py       # Обработчик /команд
│   └── logger_setup.py          # Настройка логирования
├── dialogs/                     # Диалоги (создаётся автоматически)
│   └── my_dialog.json
├── exports/                     # Экспортированные файлы
└── logs/
    └── app.log
```

### Структура файла диалога (`dialogs/my_dialog.json`)

```json
{
  "name": "my_dialog",
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:30:00",
  "system_prompt": "You are a helpful assistant.",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "Привет! Как дела?",
      "timestamp": "2024-01-15T10:00:00",
      "_debug": { "tokens": null, "response_time": null }
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "Привет! Всё хорошо, готов помочь.",
      "timestamp": "2024-01-15T10:00:05",
      "_debug": { "tokens": 42, "response_time": 1.23 }
    }
  ],
  "_stats": {
    "total_tokens": 42,
    "total_messages": 2,
    "total_response_time": 1.23
  }
}
```

> **Примечание:** Поля `_debug` и `_stats` предназначены только для дебага и **не передаются** в LLM.

---

## 📋 Команды

### Диалоги

```
/new [name]          Создать новый диалог (имя необязательно)
/open <name>         Открыть диалог
/switch <name>       Переключиться на диалог (сохраняет текущий)
/list                Список всех диалогов
/delete <name>       Удалить диалог
/history [n]         Показать последние N сообщений
/search <query>      Поиск по всем диалогам
/stats               Статистика текущего диалога
```

### Системные промты

```
/sp list             Список системных промтов
/sp new <name>       Создать системный промт
/sp edit <name>      Редактировать промт
/sp delete <name>    Удалить промт
/sp show <name>      Показать содержимое
/sp apply <name>     Применить к текущему диалогу
/sp clear            Убрать системный промт из диалога
/sp current          Показать активный системный промт
```

### RAG (контекст из файлов)

```
/rag load <path>     Загрузить файл или всё содержимое папки
/rag list            Список загруженных файлов
/rag clear           Очистить загруженные файлы
/rag remove <path>   Удалить конкретный файл из контекста
/rag save <dir>      Сохранить блоки кода из диалога в папку
```

### Экспорт

```
/export html [path]  Экспорт в HTML
/export pdf [path]   Экспорт в PDF
/export doc [path]   Экспорт в DOCX
```

### Прочее

```
/clear               Очистить экран
/help                Справка по командам
/exit  /quit         Выход (сохраняет диалог)
```

---

## 💡 Примеры использования

### Базовое общение
```
[dialog] ❯ Объясни концепцию Docker простыми словами
[dialog] ❯ Напиши пример Dockerfile для Python приложения
```

### Работа с диалогами
```
[dialog] ❯ /new python-помощник
[python-помощник] ❯ /sp apply python-expert
[python-помощник] ❯ Напиши функцию для парсинга CSV
[python-помощник] ❯ /switch другой-проект
[другой-проект] ❯ /list
```

### RAG: загрузка кода в контекст
```
[dialog] ❯ /rag load ./src/
[dialog +5f] ❯ Что делает функция calculate_metrics в моём коде?
[dialog +5f] ❯ /rag save ./refactored/
```

### Системные промты
```
[dialog] ❯ /sp new python-expert
(Enter text. Finish with a single '.' on a line)
You are an expert Python developer. Always write clean, typed code with docstrings.
.
[dialog] ❯ /sp apply python-expert
[dialog] ❯ /sp current
```

### Поиск по истории
```
[dialog] ❯ /search Docker
[dialog] ❯ /search async await
```

### Экспорт диалога
```
[dialog] ❯ /export html
[dialog] ❯ /export pdf ./reports/session.pdf
[dialog] ❯ /export doc
```

---

## 🎨 Клавиатурные сокращения

| Клавиша | Действие |
|---------|----------|
| `↑` / `↓` | Навигация по истории ввода |
| `←` / `→` | Перемещение курсора |
| `Home` / `End` | Начало / конец строки |
| `Ctrl+C` | Прервать текущий ввод |
| `Ctrl+D` | Выход |

---

## 📦 Зависимости

| Библиотека | Назначение |
|------------|------------|
| `prompt_toolkit` | Расширенный ввод в консоли |
| `rich` | Красивый вывод, Markdown, подсветка синтаксиса |
| `openai` | OpenAI-совместимый API клиент (для LM Studio) |
| `pygments` | Подсветка синтаксиса (используется rich) |
| `python-docx` | Экспорт в DOCX |
| `fpdf2` | Экспорт в PDF |
| `markdown` | Конвертация Markdown → HTML |

### Опциональные
- `pypdf` — для чтения PDF-файлов через RAG (`pip install pypdf`)

---

## 🔧 Настройка LM Studio

1. Откройте LM Studio
2. Загрузите модель (вкладка "Models")
3. Перейдите на вкладку **"Local Server"**
4. Нажмите **"Start Server"** (по умолчанию на порту 1234)
5. Скопируйте идентификатор загруженной модели и укажите его в `config.json` → `"model"`

---

## 🐛 Отладка

Логи сохраняются в файл, указанный в `config.json` → `logs.file` (по умолчанию `logs/app.log`).

```bash
tail -f logs/app.log   # Linux / macOS
```

Поле `_debug` в каждом сообщении диалога содержит количество токенов и время ответа.

---

## 📄 Лицензия

MIT License. Используйте свободно.
