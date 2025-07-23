#!/usr/bin/env python3
"""
Telegram Gift Detector - Simple API
Минимальная версия для тестирования деплоя
"""

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Создаем FastAPI приложение
app = FastAPI(
    title="Telegram Gift Detector - Simple",
    description="Minimal version for deployment testing",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Главная страница"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎁 Telegram Gift Detector</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .container { max-width: 600px; margin: 0 auto; }
            .status { background: #d4edda; color: #155724; padding: 20px; border-radius: 8px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎁 Telegram Gift Detector</h1>
            <p>Professional Edition - Deployed Successfully!</p>
            <div class="status">
                ✅ API is running and ready
            </div>
            <p><a href="/docs">📚 API Documentation</a></p>
            <p><a href="/health">🔍 Health Check</a></p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {
        "status": "healthy",
        "message": "Telegram Gift Detector API is running",
        "version": "1.0.0"
    }

@app.get("/api/status")
async def api_status():
    """API статус"""
    return {
        "success": True,
        "message": "API работает",
        "data": {
            "is_running": True,
            "detector_status": "ready_to_start"
        }
    }

# Для запуска через uvicorn
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)