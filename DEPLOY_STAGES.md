# 🚀 Поэтапный деплой Telegram Gift Detector

## 🎯 Стратегия: Умный деплой в 2 этапа

### Этап 1: Базовый деплой (FastAPI + интерфейс)
### Этап 2: Добавление Telegram функциональности

---

## 📋 ЭТАП 1: Базовый деплой

### ✅ Что деплоим сначала:
- FastAPI веб-сервер
- Умный интерфейс с проверкой зависимостей
- API endpoints для управления
- Красивый веб-интерфейс

### 📁 Файлы для первого деплоя:
```
workspace/
├── app.py              # ← Умное приложение
├── requirements.txt    # ← Только FastAPI + uvicorn
└── Procfile           # ← web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

### 🚀 Команды для деплоя:
```bash
# Убедитесь что requirements.txt содержит только:
fastapi>=0.104.1
uvicorn[standard]>=0.24.0

# Деплой пройдет успешно!
```

### 🌐 Результат этапа 1:
- ✅ Приложение успешно развернется
- ✅ Веб-интерфейс покажет "⚠️ Setup Mode"
- ✅ API будет работать
- ✅ `/docs` покажет документацию
- ✅ `/api/status` покажет что нужно установить

---

## 📋 ЭТАП 2: Добавление Telegram

После успешного деплоя этапа 1:

### 🔧 Способ A: Обновление через переменные окружения

```bash
# В настройках деплоя добавьте переменные:
INSTALL_TELEGRAM=true
```

Затем обновите `requirements.txt`:
```txt
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
pyrogram>=2.0.106
tgcrypto>=1.2.5
```

### 🔧 Способ B: Замена файла requirements

```bash
# Замените requirements.txt на requirements_full.txt:
cp requirements_full.txt requirements.txt
git add requirements.txt
git commit -m "Add Telegram dependencies"
git push
```

### 🔧 Способ C: Динамическая установка

Добавьте endpoint для установки зависимостей:

```python
@app.post("/api/install-telegram")
async def install_telegram():
    """Установка Telegram зависимостей"""
    import subprocess
    try:
        subprocess.run(["pip", "install", "pyrogram", "tgcrypto"], check=True)
        return {"success": True, "message": "Telegram libraries installed. Restart required."}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## 🎮 Использование после полного деплоя

### 1. Получите API данные
- Перейдите на https://my.telegram.org/apps
- Создайте приложение
- Скопируйте API_ID и API_HASH

### 2. Настройте переменные окружения
```bash
API_ID=your_api_id
API_HASH=your_api_hash
PHONE_NUMBER=+1234567890
```

### 3. Запустите детектор
- Откройте веб-интерфейс
- Нажмите "🚀 Start Detector"
- При первом запуске введите код из Telegram

### 4. Мониторинг
- Интерфейс покажет статус "✅ Running"
- API будет возвращать информацию о подарках
- Логи будут доступны через `/api/logs`

---

## 🔍 Отладка по этапам

### После этапа 1:
```bash
# Проверьте что API работает:
curl https://your-app.com/health
# Ответ: {"status": "healthy", ...}

curl https://your-app.com/api/status  
# Ответ: {"telegram_available": false, ...}
```

### После этапа 2:
```bash
# Проверьте наличие Telegram:
curl https://your-app.com/api/status
# Ответ: {"telegram_available": true, "config_ready": false, ...}

# После настройки переменных:
curl https://your-app.com/api/status
# Ответ: {"telegram_available": true, "config_ready": true, ...}
```

---

## 🎯 Преимущества поэтапного подхода

### ✅ Этап 1 (Базовый):
- Быстрый деплой (меньше зависимостей)
- Немедленная обратная связь
- Проверка инфраструктуры
- Красивый интерфейс для настройки

### ✅ Этап 2 (Полный):
- Добавление функциональности без пересоздания
- Сохранение настроек
- Постепенное тестирование
- Минимизация рисков

### ✅ В результате:
- Стабильный деплой
- Полная функциональность
- Удобный интерфейс управления
- Профессиональный мониторинг

---

## 🚀 Быстрые команды

### Для немедленного деплоя с Telegram:
```bash
# Используйте requirements_full.txt:
cp requirements_full.txt requirements.txt
```

### Для безопасного поэтапного деплоя:
```bash
# Сначала базовая версия:
echo "fastapi>=0.104.1" > requirements.txt
echo "uvicorn[standard]>=0.24.0" >> requirements.txt

# Потом добавьте Telegram:
echo "pyrogram>=2.0.106" >> requirements.txt  
echo "tgcrypto>=1.2.5" >> requirements.txt
```

**Выберите подход в зависимости от ваших потребностей! 🎯**