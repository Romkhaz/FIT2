# Fit-GPX Bot

Telegram‑бот для слияния GPS‑данных из FIT‑файлов Garmin с корректным треком из GPX. Бот принимает у пользователя два файла (FIT + GPX), объединяет их, сохраняя метрики (время, скорость, пульс, каденс, высоту) и выдаёт готовый GPX с правильной геометрией и длительностью.

---

## 📁 Структура проекта

```text
project-root/
├── bot.py                   # Основной код Telegram‑бота
├── merge_fit_gpx.py         # Модуль с функцией merge(fit_path, gpx_path, output_path)
├── requirements.txt         # Список зависимостей
├── Dockerfile               # Описание Docker‑образа
├── docker-compose.yml       # (опционально) для локального тестирования и деплоя
├── .env                     # Переменные окружения (TELEGRAM_TOKEN)
└── README.md                # Документация проекта
```

---

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/your-username/fit-gpx-bot.git
cd fit-gpx-bot
```

### 2. Настройка переменных окружения

Создайте в корне файла `.env`:

```ini
TELEGRAM_TOKEN=ваш_токен_от_BotFather
```

### 3. Запуск без Docker

```bash
# Установка зависимостей
pip install --no-cache-dir -r requirements.txt

# Запуск бота (long-polling)
python bot.py
```

---

## 🐳 Запуск в Docker

### Сборка образа

```bash
docker build -t fit-gpx-bot .
```

### Запуск контейнера

```bash
docker run -d \
  --name fitbot \
  --env-file .env \
  --restart unless-stopped \
  fit-gpx-bot
```

### Просмотр логов

```bash
docker logs -f fitbot
```

---

## ⚙️ Использование

1. В Telegram отправьте боту команду `/start`.
2. Пришлите FIT‑файл тренировки.
3. Пришлите корректный GPX‑трек.
4. Получите объединённый GPX‑файл с правильной траекторией, метриками и длительностью.

---

## 📦 Docker Compose (опционально)

```yaml
version: "3.8"
services:
  fitbot:
    build: .
    restart: unless-stopped
    env_file:
      - .env
```

Запустить:

```bash
docker-compose up -d
```

---

## 📋 Требования

* Python 3.9+
* Docker (для контейнеризации)
* Переменная окружения `TELEGRAM_TOKEN`

### Python‑зависимости

```text
fitparse>=1.1.5
python-telegram-bot>=13.14,<14.0
```

---

## 🔧 Детали реализации

* **merge\_fit\_gpx.py** — разбирает FIT-файл (fitparse), парсит GPX (xml.etree), вычисляет кумулятивные дистанции (формула гаверсинусов), пересчитывает времена пропорционально дистанции, вставляет метрики через Garmin TrackPointExtension.
* **bot.py** — реализует диалог с пользователем через `python-telegram-bot`: сохраняет файлы во временные, вызывает функцию merge, отправляет итог.

---

## 📝 Лицензия

MIT © Ваше Имя
