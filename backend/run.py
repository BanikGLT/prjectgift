#!/usr/bin/env python3
"""
Telegram Gift Detector - Launcher
Удобный запускатель для профессионального детектора подарков
"""

import os
import sys
import asyncio
from pathlib import Path

# Добавляем текущую папку в PATH для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

def check_dependencies():
    """Проверяет установленные зависимости"""
    try:
        import pyrogram
        import tgcrypto
        print("✅ Зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("📦 Установите зависимости: pip install -r requirements.txt")
        return False

def main():
    """Главная функция запуска"""
    
    print("🎁 TELEGRAM GIFT DETECTOR - PROFESSIONAL EDITION")
    print("=" * 60)
    
    # Проверяем зависимости
    if not check_dependencies():
        return
    
    # Проверяем конфигурацию
    try:
        from config import config
        is_valid, errors = config.validate()
        
        if not is_valid:
            print("\n❌ ОШИБКИ КОНФИГУРАЦИИ:")
            for error in errors:
                print(f"  {error}")
            print("\n📝 Отредактируйте файл config.py или установите переменные окружения")
            print("🔗 API данные: https://my.telegram.org/apps")
            return
        
        print("✅ Конфигурация валидна")
        
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return
    
    # Запускаем детектор
    try:
        from telegram_gift_detector import main as detector_main
        print("\n🚀 Запуск детектора...")
        asyncio.run(detector_main())
        
    except KeyboardInterrupt:
        print("\n👋 Остановка по запросу пользователя")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        return

if __name__ == "__main__":
    main()