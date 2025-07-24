from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import logging
from datetime import datetime
import asyncio

app = FastAPI()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные состояния
detector_status = {
    "running": False,
    "status": "Неактивен",
    "gifts_found": 0,
    "uptime": "0",
    "start_time": None,
    "history": []
}

auth_session = {
    "client": None,
    "config": None,
    "awaiting_sms": False,
    "awaiting_password": False
}

# gift_history удален - теперь используется detector_status["gifts_history"]

# Функция для запуска детектора подарков
async def start_gift_detector(client):
    """ДЕТЕКТОР ВХОДЯЩИХ ПОДАРКОВ В ЛИЧНЫЕ СООБЩЕНИЯ"""
    logger.info("🎁 Запуск детектора ВХОДЯЩИХ подарков в ЛС...")
    logger.info("🎯 Цель: Детектировать когда МНЕ присылают подарки и отвечать отправителю")
    
    # Получаем информацию о себе (владельце бота)
    me = await client.get_me()
    my_user_id = me.id
    logger.info(f"👤 Мой ID: {my_user_id} (@{me.username})")
    
    @client.on_message()
    async def handle_incoming_messages(client, message):
        """Обрабатывает ВСЕ входящие сообщения для поиска подарков"""
        try:
            # Проверяем что это ЛИЧНОЕ сообщение (не группа)
            if not message.chat or message.chat.type != "private":
                return  # Игнорируем групповые чаты
            
            # Проверяем что сообщение НЕ от меня (входящее)
            if not message.from_user or message.from_user.id == my_user_id:
                return  # Игнорируем свои сообщения
            
            sender_id = message.from_user.id
            sender_username = message.from_user.username or "N/A"
            
            logger.info(f"📨 ВХОДЯЩЕЕ ЛС от @{sender_username} (ID: {sender_id})")
            logger.info(f"📝 Текст: {getattr(message, 'text', 'N/A')}")
            
            # ДЕТЕКТИРУЕМ ПОДАРКИ В СООБЩЕНИИ
            gift_detected = await detect_gift_in_message(message)
            
            if gift_detected:
                logger.info(f"🎁 ПОДАРОК ОБНАРУЖЕН в сообщении от @{sender_username}!")
                
                # Сохраняем в историю
                if "gifts_history" not in detector_status:
                    detector_status["gifts_history"] = []
                
                detector_status["gifts_history"].append({
                    "gift_info": gift_detected,
                    "timestamp": datetime.now().isoformat(),
                    "message_id": message.message_id,
                    "sender_id": sender_id,
                    "sender_username": sender_username
                })
                
                detector_status["gifts_found"] = detector_status.get("gifts_found", 0) + 1
                logger.info(f"📊 Всего подарков получено: {detector_status['gifts_found']}")
                
                # ОТВЕЧАЕМ ОТПРАВИТЕЛЮ
                await send_gift_thank_you_response(client, message, gift_detected)
            
        except Exception as e:
            logger.error(f"Ошибка в handle_incoming_messages: {e}")
    
    async def detect_gift_in_message(message):
        """Детектирует подарки в сообщении - ВСЕ возможные способы"""
        try:
            logger.info("🔍 Анализируем сообщение на наличие подарков...")
            
            # МЕТОД 1: Service Message (самый надежный для подарков)
            if hasattr(message, 'service') and message.service:
                service_type = type(message.service).__name__
                logger.info(f"🔧 Service Message: {service_type}")
                
                # Проверяем типы связанные с подарками
                gift_service_types = ['MessageServiceStarGift', 'MessageServiceGiftPremium', 'MessageServiceGift']
                if any(gift_type in service_type for gift_type in gift_service_types):
                    logger.info(f"🎁 ПОДАРОК найден в Service Message!")
                    
                    return {
                        "type": "service_gift",
                        "source": "service_message",
                        "details": {
                            "service_type": service_type,
                            "service_data": str(message.service),
                            "gift_type": "Service Message Gift"
                        }
                    }
            
            # МЕТОД 2: Action (MessageAction для подарков)
            if hasattr(message, 'action') and message.action:
                action_type = type(message.action).__name__
                logger.info(f"⚡ Action: {action_type}")
                
                if 'Gift' in action_type or 'Star' in action_type:
                    logger.info(f"🎁 ПОДАРОК найден в Action!")
                    
                    # Извлекаем детальную информацию о подарке
                    gift_details = await extract_gift_details_from_action(message.action)
                    
                    return {
                        "type": "action_gift",
                        "source": "message_action",
                        "details": gift_details
                    }
            
            # МЕТОД 3: Media (для анимированных подарков)
            if hasattr(message, 'media') and message.media:
                media_type = type(message.media).__name__
                logger.info(f"🖼️ Media: {media_type}")
                
                if 'Gift' in media_type or 'Star' in media_type:
                    logger.info(f"🎁 ПОДАРОК найден в Media!")
                    
                    return {
                        "type": "media_gift",
                        "source": "message_media",
                        "details": {
                            "media_type": media_type,
                            "media_data": str(message.media),
                            "gift_type": "Media Gift"
                        }
                    }
            
            # МЕТОД 4: Текстовые паттерны (уведомления о подарках)
            if hasattr(message, 'text') and message.text:
                text = message.text.lower()
                
                # Паттерны подарков в тексте
                gift_patterns = [
                    'подарил', 'gift', 'star', 'звезд', 'подарок',
                    'коллекционный', 'лимитированный', 'редкий'
                ]
                
                found_patterns = [pattern for pattern in gift_patterns if pattern in text]
                if found_patterns:
                    logger.info(f"🎁 ПОДАРОЧНЫЕ ПАТТЕРНЫ найдены: {found_patterns}")
                    
                    return {
                        "type": "text_gift",
                        "source": "text_patterns",
                        "details": {
                            "text": message.text,
                            "patterns_found": found_patterns,
                            "gift_type": "Text Pattern Gift"
                        }
                    }
            
            # МЕТОД 5: Проверяем все атрибуты сообщения на наличие gift/star
            message_attrs = dir(message)
            gift_attrs = [attr for attr in message_attrs if 'gift' in attr.lower() or 'star' in attr.lower()]
            
            if gift_attrs:
                logger.info(f"🎁 ПОДАРОЧНЫЕ АТРИБУТЫ найдены: {gift_attrs}")
                
                gift_data = {}
                for attr in gift_attrs:
                    try:
                        value = getattr(message, attr)
                        if value:
                            gift_data[attr] = str(value)
                    except:
                        pass
                
                if gift_data:
                    return {
                        "type": "attribute_gift",
                        "source": "message_attributes",
                        "details": {
                            "gift_attributes": gift_data,
                            "gift_type": "Message Attribute Gift"
                        }
                    }
            
            return None  # Подарок не найден
            
        except Exception as e:
            logger.error(f"Ошибка в detect_gift_in_message: {e}")
            return None
    
    async def extract_gift_details_from_action(action):
        """Извлекает детальную информацию о подарке из action"""
        try:
            details = {
                "action_type": type(action).__name__,
                "gift_type": "Action Star Gift"
            }
            
            # Пытаемся извлечь все возможные поля подарка
            gift_fields = [
                'id', 'stars', 'limited', 'sold_out', 'convert_stars',
                'first_sale_date', 'last_sale_date', 'total_count',
                'remaining_count', 'model', 'backdrop', 'symbol',
                'can_upgrade', 'can_transfer', 'rarity'
            ]
            
            for field in gift_fields:
                if hasattr(action, field):
                    value = getattr(action, field)
                    details[field] = value
                    logger.info(f"  📊 {field}: {value}")
                elif hasattr(action, 'gift') and hasattr(action.gift, field):
                    value = getattr(action.gift, field)
                    details[field] = value
                    logger.info(f"  📊 gift.{field}: {value}")
            
            return details
            
        except Exception as e:
            logger.error(f"Ошибка извлечения деталей подарка: {e}")
            return {"action_type": str(type(action).__name__), "gift_type": "Action Gift"}
    
    async def send_gift_thank_you_response(client, message, gift_info):
        """Отправляет благодарность отправителю подарка"""
        try:
            details = gift_info['details']
            
            # Формируем красивый ответ
            response_text = f"""🎁 <b>СПАСИБО ЗА ПОДАРОК!</b>

⭐ <b>Тип подарка:</b> {details.get('gift_type', 'Unknown')}
🔍 <b>Источник:</b> {gift_info['source']}
🆔 <b>ID:</b> {details.get('id', 'N/A')}
⭐ <b>Звезды:</b> {details.get('stars', 'N/A')}
🏆 <b>Редкий:</b> {'Да' if details.get('limited') else 'Нет'}
🏠 <b>Модель:</b> {details.get('model', 'N/A')}
🖼️ <b>Фон:</b> {details.get('backdrop', 'N/A')}
🔣 <b>Символ:</b> {details.get('symbol', 'N/A')}

⏰ <b>Получено:</b> {datetime.now().strftime('%H:%M:%S')}

🌟 <b>Большое спасибо за подарок!</b> 🌟

<i>Это автоматический ответ от детектора подарков</i>"""

            # Отправляем ответ отправителю
            await client.send_message(
                chat_id=message.from_user.id,
                text=response_text,
                parse_mode="HTML"
            )
            
            logger.info(f"✅ Отправлена благодарность за подарок пользователю @{message.from_user.username}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки благодарности: {e}")
    
    logger.info("✅ Детектор ВХОДЯЩИХ подарков в ЛС запущен!")
    logger.info("🎯 Готов детектировать подарки и отвечать отправителям!")

