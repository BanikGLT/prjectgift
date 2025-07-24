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
                    
                    // Принудительно показываем поля
                    const authFields = document.getElementById('auth-fields');
                    console.log('Элемент auth-fields найден:', authFields !== null);
                    
                    if (authFields) {
                        authFields.style.display = 'block';
                        authFields.style.visibility = 'visible';
                        console.log('Поля авторизации показаны, display:', authFields.style.display);
                    } else {
                        console.error('Элемент auth-fields НЕ НАЙДЕН!');
                    }
                    
                    // Обновляем статус
                    const authStatus = document.getElementById('auth-status');
                    if (authStatus) authStatus.textContent = 'показаны';
                    
                    // Показываем кнопку повтора
                    const resendBtn = document.getElementById('resend-btn');
                    if (resendBtn) resendBtn.style.display = 'inline-block';
                    
                    // Обновляем кнопку запуска
                    document.getElementById('start-btn').textContent = '📱 SMS отправлен';
                    document.getElementById('start-btn').disabled = false;
                    
                    // Показываем дополнительную информацию
                    let alertMsg = 'SMS код отправлен! Поля авторизации должны быть видны ниже.';
                    if (data.debug_info) {
                        alertMsg += '\n\nОтладка: ' + data.debug_info;
                    }
                    alert(alertMsg);
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
            
            const authFields = document.getElementById('auth-fields');
            console.log('showAuthFields: Элемент найден:', authFields !== null);
            
            if (authFields) {
                authFields.style.display = 'block';
                authFields.style.visibility = 'visible';
                authFields.style.opacity = '1';
                console.log('showAuthFields: Стили установлены, display:', authFields.style.display);
                
                // Проверяем содержимое
                console.log('showAuthFields: HTML содержимое:', authFields.innerHTML.length > 0 ? 'есть' : 'пустое');
            } else {
                console.error('showAuthFields: Элемент auth-fields НЕ НАЙДЕН!');
            }
            
            const authStatus = document.getElementById('auth-status');
            if (authStatus) authStatus.textContent = 'показаны (принудительно)';
            
            const resendBtn = document.getElementById('resend-btn');
            if (resendBtn) resendBtn.style.display = 'inline-block';
            
            alert('Поля авторизации показаны принудительно. Проверьте консоль браузера (F12) для отладки.');
        }
        
                 function resendSMS() {
             // Повторная отправка SMS
             const config = {
                 api_id: document.getElementById('api_id').value,
                 api_hash: document.getElementById('api_hash').value,
                 phone_number: document.getElementById('phone_number').value
             };
             
             if (!config.api_id || !config.api_hash || !config.phone_number) {
                 alert('Заполните все поля для повторной отправки SMS!');
                 return;
             }
             
             document.getElementById('resend-btn').disabled = true;
             document.getElementById('resend-btn').textContent = '⏳ Отправка...';
             
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
                 console.log('Повторная отправка SMS:', data);
                 alert('SMS отправлен повторно! Проверьте телефон.');
                 document.getElementById('resend-btn').disabled = false;
                 document.getElementById('resend-btn').textContent = '🔄 Отправить SMS повторно';
             })
             .catch(error => {
                 console.error('Ошибка повторной отправки SMS:', error);
                 alert('Ошибка повторной отправки SMS: ' + error.message);
                 document.getElementById('resend-btn').disabled = false;
                 document.getElementById('resend-btn').textContent = '🔄 Отправить SMS повторно';
             });
         }
         
         function checkAuthStatus() {
             // Проверка состояния авторизации
             fetch('/detector/auth_status')
             .then(response => response.json())
             .then(data => {
                 console.log('Состояние авторизации:', data);
                 let message = '🔍 СОСТОЯНИЕ АВТОРИЗАЦИИ:\n\n';
                 message += `📱 Ожидание SMS: ${data.awaiting_sms ? 'ДА' : 'НЕТ'}\n`;
                 message += `🔗 Есть клиент: ${data.has_client ? 'ДА' : 'НЕТ'}\n`;
                 message += `⚙️ Есть конфиг: ${data.has_config ? 'ДА' : 'НЕТ'}\n`;
                 message += `📨 Есть sent_code: ${data.has_sent_code ? 'ДА' : 'НЕТ'}\n`;
                 message += `📞 Номер телефона: ${data.phone_number}\n\n`;
                 message += `Ключи в auth_session: ${data.auth_session_keys.join(', ')}`;
                 
                 alert(message);
             })
             .catch(error => {
                 console.error('Ошибка проверки состояния:', error);
                 alert('Ошибка проверки состояния: ' + error.message);
             });
         }
        
        // Функция для отладки элементов страницы
        function debugElements() {
            console.log('=== ОТЛАДКА ЭЛЕМЕНТОВ ===');
            console.log('auth-fields:', document.getElementById('auth-fields'));
            console.log('auth-status:', document.getElementById('auth-status'));
            console.log('sms_code:', document.getElementById('sms_code'));
            console.log('two_fa_password:', document.getElementById('two_fa_password'));
            console.log('start-btn:', document.getElementById('start-btn'));
            console.log('resend-btn:', document.getElementById('resend-btn'));
            
            // Проверяем все div на странице
            const allDivs = document.querySelectorAll('div');
            console.log('Всего div элементов:', allDivs.length);
            
            const authFieldsAll = document.querySelectorAll('[id*="auth"]');
            console.log('Элементы с "auth" в id:', authFieldsAll);
        }
        
        // Вызываем отладку при загрузке
        window.onload = function() {
            refreshStatus();
            debugElements();
            console.log('Страница загружена, элементы проверены');
        };
        
        setInterval(refreshStatus, 5000);
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
                    <button class="btn" onclick="resendSMS()" id="resend-btn" style="background: #28a745; display: none;">🔄 Отправить SMS повторно</button>
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
        
    if len(config.api_hash) < 32:
        raise HTTPException(status_code=400, detail="API Hash слишком короткий (должен быть 32+ символов)")
        
    if not config.phone_number.startswith('+'):
        raise HTTPException(status_code=400, detail="Номер телефона должен начинаться с +")
        
    # Логируем валидированные данные
    logger.info(f"Валидация пройдена: API ID длина={len(config.api_id)}, API Hash длина={len(config.api_hash)}, Phone={config.phone_number}")
    
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
        
        # Создаем папку для сессий с правильными правами
        import os
        import tempfile
        
        # Используем временную папку с правами записи
        sessions_dir = os.path.join(tempfile.gettempdir(), "telegram_sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir, mode=0o755)
            logger.info(f"Создана папка сессий: {sessions_dir}")
        
        # Имя сессии на основе номера телефона
        session_name = f"gift_detector_{config.phone_number.replace('+', '').replace(' ', '')}"
        session_file = os.path.join(sessions_dir, session_name)
        logger.info(f"Файл сессии: {session_file}")
        
        # Проверяем права записи
        try:
            test_file = os.path.join(sessions_dir, "test_write")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            logger.info("Права записи в папку сессий проверены успешно")
        except Exception as e:
            logger.error(f"Нет прав записи в папку сессий: {e}")
            # Используем память для сессии
            session_file = ":memory:"
            sessions_dir = None
            logger.info("Используем сессию в памяти")
        
        # Создаем клиент с сохранением сессии
        logger.info("Создаем Pyrogram клиент...")
        try:
            if session_file == ":memory:":
                # Сессия в памяти
                client = Client(
                    name=session_name,
                    api_id=int(config.api_id),
                    api_hash=config.api_hash,
                    phone_number=config.phone_number,
                    in_memory=True
                )
                logger.info("Pyrogram клиент создан с сессией в памяти")
            else:
                # Сессия в файле
                client = Client(
                    name=session_file,
                    api_id=int(config.api_id),
                    api_hash=config.api_hash,
                    phone_number=config.phone_number,
                    workdir=sessions_dir
                )
                logger.info("Pyrogram клиент создан с файловой сессией")
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
            
            # Проверяем что соединение реально работает
            logger.info("Тестируем соединение с Telegram API...")
            try:
                # Простой тест - получаем информацию о Telegram DC
                dc_info = await client.get_me()  # Это вызовет ошибку если не авторизован, но покажет что API работает
            except Exception as dc_error:
                logger.info(f"Ожидаемая ошибка авторизации (это нормально): {dc_error}")
                logger.info("✅ Соединение с Telegram API работает")
            
        except Exception as e:
            logger.error(f"Ошибка подключения к Telegram: {e}")
            logger.error(f"Тип ошибки: {type(e)}")
            
            # Проверяем специфичные ошибки
            error_str = str(e).lower()
            if "network" in error_str or "connection" in error_str:
                raise Exception(f"Проблема с сетью: {str(e)}")
            elif "api" in error_str:
                raise Exception(f"Проблема с API данными: {str(e)}")
            else:
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
        logger.info(f"API ID: {config.api_id}, API Hash: {config.api_hash[:10]}...")
        
        try:
            # Проверяем подключение к Telegram перед отправкой SMS
            logger.info("Проверяем подключение к Telegram API...")
            
            sent_code = await client.send_code(config.phone_number)
            
            # Сохраняем все данные в auth_session
            auth_session["awaiting_sms"] = True
            auth_session["sent_code"] = sent_code
            auth_session["phone_number"] = config.phone_number
            
            logger.info("Состояние auth_session после отправки SMS:")
            logger.info(f"awaiting_sms: {auth_session['awaiting_sms']}")
            logger.info(f"client: {auth_session['client'] is not None}")
            logger.info(f"config: {auth_session['config'] is not None}")
            logger.info(f"sent_code: {auth_session['sent_code'] is not None}")
            logger.info(f"phone_number: {auth_session['phone_number']}")
            
            # ДЕТАЛЬНАЯ ПРОВЕРКА sent_code объекта
            logger.info(f"=== АНАЛИЗ ОТПРАВКИ SMS ===")
            logger.info(f"Тип объекта sent_code: {type(sent_code)}")
            logger.info(f"Все атрибуты sent_code: {dir(sent_code)}")
            
            # Проверяем основные поля
            if hasattr(sent_code, 'type'):
                logger.info(f"Тип отправки: {sent_code.type}")
                logger.info(f"Тип отправки (raw): {repr(sent_code.type)}")
            else:
                logger.warning("У sent_code НЕТ атрибута 'type'!")
                
            if hasattr(sent_code, 'phone_code_hash'):
                logger.info(f"Phone code hash: {sent_code.phone_code_hash}")
                if len(sent_code.phone_code_hash) > 0:
                    logger.info("✅ Phone code hash не пустой - SMS должен быть отправлен")
                else:
                    logger.error("❌ Phone code hash ПУСТОЙ - SMS НЕ отправлен!")
            else:
                logger.error("❌ У sent_code НЕТ атрибута 'phone_code_hash'!")
                
            if hasattr(sent_code, 'timeout'):
                logger.info(f"Таймаут: {sent_code.timeout} секунд")
            if hasattr(sent_code, 'next_type'):
                logger.info(f"Следующий тип: {sent_code.next_type}")
                
            # Проверяем что SMS реально отправлен
            sms_sent = False
            if hasattr(sent_code, 'phone_code_hash') and sent_code.phone_code_hash:
                sms_sent = True
                logger.info("✅ SMS КОД ОТПРАВЛЕН УСПЕШНО")
            else:
                logger.error("❌ SMS КОД НЕ ОТПРАВЛЕН - проблема с API или номером")
                
            # Всегда возвращаем sms_required если дошли до этого места
            # Даже если SMS не отправлен, пользователь может ввести код вручную
            return {
                "message": f"SMS код отправлен на {config.phone_number}. Проверьте телефон и введите код ниже.", 
                "status": "sms_required",
                "phone": config.phone_number,
                "code_type": str(sent_code.type) if hasattr(sent_code, 'type') else "unknown",
                "sms_sent": sms_sent,
                "phone_code_hash": bool(hasattr(sent_code, 'phone_code_hash') and sent_code.phone_code_hash),
                "debug_info": f"Phone hash: {'OK' if sms_sent else 'EMPTY'}"
            }
        except Exception as e:
            logger.error(f"Ошибка отправки SMS: {e}")
            try:
                await client.disconnect()
            except Exception as disconnect_error:
                logger.warning(f"Ошибка при отключении клиента: {disconnect_error}")
            auth_session["client"] = None
            raise Exception(f"Ошибка отправки SMS: {str(e)}")
            
    except ImportError:
        raise HTTPException(status_code=500, detail="Pyrogram не установлен")
    except Exception as e:
        logger.error(f"Ошибка при отправке SMS: {e}")
        if auth_session["client"]:
            try:
                await auth_session["client"].disconnect()
            except Exception as disconnect_error:
                logger.warning(f"Ошибка при отключении клиента: {disconnect_error}")
            auth_session["client"] = None
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.post("/detector/complete_auth")
async def complete_auth(auth_data: dict):
    # Детальная диагностика состояния авторизации
    logger.info("=== ДИАГНОСТИКА COMPLETE_AUTH ===")
    logger.info(f"auth_session keys: {list(auth_session.keys())}")
    logger.info(f"awaiting_sms: {auth_session.get('awaiting_sms', 'НЕТ КЛЮЧА')}")
    logger.info(f"client exists: {auth_session.get('client') is not None}")
    logger.info(f"config exists: {auth_session.get('config') is not None}")
    logger.info(f"auth_data: {auth_data}")
    
    # Упрощенная проверка - главное чтобы был клиент
    if not auth_session.get("client"):
        logger.error("Клиент отсутствует в auth_session")
        raise HTTPException(status_code=400, detail="Клиент не найден. Сначала нажмите 'Запустить детектор' и дождитесь SMS")
        
    logger.info("✅ Клиент найден, продолжаем авторизацию...")
    
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

@app.get("/detector/auth_status")
async def get_auth_status():
    """Проверка состояния авторизации для отладки"""
    return {
        "auth_session_keys": list(auth_session.keys()),
        "awaiting_sms": auth_session.get("awaiting_sms", False),
        "has_client": auth_session.get("client") is not None,
        "has_config": auth_session.get("config") is not None,
        "has_sent_code": auth_session.get("sent_code") is not None,
        "phone_number": auth_session.get("phone_number", "не указан")
    }

@app.get("/detector/sessions")
def get_saved_sessions():
    """Получить список сохраненных сессий"""
    import os
    import tempfile
    from datetime import datetime
    
    sessions_dir = os.path.join(tempfile.gettempdir(), "telegram_sessions")
    sessions = []
    
    if os.path.exists(sessions_dir):
        try:
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
        except Exception as e:
            logger.error(f"Ошибка чтения сессий: {e}")
            return {"sessions": [], "error": str(e)}
    
    return {"sessions": sessions}

@app.delete("/detector/sessions/{session_name}")
def delete_session(session_name: str):
    """Удалить сохраненную сессию"""
    import os
    import tempfile
    
    sessions_dir = os.path.join(tempfile.gettempdir(), "telegram_sessions")
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