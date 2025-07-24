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

gift_history = []

# Функция для запуска детектора подарков
async def start_gift_detector(client):
    """Запускает обработчик сообщений для детекции Star Gifts"""
    
    # Обработчик для ВСЕХ сообщений (включая отправленные)
    @client.on_message()
    async def handle_message(client, message):
        await process_message_for_gifts(client, message)
    
    # Обработчик для RAW updates (МАКСИМАЛЬНО АГРЕССИВНЫЙ)
    @client.on_raw_update()
    async def handle_raw_update(client, update, users, chats):
        try:
            update_name = type(update).__name__
            
            # ЛОГИРУЕМ АБСОЛЮТНО ВСЕ UPDATES
            logger.info(f"🔄 RAW UPDATE: {update_name}")
            
            # Проверяем на подарки в ЛЮБЫХ updates
            if any(keyword in update_name.lower() for keyword in ['gift', 'star', 'present', 'подарок']):
                logger.info(f"⭐ ПОТЕНЦИАЛЬНЫЙ GIFT UPDATE: {update_name}")
                logger.info(f"📄 ПОЛНЫЕ данные update: {str(update)}")
                
                # Пытаемся извлечь информацию о подарке
                gift_info = await extract_gift_from_update(update, update_name)
                if gift_info:
                    logger.info(f"🎁 ПОДАРОК НАЙДЕН В RAW UPDATE!")
                    # Обновляем статистику
                    detector_status["gifts_found"] += 1
                    gift_history.append({
                        "timestamp": datetime.now().isoformat(),
                        "gift_info": gift_info,
                        "source": "raw_update",
                        "update_type": update_name
                    })
            
            # Проверяем на Star Gift в обычных сообщениях
            if hasattr(update, 'message'):
                await process_message_for_gifts(client, update.message)
            
            # Проверяем другие поля update на предмет подарков
            for attr_name in dir(update):
                if not attr_name.startswith('_'):
                    try:
                        attr_value = getattr(update, attr_name)
                        if attr_value and 'gift' in str(attr_value).lower():
                            logger.info(f"🎁 GIFT в атрибуте {attr_name}: {str(attr_value)[:200]}")
                    except:
                        pass
                
        except Exception as e:
            logger.error(f"Ошибка обработки raw update: {e}")
    
    # Дополнительный обработчик для ВСЕХ типов сообщений
    @client.on_message(group=-1)  # Высший приоритет
    async def handle_all_messages(client, message):
        try:
            # Проверяем КАЖДОЕ сообщение на предмет подарков
            message_text = getattr(message, 'text', '') or ''
            message_caption = getattr(message, 'caption', '') or ''
            
            # Ищем ключевые слова в тексте
            full_text = (message_text + ' ' + message_caption).lower()
            gift_keywords = ['star', 'gift', 'подарок', 'звезд', 'stars', '⭐', '🎁', 'мишка', 'bear']
            
            found_keywords = [kw for kw in gift_keywords if kw in full_text]
            if found_keywords:
                logger.info(f"🔍 СООБЩЕНИЕ С GIFT KEYWORDS: {found_keywords}")
                logger.info(f"📝 Текст: {full_text[:200]}")
                logger.info(f"📨 Полное сообщение: {str(message)[:500]}")
                
        except Exception as e:
            logger.error(f"Ошибка в handle_all_messages: {e}")

