# Telegram Gift Detector - Production Dockerfile
FROM python:3.11-slim

# Метаданные
LABEL maintainer="your-email@example.com"
LABEL description="Telegram Gift Detector Professional Edition with FastAPI"
LABEL version="1.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для безопасности
RUN useradd --create-home --shell /bin/bash giftdetector

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Установка прав доступа
RUN chown -R giftdetector:giftdetector /app
USER giftdetector

# Создание директории для логов
RUN mkdir -p /app/logs

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Порт для FastAPI
EXPOSE 8000

# Проверка здоровья контейнера через API
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Команда запуска FastAPI сервера
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]