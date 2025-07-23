#!/usr/bin/env python3
"""
Telegram Gift Detector - Professional Edition
Коммерческий детектор реальных Telegram подарков (Star Gifts)
Автоматически отвечает на входящие подарки с детальной информацией
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import RPCError, FloodWait, AuthKeyUnregistered, UserDeactivated
from pyrogram.raw import functions, types

# Импортируем конфигурацию
from config import config

# =============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================================================================

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramGiftDetector:
    """
    Профессиональный детектор Telegram подарков
    Поддерживает все типы подарков: Star Gifts, Unique Gifts, Regular Gifts
    """
    
    def __init__(self):
        """Инициализация детектора"""
        self.client = Client(
            name=config.SESSION_NAME,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            phone_number=config.PHONE_NUMBER
        )
        
        # Статистика работы
        self.stats = {
            "gifts_detected": 0,
            "responses_sent": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
        
        # Кэш обработанных сообщений (предотвращение дублирования)
        self.processed_messages = set()
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков событий"""
        
        @self.client.on_message(filters.incoming)
        async def handle_incoming_message(client: Client, message: Message):
            """Обработчик всех входящих сообщений"""
            await self.process_message(message)
    
    async def process_message(self, message: Message):
        """
        Основной метод обработки сообщений
        
        Args:
            message: Входящее сообщение Telegram
        """
        try:
            # Предотвращение повторной обработки
            if message.id in self.processed_messages:
                return
            
            self.processed_messages.add(message.id)
            
            # Ограничиваем размер кэша
            if len(self.processed_messages) > config.CACHE_SIZE:
                self.processed_messages.clear()
            
            # Проверяем фильтры
            if self._should_ignore_message(message):
                return
            
            # Проверяем, является ли сообщение подарком
            if await self.is_gift_message(message):
                gift_info = await self.extract_gift_info(message)
                await self.send_gift_response(message, gift_info)
                
                self.stats["gifts_detected"] += 1
                logger.info(f"Обработан подарок #{self.stats['gifts_detected']} от {gift_info.get('sender_username', 'Unknown')}")
                
                # Небольшая задержка для предотвращения флуда
                await asyncio.sleep(config.RESPONSE_DELAY)
        
        except FloodWait as e:
            logger.warning(f"FloodWait: ожидание {e.value} секунд")
            await asyncio.sleep(e.value)
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Ошибка обработки сообщения {message.id}: {e}")
    
    def _should_ignore_message(self, message: Message) -> bool:
        """Проверяет, нужно ли игнорировать сообщение"""
        
        # Игнорируем пользователей из черного списка
        if message.from_user and message.from_user.id in config.IGNORED_USERS:
            logger.debug(f"Игнорируем пользователя {message.from_user.id}")
            return True
        
        # Игнорируем чаты из черного списка
        if message.chat.id in config.IGNORED_CHATS:
            logger.debug(f"Игнорируем чат {message.chat.id}")
            return True
        
        return False
    
    async def is_gift_message(self, message: Message) -> bool:
        """
        Определяет, является ли сообщение подарком
        Использует множественные методы детекции для максимальной точности
        
        Args:
            message: Сообщение для анализа
            
        Returns:
            True если сообщение содержит подарок
        """
        
        # Метод 1: Проверка service message через Pyrogram
        if config.ENABLE_PYROGRAM_DETECTION and self._check_pyrogram_service(message):
            return True
        
        # Метод 2: Анализ через Raw API (основной метод)
        if config.ENABLE_RAW_API_DETECTION and await self._check_raw_api(message):
            return True
        
        # Метод 3: Анализ текста (резервный метод)
        if config.ENABLE_TEXT_DETECTION and self._check_text_indicators(message):
            return True
        
        return False
    
    def _check_pyrogram_service(self, message: Message) -> bool:
        """Проверка через стандартные атрибуты Pyrogram"""
        try:
            # Проверяем service message
            if hasattr(message, 'service') and message.service:
                service_str = str(message.service).lower()
                return 'gift' in service_str
            
            # Проверяем специальные атрибуты (если добавят в будущих версиях)
            gift_attributes = ['gift', 'star_gift', 'unique_gift']
            for attr in gift_attributes:
                if hasattr(message, attr) and getattr(message, attr):
                    return True
            
            return False
        except Exception as e:
            logger.debug(f"Ошибка проверки Pyrogram service: {e}")
            return False
    
    async def _check_raw_api(self, message: Message) -> bool:
        """Проверка через Raw API Telegram (наиболее точный метод)"""
        try:
            # Получаем raw сообщение
            raw_messages = await self.client.invoke(
                functions.messages.GetMessages(
                    id=[types.InputMessageID(id=message.id)]
                )
            )
            
            if not raw_messages or not raw_messages.messages:
                return False
            
            raw_msg = raw_messages.messages[0]
            
            # Проверяем action в service message
            if hasattr(raw_msg, 'action') and raw_msg.action:
                action_type = type(raw_msg.action).__name__.lower()
                
                # Известные типы действий для подарков
                gift_actions = [
                    'messageactionstargift',
                    'messageactiongift', 
                    'messageactionuniquegift',
                    'messageactiongiftpremium'
                ]
                
                if any(gift_action in action_type for gift_action in gift_actions):
                    return True
            
            # Проверяем media
            if hasattr(raw_msg, 'media') and raw_msg.media:
                media_type = type(raw_msg.media).__name__.lower()
                if 'gift' in media_type:
                    return True
            
            return False
        
        except Exception as e:
            logger.debug(f"Ошибка проверки Raw API: {e}")
            return False
    
    def _check_text_indicators(self, message: Message) -> bool:
        """Резервная проверка по текстовым индикаторам"""
        if not message.text:
            return False
        
        text_lower = message.text.lower()
        
        # Точные индикаторы подарков
        gift_indicators = [
            "🎁",
            "sent you a gift",
            "отправил вам подарок", 
            "star gift",
            "unique gift"
        ]
        
        return any(indicator in text_lower for indicator in gift_indicators)
    
    async def extract_gift_info(self, message: Message) -> Dict[str, Any]:
        """
        Извлекает детальную информацию о подарке
        
        Args:
            message: Сообщение с подарком
            
        Returns:
            Словарь с информацией о подарке
        """
        
        # Базовая информация
        gift_info = {
            "message_id": message.id,
            "sender_id": message.from_user.id if message.from_user else None,
            "sender_username": message.from_user.username if message.from_user else None,
            "sender_name": self._get_sender_name(message),
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.value if message.chat.type else None,
            "date": message.date.isoformat() if message.date else None,
            "gift_type": "unknown",
            "gift_details": {}
        }
        
        # Извлекаем детали через Raw API
        try:
            await self._extract_raw_gift_details(message, gift_info)
        except Exception as e:
            logger.warning(f"Не удалось извлечь детали подарка: {e}")
            gift_info["gift_type"] = "detected_basic"
        
        return gift_info
    
    def _get_sender_name(self, message: Message) -> str:
        """Получает полное имя отправителя"""
        if not message.from_user:
            return "Неизвестный отправитель"
        
        name_parts = []
        if message.from_user.first_name:
            name_parts.append(message.from_user.first_name)
        if message.from_user.last_name:
            name_parts.append(message.from_user.last_name)
        
        return " ".join(name_parts) if name_parts else "Без имени"
    
    async def _extract_raw_gift_details(self, message: Message, gift_info: Dict[str, Any]):
        """Извлекает детали подарка через Raw API"""
        
        raw_messages = await self.client.invoke(
            functions.messages.GetMessages(
                id=[types.InputMessageID(id=message.id)]
            )
        )
        
        if not raw_messages or not raw_messages.messages:
            return
        
        raw_msg = raw_messages.messages[0]
        
        # Анализируем action
        if hasattr(raw_msg, 'action') and raw_msg.action:
            action = raw_msg.action
            gift_info["gift_type"] = type(action).__name__
            
            # Извлекаем объект подарка
            gift_obj = None
            if hasattr(action, 'gift'):
                gift_obj = action.gift
            elif hasattr(action, 'star_gift'):
                gift_obj = action.star_gift
            elif hasattr(action, 'unique_gift'):
                gift_obj = action.unique_gift
            
            if gift_obj:
                gift_info["gift_details"] = self._parse_gift_object(gift_obj)
        
        # Анализируем media (если подарок в media)
        elif hasattr(raw_msg, 'media') and raw_msg.media:
            media = raw_msg.media
            gift_info["gift_type"] = type(media).__name__
            
            if hasattr(media, 'gift'):
                gift_info["gift_details"] = self._parse_gift_object(media.gift)
    
    def _parse_gift_object(self, gift_obj) -> Dict[str, Any]:
        """
        Парсит объект подарка и извлекает все доступные атрибуты
        
        Args:
            gift_obj: Объект подарка из Raw API
            
        Returns:
            Словарь с атрибутами подарка
        """
        details = {}
        
        # Полный список возможных атрибутов подарков
        possible_attrs = [
            # Основные атрибуты
            'id', 'stars', 'price', 'title', 'description',
            
            # Количество и доступность
            'total_amount', 'remaining_amount', 'sold_amount',
            'availability_remains', 'availability_total',
            
            # Статусы
            'is_limited', 'is_sold_out', 'is_unique', 'is_exclusive',
            'limited', 'sold_out', 'unique', 'exclusive',
            
            # Конвертация и улучшение
            'convert_stars', 'upgrade_price', 'upgrade_stars',
            'conversion_rate', 'refund_amount',
            
            # Дополнительная информация
            'sticker', 'animation', 'pattern', 'backdrop',
            'model', 'symbol', 'first_sale_date', 'last_sale_date',
            
            # Метаданные
            'currency', 'provider', 'gift_code', 'serial_number'
        ]
        
        # Извлекаем все доступные атрибуты
        for attr in possible_attrs:
            if hasattr(gift_obj, attr):
                value = getattr(gift_obj, attr)
                if value is not None:
                    # Конвертируем сложные объекты в строки
                    if hasattr(value, '__dict__'):
                        details[attr] = str(value)
                    else:
                        details[attr] = value
        
        return details
    
    async def send_gift_response(self, original_message: Message, gift_info: Dict[str, Any]):
        """
        Отправляет ответ с информацией о подарке
        
        Args:
            original_message: Оригинальное сообщение с подарком
            gift_info: Извлеченная информация о подарке
        """
        
        response_text = self._format_gift_response(gift_info)
        
        # Отправляем с повторными попытками
        for attempt in range(config.MAX_RETRIES):
            try:
                await self.client.send_message(
                    chat_id=original_message.chat.id,
                    text=response_text,
                    reply_to_message_id=original_message.id,
                    parse_mode="HTML" if config.USE_HTML_FORMATTING else None,
                    disable_web_page_preview=config.DISABLE_WEB_PAGE_PREVIEW
                )
                
                self.stats["responses_sent"] += 1
                logger.info(f"Ответ отправлен (попытка {attempt + 1})")
                return
                
            except FloodWait as e:
                logger.warning(f"FloodWait при отправке ответа: {e.value}s")
                await asyncio.sleep(e.value)
                
            except RPCError as e:
                logger.error(f"Ошибка отправки ответа (попытка {attempt + 1}): {e}")
                if attempt < config.MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Неожиданная ошибка при отправке: {e}")
                break
        
        self.stats["errors"] += 1
        logger.error("Не удалось отправить ответ после всех попыток")
    
    def _format_gift_response(self, gift_info: Dict[str, Any]) -> str:
        """
        Форматирует профессиональный ответ с информацией о подарке
        
        Args:
            gift_info: Информация о подарке
            
        Returns:
            Отформатированное сообщение
        """
        
        lines = ["🎁 <b>TELEGRAM GIFT DETECTED</b>\n"]
        
        # Информация об отправителе
        if gift_info.get('sender_username'):
            lines.append(f"👤 <b>Отправитель:</b> @{gift_info['sender_username']}")
        
        lines.append(f"📛 <b>Имя:</b> {gift_info.get('sender_name', 'Неизвестно')}")
        lines.append(f"🆔 <b>User ID:</b> <code>{gift_info.get('sender_id', 'N/A')}</code>")
        
        # Информация о сообщении
        lines.append(f"📨 <b>Message ID:</b> <code>{gift_info.get('message_id', 'N/A')}</code>")
        if gift_info.get('date'):
            lines.append(f"🕐 <b>Время:</b> {gift_info['date']}")
        
        # Тип подарка
        lines.append(f"🎯 <b>Тип подарка:</b> <code>{gift_info.get('gift_type', 'Unknown')}</code>")
        
        # Детали подарка
        gift_details = gift_info.get('gift_details', {})
        if gift_details:
            lines.append("\n🔍 <b>ДЕТАЛИ ПОДАРКА:</b>")
            
            # ID подарка
            if gift_details.get('id'):
                lines.append(f"🆔 <b>Gift ID:</b> <code>{gift_details['id']}</code>")
            
            # Цена
            if gift_details.get('stars'):
                lines.append(f"⭐ <b>Цена:</b> {gift_details['stars']} Telegram Stars")
            elif gift_details.get('price'):
                lines.append(f"💰 <b>Цена:</b> {gift_details['price']} ⭐")
            
            # Название
            if gift_details.get('title'):
                lines.append(f"📛 <b>Название:</b> {gift_details['title']}")
            
            # Количество и доступность
            if gift_details.get('total_amount'):
                lines.append(f"📦 <b>Всего выпущено:</b> {gift_details['total_amount']:,}")
            
            if gift_details.get('remaining_amount'):
                lines.append(f"📦 <b>Осталось:</b> {gift_details['remaining_amount']:,}")
            
            # Статусы
            status_indicators = []
            if gift_details.get('is_limited') or gift_details.get('limited'):
                status_indicators.append("🔒 Ограниченный")
            if gift_details.get('is_unique') or gift_details.get('unique'):
                status_indicators.append("💎 Уникальный")
            if gift_details.get('is_sold_out') or gift_details.get('sold_out'):
                status_indicators.append("❌ Распродан")
            if gift_details.get('is_exclusive') or gift_details.get('exclusive'):
                status_indicators.append("👑 Эксклюзивный")
            
            if status_indicators:
                lines.append(f"🏷 <b>Статус:</b> {' • '.join(status_indicators)}")
            
            # Конвертация и улучшение
            if gift_details.get('convert_stars'):
                lines.append(f"💫 <b>Конвертация:</b> {gift_details['convert_stars']} ⭐")
            
            if gift_details.get('upgrade_price'):
                lines.append(f"⬆️ <b>Улучшение:</b> {gift_details['upgrade_price']} ⭐")
            
            # Дополнительная информация
            if gift_details.get('serial_number'):
                lines.append(f"🔢 <b>Серийный номер:</b> {gift_details['serial_number']}")
        
        # Подпись
        lines.append(f"\n🤖 <i>Professional Gift Detector v1.0</i>")
        if config.SHOW_STATS_IN_RESPONSE:
            lines.append(f"📊 <i>Подарков обработано: {self.stats['gifts_detected']}</i>")
        
        return "\n".join(lines)
    
    async def start(self):
        """Запуск детектора"""
        try:
            await self.client.start()
            me = await self.client.get_me()
            
            logger.info("=" * 60)
            logger.info("🎁 TELEGRAM GIFT DETECTOR - PROFESSIONAL EDITION")
            logger.info("=" * 60)
            logger.info(f"✅ Авторизован как: @{me.username} ({me.first_name})")
            logger.info(f"🆔 User ID: {me.id}")
            logger.info(f"📱 Номер телефона: {me.phone_number}")
            logger.info("🎯 Статус: Ожидание подарков...")
            logger.info("=" * 60)
            
        except AuthKeyUnregistered:
            logger.error("❌ Ошибка авторизации: недействительный ключ сессии")
            raise
        except UserDeactivated:
            logger.error("❌ Аккаунт деактивирован")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            raise
    
    async def stop(self):
        """Остановка детектора"""
        try:
            await self.client.stop()
            
            # Финальная статистика
            uptime = datetime.now() - self.stats["start_time"]
            logger.info("=" * 60)
            logger.info("📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
            logger.info(f"🎁 Подарков обнаружено: {self.stats['gifts_detected']}")
            logger.info(f"💬 Ответов отправлено: {self.stats['responses_sent']}")
            logger.info(f"❌ Ошибок: {self.stats['errors']}")
            logger.info(f"⏱ Время работы: {uptime}")
            logger.info("🛑 Gift Detector остановлен")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Ошибка при остановке: {e}")


async def main():
    """Главная функция запуска"""
    
    # Валидация конфигурации
    is_valid, errors = config.validate()
    if not is_valid:
        print("❌ ОШИБКА КОНФИГУРАЦИИ!")
        for error in errors:
            print(f"  {error}")
        print("🔗 Получите данные на: https://my.telegram.org/apps")
        return
    
    # Показываем конфигурацию
    config.print_config()
    
    detector = TelegramGiftDetector()
    
    try:
        await detector.start()
        
        print("\n🚀 Gift Detector запущен и готов к работе!")
        print("🎁 Отправьте себе подарок для тестирования")
        print("📊 Логи сохраняются в gift_detector.log")
        print("⌨️  Нажмите Ctrl+C для остановки\n")
        
        # Основной цикл работы
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("👋 Получен сигнал остановки от пользователя")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        await detector.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Программа завершена пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        exit(1)