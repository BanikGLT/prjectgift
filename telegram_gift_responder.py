#!/usr/bin/env python3
"""
Telegram Gift Auto-Responder Bot
Автоматически отвечает на входящие телеграм подарки с подробной информацией

Основано на анализе кода из репозитория Gifts-Buyer
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, Set

from pyrogram import Client, filters
from pyrogram.types import Message, MessageEntity
from pyrogram.errors import RPCError

# Импорт конфигурации
try:
    from gift_responder_config import *
except ImportError:
    print("❌ Не найден файл gift_responder_config.py!")
    print("📝 Создайте файл конфигурации или скопируйте gift_responder_config.py")
    exit(1)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILENAME),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramGiftResponder:
    def __init__(self, api_id: int = None, api_hash: str = None, phone_number: str = None, session_name: str = None):
        """
        Инициализация userbot'а для ответа на подарки
        
        Args:
            api_id: API ID из my.telegram.org (если не указан, берется из конфига)
            api_hash: API Hash из my.telegram.org (если не указан, берется из конфига)
            phone_number: Номер телефона (если не указан, берется из конфига)
            session_name: Имя сессии (если не указано, берется из конфига)
        """
        # Используем параметры из конфига, если не переданы явно
        self.api_id = api_id or API_ID
        self.api_hash = api_hash or API_HASH
        self.phone_number = phone_number or PHONE_NUMBER
        self.session_name = session_name or SESSION_NAME
        
        self.client = Client(
            name=self.session_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
            phone_number=self.phone_number
        )
        
        # Статистика
        self.stats = {
            "received_gifts": 0,
            "sent_responses": 0,
            "errors": 0,
            "ignored_users": 0,
            "ignored_chats": 0,
            "start_time": datetime.now()
        }
        
        # Кэш для предотвращения спама
        self.last_response_times: Dict[int, float] = {}
        
        # Множество для отслеживания уже обработанных сообщений
        self.processed_messages: Set[int] = set()
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков сообщений"""
        
        @self.client.on_message(filters.private & filters.incoming)
        async def handle_private_message(client: Client, message: Message):
            """Обработчик приватных сообщений"""
            await self.process_message(message)
        
        @self.client.on_message(filters.group & filters.incoming)
        async def handle_group_message(client: Client, message: Message):
            """Обработчик групповых сообщений"""
            await self.process_message(message)
    
    async def process_message(self, message: Message):
        """
        Обработка входящего сообщения на предмет подарков
        
        Args:
            message: Входящее сообщение
        """
        try:
            # Проверяем, не обрабатывали ли мы уже это сообщение
            if message.id in self.processed_messages:
                return
            
            # Добавляем сообщение в обработанные
            self.processed_messages.add(message.id)
            
            # Проверяем игнор-листы
            if await self.should_ignore_message(message):
                return
            
            # Проверяем, является ли сообщение подарком
            if await self.is_gift_message(message):
                # Проверяем антиспам
                if not await self.check_antispam(message):
                    return
                
                gift_info = await self.extract_gift_info(message)
                await self.send_gift_response(message, gift_info)
                
                # Небольшая задержка между обработкой сообщений
                await asyncio.sleep(MESSAGE_PROCESSING_DELAY)
                
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            self.stats["errors"] += 1
    
    async def should_ignore_message(self, message: Message) -> bool:
        """
        Проверяет, нужно ли игнорировать сообщение
        
        Args:
            message: Сообщение для проверки
            
        Returns:
            True если сообщение нужно игнорировать
        """
        # Проверяем игнор-лист пользователей
        if message.from_user and message.from_user.id in IGNORED_USER_IDS:
            self.stats["ignored_users"] += 1
            logger.debug(f"Игнорируем пользователя {message.from_user.id}")
            return True
        
        # Проверяем игнор-лист чатов
        if message.chat.id in IGNORED_CHAT_IDS:
            self.stats["ignored_chats"] += 1
            logger.debug(f"Игнорируем чат {message.chat.id}")
            return True
        
        return False
    
    async def check_antispam(self, message: Message) -> bool:
        """
        Проверяет антиспам ограничения
        
        Args:
            message: Сообщение для проверки
            
        Returns:
            True если можно отправить ответ
        """
        if not message.from_user:
            return True
        
        user_id = message.from_user.id
        current_time = time.time()
        
        # Проверяем последний ответ этому пользователю
        if user_id in self.last_response_times:
            time_diff = current_time - self.last_response_times[user_id]
            if time_diff < MIN_RESPONSE_INTERVAL:
                logger.debug(f"Антиспам: слишком быстрый ответ пользователю {user_id}")
                return False
        
        # Обновляем время последнего ответа
        self.last_response_times[user_id] = current_time
        return True
    
    async def is_gift_message(self, message: Message) -> bool:
        """
        Проверяет, является ли сообщение подарком
        
        Args:
            message: Сообщение для проверки
            
        Returns:
            True если сообщение содержит подарок
        """
        # Проверяем различные индикаторы подарка
        gift_indicators = [
            # Проверка на наличие специальных сущностей
            message.entities and any(
                entity.type in ["gift", "paid_media"] for entity in message.entities
            ),
            # Проверка текста на ключевые слова из конфига
            message.text and any(
                keyword.lower() in message.text.lower() 
                for keyword in GIFT_KEYWORDS
            ),
            # Проверка caption на ключевые слова
            message.caption and any(
                keyword.lower() in message.caption.lower() 
                for keyword in GIFT_KEYWORDS
            ),
            # Проверка на наличие стикеров с подарками
            message.sticker and any(
                keyword.lower() in (message.sticker.file_name or "").lower()
                for keyword in GIFT_STICKER_KEYWORDS
            ),
            # Проверка на специальные типы сообщений
            hasattr(message, 'gift') and message.gift,
            # Проверка на paid media
            hasattr(message, 'paid_media') and message.paid_media
        ]
        
        # Расширенная детекция (если включена)
        if ENABLE_EXTENDED_DETECTION:
            extended_indicators = [
                # Проверка на emoji подарков в любом месте
                message.text and any(emoji in message.text for emoji in ["🎁", "🎉", "🎊", "💝", "🎀"]),
                # Проверка на числа со звездочками (возможная цена)
                message.text and any(
                    char.isdigit() and "⭐" in message.text 
                    for char in message.text
                ),
            ]
            gift_indicators.extend(extended_indicators)
        
        return any(gift_indicators)
    
    async def extract_gift_info(self, message: Message) -> Dict[str, Any]:
        """
        Извлекает информацию о подарке из сообщения
        
        Args:
            message: Сообщение с подарком
            
        Returns:
            Словарь с информацией о подарке
        """
        gift_info = {
            "message_id": message.id,
            "sender_id": message.from_user.id if message.from_user else None,
            "sender_username": message.from_user.username if message.from_user else None,
            "sender_first_name": message.from_user.first_name if message.from_user else None,
            "sender_last_name": message.from_user.last_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.value if message.chat.type else None,
            "chat_title": message.chat.title if hasattr(message.chat, 'title') else None,
            "date": message.date.isoformat() if message.date else None,
            "text": message.text,
            "caption": message.caption,
            "gift_type": "unknown",
            "gift_details": {}
        }
        
        # Извлекаем детали подарка
        if hasattr(message, 'gift') and message.gift:
            gift_info["gift_type"] = "telegram_gift"
            gift_info["gift_details"] = await self.extract_telegram_gift_details(message.gift)
        
        elif hasattr(message, 'paid_media') and message.paid_media:
            gift_info["gift_type"] = "paid_media"
            gift_info["gift_details"] = await self.extract_paid_media_details(message.paid_media)
        
        elif message.sticker:
            gift_info["gift_type"] = "sticker_gift"
            gift_info["gift_details"] = await self.extract_sticker_details(message.sticker)
        
        # Анализируем entities
        if message.entities:
            gift_info["entities"] = []
            for entity in message.entities:
                gift_info["entities"].append({
                    "type": entity.type.value if hasattr(entity.type, 'value') else str(entity.type),
                    "offset": entity.offset,
                    "length": entity.length,
                    "url": getattr(entity, 'url', None),
                    "user": getattr(entity, 'user', None)
                })
        
        return gift_info
    
    async def extract_telegram_gift_details(self, gift) -> Dict[str, Any]:
        """Извлекает детали телеграм подарка"""
        try:
            return {
                "id": getattr(gift, 'id', None),
                "price": getattr(gift, 'price', None),
                "currency": getattr(gift, 'currency', None),
                "total_amount": getattr(gift, 'total_amount', None),
                "remaining_amount": getattr(gift, 'remaining_amount', None),
                "is_limited": getattr(gift, 'is_limited', None),
                "is_sold_out": getattr(gift, 'is_sold_out', None),
                "upgrade_price": getattr(gift, 'upgrade_price', None),
                "sticker": getattr(gift, 'sticker', None)
            }
        except Exception as e:
            logger.error(f"Ошибка извлечения данных подарка: {e}")
            return {"error": str(e)}
    
    async def extract_paid_media_details(self, paid_media) -> Dict[str, Any]:
        """Извлекает детали платного медиа"""
        try:
            return {
                "stars_amount": getattr(paid_media, 'stars_amount', None),
                "media_count": len(paid_media.media) if hasattr(paid_media, 'media') else 0,
                "media_types": [type(media).__name__ for media in paid_media.media] if hasattr(paid_media, 'media') else []
            }
        except Exception as e:
            logger.error(f"Ошибка извлечения данных paid media: {e}")
            return {"error": str(e)}
    
    async def extract_sticker_details(self, sticker) -> Dict[str, Any]:
        """Извлекает детали стикера"""
        try:
            return {
                "file_id": sticker.file_id,
                "file_unique_id": sticker.file_unique_id,
                "file_name": sticker.file_name,
                "emoji": sticker.emoji,
                "set_name": sticker.set_name,
                "is_animated": sticker.is_animated,
                "is_video": sticker.is_video,
                "width": sticker.width,
                "height": sticker.height,
                "file_size": sticker.file_size
            }
        except Exception as e:
            logger.error(f"Ошибка извлечения данных стикера: {e}")
            return {"error": str(e)}
    
    async def send_gift_response(self, original_message: Message, gift_info: Dict[str, Any]):
        """
        Отправляет ответ с информацией о подарке
        
        Args:
            original_message: Оригинальное сообщение с подарком
            gift_info: Информация о подарке
        """
        # Формируем ответное сообщение
        response_text = await self.format_gift_response(gift_info)
        
        # Пытаемся отправить ответ с повторными попытками
        success = False
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                # Отправляем ответ
                parse_mode = "HTML" if USE_HTML_FORMATTING else None
                
                await self.client.send_message(
                    chat_id=original_message.chat.id,
                    text=response_text,
                    reply_to_message_id=original_message.id,
                    parse_mode=parse_mode
                )
                
                success = True
                break
                
            except RPCError as e:
                logger.warning(f"Попытка {attempt + 1}/{MAX_RETRY_ATTEMPTS} не удалась: {e}")
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(f"Все попытки отправки ответа исчерпаны: {e}")
                    self.stats["errors"] += 1
                    
            except Exception as e:
                logger.error(f"Неожиданная ошибка при отправке ответа: {e}")
                self.stats["errors"] += 1
                break
        
        if success:
            self.stats["sent_responses"] += 1
            self.stats["received_gifts"] += 1
            
            logger.info(f"Отправлен ответ на подарок от {gift_info.get('sender_username', gift_info.get('sender_id'))}")
            
            # Сохраняем информацию о подарке
            if SAVE_GIFT_LOGS:
                await self.save_gift_log(gift_info)
            
            # Отправляем уведомление в специальный чат (если настроено)
            if ENABLE_NOTIFICATION_CHAT and NOTIFICATION_CHAT_ID:
                await self.send_notification_to_chat(gift_info)
    
    async def format_gift_response(self, gift_info: Dict[str, Any]) -> str:
        """
        Форматирует ответное сообщение с информацией о подарке
        
        Args:
            gift_info: Информация о подарке
            
        Returns:
            Отформатированный текст ответа
        """
        # Основная информация
        response_parts = [
            "🎁 <b>Информация о подарке:</b>\n",
            f"📨 <b>ID сообщения:</b> <code>{gift_info['message_id']}</code>",
        ]
        
        # Информация об отправителе
        if gift_info.get('sender_id'):
            sender_info = f"👤 <b>Отправитель:</b> "
            if gift_info.get('sender_username'):
                sender_info += f"@{gift_info['sender_username']} "
            if gift_info.get('sender_first_name'):
                sender_info += f"({gift_info['sender_first_name']}"
                if gift_info.get('sender_last_name'):
                    sender_info += f" {gift_info['sender_last_name']}"
                sender_info += ")"
            sender_info += f"\n🆔 <b>ID отправителя:</b> <code>{gift_info['sender_id']}</code>"
            response_parts.append(sender_info)
        
        # Информация о чате
        response_parts.append(f"💬 <b>ID чата:</b> <code>{gift_info['chat_id']}</code>")
        if gift_info.get('chat_title'):
            response_parts.append(f"📋 <b>Название чата:</b> {gift_info['chat_title']}")
        response_parts.append(f"📂 <b>Тип чата:</b> {gift_info.get('chat_type', 'unknown')}")
        
        # Время получения
        if gift_info.get('date'):
            response_parts.append(f"🕐 <b>Время:</b> {gift_info['date']}")
        
        # Тип подарка
        response_parts.append(f"🎯 <b>Тип подарка:</b> {gift_info.get('gift_type', 'unknown')}")
        
        # Детали подарка
        gift_details = gift_info.get('gift_details', {})
        if gift_details and not gift_details.get('error'):
            response_parts.append("\n🔍 <b>Детали подарка:</b>")
            
            if gift_info['gift_type'] == 'telegram_gift':
                if gift_details.get('id'):
                    response_parts.append(f"🆔 ID подарка: <code>{gift_details['id']}</code>")
                if gift_details.get('price'):
                    response_parts.append(f"💰 Цена: {gift_details['price']} ⭐")
                if gift_details.get('total_amount'):
                    response_parts.append(f"📦 Общее количество: {gift_details['total_amount']}")
                if gift_details.get('remaining_amount'):
                    response_parts.append(f"📦 Осталось: {gift_details['remaining_amount']}")
                if gift_details.get('is_limited') is not None:
                    response_parts.append(f"🔒 Ограниченный: {'Да' if gift_details['is_limited'] else 'Нет'}")
                if gift_details.get('is_sold_out') is not None:
                    response_parts.append(f"❌ Распродан: {'Да' if gift_details['is_sold_out'] else 'Нет'}")
                if gift_details.get('upgrade_price'):
                    response_parts.append(f"⬆️ Цена улучшения: {gift_details['upgrade_price']} ⭐")
            
            elif gift_info['gift_type'] == 'paid_media':
                if gift_details.get('stars_amount'):
                    response_parts.append(f"⭐ Стоимость: {gift_details['stars_amount']} звезд")
                if gift_details.get('media_count'):
                    response_parts.append(f"📁 Количество медиа: {gift_details['media_count']}")
                if gift_details.get('media_types'):
                    response_parts.append(f"📄 Типы медиа: {', '.join(gift_details['media_types'])}")
            
            elif gift_info['gift_type'] == 'sticker_gift':
                if gift_details.get('emoji'):
                    response_parts.append(f"😀 Эмодзи: {gift_details['emoji']}")
                if gift_details.get('set_name'):
                    response_parts.append(f"📦 Набор: {gift_details['set_name']}")
                if gift_details.get('file_size'):
                    response_parts.append(f"📏 Размер файла: {gift_details['file_size']} байт")
        
        # Текст сообщения (если есть)
        if gift_info.get('text'):
            text_preview = gift_info['text'][:100] + "..." if len(gift_info['text']) > 100 else gift_info['text']
            response_parts.append(f"\n💬 <b>Текст:</b> {text_preview}")
        
        # Entities (если есть)
        if gift_info.get('entities'):
            entities_info = []
            for entity in gift_info['entities'][:3]:  # Показываем только первые 3
                entities_info.append(f"• {entity['type']}")
            if entities_info:
                response_parts.append(f"\n🏷 <b>Сущности:</b> {', '.join(entities_info)}")
        
        response_parts.append(f"\n🤖 <i>Автоответ от Gift Responder Bot</i>")
        
        return "\n".join(response_parts)
    
    async def send_notification_to_chat(self, gift_info: Dict[str, Any]):
        """
        Отправляет уведомление о подарке в специальный чат
        
        Args:
            gift_info: Информация о подарке
        """
        try:
            notification_text = f"🔔 <b>Получен новый подарок!</b>\n\n"
            notification_text += f"👤 От: {gift_info.get('sender_username', 'Неизвестно')}\n"
            notification_text += f"🆔 ID: <code>{gift_info.get('sender_id', 'Неизвестно')}</code>\n"
            notification_text += f"💬 Чат: <code>{gift_info.get('chat_id', 'Неизвестно')}</code>\n"
            notification_text += f"🎯 Тип: {gift_info.get('gift_type', 'unknown')}\n"
            notification_text += f"🕐 Время: {gift_info.get('date', 'Неизвестно')}"
            
            await self.client.send_message(
                chat_id=NOTIFICATION_CHAT_ID,
                text=notification_text,
                parse_mode="HTML" if USE_HTML_FORMATTING else None
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
    
    async def save_gift_log(self, gift_info: Dict[str, Any]):
        """
        Сохраняет информацию о подарке в лог файл
        
        Args:
            gift_info: Информация о подарке
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "gift_info": gift_info
            }
            
            with open(GIFT_LOG_FILENAME, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + "\n")
                
        except Exception as e:
            logger.error(f"Ошибка сохранения лога: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику работы бота"""
        uptime = datetime.now() - self.stats["start_time"]
        return {
            **self.stats,
            "uptime": str(uptime),
            "uptime_seconds": uptime.total_seconds()
        }
    
    async def start(self):
        """Запуск userbot'а"""
        try:
            await self.client.start()
            me = await self.client.get_me()
            logger.info(f"✅ Userbot запущен! Пользователь: @{me.username} ({me.first_name})")
            logger.info("🎁 Ожидание входящих подарков...")
            
            # Показываем статистику каждые 5 минут
            asyncio.create_task(self.stats_reporter())
            
        except Exception as e:
            logger.error(f"Ошибка запуска: {e}")
            raise
    
    async def stats_reporter(self):
        """Периодически выводит статистику"""
        while True:
            await asyncio.sleep(STATS_REPORT_INTERVAL)
            stats = await self.get_stats()
            logger.info(f"📊 Статистика: подарков: {stats['received_gifts']}, "
                       f"ответов: {stats['sent_responses']}, "
                       f"ошибок: {stats['errors']}, "
                       f"игнор пользователей: {stats['ignored_users']}, "
                       f"игнор чатов: {stats['ignored_chats']}, "
                       f"время работы: {stats['uptime']}")
            
            # Обновляем заголовок терминала (если включено)
            if ENABLE_TERMINAL_TITLE_STATS:
                try:
                    import os
                    title = f"Gift Responder - Подарков: {stats['received_gifts']} | Ответов: {stats['sent_responses']}"
                    os.system(f'title {title}' if os.name == 'nt' else f'echo -ne "\\033]0;{title}\\007"')
                except:
                    pass
    
    async def stop(self):
        """Остановка userbot'а"""
        try:
            await self.client.stop()
            logger.info("🛑 Userbot остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки: {e}")


async def main():
    """Главная функция"""
    # Проверяем конфигурацию
    if not validate_config():
        logger.error("❌ Некорректная конфигурация!")
        return
    
    logger.info("✅ Конфигурация проверена")
    
    # Создаем и запускаем бота
    bot = TelegramGiftResponder()
    
    try:
        await bot.start()
        
        # Показываем начальную статистику
        stats = await bot.get_stats()
        logger.info(f"🚀 Бот готов к работе!")
        logger.info(f"📊 Начальная статистика: {stats}")
        logger.info(f"🔧 Настройки:")
        logger.info(f"  • Детекция ключевых слов: {len(GIFT_KEYWORDS)} слов")
        logger.info(f"  • Антиспам интервал: {MIN_RESPONSE_INTERVAL} сек")
        logger.info(f"  • Сохранение логов: {'Да' if SAVE_GIFT_LOGS else 'Нет'}")
        logger.info(f"  • Расширенная детекция: {'Да' if ENABLE_EXTENDED_DETECTION else 'Нет'}")
        logger.info(f"  • Уведомления в чат: {'Да' if ENABLE_NOTIFICATION_CHAT else 'Нет'}")
        
        # Ждем бесконечно
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        await bot.stop()


if __name__ == "__main__":
    # Запуск бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Программа завершена пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")