async def check_for_gifts(message):
    """Проверяет сообщение на наличие STAR GIFTS согласно Telegram API"""
    
    logger.info("🔍 НАЧИНАЕМ ПОИСК STAR GIFTS (Telegram API)...")
    
    # 1. Проверяем action поле (основной способ для Star Gifts)
    if hasattr(message, 'action') and message.action:
        action_type = str(type(message.action).__name__)
        logger.info(f"🎬 Action detected: {action_type}")
        
        # Ищем MessageActionStarGift или подобные
        if 'star' in action_type.lower() and 'gift' in action_type.lower():
            logger.info(f"⭐ STAR GIFT ACTION найден: {action_type}")
            return await extract_star_gift_from_action(message.action, action_type)
        
        if 'gift' in action_type.lower():
            logger.info(f"🎁 GIFT ACTION найден: {action_type}")
            return await extract_star_gift_from_action(message.action, action_type)
    
    # 2. Проверяем media на предмет Star Gift
    if hasattr(message, 'media') and message.media:
        media_type = str(type(message.media).__name__)
        logger.info(f"📺 Media detected: {media_type}")
        
        # Проверяем MessageMediaStarGift
        if 'star' in media_type.lower() and 'gift' in media_type.lower():
            logger.info(f"⭐ STAR GIFT MEDIA найден: {media_type}")
            return await extract_star_gift_from_media(message.media, media_type)
        
        # Проверяем на подарочные документы/анимации
        if hasattr(message.media, 'document'):
            doc = message.media.document
            if hasattr(doc, 'attributes'):
                for attr in doc.attributes:
                    attr_type = str(type(attr).__name__)
                    if 'gift' in attr_type.lower():
                        logger.info(f"🎁 Gift attribute найден: {attr_type}")
                        return {
                            "type": "star_gift",
                            "source": "document_attribute",
                            "details": await extract_gift_from_document(doc, attr)
                        }
    
    # 3. Проверяем service messages (fallback)
    if hasattr(message, 'service') and message.service:
        service_type = str(type(message.service).__name__)
        logger.info(f"🔧 Service message: {service_type}")
        
        # MessageServiceStarGift или подобные
        if 'star' in service_type.lower() or 'gift' in service_type.lower():
            logger.info(f"⭐ STAR GIFT SERVICE найден: {service_type}")
            return await extract_star_gift_from_service(message.service, service_type)
    
    # 4. Проверяем текст на паттерны Star Gift
    if hasattr(message, 'text') and message.text:
        text = message.text.lower()
        star_gift_patterns = ['star gift', 'подарок', 'звезд', 'stars', '⭐', '🎁']
        
        found_patterns = [p for p in star_gift_patterns if p in text]
        if found_patterns:
            logger.info(f"📝 Star Gift паттерны в тексте: {found_patterns}")
            # Дополнительная проверка - может быть это уведомление о подарке
            if any(word in text for word in ['получил', 'отправил', 'подарил']):
                logger.info("🎁 Возможное уведомление о Star Gift")
                return {
                    "type": "star_gift",
                    "source": "text_notification",
                    "details": {
                        "gift_type": "Text Notification",
                        "text": message.text,
                        "patterns": found_patterns
                    }
                }
    
    logger.info("❌ Star Gift НЕ найден")
    return None

