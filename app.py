from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="🎁 Telegram Gift Detector",
    description="Professional gift detection service for Telegram",
    version="1.0.0"
)

# Глобальные переменные для состояния
detector_status = {
    "running": False,
    "started_at": None,
    "gifts_detected": 0,
    "last_gift": None,
    "error": None
}

gift_history = []

# Временное хранение данных авторизации
auth_session = {
    "client": None,
    "config": None,
    "awaiting_sms": False,
    "awaiting_password": False
}

class TelegramConfig(BaseModel):
    api_id: str
    api_hash: str
    phone_number: str
    session_name: Optional[str] = "gift_detector"

@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎁 Telegram Gift Detector</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); overflow: hidden; }
        .header { background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: white; padding: 30px; text-align: center; }
        .content { padding: 30px; }
        .status-card { background: #f8f9fa; border-radius: 10px; padding: 20px; margin: 20px 0; border-left: 4px solid #28a745; }
        .status-card.inactive { border-left-color: #dc3545; }
        .btn { background: #007bff; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-size: 16px; margin: 5px; transition: all 0.3s; }
        .btn:hover { background: #0056b3; transform: translateY(-2px); }
        .btn.danger { background: #dc3545; }
        .btn.danger:hover { background: #c82333; }
        .config-form { background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .form-group { margin: 15px 0; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; }
        .form-group small { display: block; margin-top: 5px; color: #666; font-size: 12px; }
        #auth-fields { background: #f0f8ff; border: 2px solid #007bff; border-radius: 10px; padding: 20px; margin: 20px 0; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: white; border: 1px solid #eee; border-radius: 10px; padding: 20px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .gift-history { max-height: 300px; overflow-y: auto; background: #f8f9fa; border-radius: 10px; padding: 15px; }
        .gift-item { background: white; margin: 10px 0; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745; }
        </style>
        <script>
        function refreshStatus() {
            fetch('/detector/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status-info').innerHTML = 
                        '<strong>Статус:</strong> ' + (data.running ? '🟢 Активен' : '🔴 Остановлен') + '<br>' +
                        '<strong>Подарков обнаружено:</strong> ' + data.gifts_detected + '<br>' +
                        (data.started_at ? '<strong>Запущен:</strong> ' + new Date(data.started_at).toLocaleString() : '') +
                        (data.error ? '<br><strong>Ошибка:</strong> ' + data.error : '');
                    
                    document.getElementById('status-card').className = 'status-card ' + (data.running ? '' : 'inactive');
                });
        }
        
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
            
            document.getElementById('start-btn').disabled = true;
            document.getElementById('start-btn').textContent = '⏳ Отправка SMS...';
            
            fetch('/detector/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(`HTTP ${response.status}: ${text}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('Ответ сервера:', data);
                
                if (data.status === 'sms_required') {
                    // Показываем поля для авторизации
                    console.log('Показываем поля авторизации');
                    document.getElementById('auth-fields').style.display = 'block';
                    document.getElementById('auth-status').textContent = 'показаны';
                    document.getElementById('start-btn').textContent = '📱 SMS отправлен';
                    document.getElementById('start-btn').disabled = false;
                    alert('SMS код отправлен! Введите его в поле ниже.');
                } else if (data.status === 'success') {
                    alert(data.message);
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('start-btn').textContent = '🚀 Запустить детектор';
                } else {
                    alert(data.message || 'Неизвестный статус: ' + data.status);
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('start-btn').textContent = '🚀 Запустить детектор';
                }
                refreshStatus();
            })
            .catch(error => {
                console.error('Ошибка запуска:', error);
                alert('Ошибка: ' + error.message);
                document.getElementById('start-btn').disabled = false;
                document.getElementById('start-btn').textContent = '🚀 Запустить детектор';
            });
        }
        
        function completeAuth() {
            const sms_code = document.getElementById('sms_code').value;
            const password = document.getElementById('two_fa_password').value;
            
            if (!sms_code) {
                alert('Введите SMS код!');
                return;
            }
            
            fetch('/detector/complete_auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    sms_code: sms_code,
                    password: password
                })
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(`HTTP ${response.status}: ${text}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    alert('✅ Авторизация успешна! Детектор запущен.');
                    document.getElementById('auth-fields').style.display = 'none';
                    document.getElementById('auth-status').textContent = 'скрыты';
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('start-btn').textContent = '🚀 Запустить детектор';
                } else {
                    alert('❌ ' + (data.message || 'Ошибка авторизации'));
                }
                refreshStatus();
            })
            .catch(error => {
                console.error('Ошибка авторизации:', error);
                alert('Ошибка авторизации: ' + error.message);
            });
        }
        
        function stopDetector() {
            fetch('/detector/stop', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                refreshStatus();
            });
        }
        
        function loadSessions() {
            fetch('/detector/sessions')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    const sessionsList = document.getElementById('sessions-list');
                    if (data.sessions.length === 0) {
                        sessionsList.innerHTML = '<p>Сохраненных сессий нет</p>';
                        return;
                    }
                    
                    let html = '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">';
                    html += '<h4>Сохраненные сессии:</h4>';
                    
                    data.sessions.forEach(session => {
                        const date = new Date(session.modified).toLocaleString();
                        html += `
                            <div style="background: white; margin: 10px 0; padding: 15px; border-radius: 6px; border: 1px solid #ddd;">
                                <strong>📱 ${session.phone}</strong><br>
                                <small>Размер: ${(session.size / 1024).toFixed(1)} KB | Изменено: ${date}</small><br>
                                <button class="btn danger" style="margin-top: 10px; font-size: 12px; padding: 5px 10px;" 
                                        onclick="deleteSession('${session.name}')">🗑️ Удалить</button>
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                    sessionsList.innerHTML = html;
                })
                .catch(error => {
                    console.error('Ошибка загрузки сессий:', error);
                    document.getElementById('sessions-list').innerHTML = '<p>Ошибка загрузки сессий: ' + error.message + '</p>';
                });
        }
        
        function deleteSession(sessionName) {
            if (!confirm('Удалить эту сессию? Потребуется повторная авторизация.')) {
                return;
            }
            
            fetch(`/detector/sessions/${sessionName}`, {
                method: 'DELETE'
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(`HTTP ${response.status}: ${text}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                alert(data.message);
                loadSessions(); // Обновляем список
            })
            .catch(error => {
                console.error('Ошибка удаления сессии:', error);
                alert('Ошибка удаления сессии: ' + error.message);
            });
        }
        
        function showAuthFields() {
            // Принудительно показываем поля авторизации для отладки
            console.log('Принудительно показываем поля авторизации');
            document.getElementById('auth-fields').style.display = 'block';
            document.getElementById('auth-status').textContent = 'показаны (принудительно)';
            alert('Поля авторизации показаны принудительно. Используйте для ввода SMS кода.');
        }
        
        setInterval(refreshStatus, 5000);
        window.onload = refreshStatus;
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎁 Telegram Gift Detector</h1>
                <p>Профессиональный детектор подарков в Telegram</p>
            </div>
            
            <div class="content">
                <div id="status-card" class="status-card">
                    <h3>📊 Статус системы</h3>
                    <div id="status-info">Загрузка...</div>
                </div>
                
                <div class="config-form">
                    <h3>⚙️ Конфигурация Telegram</h3>
                    <div id="debug-info" style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 10px 0; border-radius: 5px; font-size: 12px;">
                        <strong>Отладка:</strong> Поля авторизации <span id="auth-status">скрыты</span>
                    </div>
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
                    
                    <!-- Поля для авторизации -->
                    <div id="auth-fields" style="display: none;">
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
                    
                    <button class="btn" onclick="startDetector()" id="start-btn">🚀 Запустить детектор</button>
                    <button class="btn danger" onclick="stopDetector()">⏹️ Остановить детектор</button>
                    <button class="btn" onclick="showAuthFields()" style="background: #ffc107; color: #000;">📱 Показать поля авторизации</button>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number" id="gifts-count">0</div>
                        <div>Подарков найдено</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="uptime">0</div>
                        <div>Время работы</div>
                    </div>
                </div>
                
                <div>
                    <h3>💾 Управление сессиями</h3>
                    <div class="config-form">
                        <button class="btn" onclick="loadSessions()">🔄 Обновить список сессий</button>
                        <div id="sessions-list" style="margin-top: 15px;">
                            <p>Нажмите "Обновить список сессий" для просмотра</p>
                        </div>
                    </div>
                </div>
                
                <div>
                    <h3>📝 История подарков</h3>
                    <div class="gift-history" id="gift-history">
                        <p>История подарков появится здесь...</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "Telegram Gift Detector",
        "uptime": "running"
    }

@app.get("/info")
def get_info():
    return {
        "name": "Telegram Gift Detector",
        "version": "1.0.0",
        "description": "Smart Telegram gift detection service",
        "status": "ready for deployment",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "info": "/info",
            "docs": "/docs"
        }
    }

@app.get("/status")
def get_status():
    return {
        "service": "online",
        "deployment": "successful",
        "ready": True
    }

@app.get("/detector/status")
def get_detector_status():
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
    
    try:
        logger.info("Начинаем процесс авторизации...")
        logger.info(f"API ID: {config.api_id}, Phone: {config.phone_number}")
        
        try:
            from pyrogram import Client
            from pyrogram.errors import SessionPasswordNeeded
            logger.info("Pyrogram импортирован успешно")
        except ImportError as e:
            logger.error(f"Ошибка импорта Pyrogram: {e}")
            raise HTTPException(status_code=500, detail=f"Pyrogram не установлен: {str(e)}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при импорте: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка импорта: {str(e)}")
        
        # Создаем папку для сессий
        import os
        sessions_dir = "sessions"
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)
            logger.info(f"Создана папка сессий: {sessions_dir}")
        
        # Имя сессии на основе номера телефона
        session_name = f"gift_detector_{config.phone_number.replace('+', '').replace(' ', '')}"
        session_file = os.path.join(sessions_dir, session_name)
        logger.info(f"Файл сессии: {session_file}")
        
        # Создаем клиент с сохранением сессии
        logger.info("Создаем Pyrogram клиент...")
        try:
            client = Client(
                name=session_file,
                api_id=int(config.api_id),
                api_hash=config.api_hash,
                phone_number=config.phone_number,
                workdir=sessions_dir
            )
            logger.info("Pyrogram клиент создан успешно")
        except Exception as e:
            logger.error(f"Ошибка создания Pyrogram клиента: {e}")
            raise Exception(f"Ошибка создания клиента: {str(e)}")
        
        # Сохраняем в сессию
        auth_session["client"] = client
        auth_session["config"] = config
        logger.info("Данные сохранены в auth_session")
        
        # Пытаемся подключиться
        logger.info("Подключаемся к Telegram...")
        try:
            await client.connect()
            logger.info("Подключение к Telegram успешно")
        except Exception as e:
            logger.error(f"Ошибка подключения к Telegram: {e}")
            raise Exception(f"Ошибка подключения: {str(e)}")
        
        # Проверяем, авторизован ли уже (есть ли сохраненная сессия)
        logger.info("Проверяем существующую авторизацию...")
        try:
            me = await client.get_me()
            if me:
                logger.info(f"Найдена действующая сессия для {me.first_name}")
                # Уже авторизован, запускаем детектор
                auth_session["awaiting_sms"] = False
                username = f"@{me.username}" if me.username else "без username"
                logger.info(f"Используется сохраненная сессия для {me.first_name} ({username})")
                return await _start_detector_after_auth()
        except Exception as e:
            logger.info(f"Сохраненная сессия недействительна: {e}")
        
        # Нужна новая авторизация, отправляем SMS
        logger.info(f"Отправляем SMS код на {config.phone_number}...")
        try:
            sent_code = await client.send_code(config.phone_number)
            auth_session["awaiting_sms"] = True
            
            logger.info(f"SMS код успешно отправлен на {config.phone_number}")
            return {"message": "SMS код отправлен", "status": "sms_required"}
        except Exception as e:
            logger.error(f"Ошибка отправки SMS: {e}")
            try:
                await client.disconnect()
            except:
                pass
            auth_session["client"] = None
            raise Exception(f"Ошибка отправки SMS: {str(e)}")
            
    except ImportError:
        raise HTTPException(status_code=500, detail="Pyrogram не установлен")
    except Exception as e:
        logger.error(f"Ошибка при отправке SMS: {e}")
        if auth_session["client"]:
            await auth_session["client"].disconnect()
            auth_session["client"] = None
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.post("/detector/complete_auth")
async def complete_auth(auth_data: dict):
    if not auth_session["awaiting_sms"] or not auth_session["client"]:
        raise HTTPException(status_code=400, detail="Авторизация не начата")
    
    try:
        from pyrogram.errors import SessionPasswordNeeded, BadRequest
        
        client = auth_session["client"]
        sms_code = auth_data.get("sms_code")
        password = auth_data.get("password", "")
        
        if not sms_code:
            raise HTTPException(status_code=400, detail="SMS код обязателен")
        
        try:
            # Пытаемся войти с SMS кодом
            await client.sign_in(auth_session["config"].phone_number, sms_code)
            logger.info("Авторизация по SMS коду успешна")
            
        except SessionPasswordNeeded:
            # Нужен пароль 2FA
            if not password:
                raise HTTPException(status_code=400, detail="Требуется пароль 2FA")
            await client.check_password(password)
            logger.info("Авторизация по 2FA успешна")
        
        # Авторизация успешна
        auth_session["awaiting_sms"] = False
        return await _start_detector_after_auth()
        
    except BadRequest as e:
        raise HTTPException(status_code=400, detail=f"Неверный код или пароль: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка авторизации: {e}")
        if auth_session["client"]:
            await auth_session["client"].disconnect()
            auth_session["client"] = None
        raise HTTPException(status_code=500, detail=f"Ошибка авторизации: {str(e)}")

async def _start_detector_after_auth():
    """Запуск детектора после успешной авторизации"""
    try:
        from telegram_detector import TelegramGiftDetector
        
        detector_status["running"] = True
        detector_status["started_at"] = datetime.now().isoformat()
        detector_status["error"] = None
        detector_status["gifts_detected"] = 0
        
        config = auth_session["config"]
        logger.info(f"Детектор запущен для {config.phone_number}")
        
        # Callback для обработки найденных подарков
        async def gift_found_callback(gift_info):
            gift_history.append(gift_info)
            detector_status["gifts_detected"] += 1
            detector_status["last_gift"] = gift_info
            logger.info(f"Обнаружен подарок: {gift_info}")
        
        # Создаем и запускаем детектор с уже авторизованным клиентом
        detector = TelegramGiftDetector(
            config.api_id,
            config.api_hash, 
            config.phone_number
        )
        detector.client = auth_session["client"]  # Используем уже авторизованный клиент
        
        # Запускаем в фоне (здесь нужно будет доработать для background task)
        # background_tasks.add_task(detector.start, gift_found_callback)
        
        return {"message": "Детектор успешно запущен!", "status": "success"}
        
    except Exception as e:
        detector_status["error"] = str(e)
        detector_status["running"] = False
        logger.error(f"Ошибка запуска детектора: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка запуска: {str(e)}")

@app.post("/detector/stop")
async def stop_detector():
    if not detector_status["running"]:
        raise HTTPException(status_code=400, detail="Детектор не запущен")
    
    try:
        from telegram_detector import stop_telegram_detector
        await stop_telegram_detector()
    except Exception as e:
        logger.error(f"Ошибка остановки детектора: {e}")
    
    detector_status["running"] = False
    detector_status["started_at"] = None
    detector_status["error"] = None
    
    logger.info("Детектор остановлен")
    return {"message": "Детектор остановлен", "status": "stopped"}

@app.get("/detector/history")
def get_gift_history():
    return {"gifts": gift_history}

@app.get("/detector/sessions")
def get_saved_sessions():
    """Получить список сохраненных сессий"""
    import os
    sessions_dir = "sessions"
    sessions = []
    
    if os.path.exists(sessions_dir):
        for file in os.listdir(sessions_dir):
            if file.endswith('.session'):
                session_name = file.replace('.session', '')
                file_path = os.path.join(sessions_dir, file)
                file_size = os.path.getsize(file_path)
                modified_time = os.path.getmtime(file_path)
                
                sessions.append({
                    "name": session_name,
                    "size": file_size,
                    "modified": datetime.fromtimestamp(modified_time).isoformat(),
                    "phone": session_name.replace('gift_detector_', '+').replace('gift_detector', 'unknown')
                })
    
    return {"sessions": sessions}

@app.delete("/detector/sessions/{session_name}")
def delete_session(session_name: str):
    """Удалить сохраненную сессию"""
    import os
    sessions_dir = "sessions"
    session_file = os.path.join(sessions_dir, f"{session_name}.session")
    
    if os.path.exists(session_file):
        os.remove(session_file)
        logger.info(f"Сессия {session_name} удалена")
        return {"message": f"Сессия {session_name} удалена"}
    else:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

@app.post("/detector/simulate-gift")
async def simulate_gift():
    """Эндпоинт для тестирования - имитирует обнаружение подарка"""
    if not detector_status["running"]:
        raise HTTPException(status_code=400, detail="Детектор не запущен")
    
    # Имитация обнаружения подарка
    fake_gift = {
        "id": f"gift_{len(gift_history) + 1}",
        "type": "Star Gift",
        "price": "2500 stars",
        "quantity": "100/1000",
        "status": "limited",
        "detected_at": datetime.now().isoformat(),
        "sender": "TestUser",
        "chat": "Test Chat"
    }
    
    gift_history.append(fake_gift)
    detector_status["gifts_detected"] += 1
    detector_status["last_gift"] = fake_gift
    
    return {"message": "Тестовый подарок добавлен", "gift": fake_gift}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)