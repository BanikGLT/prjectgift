# 🎁 Telegram Gift Detector

Умный детектор подарков в Telegram с веб-интерфейсом для управления.

## 🚀 Быстрое развертывание

### Вариант 1: Базовое развертывание (Рекомендуется)
```bash
# Используйте файлы в корне проекта:
# - app.py (умное приложение с автоопределением зависимостей)
# - Procfile (конфигурация для деплоя)
# - requirements.txt (минимальные зависимости)
```

### Вариант 2: Полнофункциональный бэкенд
```bash
cd backend/
python run.py
```

## 📁 Структура проекта

- **Корень проекта**: Файлы для быстрого развертывания
- **backend/**: Полнофункциональный детектор с веб-интерфейсом
- **app/**: Оригинальная версия детектора

## ⚡ Особенности умного развертывания

Приложение автоматически определяет доступные зависимости:
- Если Telegram библиотеки недоступны → показывает интерфейс настройки
- Если все зависимости установлены → запускает полный детектор

## 🔧 Настройка

1. Скопируйте `backend/.env.example` в `backend/.env`
2. Заполните настройки Telegram API
3. Запустите приложение

## 📊 Возможности

- ✅ Детекция всех типов подарков
- ✅ Автоматические ответы отправителям
- ✅ Веб-интерфейс для управления
- ✅ Статистика и история
- ✅ Умное развертывание