async def extract_star_gift_from_action(action, action_type):
    """Извлекает Star Gift из action поля"""
    try:
        details = {
            "gift_type": "Star Gift from Action",
            "action_type": action_type,
            "raw_data": str(action)
        }
        
        # Ищем специфичные поля Star Gift
        if hasattr(action, 'gift'):
            gift = action.gift
            details["gift_object"] = str(gift)
            
            # ПОЛНАЯ StarGift структура согласно API
            star_gift_fields = [
                'id',                    # ID подарка
                'stars',                 # Стоимость в звездах
                'limited',               # Лимитированный ли
                'sold_out',              # Распродан ли
                'convert_stars',         # Звезды для конвертации
                'first_sale_date',       # Дата первой продажи
                'last_sale_date',        # Дата последней продажи
                'total_count',           # Общее количество
                'remaining_count',       # Оставшееся количество
                'availability_remains',  # Доступность
                'availability_total',    # Общая доступность
                'transfer_star_count',   # Звезды для передачи
                'upgrade_star_count',    # Звезды для улучшения
                'model',                 # 3D модель
                'backdrop',              # Фон
                'symbol',                # Символ
                'pattern',               # Паттерн
                'center_icon',           # Центральная иконка
                'sticker',               # Связанный стикер
                'can_upgrade',           # Можно ли улучшить
                'can_transfer',          # Можно ли передать
                'is_name_color_default', # Цвет названия по умолчанию
                'rarity',                # Редкость
                'type'                   # Тип подарка
            ]
            
            for field in star_gift_fields:
                if hasattr(gift, field):
                    value = getattr(gift, field)
                    details[field] = value
                    logger.info(f"  📊 {field}: {value}")
            
            # Определяем тип подарка
            if details.get('limited'):
                if details.get('remaining_count', 0) == 0:
                    details['gift_category'] = "🔥 РЕДКИЙ (РАСПРОДАН)"
                else:
                    remaining = details.get('remaining_count', 0)
                    total = details.get('total_count', 0)
                    details['gift_category'] = f"⭐ РЕДКИЙ ({remaining}/{total})"
            else:
                details['gift_category'] = "🎁 ОБЫЧНЫЙ"
            
            if details.get('can_upgrade'):
                details['gift_category'] += " + УЛУЧШАЕМЫЙ"
            if details.get('can_transfer'):
                details['gift_category'] += " + ПЕРЕДАВАЕМЫЙ"
        
        return {
            "type": "star_gift",
            "source": "action",
            "details": details
        }
    except Exception as e:
        logger.error(f"Ошибка извлечения Star Gift из action: {e}")
        return {
            "type": "star_gift",
            "source": "action",
            "details": {"gift_type": "Star Gift from Action", "raw_data": str(action)}
        }

