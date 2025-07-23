#!/usr/bin/env python3
"""
Telegram Gift Detector - Main Entry Point
Упрощенная точка входа для облачного деплоя
"""

import os
import uvicorn
from api import app

if __name__ == "__main__":
    # Получаем порт из переменной окружения
    port = int(os.environ.get("PORT", 8000))
    
    # Запуск FastAPI сервера
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )