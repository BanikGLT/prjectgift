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
            
            fetch('/detector/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                refreshStatus();
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
                    
                    <button class="btn" onclick="startDetector()">🚀 Запустить детектор</button>
                    <button class="btn danger" onclick="stopDetector()">⏹️ Остановить детектор</button>
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
async def start_detector(config: TelegramConfig, background_tasks: BackgroundTasks):
    if detector_status["running"]:
        raise HTTPException(status_code=400, detail="Детектор уже запущен")
    
    try:
        from telegram_detector import start_telegram_detector
        
        detector_status["running"] = True
        detector_status["started_at"] = datetime.now().isoformat()
        detector_status["error"] = None
        detector_status["gifts_detected"] = 0
        
        logger.info(f"Детектор запущен с конфигурацией: {config.phone_number}")
        
        # Callback для обработки найденных подарков
        async def gift_found_callback(gift_info):
            gift_history.append(gift_info)
            detector_status["gifts_detected"] += 1
            detector_status["last_gift"] = gift_info
            logger.info(f"Обнаружен подарок: {gift_info}")
        
        # Запуск реального Telegram детектора в фоне
        background_tasks.add_task(
            start_telegram_detector,
            config.api_id,
            config.api_hash, 
            config.phone_number,
            gift_found_callback
        )
        
        return {"message": "Детектор успешно запущен!", "status": "started"}
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