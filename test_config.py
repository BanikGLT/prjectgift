#!/usr/bin/env python3
"""
Скрипт для тестирования конфигурации Gift Responder
"""

import sys
import asyncio
from pyrogram import Client
from pyrogram.errors import RPCError

def test_config():
    """Тестирует конфигурацию"""
    print("🔧 Тестирование конфигурации Gift Responder...\n")
    
    try:
        from gift_responder_config import *
        print("✅ Файл конфигурации загружен успешно")
    except ImportError as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False
    
    # Проверяем валидацию
    if not validate_config():
        return False
    
    print("✅ Базовая валидация пройдена")
    
    # Тестируем подключение к Telegram
    print("\n🔗 Тестирование подключения к Telegram...")
    
    try:
        client = Client(
            name="test_session",
            api_id=API_ID,
            api_hash=API_HASH,
            phone_number=PHONE_NUMBER
        )
        
        async def test_connection():
            try:
                await client.start()
                me = await client.get_me()
                print(f"✅ Подключение успешно!")
                print(f"   Пользователь: @{me.username} ({me.first_name})")
                print(f"   ID: {me.id}")
                await client.stop()
                return True
            except RPCError as e:
                print(f"❌ Ошибка Telegram API: {e}")
                return False
            except Exception as e:
                print(f"❌ Неожиданная ошибка: {e}")
                return False
        
        result = asyncio.run(test_connection())
        if not result:
            return False
            
    except Exception as e:
        print(f"❌ Ошибка создания клиента: {e}")
        return False
    
    # Тестируем настройки детекции
    print("\n🔍 Тестирование настроек детекции...")
    print(f"   Ключевых слов: {len(GIFT_KEYWORDS)}")
    print(f"   Стикер ключевых слов: {len(GIFT_STICKER_KEYWORDS)}")
    print(f"   Расширенная детекция: {'Включена' if ENABLE_EXTENDED_DETECTION else 'Выключена'}")
    
    # Тестируем настройки безопасности
    print("\n🛡️ Тестирование настроек безопасности...")
    print(f"   Игнорируемых пользователей: {len(IGNORED_USER_IDS)}")
    print(f"   Игнорируемых чатов: {len(IGNORED_CHAT_IDS)}")
    print(f"   Антиспам интервал: {MIN_RESPONSE_INTERVAL} сек")
    
    # Тестируем настройки логирования
    print("\n📝 Тестирование настроек логирования...")
    print(f"   Уровень логирования: {LOG_LEVEL}")
    print(f"   Файл логов: {LOG_FILENAME}")
    print(f"   Сохранение подарков: {'Да' if SAVE_GIFT_LOGS else 'Нет'}")
    if SAVE_GIFT_LOGS:
        print(f"   Файл подарков: {GIFT_LOG_FILENAME}")
    
    # Тестируем уведомления
    print("\n🔔 Тестирование настроек уведомлений...")
    if ENABLE_NOTIFICATION_CHAT:
        print(f"   Уведомления: Включены")
        print(f"   ID чата: {NOTIFICATION_CHAT_ID}")
    else:
        print("   Уведомления: Выключены")
    
    print("\n✅ Все тесты пройдены успешно!")
    print("🚀 Конфигурация готова к использованию!")
    
    return True

def test_gift_detection():
    """Тестирует детекцию подарков"""
    print("\n🎁 Тестирование детекции подарков...")
    
    try:
        from gift_responder_config import GIFT_KEYWORDS, GIFT_STICKER_KEYWORDS
    except ImportError:
        print("❌ Не удалось загрузить конфигурацию")
        return False
    
    # Тестовые сообщения
    test_messages = [
        "🎁 Вот тебе подарок!",
        "I have a gift for you",
        "Дарю тебе звезды ⭐",
        "Here are some stars 💎",
        "Обычное сообщение без подарков",
        "🎉 Surprise! 🎊",
        "1500 ⭐ за это"
    ]
    
    print("   Тестовые сообщения:")
    for i, message in enumerate(test_messages, 1):
        detected = any(
            keyword.lower() in message.lower() 
            for keyword in GIFT_KEYWORDS
        )
        status = "✅ ПОДАРОК" if detected else "❌ НЕ ПОДАРОК"
        print(f"   {i}. '{message}' -> {status}")
    
    return True

if __name__ == "__main__":
    print("🎁 Gift Responder - Тестирование конфигурации\n")
    
    success = test_config()
    
    if success:
        test_gift_detection()
        print("\n🎉 Тестирование завершено успешно!")
        print("💡 Теперь можно запускать telegram_gift_responder.py")
    else:
        print("\n❌ Тестирование не пройдено!")
        print("📝 Исправьте ошибки в gift_responder_config.py")
        sys.exit(1)