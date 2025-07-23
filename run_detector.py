#!/usr/bin/env python3
"""
Простой запуск Telegram Gift Detector из консоли
"""

import asyncio
import os
from telegram_detector import start_telegram_detector

async def main():
    print("🎁 Telegram Gift Detector")
    print("=" * 40)
    
    # Получаем данные для авторизации
    api_id = input("Введите API ID: ").strip()
    api_hash = input("Введите API Hash: ").strip()
    phone = input("Введите номер телефона (+7XXXXXXXXXX): ").strip()
    
    print(f"\n🚀 Запускаем детектор для {phone}...")
    print("📱 Если потребуется код из SMS - введите его в консоль")
    
    async def gift_found(gift_info):
        print(f"\n🎁 НАЙДЕН ПОДАРОК!")
        print(f"   Тип: {gift_info.get('type')}")
        print(f"   Отправитель: {gift_info.get('sender')}")
        print(f"   Чат: {gift_info.get('chat')}")
        print(f"   Метод: {gift_info.get('detection_method')}")
        print("-" * 40)
    
    try:
        await start_telegram_detector(api_id, api_hash, phone, gift_found)
    except KeyboardInterrupt:
        print("\n⏹️ Остановлено пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())