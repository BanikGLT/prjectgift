"""
Telegram Gift Detector - Configuration File
Файл конфигурации для профессионального детектора подарков
"""

import os
from typing import Optional

class Config:
    """Класс конфигурации детектора подарков"""
    
    # =============================================================================
    # ОСНОВНЫЕ НАСТРОЙКИ TELEGRAM API (ОБЯЗАТЕЛЬНО)
    # =============================================================================
    
    # Получите эти данные на https://my.telegram.org/apps
    API_ID: int = int(os.getenv('API_ID', 12345678))
    API_HASH: str = os.getenv('API_HASH', 'your_api_hash_here')
    PHONE_NUMBER: str = os.getenv('PHONE_NUMBER', '+1234567890')
    
    # =============================================================================
    # НАСТРОЙКИ СЕССИИ
    # =============================================================================
    
    SESSION_NAME: str = os.getenv('SESSION_NAME', 'gift_detector_pro')
    
    # =============================================================================
    # НАСТРОЙКИ ЛОГИРОВАНИЯ
    # =============================================================================
    
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: str = os.getenv('LOG_FILE', 'gift_detector.log')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # =============================================================================
    # НАСТРОЙКИ ПРОИЗВОДИТЕЛЬНОСТИ
    # =============================================================================
    
    # Задержка между ответами (предотвращение флуда)
    RESPONSE_DELAY: float = float(os.getenv('RESPONSE_DELAY', 0.5))
    
    # Максимальное количество попыток отправки ответа
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', 3))
    
    # Размер кэша обработанных сообщений
    CACHE_SIZE: int = int(os.getenv('CACHE_SIZE', 1000))
    
    # =============================================================================
    # НАСТРОЙКИ ДЕТЕКЦИИ
    # =============================================================================
    
    # Включить детекцию через Pyrogram service messages
    ENABLE_PYROGRAM_DETECTION: bool = os.getenv('ENABLE_PYROGRAM_DETECTION', 'true').lower() == 'true'
    
    # Включить детекцию через Raw API (рекомендуется)
    ENABLE_RAW_API_DETECTION: bool = os.getenv('ENABLE_RAW_API_DETECTION', 'true').lower() == 'true'
    
    # Включить резервную детекцию по тексту
    ENABLE_TEXT_DETECTION: bool = os.getenv('ENABLE_TEXT_DETECTION', 'true').lower() == 'true'
    
    # =============================================================================
    # НАСТРОЙКИ ОТВЕТОВ
    # =============================================================================
    
    # Включить HTML форматирование в ответах
    USE_HTML_FORMATTING: bool = os.getenv('USE_HTML_FORMATTING', 'true').lower() == 'true'
    
    # Отключить предварительный просмотр ссылок
    DISABLE_WEB_PAGE_PREVIEW: bool = os.getenv('DISABLE_WEB_PAGE_PREVIEW', 'true').lower() == 'true'
    
    # Показывать статистику в ответах
    SHOW_STATS_IN_RESPONSE: bool = os.getenv('SHOW_STATS_IN_RESPONSE', 'true').lower() == 'true'
    
    # =============================================================================
    # ФИЛЬТРЫ И ОГРАНИЧЕНИЯ
    # =============================================================================
    
    # Список ID пользователей для игнорирования (через запятую)
    IGNORED_USERS: list = [
        int(x.strip()) for x in os.getenv('IGNORED_USERS', '').split(',') 
        if x.strip().isdigit()
    ]
    
    # Список ID чатов для игнорирования (через запятую)
    IGNORED_CHATS: list = [
        int(x.strip()) for x in os.getenv('IGNORED_CHATS', '').split(',') 
        if x.strip().isdigit()
    ]
    
    # Минимальный интервал между ответами одному пользователю (секунды)
    MIN_RESPONSE_INTERVAL: int = int(os.getenv('MIN_RESPONSE_INTERVAL', 5))
    
    # =============================================================================
    # ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
    # =============================================================================
    
    # Сохранять детальные логи подарков в JSON
    SAVE_GIFT_LOGS: bool = os.getenv('SAVE_GIFT_LOGS', 'false').lower() == 'true'
    
    # Файл для сохранения логов подарков
    GIFT_LOGS_FILE: str = os.getenv('GIFT_LOGS_FILE', 'gifts_log.json')
    
    # Показывать статистику каждые N секунд (0 = отключено)
    STATS_INTERVAL: int = int(os.getenv('STATS_INTERVAL', 300))
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Валидация конфигурации
        
        Returns:
            tuple: (is_valid, errors_list)
        """
        errors = []
        
        # Проверяем обязательные параметры
        if cls.API_ID == 12345678:
            errors.append("❌ API_ID не настроен")
        
        if cls.API_HASH == 'your_api_hash_here':
            errors.append("❌ API_HASH не настроен")
        
        if cls.PHONE_NUMBER == '+1234567890':
            errors.append("❌ PHONE_NUMBER не настроен")
        
        # Проверяем типы данных
        if not isinstance(cls.API_ID, int) or cls.API_ID <= 0:
            errors.append("❌ API_ID должен быть положительным числом")
        
        if not isinstance(cls.API_HASH, str) or len(cls.API_HASH) < 10:
            errors.append("❌ API_HASH должен быть строкой длиной минимум 10 символов")
        
        if not isinstance(cls.PHONE_NUMBER, str) or not cls.PHONE_NUMBER.startswith('+'):
            errors.append("❌ PHONE_NUMBER должен начинаться с '+'")
        
        # Проверяем диапазоны значений
        if not 0.1 <= cls.RESPONSE_DELAY <= 10:
            errors.append("❌ RESPONSE_DELAY должен быть от 0.1 до 10 секунд")
        
        if not 1 <= cls.MAX_RETRIES <= 10:
            errors.append("❌ MAX_RETRIES должен быть от 1 до 10")
        
        if not 100 <= cls.CACHE_SIZE <= 10000:
            errors.append("❌ CACHE_SIZE должен быть от 100 до 10000")
        
        return len(errors) == 0, errors
    
    @classmethod
    def print_config(cls):
        """Выводит текущую конфигурацию (без секретных данных)"""
        print("=" * 60)
        print("🔧 КОНФИГУРАЦИЯ GIFT DETECTOR")
        print("=" * 60)
        print(f"📱 API ID: {cls.API_ID}")
        print(f"🔐 API Hash: {'*' * len(cls.API_HASH)}")
        print(f"📞 Phone: {cls.PHONE_NUMBER[:3]}***{cls.PHONE_NUMBER[-4:]}")
        print(f"💾 Session: {cls.SESSION_NAME}")
        print(f"📊 Log Level: {cls.LOG_LEVEL}")
        print(f"⏱️  Response Delay: {cls.RESPONSE_DELAY}s")
        print(f"🔄 Max Retries: {cls.MAX_RETRIES}")
        print(f"📦 Cache Size: {cls.CACHE_SIZE}")
        print(f"🎯 Detections: Pyrogram={cls.ENABLE_PYROGRAM_DETECTION}, "
              f"Raw={cls.ENABLE_RAW_API_DETECTION}, Text={cls.ENABLE_TEXT_DETECTION}")
        print(f"🚫 Ignored Users: {len(cls.IGNORED_USERS)}")
        print(f"🚫 Ignored Chats: {len(cls.IGNORED_CHATS)}")
        print("=" * 60)

# Создаем экземпляр конфигурации
config = Config()

# Валидация при импорте
is_valid, errors = config.validate()
if not is_valid:
    print("❌ ОШИБКИ КОНФИГУРАЦИИ:")
    for error in errors:
        print(f"  {error}")
    print("\n📝 Исправьте ошибки перед запуском!")
    print("🔗 Получите API данные: https://my.telegram.org/apps")

# Экспорт для обратной совместимости
API_ID = config.API_ID
API_HASH = config.API_HASH
PHONE_NUMBER = config.PHONE_NUMBER
SESSION_NAME = config.SESSION_NAME
LOG_LEVEL = config.LOG_LEVEL
RESPONSE_DELAY = config.RESPONSE_DELAY
MAX_RETRIES = config.MAX_RETRIES