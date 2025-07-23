#!/usr/bin/env python3
"""
Telegram Gift Detector - Startup Script
Простой скрипт запуска для отладки деплоя
"""

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Запуск Telegram Gift Detector...")
    
    # Проверяем Python версию
    logger.info(f"🐍 Python версия: {sys.version}")
    
    # Проверяем переменные окружения
    port = os.environ.get("PORT", "8000")
    logger.info(f"🌐 Порт: {port}")
    
    # Проверяем рабочую директорию
    logger.info(f"📁 Рабочая директория: {os.getcwd()}")
    
    # Проверяем наличие файлов
    files = os.listdir(".")
    logger.info(f"📄 Файлы: {files}")
    
    try:
        # Импортируем и запускаем FastAPI
        logger.info("📦 Импорт модулей...")
        import uvicorn
        from api import app
        
        logger.info("✅ Модули импортированы успешно")
        
        # Запуск сервера
        logger.info(f"🚀 Запуск сервера на порту {port}...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=int(port),
            log_level="info"
        )
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        # Попробуем установить зависимости
        logger.info("🔧 Попытка установки зависимостей...")
        os.system("pip install fastapi uvicorn")
        
        # Повторная попытка
        try:
            import uvicorn
            from api import app
            uvicorn.run(app, host="0.0.0.0", port=int(port))
        except Exception as e2:
            logger.error(f"❌ Повторная ошибка: {e2}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()