async def extract_star_gift_from_media(media, media_type):
    """Извлекает Star Gift из media поля"""
    try:
        details = {
            "gift_type": "Star Gift from Media",
            "media_type": media_type,
            "raw_data": str(media)
        }
        
        if hasattr(media, 'gift'):
            details["gift_data"] = str(media.gift)
        
        return {
            "type": "star_gift",
            "source": "media",
            "details": details
        }
    except Exception as e:
        logger.error(f"Ошибка извлечения Star Gift из media: {e}")
        return {
            "type": "star_gift",
            "source": "media",
            "details": {"gift_type": "Star Gift from Media", "raw_data": str(media)}
        }

async def extract_star_gift_from_service(service, service_type):
    """Извлекает Star Gift из service поля"""
    try:
        details = {
            "gift_type": "Star Gift from Service",
            "service_type": service_type,
            "raw_data": str(service)
        }
        
        # Извлекаем все доступные атрибуты
        for attr in dir(service):
            if not attr.startswith('_'):
                try:
                    value = getattr(service, attr)
                    if not callable(value):
                        details[attr] = str(value)
                except:
                    pass
        
        return {
            "type": "star_gift",
            "source": "service",
            "details": details
        }
    except Exception as e:
        logger.error(f"Ошибка извлечения Star Gift из service: {e}")
        return {
            "type": "star_gift",
            "source": "service", 
            "details": {"gift_type": "Star Gift from Service", "raw_data": str(service)}
        }

async def extract_gift_from_document(document, attribute):
    """Извлекает подарок из документа"""
    return {
        "gift_type": "Gift from Document",
        "document_id": getattr(document, 'id', 'unknown'),
        "attribute_type": str(type(attribute).__name__),
        "attribute_data": str(attribute)
    }

async def extract_star_gift_info(service):
    """Извлекает детальную информацию о Star Gift"""
    try:
        details = {
            "gift_type": "Star Gift",
            "raw_data": str(service)
        }
        
        # Пытаемся извлечь специфичные поля
        if hasattr(service, 'gift'):
            gift = service.gift
            if hasattr(gift, 'stars'):
                details["stars"] = gift.stars
            if hasattr(gift, 'id'):
                details["gift_id"] = gift.id
            if hasattr(gift, 'limited'):
                details["limited"] = gift.limited
            if hasattr(gift, 'sold_out'):
                details["sold_out"] = gift.sold_out
                
        return details
    except Exception as e:
        logger.error(f"Ошибка извлечения Star Gift info: {e}")
        return {"gift_type": "Star Gift", "raw_data": str(service)}

# Удалены функции для других типов подарков - фокус только на Star Gifts

async def send_gift_response(client, original_message, gift_info):
    """Отправляет ответ с информацией о STAR GIFT"""
    
    try:
        details = gift_info['details']
        
        # Формируем красивый детальный ответ
        response_text = f"""⭐ <b>STAR GIFT ПОЛУЧЕН!</b>

🎁 <b>Категория:</b> {details.get('gift_category', 'Неизвестно')}
⭐ <b>Стоимость:</b> {details.get('stars', 'N/A')} звезд
🆔 <b>ID подарка:</b> {details.get('id', 'N/A')}

📊 <b>РЕДКОСТЬ:</b>
🏆 <b>Лимитированный:</b> {'Да' if details.get('limited') else 'Нет'}
📈 <b>Остаток:</b> {details.get('remaining_count', 'N/A')}/{details.get('total_count', 'N/A')}
🔥 <b>Распродан:</b> {'Да' if details.get('sold_out') else 'Нет'}

✨ <b>ВОЗМОЖНОСТИ:</b>
🔄 <b>Можно улучшить:</b> {'Да' if details.get('can_upgrade') else 'Нет'}
📤 <b>Можно передать:</b> {'Да' if details.get('can_transfer') else 'Нет'}
⭐ <b>Звезды для передачи:</b> {details.get('transfer_star_count', 'N/A')}
🌟 <b>Звезды для улучшения:</b> {details.get('upgrade_star_count', 'N/A')}

🎨 <b>ДИЗАЙН:</b>
🏠 <b>Модель:</b> {details.get('model', 'N/A')}
🖼️ <b>Фон:</b> {details.get('backdrop', 'N/A')}
🔣 <b>Символ:</b> {details.get('symbol', 'N/A')}
🎭 <b>Паттерн:</b> {details.get('pattern', 'N/A')}

📅 <b>ДАТЫ:</b>
🚀 <b>Первая продажа:</b> {details.get('first_sale_date', 'N/A')}
🏁 <b>Последняя продажа:</b> {details.get('last_sale_date', 'N/A')}

🆔 <b>ID сообщения:</b> {original_message.message_id}
⏰ <b>Время получения:</b> {datetime.now().strftime('%H:%M:%S')}

🌟 <b>СПАСИБО ЗА КОЛЛЕКЦИОННЫЙ STAR GIFT!</b> 🌟"""

        # Отправляем ответ отправителю в личные сообщения
        if original_message.from_user:
            try:
                await client.send_message(
                    chat_id=original_message.from_user.id,
                    text=response_text,
                    parse_mode="HTML"
                )
                logger.info(f"✅ Отправлен детальный ответ о STAR GIFT в ЛС пользователю {original_message.from_user.id}")
            except Exception as dm_error:
                logger.warning(f"Не удалось отправить в ЛС: {dm_error}")
                # Fallback: отправляем в тот же чат
                if original_message.chat:
                    await client.send_message(
                        chat_id=original_message.chat.id,
                        text=response_text,
                        parse_mode="HTML",
                        reply_to_message_id=original_message.message_id
                    )
                    logger.info(f"📨 Отправлен детальный ответ о STAR GIFT в чат {original_message.chat.id}")
        
    except Exception as e:
        logger.error(f"Ошибка отправки ответа: {e}")

