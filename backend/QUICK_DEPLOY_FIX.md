# 🚨 БЫСТРОЕ ИСПРАВЛЕНИЕ ДЕПЛОЯ

## Проблема
Деплой зависает на этапе "Search for the port" - система не может найти запущенное приложение.

## ✅ БЫСТРОЕ РЕШЕНИЕ

### 1. Замените Procfile
```bash
# В корне проекта создайте/замените Procfile:
echo "web: uvicorn backend.simple_api:app --host 0.0.0.0 --port \$PORT" > Procfile
```

### 2. Переместите файлы в корень (если нужно)
```bash
# Если деплой ищет файлы в корне проекта:
cp backend/simple_api.py ./
cp backend/requirements_minimal.txt ./requirements.txt
```

### 3. Обновите requirements.txt в корне
```txt
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
```

### 4. Создайте простой app.py в корне
```python
#!/usr/bin/env python3
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Telegram Gift Detector")

@app.get("/")
async def root():
    return HTMLResponse("""
    <h1>🎁 Telegram Gift Detector</h1>
    <p>✅ Deployed Successfully!</p>
    <a href="/docs">API Docs</a>
    """)

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "API is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### 5. Обновите Procfile
```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

## 🔧 АЛЬТЕРНАТИВНЫЕ ВАРИАНТЫ

### Вариант A: Gunicorn
```bash
# requirements.txt
fastapi
uvicorn
gunicorn

# Procfile
web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app --bind 0.0.0.0:$PORT
```

### Вариант B: Прямой запуск Python
```bash
# Procfile
web: python app.py
```

### Вариант C: Указание директории
```bash
# Procfile
web: cd backend && uvicorn simple_api:app --host 0.0.0.0 --port $PORT
```

## 📊 ОТЛАДКА

### Проверьте логи деплоя
```bash
# Найдите в логах:
# 1. "Successfully installed" - зависимости установлены
# 2. "Application startup complete" - сервер запустился
# 3. Ошибки импорта модулей
```

### Тестирование локально
```bash
# Протестируйте команду из Procfile локально:
PORT=8000 uvicorn app:app --host 0.0.0.0 --port $PORT
```

## 🎯 МИНИМАЛЬНЫЙ РАБОЧИЙ ПРИМЕР

Создайте эти файлы в корне проекта:

**app.py:**
```python
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/health")
def health():
    return {"status": "ok"}
```

**requirements.txt:**
```
fastapi
uvicorn
```

**Procfile:**
```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

## 🚀 ПОСЛЕ ИСПРАВЛЕНИЯ

1. ✅ Деплой должен завершиться успешно
2. ✅ Приложение будет доступно по URL
3. ✅ `/health` endpoint будет отвечать
4. ✅ `/docs` покажет API документацию

## 🔄 СЛЕДУЮЩИЕ ШАГИ

После успешного деплоя простой версии:
1. Постепенно добавляйте функциональность
2. Тестируйте каждое изменение
3. Добавьте переменные окружения для API ключей
4. Интегрируйте полную версию детектора подарков