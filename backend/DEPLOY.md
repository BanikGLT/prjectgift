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

# Порт для FastAPI
EXPOSE 8000

# Проверка здоровья контейнера через API
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Команда запуска FastAPI сервера
CMD ["python", "api.py"]

# =============================================================================
# 🚀 ПОЛНАЯ ИНСТРУКЦИЯ ПО ДЕПЛОЮ
# =============================================================================

## 📋 Варианты деплоя

### 1️⃣ Docker (Рекомендуется)
### 2️⃣ VPS с systemd
### 3️⃣ Облачные платформы (Heroku, Railway, DigitalOcean)

# =============================================================================
# 🐳 ДЕПЛОЙ ЧЕРЕЗ DOCKER
# =============================================================================

## Быстрый старт

```bash
# 1. Клонирование и настройка
git clone <your-repo>
cd backend/

# 2. Настройка переменных окружения
cp .env.example .env
nano .env  # Укажите ваши API данные

# 3. Автоматический деплой
chmod +x deploy.sh
./deploy.sh

# 4. Доступ к веб-интерфейсу
# http://your-server:8000
```

## Ручной деплой

```bash
# Сборка образа
docker-compose build

# Запуск контейнера
docker-compose up -d

# Проверка статуса
docker-compose ps
docker-compose logs -f
```

## Управление

```bash
# Остановка
docker-compose down

# Перезапуск
docker-compose restart

# Обновление
git pull
docker-compose build --no-cache
docker-compose up -d

# Очистка
docker-compose down -v --rmi all
```

# =============================================================================
# 🖥️ ДЕПЛОЙ НА VPS
# =============================================================================

## Подготовка сервера (Ubuntu 20.04+)

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install python3 python3-pip python3-venv nginx -y

# Установка Docker (опционально)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER
```

## Деплой приложения

```bash
# Создание директории
sudo mkdir -p /opt/gift-detector
sudo chown $USER:$USER /opt/gift-detector
cd /opt/gift-detector

# Клонирование кода
git clone <your-repo> .
cd backend/

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка конфигурации
cp .env.example .env
nano .env
```

## Создание systemd сервиса

```bash
# Создание файла сервиса
sudo nano /etc/systemd/system/gift-detector.service
```

**Содержимое файла:**
```ini
[Unit]
Description=Telegram Gift Detector FastAPI Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/gift-detector/backend
Environment=PATH=/opt/gift-detector/backend/venv/bin
ExecStart=/opt/gift-detector/backend/venv/bin/python api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Активация сервиса:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable gift-detector
sudo systemctl start gift-detector
sudo systemctl status gift-detector
```

## Настройка Nginx (обратный прокси)

```bash
# Создание конфигурации Nginx
sudo nano /etc/nginx/sites-available/gift-detector
```

**Конфигурация Nginx:**
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Замените на ваш домен

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Статические файлы (если есть)
    location /static/ {
        alias /opt/gift-detector/backend/static/;
    }
}
```

**Активация конфигурации:**
```bash
sudo ln -s /etc/nginx/sites-available/gift-detector /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL сертификат (Let's Encrypt)

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получение сертификата
sudo certbot --nginx -d your-domain.com

# Автообновление
sudo crontab -e
# Добавить: 0 12 * * * /usr/bin/certbot renew --quiet
```

# =============================================================================
# ☁️ ДЕПЛОЙ В ОБЛАКО
# =============================================================================

## Heroku

```bash
# Установка Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Создание приложения
heroku create your-gift-detector

# Настройка переменных окружения
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
heroku config:set PHONE_NUMBER=your_phone

# Деплой
git push heroku main
```

**Procfile для Heroku:**
```
web: python api.py
```

## Railway

```bash
# 1. Подключите GitHub репозиторий к Railway
# 2. Настройте переменные окружения в веб-интерфейсе
# 3. Railway автоматически развернет приложение
```

## DigitalOcean App Platform

```yaml
# app.yaml
name: gift-detector
services:
- name: api
  source_dir: backend
  github:
    repo: your-username/your-repo
    branch: main
  run_command: python api.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: API_ID
    value: your_api_id
  - key: API_HASH
    value: your_api_hash
  - key: PHONE_NUMBER
    value: your_phone
```

# =============================================================================
# 🔧 НАСТРОЙКА ДОМЕНА И SSL
# =============================================================================

## Настройка DNS

```bash
# A-запись для домена
your-domain.com -> IP_ADDRESS

# CNAME для поддомена
api.your-domain.com -> your-domain.com
```

## Настройка файрвола

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Или конкретные порты
sudo ufw allow 8000/tcp  # FastAPI (если без Nginx)
```

# =============================================================================
# 📊 МОНИТОРИНГ И ЛОГИРОВАНИЕ
# =============================================================================

## Просмотр логов

```bash
# Docker
docker-compose logs -f

# Systemd
journalctl -u gift-detector -f

# Файлы логов
tail -f /opt/gift-detector/backend/gift_detector.log
```

## Мониторинг ресурсов

```bash
# Использование CPU/RAM
htop
docker stats

# Дисковое пространство
df -h
du -sh /opt/gift-detector/
```

## Автоматическое резервное копирование

```bash
# Создание скрипта backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /backup/gift-detector_$DATE.tar.gz /opt/gift-detector/

# Добавление в crontab
0 2 * * * /opt/gift-detector/backup.sh
```

# =============================================================================
# 🔐 БЕЗОПАСНОСТЬ
# =============================================================================

## Рекомендации

1. **Используйте HTTPS** - всегда шифруйте трафик
2. **Ограничьте доступ** - используйте файрвол
3. **Регулярно обновляйте** - система и зависимости
4. **Мониторьте логи** - следите за подозрительной активностью
5. **Бэкапы** - регулярно создавайте резервные копии

## Настройка базовой аутентификации

```python
# В api.py добавить
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "your_password")
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.username

# Защита эндпоинтов
@app.get("/api/status")
async def get_status(current_user: str = Depends(get_current_user)):
    # ...
```

# =============================================================================
# 🎯 ФИНАЛЬНАЯ ПРОВЕРКА
# =============================================================================

После деплоя проверьте:

1. ✅ **API доступен**: `curl http://your-domain.com/api/health`
2. ✅ **Веб-интерфейс работает**: откройте `http://your-domain.com`
3. ✅ **Детектор запускается**: через веб-интерфейс или API
4. ✅ **Логи пишутся**: проверьте файлы логов
5. ✅ **SSL работает**: `https://your-domain.com`
6. ✅ **Автозапуск настроен**: перезагрузите сервер

## Полезные команды

```bash
# Проверка статуса API
curl -X GET http://localhost:8000/api/status

# Запуск детектора через API
curl -X POST http://localhost:8000/api/start

# Получение логов
curl -X GET http://localhost:8000/api/logs

# Проверка здоровья
curl -X GET http://localhost:8000/api/health
```

🎉 **Поздравляем! Ваш Telegram Gift Detector успешно развернут!**

Доступ к веб-интерфейсу: `http://your-domain.com`
API документация: `http://your-domain.com/docs`