class TelegramConfig(BaseModel):
    api_id: str
    api_hash: str
    phone_number: str

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Gift Detector</title>
        <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .form-group { margin: 15px 0; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; background: #007bff; color: white; }
        .btn:hover { background: #0056b3; }
        .danger { background: #dc3545; }
        .danger:hover { background: #c82333; }
        #auth-fields { background: #f0f8ff; border: 2px solid #007bff; border-radius: 10px; padding: 20px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎁 Telegram Gift Detector</h1>
            
            <div class="form-group">
                <label>API ID:</label>
                <input type="text" id="api_id" placeholder="Ваш API ID">
            </div>
            <div class="form-group">
                <label>API Hash:</label>
                <input type="text" id="api_hash" placeholder="Ваш API Hash">
            </div>
            <div class="form-group">
                <label>Номер телефона:</label>
                <input type="text" id="phone_number" placeholder="+7XXXXXXXXXX">
            </div>
            
            <div id="auth-fields">
                <h3>📱 Поля авторизации:</h3>
                <div class="form-group">
                    <label>SMS код:</label>
                    <input type="text" id="sms_code" placeholder="12345" maxlength="5">
                    <small>Введите код из SMS</small>
                </div>
                <div class="form-group">
                    <label>Пароль 2FA (если включен):</label>
                    <input type="password" id="two_fa_password" placeholder="Ваш пароль 2FA">
                    <small>Оставьте пустым если 2FA не включен</small>
                </div>
                <button class="btn" onclick="completeAuth()">✅ Подтвердить авторизацию</button>
            </div>
            
                    <button class="btn" onclick="startDetector()">🚀 Запустить детектор</button>
        <button class="btn danger" onclick="stopDetector()">⏹️ Остановить детектор</button>
        <button class="btn" onclick="checkAuthStatus()">🔍 Проверить авторизацию</button>
        <button class="btn" onclick="viewHistory()">📜 История подарков</button>
        <button class="btn" onclick="simulateGift()">🎁 Тестовый подарок</button>
        <button class="btn" onclick="viewSessions()">💾 Сессии</button>
        <button class="btn" onclick="debugInfo()">🐛 Отладка</button>
            
            <div style="margin-top: 20px;">
                <h3>Статус: <span id="status">Неактивен</span></h3>
                <p>Подарков найдено: <span id="gifts-count">0</span></p>
            </div>
        </div>

        <script>
        function startDetector() {
            const config = {
                api_id: document.getElementById('api_id').value,
                api_hash: document.getElementById('api_hash').value,
                phone_number: document.getElementById('phone_number').value
            };
            
            if (!config.api_id || !config.api_hash || !config.phone_number) {
                alert('Заполните все поля!');
                return;
            }
            
            console.log('Отправляем конфиг:', config);
            
            fetch('/detector/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(async response => {
                console.log('Response status:', response.status);
                console.log('Response ok:', response.ok);
                
                if (!response.ok) {
                    // Читаем ошибку как текст
                    const errorText = await response.text();
                    console.error('Error response:', errorText);
                    
                    try {
                        const errorData = JSON.parse(errorText);
                        throw new Error(errorData.detail || errorText);
                    } catch (parseError) {
                        throw new Error(errorText || `HTTP ${response.status}`);
                    }
                }
                
                return response.json();
            })
            .then(data => {
                console.log('Success data:', data);
                alert('Ответ сервера: ' + data.message);
                
                if (data.status === 'sms_required') {
                    console.log('SMS отправлен, показываем поля авторизации');
                }
            })
            .catch(error => {
                console.error('Полная ошибка:', error);
                alert('Ошибка: ' + error.message);
            });
        }
        
        function completeAuth() {
            const authData = {
                sms_code: document.getElementById('sms_code').value,
                password: document.getElementById('two_fa_password').value
            };
            
            if (!authData.sms_code) {
                alert('Введите SMS код!');
                return;
            }
            
            console.log('Отправляем auth data:', authData);
            
            fetch('/detector/complete_auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(authData)
            })
            .then(async response => {
                console.log('Auth response status:', response.status);
                
                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('Auth error response:', errorText);
                    
                    try {
                        const errorData = JSON.parse(errorText);
                        throw new Error(errorData.detail || errorText);
                    } catch (parseError) {
                        throw new Error(errorText || `HTTP ${response.status}`);
                    }
                }
                
                return response.json();
            })
            .then(data => {
                console.log('Auth success data:', data);
                alert('Результат авторизации: ' + data.message);
                
                if (data.status === 'success') {
                    console.log('Авторизация успешна, детектор запущен');
                }
            })
            .catch(error => {
                console.error('Auth полная ошибка:', error);
                alert('Ошибка авторизации: ' + error.message);
            });
        }
        
        function stopDetector() {
            fetch('/detector/stop', {method: 'POST'})
            .then(response => response.json())
            .then(data => alert(data.message))
            .catch(error => alert('Ошибка: ' + error.message));
        }
        
                    function refreshStatus() {
                fetch('/detector/status')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('status').textContent = data.status;
                        document.getElementById('gifts-count').textContent = data.gifts_found || 0;
                    })
                    .catch(error => console.error('Error:', error));
            }
            
            function checkAuthStatus() {
                fetch('/detector/auth_status')
                    .then(response => response.json())
                    .then(data => {
                        alert('Состояние авторизации:\\n' + JSON.stringify(data, null, 2));
                        console.log('Auth Status:', data);
                    })
                    .catch(error => alert('Ошибка: ' + error.message));
            }
            
            function viewHistory() {
                fetch('/detector/history')
                    .then(response => response.json())
                    .then(data => {
                        let historyText = `Найдено подарков: ${data.total_count}\\n\\n`;
                        data.gifts.forEach((gift, index) => {
                            historyText += `${index + 1}. ${gift.gift_info.details.gift_category} (${gift.timestamp})\\n`;
                        });
                        alert(historyText || 'История пуста');
                    })
                    .catch(error => alert('Ошибка: ' + error.message));
            }
            
            function simulateGift() {
                fetch('/detector/simulate-gift', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        refreshStatus(); // Обновляем счетчик
                    })
                    .catch(error => alert('Ошибка: ' + error.message));
            }
            
            function viewSessions() {
                fetch('/detector/sessions')
                    .then(response => response.json())
                    .then(data => {
                        let sessionsText = 'Сохраненные сессии:\\n\\n';
                        if (data.sessions.length === 0) {
                            sessionsText += 'Нет сохраненных сессий';
                        } else {
                            data.sessions.forEach(session => {
                                sessionsText += `📁 ${session.name} (${session.size} bytes, ${session.modified})\\n`;
                            });
                        }
                        alert(sessionsText);
                    })
                    .catch(error => alert('Ошибка: ' + error.message));
            }
            
            function debugInfo() {
                fetch('/detector/debug')
                    .then(response => response.json())
                    .then(data => {
                        const debugText = `ОТЛАДОЧНАЯ ИНФОРМАЦИЯ:\\n\\n` +
                            `Detector Status: ${JSON.stringify(data.detector_status, null, 2)}\\n\\n` +
                            `Auth Session Keys: ${data.auth_session_keys.join(', ')}\\n` +
                            `Has Client: ${data.has_client}\\n` +
                            `Awaiting SMS: ${data.awaiting_sms}\\n` +
                            `Phone Number: ${data.phone_number}`;
                        
                        console.log('Debug Info:', data);
                        alert(debugText);
                    })
                    .catch(error => {
                        console.error('Debug error:', error);
                        alert('Ошибка получения отладочной информации: ' + error.message);
                    });
            }
            
            setInterval(refreshStatus, 5000);
            refreshStatus();
        </script>
    </body>
    </html>
    """

@app.get("/detector/status")
async def get_status():
    return detector_status

@app.get("/detector/debug")
async def get_debug_info():
    """Отладочная информация"""
    return {
        "detector_status": detector_status,
        "auth_session_keys": list(auth_session.keys()),
        "has_client": "client" in auth_session,
        "awaiting_sms": auth_session.get("awaiting_sms", False),
        "phone_number": auth_session.get("phone_number", "N/A")
    }

@app.post("/detector/start")
async def start_detector(config: TelegramConfig):
    logger.info(f"🚀 Получен запрос на запуск детектора: {config}")
    
    if detector_status["running"]:
        logger.warning("Детектор уже запущен")
        raise HTTPException(status_code=400, detail="Детектор уже запущен")
    
    # Валидация входных данных
    logger.info(f"Валидируем данные: api_id={config.api_id}, api_hash={config.api_hash[:8]}..., phone={config.phone_number}")
    
    if not config.api_id or not config.api_hash or not config.phone_number:
        logger.error("Не все поля заполнены")
        raise HTTPException(status_code=400, detail="Все поля обязательны для заполнения")
    
    if not config.api_id.isdigit():
        raise HTTPException(status_code=400, detail="API ID должен содержать только цифры")
        
    if len(config.api_hash) < 32:
        raise HTTPException(status_code=400, detail="API Hash слишком короткий (должен быть 32+ символов)")
        
    if not config.phone_number.startswith('+'):
        raise HTTPException(status_code=400, detail="Номер телефона должен начинаться с +")
        
    logger.info(f"Валидация пройдена: API ID длина={len(config.api_id)}, API Hash длина={len(config.api_hash)}, Phone={config.phone_number}")
    
    try:
        logger.info("Начинаем процесс авторизации...")
        
        try:
            from pyrogram import Client
            from pyrogram.errors import SessionPasswordNeeded
            logger.info("Pyrogram импортирован успешно")
        except ImportError as e:
            logger.error(f"Ошибка импорта Pyrogram: {e}")
            raise HTTPException(status_code=500, detail=f"Pyrogram не установлен: {str(e)}")
        
        # Создаем папку для сессий
        import os
        import tempfile
        
        sessions_dir = os.path.join(tempfile.gettempdir(), "telegram_sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir, mode=0o755)
            logger.info(f"Создана папка сессий: {sessions_dir}")
        
        session_name = f"gift_detector_{config.phone_number.replace('+', '').replace(' ', '')}"
        session_file = os.path.join(sessions_dir, session_name)
        logger.info(f"Файл сессии: {session_file}")
        
        # Проверяем права записи
        try:
            test_file = os.path.join(sessions_dir, "test_write")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            logger.info("Права записи проверены успешно")
        except Exception as e:
            logger.error(f"Нет прав записи: {e}")
            session_file = ":memory:"
            sessions_dir = None
            logger.info("Используем сессию в памяти")
        
        # Создаем клиент
        logger.info("Создаем Pyrogram клиент...")
        if session_file == ":memory:":
            client = Client(
                name=session_name,
                api_id=int(config.api_id),
                api_hash=config.api_hash,
                phone_number=config.phone_number,
                in_memory=True
            )
        else:
            client = Client(
                name=session_file,
                api_id=int(config.api_id),
                api_hash=config.api_hash,
                phone_number=config.phone_number,
                workdir=sessions_dir
            )
        
        # Сохраняем в auth_session
        auth_session["client"] = client
        auth_session["config"] = config
        
        # Подключаемся
        logger.info("Подключаемся к Telegram...")
        await client.connect()
        logger.info("Подключение успешно")
        
        # Проверяем существующую авторизацию
        try:
            me = await client.get_me()
            if me:
                logger.info(f"Найдена действующая сессия для {me.first_name}")
                auth_session["awaiting_sms"] = False
                detector_status["running"] = True
                detector_status["status"] = "Активен"
                detector_status["start_time"] = datetime.now()
                
                # Запускаем детектор сразу
                await start_gift_detector(client)
                
                return {"message": "Сессия найдена, детектор запущен!", "status": "success"}
        except Exception as e:
            logger.info(f"Сохраненная сессия недействительна: {e}")
        
        # Отправляем SMS
        logger.info(f"Отправляем SMS код на {config.phone_number}...")
        sent_code = await client.send_code(config.phone_number)
        
        auth_session["awaiting_sms"] = True
        auth_session["sent_code"] = sent_code
        auth_session["phone_number"] = config.phone_number
        
        logger.info(f"SMS код успешно отправлен на {config.phone_number}")
        return {
            "message": f"SMS код отправлен на {config.phone_number}. Введите его в поле ниже.", 
            "status": "sms_required"
        }
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        if auth_session.get("client"):
            try:
                await auth_session["client"].disconnect()
            except:
                pass
            auth_session["client"] = None
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.post("/detector/complete_auth")
async def complete_auth(auth_data: dict):
    logger.info(f"📱 Получен запрос на подтверждение авторизации: {auth_data}")
    
    if not auth_session.get("client"):
        logger.error("Клиент не найден в auth_session")
        raise HTTPException(status_code=400, detail="Клиент не найден. Сначала нажмите 'Запустить детектор'")
        
    logger.info("Начинаем подтверждение авторизации...")
    
    try:
        from pyrogram.errors import SessionPasswordNeeded, BadRequest
        
        client = auth_session["client"]
        sms_code = auth_data.get("sms_code")
        password = auth_data.get("password", "")
        
        if not sms_code:
            raise HTTPException(status_code=400, detail="SMS код обязателен")
        
        logger.info(f"Попытка авторизации с SMS кодом: {sms_code}")
        
        try:
            # Пытаемся войти с SMS кодом (правильный порядок параметров)
            await client.sign_in(auth_session["config"].phone_number, auth_session["sent_code"].phone_code_hash, sms_code)
            logger.info("Авторизация по SMS успешна!")
            
        except SessionPasswordNeeded:
            logger.info("Требуется пароль 2FA")
            if not password:
                return {
                    "message": "Требуется пароль 2FA. Введите пароль и повторите.", 
                    "status": "password_required"
                }
            
            await client.check_password(password)
            logger.info("Авторизация по 2FA успешна!")
        
        # Авторизация успешна - запускаем детектор
        auth_session["awaiting_sms"] = False
        detector_status["running"] = True
        detector_status["status"] = "Активен"
        detector_status["start_time"] = datetime.now()
        
        # Запускаем обработчик сообщений
        await start_gift_detector(client)
        
        logger.info("Детектор запущен успешно!")
        return {
            "message": "✅ Авторизация успешна! Детектор запущен и готов к работе.", 
            "status": "success"
        }
        
    except BadRequest as e:
        logger.error(f"Неверный SMS код: {e}")
        return {
            "message": f"Неверный SMS код: {str(e)}", 
            "status": "error"
        }
    except Exception as e:
        logger.error(f"Ошибка авторизации: {e}")
        return {
            "message": f"Ошибка авторизации: {str(e)}", 
            "status": "error"
        }

@app.post("/detector/stop")
async def stop_detector():
    global detector_status
    detector_status["running"] = False
    detector_status["status"] = "Остановлен"
    detector_status["stop_time"] = datetime.now()
    
    # Отключаем клиент если он есть
    if "client" in auth_session and auth_session["client"]:
        try:
            await auth_session["client"].stop()
            logger.info("Клиент Pyrogram остановлен")
        except Exception as e:
            logger.warning(f"Ошибка при остановке клиента: {e}")
    
    return {"message": "Детектор остановлен", "status": "success"}

@app.get("/detector/history")
async def get_gift_history():
    """Получить историю найденных подарков"""
    return {
        "gifts": detector_status.get("gifts_history", []),
        "total_count": detector_status.get("gifts_found", 0)
    }

@app.get("/detector/auth_status")
async def get_auth_status():
    """Проверить состояние авторизации"""
    return {
        "auth_session": {
            "awaiting_sms": auth_session.get("awaiting_sms", False),
            "phone_number": auth_session.get("phone_number", ""),
            "has_client": "client" in auth_session,
            "has_sent_code": "sent_code" in auth_session
        },
        "detector_status": detector_status
    }

@app.get("/detector/sessions")
async def list_sessions():
    """Список сохраненных сессий"""
    try:
        if not os.path.exists(sessions_dir):
            return {"sessions": []}
        
        sessions = []
        for file in os.listdir(sessions_dir):
            if file.endswith('.session'):
                session_name = file.replace('.session', '')
                file_path = os.path.join(sessions_dir, file)
                stat = os.stat(file_path)
                sessions.append({
                    "name": session_name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Ошибка получения списка сессий: {e}")
        return {"sessions": [], "error": str(e)}

@app.delete("/detector/sessions/{session_name}")
async def delete_session(session_name: str):
    """Удалить сохраненную сессию"""
    try:
        session_file = os.path.join(sessions_dir, f"{session_name}.session")
        if os.path.exists(session_file):
            os.remove(session_file)
            return {"message": f"Сессия {session_name} удалена", "status": "success"}
        else:
            return {"message": f"Сессия {session_name} не найдена", "status": "error"}
    except Exception as e:
        logger.error(f"Ошибка удаления сессии {session_name}: {e}")
        return {"message": f"Ошибка удаления сессии: {e}", "status": "error"}

@app.post("/detector/simulate-gift")
async def simulate_gift():
    """Симуляция получения подарка для тестирования"""
    if not detector_status["running"]:
        return {"message": "Детектор не запущен", "status": "error"}
    
    # Создаем тестовый подарок
    test_gift = {
        "type": "star_gift",
        "source": "simulation",
        "details": {
            "gift_category": "🎁 ТЕСТОВЫЙ ПОДАРОК",
            "stars": 15,
            "id": "test_bear_001",
            "limited": True,
            "remaining_count": 50,
            "total_count": 1000,
            "can_upgrade": True,
            "can_transfer": True,
            "transfer_star_count": 25,
            "upgrade_star_count": 50,
            "model": "bear_3d_model",
            "backdrop": "forest_backdrop",
            "symbol": "🐻",
            "pattern": "golden_pattern"
        }
    }
    
    # Добавляем в историю
    if "gifts_history" not in detector_status:
        detector_status["gifts_history"] = []
    
    detector_status["gifts_history"].append({
        "gift_info": test_gift,
        "timestamp": datetime.now().isoformat(),
        "message_id": "TEST_MSG",
        "chat_id": "TEST_CHAT"
    })
    
    detector_status["gifts_found"] = detector_status.get("gifts_found", 0) + 1
    
    return {"message": "Тестовый подарок добавлен в историю", "status": "success", "gift": test_gift}