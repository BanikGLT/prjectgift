"""
Telegram Gift Detector - Полный функционал обнаружения подарков
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
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
        """Запуск детектора подарков"""
        try:
            # Попытка импорта Pyrogram (может не быть установлен)
            try:
                from pyrogram import Client, filters
                from pyrogram.types import Message
            except ImportError:
                logger.warning("Pyrogram не установлен. Работаем в режиме имитации.")
                await self._simulate_mode()
                return
            
            self.gift_callback = gift_callback
            
            # Создание клиента Pyrogram
            self.client = Client(
                name=self.session_name,
                api_id=int(self.api_id),
                api_hash=self.api_hash,
                phone_number=self.phone_number
            )
            
            # Регистрация обработчиков
            @self.client.on_message()
            async def message_handler(client, message: Message):
                await self._process_message(message)
            
            # Запуск клиента
            await self.client.start()
            self.is_running = True
            logger.info("Telegram Gift Detector запущен успешно!")
            
            # Ожидание остановки
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Ошибка запуска детектора: {e}")
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
        """Обработка сообщений для поиска подарков"""
        try:
            gift_info = None
            
            # Метод 1: Проверка service messages
            if hasattr(message, 'service') and message.service:
                gift_info = await self._extract_from_service_message(message)
            
            # Метод 2: Анализ Raw API данных
            if not gift_info and hasattr(message, 'raw'):
                gift_info = await self._extract_from_raw_data(message.raw)
            
            # Метод 3: Текстовый анализ
            if not gift_info and message.text:
                gift_info = await self._extract_from_text(message)
            
            # Если подарок найден, отправляем уведомление
            if gift_info and self.gift_callback:
                await self.gift_callback(gift_info)
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
    
    async def _extract_from_service_message(self, message) -> Optional[Dict[str, Any]]:
        """Извлечение информации из service message"""
        try:
            if hasattr(message.service, 'gift'):
                gift = message.service.gift
                return {
                    "id": getattr(gift, 'id', 'unknown'),
                    "type": getattr(gift, 'type', 'Unknown Gift'),
                    "price": f"{getattr(gift, 'star_count', 0)} stars",
                    "quantity": f"{getattr(gift, 'remaining_count', 0)}/{getattr(gift, 'total_count', 0)}",
                    "status": "limited" if getattr(gift, 'limited', False) else "regular",
                    "detected_at": datetime.now().isoformat(),
                    "sender": message.from_user.username if message.from_user else "Unknown",
                    "chat": message.chat.title if message.chat else "Unknown",
                    "detection_method": "service_message"
                }
        except Exception as e:
            logger.error(f"Ошибка извлечения из service message: {e}")
        return None
    
    async def _extract_from_raw_data(self, raw_data) -> Optional[Dict[str, Any]]:
        """Извлечение информации из Raw API данных"""
        try:
            # Поиск gift-related полей в raw данных
            raw_str = str(raw_data)
            
            if 'gift' in raw_str.lower() or 'star' in raw_str.lower():
                # Парсинг raw данных для извлечения информации о подарке
                gift_data = {
                    "id": self._extract_field(raw_str, 'id'),
                    "type": self._extract_field(raw_str, 'type', 'Star Gift'),
                    "price": self._extract_field(raw_str, 'star_count', '0') + ' stars',
                    "quantity": f"{self._extract_field(raw_str, 'remaining_count', '0')}/{self._extract_field(raw_str, 'total_count', '0')}",
                    "status": "limited" if 'limited' in raw_str.lower() else "regular",
                    "detected_at": datetime.now().isoformat(),
                    "sender": self._extract_field(raw_str, 'username', 'Unknown'),
                    "chat": self._extract_field(raw_str, 'title', 'Unknown'),
                    "detection_method": "raw_api"
                }
                return gift_data
        except Exception as e:
            logger.error(f"Ошибка извлечения из raw данных: {e}")
        return None
    
    async def _extract_from_text(self, message) -> Optional[Dict[str, Any]]:
        """Извлечение информации из текста сообщения"""
        try:
            text = message.text.lower()
            
            # Поиск ключевых слов подарков
            gift_keywords = ['gift', 'подарок', 'star', 'звезда', 'premium', 'unique']
            
            if any(keyword in text for keyword in gift_keywords):
                return {
                    "id": f"text_detected_{datetime.now().timestamp()}",
                    "type": "Text Detected Gift",
                    "price": self._extract_price_from_text(text),
                    "quantity": "unknown",
                    "status": "detected_in_text",
                    "detected_at": datetime.now().isoformat(),
                    "sender": message.from_user.username if message.from_user else "Unknown",
                    "chat": message.chat.title if message.chat else "Unknown",
                    "detection_method": "text_analysis",
                    "original_text": message.text
                }
        except Exception as e:
            logger.error(f"Ошибка анализа текста: {e}")
        return None
    
    def _extract_field(self, text: str, field: str, default: str = "unknown") -> str:
        """Извлечение поля из текста"""
        import re
        pattern = rf'{field}["\s]*[:=]["\s]*([^",\s]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else default
    
    def _extract_price_from_text(self, text: str) -> str:
        """Извлечение цены из текста"""
        import re
        # Поиск чисел со словом "star" или "звезд"
        pattern = r'(\d+)\s*(star|звезд|stars)'
        match = re.search(pattern, text, re.IGNORECASE)
        return f"{match.group(1)} stars" if match else "unknown price"

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