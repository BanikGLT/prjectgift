"""
Telegram Gift Detector - Реальный детектор с автоответами
"""

import logging
import asyncio
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramGiftDetector:
    def __init__(self, api_id: str, api_hash: str, phone_number: str, session_name: str = "gift_detector"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.session_name = session_name
        self.client = None
        self.is_running = False
        self.gift_callback = None
        
        # Создаем папку для сессий если её нет
        import os
        self.sessions_dir = "sessions"
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)
        
        # Полный путь к файлу сессии
        self.session_file = os.path.join(self.sessions_dir, f"{session_name}.session")
        
    async def start(self, gift_callback=None):
        """Запуск детектора подарков с реальной авторизацией"""
        try:
            # Импорт Pyrogram
            from pyrogram import Client, filters
            from pyrogram.types import Message
            from pyrogram.errors import SessionPasswordNeeded
            
            self.gift_callback = gift_callback
            
            # Создание клиента Pyrogram с сохранением сессии
            self.client = Client(
                name=self.session_file,  # Используем полный путь к файлу сессии
                api_id=int(self.api_id),
                api_hash=self.api_hash,
                phone_number=self.phone_number,
                workdir=self.sessions_dir  # Указываем рабочую директорию для сессий
            )
            
            # Регистрация обработчиков ВСЕХ сообщений
            @self.client.on_message()
            async def message_handler(client, message: Message):
                await self._process_message(message)
            
            # Запуск клиента с интерактивной авторизацией
            logger.info("Запуск Telegram клиента...")
            await self.client.start()
            
            # Получаем информацию о себе
            me = await self.client.get_me()
            logger.info(f"Авторизован как: {me.first_name} (@{me.username})")
            
            self.is_running = True
            logger.info("🎁 Telegram Gift Detector запущен! Мониторим подарки...")
            
            # Бесконечный цикл мониторинга
            while self.is_running:
                await asyncio.sleep(1)
                
        except ImportError:
            logger.error("❌ Pyrogram не установлен! Установите: pip install pyrogram tgcrypto")
            raise Exception("Pyrogram не установлен")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска детектора: {e}")
            raise
    
    async def stop(self):
        """Остановка детектора"""
        self.is_running = False
        if self.client:
            await self.client.stop()
        logger.info("Telegram Gift Detector остановлен")
    
    async def _simulate_mode(self):
        """Режим имитации без Pyrogram"""
        self.is_running = True
        logger.info("Запущен в режиме имитации (Pyrogram не установлен)")
        
        # Имитируем обнаружение подарков каждые 30 секунд
        counter = 1
        while self.is_running:
            await asyncio.sleep(30)
            if self.is_running and self.gift_callback:
                fake_gift = {
                    "id": f"sim_gift_{counter}",
                    "type": "Simulated Star Gift",
                    "price": f"{1000 + counter * 500} stars",
                    "quantity": f"{100 - counter * 10}/1000",
                    "status": "limited",
                    "detected_at": datetime.now().isoformat(),
                    "sender": f"SimUser{counter}",
                    "chat": "Simulation Chat",
                    "serial_number": f"SIM{counter:06d}",
                    "rarity": "rare" if counter % 3 == 0 else "common"
                }
                await self.gift_callback(fake_gift)
                counter += 1
    
    async def _process_message(self, message):
        """Обработка сообщений для поиска подарков и автоответов"""
        try:
            # Пропускаем собственные сообщения
            if message.from_user and message.from_user.is_self:
                return
            
            gift_info = None
            
            # 🎁 ОСНОВНОЙ МЕТОД: Поиск официальных Telegram Gifts в service messages
            if message.service:
                gift_info = await self._check_service_message(message)
            
            # 🎁 ДОПОЛНИТЕЛЬНЫЙ: Поиск упоминаний подарков в тексте (для отладки)
            if not gift_info and message.text and len(message.text) < 500:
                gift_info = await self._check_gift_mentions(message)
            
            # Если подарок найден - отправляем информацию отправителю
            if gift_info:
                await self._send_gift_info_to_sender(message, gift_info)
                
                # Уведомляем веб-интерфейс
                if self.gift_callback:
                    await self.gift_callback(gift_info)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    async def _check_service_message(self, message) -> Optional[Dict[str, Any]]:
        """Проверка service messages на наличие Telegram Gifts"""
        try:
            # Проверяем messageActionStarGift и другие gift service messages
            if hasattr(message, 'service') and message.service:
                service_type = str(type(message.service).__name__)
                
                # Проверяем на Star Gift (основной тип подарков)
                if 'StarGift' in service_type or 'Gift' in service_type:
                    logger.info(f"🎁 Обнаружен Telegram Gift: {service_type}")
                    
                    gift_info = {
                        "id": f"gift_{message.id}_{int(datetime.now().timestamp())}",
                        "type": "Telegram Star Gift",
                        "service_type": service_type,
                        "detected_at": datetime.now().isoformat(),
                        "sender": self._get_sender_info(message),
                        "chat": self._get_chat_info(message),
                        "detection_method": "star_gift_service",
                        "message_id": message.id,
                        "is_private_message": message.chat.type.name == "PRIVATE" if hasattr(message.chat, 'type') else True
                    }
                    
                    # Извлекаем данные о подарке из service message
                    if hasattr(message.service, 'gift'):
                        gift = message.service.gift
                        gift_info.update({
                            "gift_id": getattr(gift, 'id', None),
                            "stars": getattr(gift, 'stars', 0),
                            "convert_stars": getattr(gift, 'convert_stars', 0),
                            "first_sale_date": getattr(gift, 'first_sale_date', None),
                            "last_sale_date": getattr(gift, 'last_sale_date', None),
                            "birthday_months": getattr(gift, 'birthday_months', None),
                            "sold_out": getattr(gift, 'sold_out', False),
                            "limited": getattr(gift, 'limited', False),
                            "total_count": getattr(gift, 'total_count', 0),
                            "remaining_count": getattr(gift, 'remaining_count', 0)
                        })
                        
                        # Формируем читаемую информацию
                        gift_info["price"] = f"{gift_info['stars']} ⭐"
                        if gift_info['limited'] and gift_info['total_count'] > 0:
                            gift_info["availability"] = f"{gift_info['remaining_count']}/{gift_info['total_count']} осталось"
                        else:
                            gift_info["availability"] = "Неограниченно"
                    
                    # Проверяем другие поля service message
                    elif hasattr(message.service, '__dict__'):
                        service_data = message.service.__dict__
                        gift_info.update({
                            "service_data": str(service_data),
                            "price": self._extract_price_from_service(service_data),
                            "quantity": self._extract_quantity_from_service(service_data)
                        })
                    
                    return gift_info
                
                # Проверяем messageActionGiftPremium (подарочная Premium подписка)
                elif 'GiftPremium' in service_type:
                    logger.info(f"🎁 Обнаружен подарок Premium: {service_type}")
                    
                    gift_info = {
                        "id": f"premium_{message.id}_{int(datetime.now().timestamp())}",
                        "type": "Telegram Premium Gift",
                        "service_type": service_type,
                        "detected_at": datetime.now().isoformat(),
                        "sender": self._get_sender_info(message),
                        "chat": self._get_chat_info(message),
                        "detection_method": "premium_gift_service",
                        "message_id": message.id,
                        "is_private_message": message.chat.type.name == "PRIVATE" if hasattr(message.chat, 'type') else True
                    }
                    
                    # Извлекаем данные о Premium подарке
                    if hasattr(message.service, '__dict__'):
                        service_data = message.service.__dict__
                        gift_info.update({
                            "months": service_data.get('months', 0),
                            "currency": service_data.get('currency', 'USD'),
                            "amount": service_data.get('amount', 0),
                            "crypto_currency": service_data.get('crypto_currency', None),
                            "crypto_amount": service_data.get('crypto_amount', None)
                        })
                        
                        gift_info["price"] = f"{gift_info['amount']/100:.2f} {gift_info['currency']}"
                        gift_info["duration"] = f"{gift_info['months']} месяцев Premium"
                    
                    return gift_info
                    
        except Exception as e:
            logger.error(f"❌ Ошибка проверки service message: {e}")
        return None
    
    async def _check_gift_mentions(self, message) -> Optional[Dict[str, Any]]:
        """Поиск упоминаний подарков в тексте (для отладки)"""
        try:
            text = message.text.lower()
            
            # Простые паттерны для отладки
            gift_patterns = [
                'telegram gift',
                'star gift', 
                'подарок звезд',
                'gift received',
                'получен подарок'
            ]
            
            for pattern in gift_patterns:
                if pattern in text:
                    logger.info(f"🎁 Упоминание подарка в тексте: {pattern}")
                    return {
                        "id": f"mention_{message.id}",
                        "type": "Gift Mention",
                        "pattern": pattern,
                        "detected_at": datetime.now().isoformat(),
                        "sender": self._get_sender_info(message),
                        "chat": self._get_chat_info(message),
                        "detection_method": "text_mention",
                        "is_private_message": message.chat.type.name == "PRIVATE" if hasattr(message.chat, 'type') else True,
                        "text_preview": text[:100] + "..." if len(text) > 100 else text
                    }
                    
        except Exception as e:
            logger.error(f"❌ Ошибка поиска упоминаний: {e}")
        return None
    

    
    async def _send_gift_info_to_sender(self, original_message, gift_info):
        """Отправка информации о подарке отправителю"""
        try:
            # Формируем детальную информацию о подарке
            response_text = self._format_gift_response(gift_info)
            
            # Отправляем ответ отправителю в личные сообщения
            if original_message.from_user:
                try:
                    await self.client.send_message(
                        chat_id=original_message.from_user.id,
                        text=response_text,
                        parse_mode="HTML"
                    )
                    logger.info(f"✅ Отправлена информация о подарке пользователю {original_message.from_user.username}")
                except Exception as e:
                    # Если не можем отправить в ЛС, отвечаем в том же чате
                    logger.warning(f"Не удалось отправить в ЛС, отвечаем в чате: {e}")
                    await self.client.send_message(
                        chat_id=original_message.chat.id,
                        text=response_text,
                        reply_to_message_id=original_message.id,
                        parse_mode="HTML"
                    )
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки ответа: {e}")
    
    def _format_gift_response(self, gift_info) -> str:
        """Форматирование ответа с информацией о Telegram Gift"""
        
        # Базовая информация
        response = f"🎁 <b>TELEGRAM GIFT ОБНАРУЖЕН!</b>\n\n"
        response += f"📋 <b>Основная информация:</b>\n"
        response += f"• <b>Тип:</b> {gift_info.get('type', 'Unknown Gift')}\n"
        response += f"• <b>ID:</b> <code>{gift_info.get('id', 'N/A')}</code>\n"
        response += f"• <b>Время:</b> {gift_info.get('detected_at', 'N/A')}\n"

        # Информация о цене и доступности
        if gift_info.get('price'):
            response += f"\n💰 <b>Стоимость:</b>\n"
            response += f"• <b>Цена:</b> {gift_info.get('price')}\n"
            
            if gift_info.get('availability'):
                response += f"• <b>Доступность:</b> {gift_info.get('availability')}\n"
            
            if gift_info.get('convert_stars'):
                response += f"• <b>Конвертация:</b> {gift_info.get('convert_stars')} ⭐\n"

        # Информация об отправителе
        response += f"\n👤 <b>Отправитель:</b> {gift_info.get('sender', 'Неизвестно')}\n"
        
        # Техническая информация
        response += f"\n🔧 <b>Детали:</b>\n"
        response += f"• <b>Метод:</b> {gift_info.get('detection_method', 'N/A')}\n"
        response += f"• <b>Service:</b> <code>{gift_info.get('service_type', 'N/A')}</code>\n"

        response += f"\n🤖 <i>Telegram Gift Detector v2.0</i>"
        
        return response.strip()
    
    def _get_sender_info(self, message) -> str:
        """Получение информации об отправителе"""
        if not message.from_user:
            return "Unknown"
        
        username = f"@{message.from_user.username}" if message.from_user.username else ""
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        
        return f"{full_name} {username}".strip() or f"ID:{message.from_user.id}"
    
    def _get_chat_info(self, message) -> str:
        """Получение информации о чате"""
        if not message.chat:
            return "Unknown"
        
        if message.chat.title:
            return message.chat.title
        elif message.chat.first_name:
            return f"{message.chat.first_name} {message.chat.last_name or ''}".strip()
        else:
            return f"ID:{message.chat.id}"
    
    def _extract_price_from_service(self, service_data) -> str:
        """Извлечение цены из service данных"""
        service_str = str(service_data).lower()
        
        # Поиск различных форматов цены
        patterns = [
            r'star_count["\s]*[:=]["\s]*(\d+)',
            r'price["\s]*[:=]["\s]*(\d+)',
            r'stars["\s]*[:=]["\s]*(\d+)',
            r'(\d+)\s*star'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, service_str)
            if match:
                return f"{match.group(1)} stars"
        
        return "Неизвестно"
    
    def _extract_quantity_from_service(self, service_data) -> str:
        """Извлечение количества из service данных"""
        service_str = str(service_data).lower()
        
        # Поиск информации о количестве
        patterns = [
            r'remaining["\s]*[:=]["\s]*(\d+).*total["\s]*[:=]["\s]*(\d+)',
            r'(\d+)/(\d+)',
            r'left["\s]*[:=]["\s]*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, service_str)
            if match:
                if len(match.groups()) >= 2:
                    return f"{match.group(1)}/{match.group(2)}"
                else:
                    return f"{match.group(1)} left"
        
        return "Неизвестно"
    
    def _extract_price_from_text(self, text: str) -> str:
        """Извлечение цены из текста"""
        # Расширенные паттерны для поиска цены
        patterns = [
            r'(\d+)\s*(star|звезд|stars|⭐)',
            r'price[:\s]*(\d+)',
            r'цена[:\s]*(\d+)',
            r'стоит[:\s]*(\d+)',
            r'costs[:\s]*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)} stars"
        
        return "Неизвестно"

# Глобальная переменная для хранения экземпляра детектора
_detector_instance = None

async def start_telegram_detector(api_id: str, api_hash: str, phone_number: str, gift_callback=None):
    """Запуск Telegram детектора"""
    global _detector_instance
    
    if _detector_instance and _detector_instance.is_running:
        raise Exception("Детектор уже запущен")
    
    _detector_instance = TelegramGiftDetector(api_id, api_hash, phone_number)
    await _detector_instance.start(gift_callback)

async def stop_telegram_detector():
    """Остановка Telegram детектора"""
    global _detector_instance
    
    if _detector_instance:
        await _detector_instance.stop()
        _detector_instance = None

def is_detector_running() -> bool:
    """Проверка статуса детектора"""
    global _detector_instance
    return _detector_instance is not None and _detector_instance.is_running