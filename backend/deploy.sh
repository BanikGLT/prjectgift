#!/bin/bash

# =============================================================================
# Telegram Gift Detector - Автоматический деплой скрипт
# =============================================================================

set -e  # Остановка при ошибках

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}🎁 TELEGRAM GIFT DETECTOR DEPLOY${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Проверка зависимостей
check_dependencies() {
    print_info "Проверка зависимостей..."
    
    # Проверка Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker не установлен!"
        print_info "Установите Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Проверка Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose не установлен!"
        print_info "Установите Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    print_success "Все зависимости установлены"
}

# Проверка конфигурации
check_config() {
    print_info "Проверка конфигурации..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_warning "Файл .env не найден, создаю из примера..."
            cp .env.example .env
            print_error "ВАЖНО: Отредактируйте файл .env с вашими API данными!"
            print_info "nano .env"
            exit 1
        else
            print_error "Файл .env.example не найден!"
            exit 1
        fi
    fi
    
    # Проверка критических переменных
    source .env
    
    if [ "$API_ID" = "12345678" ] || [ "$API_HASH" = "your_api_hash_here" ]; then
        print_error "API данные не настроены в файле .env!"
        print_info "Отредактируйте .env файл с правильными данными"
        exit 1
    fi
    
    print_success "Конфигурация проверена"
}

# Создание необходимых директорий
create_directories() {
    print_info "Создание директорий..."
    
    mkdir -p logs
    mkdir -p sessions
    mkdir -p data
    
    print_success "Директории созданы"
}

# Сборка Docker образа
build_image() {
    print_info "Сборка Docker образа..."
    
    docker-compose build --no-cache
    
    print_success "Docker образ собран"
}

# Запуск контейнера
start_container() {
    print_info "Запуск контейнера..."
    
    # Остановка существующего контейнера
    docker-compose down 2>/dev/null || true
    
    # Запуск нового контейнера
    docker-compose up -d
    
    print_success "Контейнер запущен"
}

# Проверка статуса
check_status() {
    print_info "Проверка статуса..."
    
    sleep 5
    
    if docker-compose ps | grep -q "Up"; then
        print_success "Детектор успешно запущен!"
        
        # Показываем логи
        print_info "Последние логи:"
        docker-compose logs --tail=20
        
        print_info "Для просмотра логов в реальном времени:"
        echo "docker-compose logs -f"
        
    else
        print_error "Контейнер не запустился!"
        print_info "Проверьте логи:"
        docker-compose logs
        exit 1
    fi
}

# Показ информации о мониторинге
show_monitoring_info() {
    echo
    print_info "=== КОМАНДЫ ДЛЯ МОНИТОРИНГА ==="
    echo "📊 Статус:           docker-compose ps"
    echo "📋 Логи:             docker-compose logs -f"
    echo "🔄 Перезапуск:       docker-compose restart"
    echo "⏹️  Остановка:        docker-compose down"
    echo "🗑️  Удаление:         docker-compose down -v --rmi all"
    echo
    print_info "=== ФАЙЛЫ ЛОГОВ ==="
    echo "📁 Логи:             ./logs/gift_detector.log"
    echo "💾 Сессии:           ./sessions/"
    echo "📊 Данные:           docker volume ls"
    echo
}

# Главная функция
main() {
    print_header
    
    # Проверки
    check_dependencies
    check_config
    create_directories
    
    # Деплой
    build_image
    start_container
    check_status
    
    # Информация
    show_monitoring_info
    
    print_success "🎉 ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!"
    print_info "Детектор работает и ожидает подарки..."
}

# Обработка аргументов командной строки
case "${1:-}" in
    "check")
        print_header
        check_dependencies
        check_config
        print_success "Все проверки пройдены!"
        ;;
    "build")
        print_header
        build_image
        ;;
    "start")
        print_header
        start_container
        check_status
        ;;
    "stop")
        print_info "Остановка контейнера..."
        docker-compose down
        print_success "Контейнер остановлен"
        ;;
    "restart")
        print_info "Перезапуск контейнера..."
        docker-compose restart
        print_success "Контейнер перезапущен"
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        docker-compose ps
        ;;
    "clean")
        print_warning "Удаление всех данных..."
        read -p "Вы уверены? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v --rmi all
            print_success "Все данные удалены"
        fi
        ;;
    "help"|"-h"|"--help")
        echo "Использование: $0 [команда]"
        echo
        echo "Команды:"
        echo "  (пусто)   - Полный деплой"
        echo "  check     - Проверка зависимостей и конфигурации"
        echo "  build     - Сборка Docker образа"
        echo "  start     - Запуск контейнера"
        echo "  stop      - Остановка контейнера"
        echo "  restart   - Перезапуск контейнера"
        echo "  logs      - Просмотр логов"
        echo "  status    - Статус контейнера"
        echo "  clean     - Удаление всех данных"
        echo "  help      - Эта справка"
        ;;
    "")
        main
        ;;
    *)
        print_error "Неизвестная команда: $1"
        print_info "Используйте: $0 help"
        exit 1
        ;;
esac