async def extract_gift_from_update(update, update_name):
    """Извлекает подарок из raw update"""
    try:
        gift_info = {
            "type": "star_gift",
            "source": "raw_update",
            "update_type": update_name,
            "details": {
                "gift_type": f"Gift from {update_name}",
                "raw_data": str(update)
            }
        }
        
        # Ищем специфичные поля подарков
        for attr in dir(update):
            if not attr.startswith('_'):
                try:
                    value = getattr(update, attr)
                    if value and any(keyword in str(value).lower() for keyword in ['gift', 'star', 'подарок']):
                        gift_info["details"][attr] = str(value)
                except:
                    pass
        
        return gift_info
    except Exception as e:
        logger.error(f"Ошибка извлечения подарка из update: {e}")
        return None
    
    async def process_message_for_gifts(client, message):
        try:
            # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ КАЖДОГО СООБЩЕНИЯ
            logger.info(f"📨 ПОЛУЧЕНО СООБЩЕНИЕ:")
            logger.info(f"  - ID: {message.message_id}")
            logger.info(f"  - От: {message.from_user.id if message.from_user else 'unknown'}")
            logger.info(f"  - Чат: {message.chat.id if message.chat else 'unknown'}")
            logger.info(f"  - Тип: {type(message)}")
            logger.info(f"  - Текст: {message.text[:100] if message.text else 'нет текста'}")
            
            # ПРОВЕРЯЕМ ВСЕ АТРИБУТЫ СООБЩЕНИЯ
            logger.info(f"  - Есть service: {hasattr(message, 'service')}")
            if hasattr(message, 'service') and message.service:
                logger.info(f"  - Service type: {type(message.service)}")
                logger.info(f"  - Service name: {type(message.service).__name__}")
                logger.info(f"  - Service data: {str(message.service)[:500]}")
                logger.info(f"  - Service attributes: {[attr for attr in dir(message.service) if not attr.startswith('_')]}")
            
            # ПРОВЕРЯЕМ ДРУГИЕ ВОЗМОЖНЫЕ ПОЛЯ
            logger.info(f"  - Есть media: {hasattr(message, 'media')}")
            logger.info(f"  - Есть action: {hasattr(message, 'action')}")
            logger.info(f"  - Есть gift: {hasattr(message, 'gift')}")
            logger.info(f"  - Есть star_gift: {hasattr(message, 'star_gift')}")
            
            # Проверяем на подарки
            gift_info = await check_for_gifts(message)
            if gift_info:
                logger.info(f"🎁 НАЙДЕН ПОДАРОК: {gift_info}")
                
                # Сохраняем в историю
                gift_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "gift_info": gift_info,
                    "message_id": message.message_id,
                    "from_user": message.from_user.id if message.from_user else None
                })
                
                # Обновляем статистику
                detector_status["gifts_found"] += 1
                
                # Отправляем ответ отправителю
                await send_gift_response(client, message, gift_info)
            else:
                logger.info("❌ Подарок НЕ найден в этом сообщении")
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            logger.error(f"Тип ошибки: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Пытаемся поймать события отправки сообщений
    try:
        from pyrogram import filters
        
        @client.on_message(filters.outgoing)  # Исходящие сообщения
        async def handle_outgoing_messages(client, message):
            try:
                logger.info(f"📤 ИСХОДЯЩЕЕ СООБЩЕНИЕ: {message.message_id}")
                
                # Проверяем исходящие сообщения на предмет отправки подарков
                if hasattr(message, 'media') and message.media:
                    logger.info(f"📺 Исходящее media: {type(message.media).__name__}")
                
                # Проверяем на подарки в исходящих
                gift_info = await check_for_gifts(message)
                if gift_info:
                    logger.info(f"🎁 ПОДАРОК В ИСХОДЯЩЕМ СООБЩЕНИИ!")
                    
            except Exception as e:
                logger.error(f"Ошибка в handle_outgoing_messages: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка создания outgoing handler: {e}")
    
    logger.info("🎁 Детектор подарков активирован и слушает сообщения!")
    logger.info("🔍 Включены обработчики:")
    logger.info("  - 📨 Входящие сообщения")
    logger.info("  - 📤 Исходящие сообщения")  
    logger.info("  - 🔄 Raw updates")
    logger.info("  - 🔍 Keyword scanning")

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
            
            # Поля из StarGift структуры
            for field in ['id', 'stars', 'limited', 'sold_out', 'convert_stars', 'first_sale_date', 'last_sale_date']:
                if hasattr(gift, field):
                    details[field] = getattr(gift, field)
        
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
        # Формируем детальный ответ для Star Gift
        response_text = f"""⭐ <b>STAR GIFT ПОЛУЧЕН!</b>

🎁 <b>Тип:</b> {gift_info['details']['gift_type']}
⭐ <b>Звезды:</b> {gift_info['details'].get('stars', 'N/A')}
🆔 <b>ID подарка:</b> {gift_info['details'].get('gift_id', 'N/A')}
🏆 <b>Лимитированный:</b> {gift_info['details'].get('limited', 'N/A')}
📊 <b>Распродан:</b> {gift_info['details'].get('sold_out', 'N/A')}
🆔 <b>ID сообщения:</b> {original_message.message_id}
⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S')}
📝 <b>Service Type:</b> {gift_info['service_type']}

🌟 <b>СПАСИБО ЗА STAR GIFT!</b> 🌟

<i>Полные данные:</i>
<code>{gift_info['details'].get('raw_data', 'N/A')[:500]}</code>"""

        # Отправляем ответ отправителю в личные сообщения
        if original_message.from_user:
            try:
                await client.send_message(
                    chat_id=original_message.from_user.id,
                    text=response_text,
                    parse_mode="HTML"
                )
                logger.info(f"✅ Отправлен ответ о STAR GIFT в ЛС пользователю {original_message.from_user.id}")
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
                    logger.info(f"📨 Отправлен ответ о STAR GIFT в чат {original_message.chat.id}")
        
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
            
            fetch('/detector/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                alert('Ответ сервера: ' + data.message);
                console.log('Данные:', data);
            })
            .catch(error => {
                alert('Ошибка: ' + error.message);
                console.error('Ошибка:', error);
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
            
            fetch('/detector/complete_auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(authData)
            })
            .then(response => response.json())
            .then(data => {
                alert('Результат авторизации: ' + data.message);
                console.log('Авторизация:', data);
            })
            .catch(error => {
                alert('Ошибка авторизации: ' + error.message);
                console.error('Ошибка:', error);
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
        
        setInterval(refreshStatus, 5000);
        refreshStatus();
        </script>
    </body>
    </html>
    """

@app.get("/detector/status")
async def get_status():
    return detector_status

@app.post("/detector/start")
async def start_detector(config: TelegramConfig):
    if detector_status["running"]:
        raise HTTPException(status_code=400, detail="Детектор уже запущен")
    
    # Валидация входных данных
    if not config.api_id or not config.api_hash or not config.phone_number:
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
    if not auth_session.get("client"):
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
    return {"message": "Детектор остановлен"}