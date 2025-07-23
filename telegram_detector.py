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
        
    async def start(self, gift_callback=None):
        """Запуск детектора подарков с реальной авторизацией"""
        try:
            # Импорт Pyrogram
            from pyrogram import Client, filters
            from pyrogram.types import Message
            from pyrogram.errors import SessionPasswordNeeded
            
            self.gift_callback = gift_callback
            
            # Создание клиента Pyrogram
            self.client = Client(
                name=self.session_name,
                api_id=int(self.api_id),
                api_hash=self.api_hash,
                phone_number=self.phone_number
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
            
            # 🎁 МЕТОД 1: Поиск в service messages (самый точный)
            if message.service:
                gift_info = await self._check_service_message(message)
            
            # 🎁 МЕТОД 2: Поиск gift stickers и gift buttons
            if not gift_info:
                gift_info = await self._check_gift_stickers(message)
            
            # 🎁 МЕТОД 3: Анализ текста сообщения
            if not gift_info and message.text:
                gift_info = await self._check_text_content(message)
            
            # 🎁 МЕТОД 4: Анализ медиа и документов
            if not gift_info:
                gift_info = await self._check_media_content(message)
            
            # Если подарок найден - отправляем информацию отправителю
            if gift_info:
                await self._send_gift_info_to_sender(message, gift_info)
                
                # Уведомляем веб-интерфейс
                if self.gift_callback:
                    await self.gift_callback(gift_info)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    async def _check_service_message(self, message) -> Optional[Dict[str, Any]]:
        """Проверка service messages на наличие подарков"""
        try:
            # Проверяем различные типы service messages
            service_type = str(type(message.service).__name__)
            
            if 'gift' in service_type.lower():
                logger.info(f"🎁 Обнаружен подарок в service message: {service_type}")
                
                gift_info = {
                    "id": f"service_{message.id}",
                    "type": "Telegram Gift",
                    "service_type": service_type,
                    "detected_at": datetime.now().isoformat(),
                    "sender": self._get_sender_info(message),
                    "chat": self._get_chat_info(message),
                    "detection_method": "service_message",
                    "message_id": message.id
                }
                
                # Пытаемся извлечь дополнительную информацию
                if hasattr(message.service, '__dict__'):
                    service_data = message.service.__dict__
                    gift_info.update({
                        "service_data": str(service_data),
                        "price": self._extract_price_from_service(service_data),
                        "quantity": self._extract_quantity_from_service(service_data)
                    })
                
                return gift_info
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки service message: {e}")
        return None
    
    async def _check_gift_stickers(self, message) -> Optional[Dict[str, Any]]:
        """Проверка стикеров и кнопок подарков"""
        try:
            # Проверяем стикеры
            if message.sticker:
                sticker_set = message.sticker.set_name
                if sticker_set and ('gift' in sticker_set.lower() or 'star' in sticker_set.lower()):
                    logger.info(f"🎁 Обнаружен gift sticker: {sticker_set}")
                    return {
                        "id": f"sticker_{message.id}",
                        "type": "Gift Sticker",
                        "sticker_set": sticker_set,
                        "detected_at": datetime.now().isoformat(),
                        "sender": self._get_sender_info(message),
                        "chat": self._get_chat_info(message),
                        "detection_method": "gift_sticker"
                    }
            
            # Проверяем inline кнопки
            if message.reply_markup and hasattr(message.reply_markup, 'inline_keyboard'):
                for row in message.reply_markup.inline_keyboard:
                    for button in row:
                        if button.text and ('gift' in button.text.lower() or '🎁' in button.text):
                            logger.info(f"🎁 Обнаружена gift кнопка: {button.text}")
                            return {
                                "id": f"button_{message.id}",
                                "type": "Gift Button",
                                "button_text": button.text,
                                "detected_at": datetime.now().isoformat(),
                                "sender": self._get_sender_info(message),
                                "chat": self._get_chat_info(message),
                                "detection_method": "gift_button"
                            }
                            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки стикеров: {e}")
        return None
    
    async def _check_text_content(self, message) -> Optional[Dict[str, Any]]:
        """Анализ текста сообщения на наличие подарков"""
        try:
            text = message.text.lower()
            
            # Расширенные ключевые слова для подарков
            gift_patterns = [
                r'🎁.*gift',
                r'star.*gift',
                r'подарок.*звезд',
                r'gift.*star',
                r'premium.*gift',
                r'unique.*gift',
                r'limited.*gift',
                r'collect.*gift',
                r'получить.*подарок',
                r'send.*gift',
                r'отправить.*подарок'
            ]
            
            for pattern in gift_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.info(f"🎁 Обнаружен подарок в тексте: {pattern}")
                    
                    return {
                        "id": f"text_{message.id}",
                        "type": "Text Gift Detection",
                        "pattern_matched": pattern,
                        "price": self._extract_price_from_text(text),
                        "detected_at": datetime.now().isoformat(),
                        "sender": self._get_sender_info(message),
                        "chat": self._get_chat_info(message),
                        "detection_method": "text_analysis",
                        "original_text": message.text[:200] + "..." if len(message.text) > 200 else message.text
                    }
                    
        except Exception as e:
            logger.error(f"❌ Ошибка анализа текста: {e}")
        return None
    
    async def _check_media_content(self, message) -> Optional[Dict[str, Any]]:
        """Проверка медиа контента на наличие подарков"""
        try:
            # Проверяем документы
            if message.document:
                file_name = message.document.file_name or ""
                if 'gift' in file_name.lower():
                    logger.info(f"🎁 Обнаружен gift документ: {file_name}")
                    return {
                        "id": f"doc_{message.id}",
                        "type": "Gift Document",
                        "file_name": file_name,
                        "detected_at": datetime.now().isoformat(),
                        "sender": self._get_sender_info(message),
                        "chat": self._get_chat_info(message),
                        "detection_method": "document_analysis"
                    }
            
            # Проверяем фото с caption
            if message.photo and message.caption:
                caption = message.caption.lower()
                if any(word in caption for word in ['gift', 'подарок', 'star', '🎁']):
                    logger.info(f"🎁 Обнаружен gift в photo caption")
                    return {
                        "id": f"photo_{message.id}",
                        "type": "Gift Photo",
                        "caption": message.caption[:100],
                        "detected_at": datetime.now().isoformat(),
                        "sender": self._get_sender_info(message),
                        "chat": self._get_chat_info(message),
                        "detection_method": "photo_caption"
                    }
                    
        except Exception as e:
            logger.error(f"❌ Ошибка проверки медиа: {e}")
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
        """Форматирование ответа с информацией о подарке"""
        response = f"""
🎁 <b>ОБНАРУЖЕН ПОДАРОК!</b>

📋 <b>Информация:</b>
• ID: <code>{gift_info.get('id', 'N/A')}</code>
• Тип: {gift_info.get('type', 'Unknown')}
• Метод: {gift_info.get('detection_method', 'N/A')}
• Время: {gift_info.get('detected_at', 'N/A')}

💰 <b>Детали:</b>
• Цена: {gift_info.get('price', 'Неизвестно')}
• Количество: {gift_info.get('quantity', 'Неизвестно')}
• Статус: {gift_info.get('status', 'Неизвестно')}

📍 <b>Источник:</b>
• Отправитель: {gift_info.get('sender', 'Неизвестно')}
• Чат: {gift_info.get('chat', 'Неизвестно')}

🤖 <i>Автоматически обнаружено Telegram Gift Detector</i>
        """.strip()
        
        return response
    
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