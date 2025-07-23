#!/usr/bin/env python3
"""
Telegram Gift Detector - FastAPI Web Interface
Веб-интерфейс для управления детектором подарков
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config import config
from telegram_gift_detector import TelegramGiftDetector

# =============================================================================
# НАСТРОЙКА FASTAPI
# =============================================================================

app = FastAPI(
    title="Telegram Gift Detector API",
    description="Professional API for managing Telegram Gift Detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные переменные
detector_instance: Optional[TelegramGiftDetector] = None
detector_task: Optional[asyncio.Task] = None
is_running = False

# =============================================================================
# PYDANTIC МОДЕЛИ
# =============================================================================

class DetectorStatus(BaseModel):
    """Статус детектора"""
    is_running: bool
    uptime: Optional[str] = None
    gifts_detected: int = 0
    responses_sent: int = 0
    errors: int = 0
    last_gift: Optional[Dict[str, Any]] = None

class ConfigUpdate(BaseModel):
    """Обновление конфигурации"""
    response_delay: Optional[float] = None
    max_retries: Optional[int] = None
    enable_pyrogram_detection: Optional[bool] = None
    enable_raw_api_detection: Optional[bool] = None
    enable_text_detection: Optional[bool] = None
    log_level: Optional[str] = None

class ApiResponse(BaseModel):
    """Стандартный ответ API"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Главная страница с веб-интерфейсом"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎁 Telegram Gift Detector</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
            .status.running { background: #d4edda; color: #155724; }
            .status.stopped { background: #f8d7da; color: #721c24; }
            .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-primary { background: #007bff; color: white; }
            .btn-success { background: #28a745; color: white; }
            .btn-danger { background: #dc3545; color: white; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
            .stat-card { text-align: center; padding: 20px; background: #e9ecef; border-radius: 8px; }
            .logs { background: #000; color: #00ff00; padding: 15px; border-radius: 4px; font-family: monospace; height: 300px; overflow-y: scroll; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎁 Telegram Gift Detector</h1>
                <p>Professional Edition - Backend Interface</p>
            </div>
            
            <div class="card">
                <h2>📊 Статус системы</h2>
                <div id="status" class="status">Загрузка...</div>
                <div class="stats" id="stats"></div>
            </div>
            
            <div class="card">
                <h2>🎮 Управление</h2>
                <button class="btn btn-success" onclick="startDetector()">▶️ Запустить</button>
                <button class="btn btn-danger" onclick="stopDetector()">⏹️ Остановить</button>
                <button class="btn btn-primary" onclick="restartDetector()">🔄 Перезапустить</button>
                <button class="btn btn-primary" onclick="refreshStatus()">🔄 Обновить</button>
            </div>
            
            <div class="card">
                <h2>🎁 Последние подарки</h2>
                <div id="gifts">Загрузка...</div>
            </div>
            
            <div class="card">
                <h2>📋 Логи</h2>
                <div class="logs" id="logs">Загрузка логов...</div>
            </div>
        </div>
        
        <script>
            // JavaScript для управления интерфейсом
            async function apiCall(endpoint, method = 'GET', data = null) {
                try {
                    const options = { method };
                    if (data) {
                        options.headers = { 'Content-Type': 'application/json' };
                        options.body = JSON.stringify(data);
                    }
                    const response = await fetch(endpoint, options);
                    return await response.json();
                } catch (error) {
                    console.error('API Error:', error);
                    return { success: false, message: error.message };
                }
            }
            
            async function refreshStatus() {
                const status = await apiCall('/api/status');
                const statusDiv = document.getElementById('status');
                const statsDiv = document.getElementById('stats');
                
                if (status.data) {
                    const isRunning = status.data.is_running;
                    statusDiv.className = `status ${isRunning ? 'running' : 'stopped'}`;
                    statusDiv.textContent = isRunning ? '🟢 Детектор запущен' : '🔴 Детектор остановлен';
                    
                    statsDiv.innerHTML = `
                        <div class="stat-card">
                            <h3>${status.data.gifts_detected || 0}</h3>
                            <p>Подарков обнаружено</p>
                        </div>
                        <div class="stat-card">
                            <h3>${status.data.responses_sent || 0}</h3>
                            <p>Ответов отправлено</p>
                        </div>
                        <div class="stat-card">
                            <h3>${status.data.errors || 0}</h3>
                            <p>Ошибок</p>
                        </div>
                        <div class="stat-card">
                            <h3>${status.data.uptime || 'N/A'}</h3>
                            <p>Время работы</p>
                        </div>
                    `;
                }
            }
            
            async function startDetector() {
                const result = await apiCall('/api/start', 'POST');
                alert(result.message);
                if (result.success) refreshStatus();
            }
            
            async function stopDetector() {
                const result = await apiCall('/api/stop', 'POST');
                alert(result.message);
                if (result.success) refreshStatus();
            }
            
            async function restartDetector() {
                const result = await apiCall('/api/restart', 'POST');
                alert(result.message);
                if (result.success) refreshStatus();
            }
            
            // Автообновление каждые 5 секунд
            setInterval(() => {
                refreshStatus();
            }, 5000);
            
            // Первоначальная загрузка
            refreshStatus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/status")
async def get_status():
    """Получить статус детектора"""
    try:
        stats = {
            "is_running": is_running,
            "gifts_detected": 0,
            "responses_sent": 0, 
            "errors": 0,
            "uptime": None
        }
        
        if detector_instance and hasattr(detector_instance, 'stats'):
            stats.update(detector_instance.stats)
            
        return ApiResponse(
            success=True,
            message="Статус получен",
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/start")
async def start_detector(background_tasks: BackgroundTasks):
    """Запустить детектор"""
    global detector_instance, detector_task, is_running
    
    if is_running:
        return ApiResponse(
            success=False,
            message="Детектор уже запущен"
        )
    
    try:
        # Создаем новый экземпляр детектора
        detector_instance = TelegramGiftDetector()
        
        # Запускаем в фоновой задаче
        async def run_detector():
            global is_running
            try:
                is_running = True
                await detector_instance.start()
                # Ждем бесконечно
                await asyncio.Event().wait()
            except Exception as e:
                logging.error(f"Ошибка детектора: {e}")
                is_running = False
            finally:
                if detector_instance:
                    await detector_instance.stop()
                is_running = False
        
        detector_task = asyncio.create_task(run_detector())
        
        # Даем время на запуск
        await asyncio.sleep(2)
        
        return ApiResponse(
            success=True,
            message="Детектор запущен успешно"
        )
        
    except Exception as e:
        is_running = False
        raise HTTPException(status_code=500, detail=f"Ошибка запуска: {str(e)}")

@app.post("/api/stop")
async def stop_detector():
    """Остановить детектор"""
    global detector_instance, detector_task, is_running
    
    if not is_running:
        return ApiResponse(
            success=False,
            message="Детектор уже остановлен"
        )
    
    try:
        is_running = False
        
        if detector_task:
            detector_task.cancel()
            try:
                await detector_task
            except asyncio.CancelledError:
                pass
        
        if detector_instance:
            await detector_instance.stop()
            detector_instance = None
        
        detector_task = None
        
        return ApiResponse(
            success=True,
            message="Детектор остановлен"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка остановки: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# =============================================================================
# ЗАПУСК СЕРВЕРА
# =============================================================================

if __name__ == "__main__":
    import os
    
    # Настройка логирования для FastAPI
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Получаем порт из переменной окружения (для облачных платформ)
    port = int(os.environ.get("PORT", 8000))
    
    # Запуск сервера
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,  # В продакшене отключаем reload
        access_log=True
    )