#!/usr/bin/env python3
"""
Telegram Gift Detector - Smart Deploy Version
Умная версия: работает с Telegram если есть зависимости, иначе показывает настройки
"""

import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI

app = FastAPI()
 
@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Telegram Gift Detector"}

@app.get("/info")
def get_info():
    return {
        "name": "Telegram Gift Detector",
        "version": "1.0.0",
        "description": "Smart Telegram gift detection service",
        "status": "ready for deployment"
    }