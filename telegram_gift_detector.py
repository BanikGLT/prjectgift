#!/usr/bin/env python3
"""
Telegram Gift Detector - Простой детектор подарков
Автоматически отвечает на входящие Telegram Gifts с информацией о них
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError
from pyrogram.raw import functions, types

# Настройки (замените на свои данные)
API_ID = 12345678  # Ваш API ID из https://my.telegram.org/apps
API_HASH = "your_api_hash_here"  # Ваш API Hash
PHONE_NUMBER = "+1234567890"  # Ваш номер телефона

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramGiftDetector:
    def __init__(self):
        self.client = Client(
            name="gift_detector",
            api_id=API_ID,
            api_hash=API_HASH,
            phone_number=PHONE_NUMBER
        )
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчика сообщений"""
        
        @self.client.on_message(filters.incoming)
        async def handle_message(client: Client, message: Message):
            await self.process_message(message)
    
    async def process_message(self, message: Message):
        """Обработка входящего сообщения"""
        try:
            if await self.is_gift_message(message):
                gift_info = await self.extract_gift_info(message)
                await self.send_gift_response(message, gift_info)
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
    
    async def is_gift_message(self, message: Message) -> bool:
        """Проверяет, является ли сообщение подарком"""
        
        # 1. Проверка service message
        if hasattr(message, 'service') and message.service:
            service_str = str(message.service).lower()
            if 'gift' in service_str:
                return True
        
        # 2. Проверка через raw API
        try:
            raw_messages = await self.client.invoke(
                functions.messages.GetMessages(
                    id=[types.InputMessageID(id=message.id)]
                )
            )
            
            if raw_messages and raw_messages.messages:
                raw_msg = raw_messages.messages[0]
                
                # Проверяем action в service message
                if hasattr(raw_msg, 'action'):
                    action_type = type(raw_msg.action).__name__.lower()
                    if 'gift' in action_type or 'star' in action_type:
                        return True
                
                # Проверяем media
                if hasattr(raw_msg, 'media'):
                    media_type = type(raw_msg.media).__name__.lower()
                    if 'gift' in media_type:
                        return True
        
        except Exception as e:
            logger.debug(f"Ошибка проверки raw данных: {e}")
        
        # 3. Проверка по ключевым словам (базовая)
        if message.text:
            gift_keywords = ["🎁", "gift", "подарок", "⭐"]
            if any(keyword in message.text.lower() for keyword in gift_keywords):
                return True
        
        return False
    
    async def extract_gift_info(self, message: Message) -> Dict[str, Any]:
        """Извлекает информацию о подарке"""
        
        gift_info = {
            "message_id": message.id,
            "sender_id": message.from_user.id if message.from_user else None,
            "sender_username": message.from_user.username if message.from_user else None,
            "sender_name": self._get_sender_name(message),
            "chat_id": message.chat.id,
            "date": message.date.isoformat() if message.date else None,
            "gift_type": "unknown",
            "gift_details": {}
        }
        
        # Извлекаем детали через raw API
        try:
            raw_messages = await self.client.invoke(
                functions.messages.GetMessages(
                    id=[types.InputMessageID(id=message.id)]
                )
            )
            
            if raw_messages and raw_messages.messages:
                raw_msg = raw_messages.messages[0]
                await self._parse_raw_gift_data(raw_msg, gift_info)
        
        except Exception as e:
            logger.debug(f"Не удалось извлечь raw данные: {e}")
            # Базовая информация из обычного сообщения
            gift_info["gift_type"] = "detected_by_keywords"
        
        return gift_info
    
    def _get_sender_name(self, message: Message) -> str:
        """Получает имя отправителя"""
        if not message.from_user:
            return "Неизвестно"
        
        name_parts = []
        if message.from_user.first_name:
            name_parts.append(message.from_user.first_name)
        if message.from_user.last_name:
            name_parts.append(message.from_user.last_name)
        
        return " ".join(name_parts) if name_parts else "Неизвестно"
    
    async def _parse_raw_gift_data(self, raw_msg, gift_info: Dict[str, Any]):
        """Парсит raw данные для извлечения информации о подарке"""
        
        # Проверяем action
        if hasattr(raw_msg, 'action'):
            action = raw_msg.action
            action_type = type(action).__name__
            
            gift_info["gift_type"] = action_type
            
            # Извлекаем детали подарка
            if hasattr(action, 'gift'):
                gift = action.gift
                gift_info["gift_details"] = self._extract_gift_details(gift)
            elif hasattr(action, 'star_gift'):
                star_gift = action.star_gift
                gift_info["gift_details"] = self._extract_gift_details(star_gift)
        
        # Проверяем media
        elif hasattr(raw_msg, 'media'):
            media = raw_msg.media
            media_type = type(media).__name__
            gift_info["gift_type"] = media_type
            
            if hasattr(media, 'gift'):
                gift_info["gift_details"] = self._extract_gift_details(media.gift)
    
    def _extract_gift_details(self, gift_obj) -> Dict[str, Any]:
        """Извлекает детали из объекта подарка"""
        details = {}
        
        # Основные атрибуты подарка
        gift_attrs = [
            'id', 'stars', 'price', 'total_amount', 'remaining_amount',
            'is_limited', 'is_sold_out', 'is_unique', 'convert_stars',
            'upgrade_price', 'title'
        ]
        
        for attr in gift_attrs:
            if hasattr(gift_obj, attr):
                value = getattr(gift_obj, attr)
                if value is not None:
                    details[attr] = value
        
        return details
    
    async def send_gift_response(self, original_message: Message, gift_info: Dict[str, Any]):
        """Отправляет ответ с информацией о подарке"""
        
        try:
            response_text = self._format_response(gift_info)
            
            await self.client.send_message(
                chat_id=original_message.chat.id,
                text=response_text,
                reply_to_message_id=original_message.id,
                parse_mode="HTML"
            )
            
            logger.info(f"Ответ отправлен на подарок от {gift_info.get('sender_username', gift_info.get('sender_id'))}")
            
        except RPCError as e:
            logger.error(f"Ошибка отправки ответа: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
    
    def _format_response(self, gift_info: Dict[str, Any]) -> str:
        """Форматирует ответное сообщение"""
        
        response_parts = [
            "🎁 <b>Информация о подарке:</b>\n"
        ]
        
        # Информация об отправителе
        if gift_info.get('sender_username'):
            response_parts.append(f"👤 <b>От:</b> @{gift_info['sender_username']} ({gift_info.get('sender_name', '')})")
        else:
            response_parts.append(f"👤 <b>От:</b> {gift_info.get('sender_name', 'Неизвестно')}")
        
        response_parts.append(f"🆔 <b>ID отправителя:</b> <code>{gift_info.get('sender_id', 'Неизвестно')}</code>")
        
        # Время
        if gift_info.get('date'):
            response_parts.append(f"🕐 <b>Время:</b> {gift_info['date']}")
        
        # Тип подарка
        response_parts.append(f"🎯 <b>Тип:</b> {gift_info.get('gift_type', 'unknown')}")
        
        # Детали подарка
        gift_details = gift_info.get('gift_details', {})
        if gift_details:
            response_parts.append("\n🔍 <b>Детали подарка:</b>")
            
            if gift_details.get('id'):
                response_parts.append(f"🆔 ID подарка: <code>{gift_details['id']}</code>")
            
            if gift_details.get('stars'):
                response_parts.append(f"⭐ Цена: {gift_details['stars']} звезд")
            elif gift_details.get('price'):
                response_parts.append(f"💰 Цена: {gift_details['price']} ⭐")
            
            if gift_details.get('total_amount'):
                response_parts.append(f"📦 Всего выпущено: {gift_details['total_amount']}")
            
            if gift_details.get('remaining_amount'):
                response_parts.append(f"📦 Осталось: {gift_details['remaining_amount']}")
            
            if gift_details.get('is_limited'):
                response_parts.append(f"🔒 Ограниченный: {'Да' if gift_details['is_limited'] else 'Нет'}")
            
            if gift_details.get('is_unique'):
                response_parts.append(f"💎 Уникальный: {'Да' if gift_details['is_unique'] else 'Нет'}")
            
            if gift_details.get('convert_stars'):
                response_parts.append(f"💫 Конвертация: {gift_details['convert_stars']} ⭐")
            
            if gift_details.get('title'):
                response_parts.append(f"📛 Название: {gift_details['title']}")
        
        response_parts.append(f"\n🤖 <i>Автоответ Gift Detector</i>")
        
        return "\n".join(response_parts)
    
    async def start(self):
        """Запуск детектора"""
        try:
            await self.client.start()
            me = await self.client.get_me()
            logger.info(f"✅ Gift Detector запущен! Пользователь: @{me.username}")
            logger.info("🎁 Ожидание входящих подарков...")
        except Exception as e:
            logger.error(f"Ошибка запуска: {e}")
            raise
    
    async def stop(self):
        """Остановка детектора"""
        try:
            await self.client.stop()
            logger.info("🛑 Gift Detector остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки: {e}")


async def main():
    """Главная функция"""
    
    # Проверяем настройки
    if API_ID == 12345678 or API_HASH == "your_api_hash_here":
        print("❌ Настройте API_ID и API_HASH в начале файла!")
        print("📝 Получите данные на https://my.telegram.org/apps")
        return
    
    detector = TelegramGiftDetector()
    
    try:
        await detector.start()
        
        print("🚀 Gift Detector готов к работе!")
        print("🎁 Отправьте себе подарок для тестирования")
        print("⌨️  Нажмите Ctrl+C для остановки")
        
        # Ждем бесконечно
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("👋 Остановка по запросу пользователя...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        await detector.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Программа завершена")
    except Exception as e:
        print(f"❌ Ошибка: {e}")