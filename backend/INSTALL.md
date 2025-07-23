# 🚀 Установка Telegram Gift Detector - Professional Edition

## 📋 Системные требования

- **Python 3.8+** (рекомендуется Python 3.9+)
- **Linux/macOS/Windows** (тестировано на Ubuntu 20.04+)
- **Активный аккаунт Telegram**
- **Доступ в интернет**

## 🔧 Пошаговая установка

### Шаг 1: Подготовка системы

```bash
# Обновление системы (Ubuntu/Debian)
sudo apt update && sudo apt upgrade -y

# Установка Python и pip (если не установлены)
sudo apt install python3 python3-pip python3-venv -y

# Проверка версии Python
python3 --version  # Должно быть 3.8+
```

### Шаг 2: Создание рабочей директории

```bash
# Создание папки проекта
mkdir -p ~/telegram_gift_detector
cd ~/telegram_gift_detector

# Создание виртуального окружения (рекомендуется)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows

# Обновление pip
pip install --upgrade pip
```

### Шаг 3: Установка зависимостей

```bash
# Установка основных зависимостей
pip install pyrogram>=2.0.106
pip install tgcrypto>=1.2.5

# Или из файла requirements.txt (если скопировали файлы)
pip install -r requirements.txt
```

### Шаг 4: Получение API данных Telegram

1. **Перейдите на https://my.telegram.org/apps**
2. **Войдите в свой аккаунт Telegram**
3. **Создайте новое приложение:**
   - App title: `Gift Detector Pro`
   - Short name: `gift_detector_pro`
   - Platform: `Other`
4. **Скопируйте данные:**
   - `API ID` (число, например: 12345678)
   - `API Hash` (строка, например: "1a2b3c4d5e6f7g8h9i0j")

### Шаг 5: Настройка конфигурации

**Вариант A: Редактирование config.py**

```bash
# Отредактируйте файл config.py
nano config.py

# Найдите и измените строки:
API_ID: int = int(os.getenv('API_ID', 12345678))      # Ваш API ID
API_HASH: str = os.getenv('API_HASH', 'your_hash')   # Ваш API Hash
PHONE_NUMBER: str = os.getenv('PHONE_NUMBER', '+1234567890')  # Ваш номер
```

**Вариант B: Переменные окружения (рекомендуется)**

```bash
# Скопируйте пример файла окружения
cp .env.example .env

# Отредактируйте файл .env
nano .env

# Укажите ваши данные:
API_ID=12345678
API_HASH=your_actual_api_hash_here
PHONE_NUMBER=+1234567890
```

### Шаг 6: Первый запуск и авторизация

```bash
# Запуск детектора
python3 run.py

# При первом запуске потребуется:
# 1. Ввести код подтверждения из Telegram
# 2. Возможно ввести пароль двухфакторной аутентификации
```

**Пример первого запуска:**
```
🎁 TELEGRAM GIFT DETECTOR - PROFESSIONAL EDITION
============================================================
✅ Зависимости установлены
✅ Конфигурация валидна

🚀 Запуск детектора...
Please enter your phone number (international format): +1234567890
Please enter the confirmation code: 12345
✅ Gift Detector запущен! Пользователь: @your_username
🎯 Статус: Ожидание подарков...
```

## ✅ Проверка работоспособности

### Тест 1: Проверка конфигурации

```bash
python3 -c "from config import config; config.print_config()"
```

### Тест 2: Проверка импортов

```bash
python3 -c "
import pyrogram
import tgcrypto
from telegram_gift_detector import TelegramGiftDetector
print('✅ Все модули импортированы успешно')
"
```

### Тест 3: Тестовый запуск

```bash
# Запуск на 30 секунд для теста
timeout 30 python3 run.py
```

## 🔄 Настройка автозапуска (Linux)

### Создание systemd сервиса

```bash
# Создание файла сервиса
sudo nano /etc/systemd/system/gift-detector.service
```

**Содержимое файла сервиса:**
```ini
[Unit]
Description=Telegram Gift Detector Professional
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/telegram_gift_detector
Environment=PATH=/home/your_username/telegram_gift_detector/venv/bin
ExecStart=/home/your_username/telegram_gift_detector/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Активация сервиса:**
```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable gift-detector

# Запуск сервиса
sudo systemctl start gift-detector

# Проверка статуса
sudo systemctl status gift-detector

# Просмотр логов
journalctl -u gift-detector -f
```

## 📊 Мониторинг

### Просмотр логов в реальном времени

```bash
# Основные логи
tail -f gift_detector.log

# Только подарки
tail -f gift_detector.log | grep "Обработан подарок"

# Ошибки
tail -f gift_detector.log | grep "ERROR"
```

### Статистика работы

```bash
# Количество обработанных подарков
grep "Обработан подарок" gift_detector.log | wc -l

# Последние 10 подарков
grep "Обработан подарок" gift_detector.log | tail -10
```

## 🛠 Устранение проблем

### Проблема: "ModuleNotFoundError: No module named 'pyrogram'"

**Решение:**
```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Установите зависимости
pip install pyrogram tgcrypto
```

### Проблема: "API_ID не настроен"

**Решение:**
```bash
# Проверьте файл config.py или .env
cat config.py | grep API_ID
cat .env | grep API_ID

# Убедитесь, что значения не являются примерами
```

### Проблема: "AuthKeyUnregistered"

**Решение:**
```bash
# Удалите файл сессии и авторизуйтесь заново
rm *.session*
python3 run.py
```

### Проблема: Подарки не детектируются

**Решение:**
```bash
# Включите DEBUG логирование
export LOG_LEVEL=DEBUG
python3 run.py

# Проверьте настройки детекции в config.py
```

## 🔐 Безопасность

### Рекомендации по безопасности:

1. **Никогда не делитесь API данными**
2. **Используйте .env файлы для секретов**
3. **Регулярно обновляйте зависимости**
4. **Мониторьте логи на подозрительную активность**
5. **Используйте отдельный сервер для production**

### Обновление зависимостей:

```bash
# Обновление всех пакетов
pip install --upgrade pyrogram tgcrypto

# Проверка устаревших пакетов
pip list --outdated
```

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи** - `tail -f gift_detector.log`
2. **Убедитесь в правильности конфигурации** 
3. **Проверьте интернет-соединение**
4. **Убедитесь, что аккаунт не заблокирован**

---

**🎯 После успешной установки детектор будет автоматически отвечать на все входящие Telegram подарки с детальной информацией!**