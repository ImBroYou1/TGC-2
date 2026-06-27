#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🖥️  Server Admin Bot Installer    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# ==========================================
# [1/5] Пошук та встановлення Python
# ==========================================
echo -e "${YELLOW}[1/5] Пошук сумісного Python...${NC}"

PYTHON_CMD=""

if command -v python3 &> /dev/null; then
    VER=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [ "$VER" -ge 10 ]; then
        PYTHON_CMD="python3"
    else
        echo -e "${RED}Знайдений Python 3.${VER} застарілий (потрібен >= 3.10).${NC}"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}Встановлюємо актуальну версію Python...${NC}"
    if command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm python python-pip
        PYTHON_CMD="python3"
    elif command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y python3 python3-venv python3-pip
        PYTHON_CMD="python3"
    else
        echo -e "${RED}❌ Не вдалося автоматично встановити Python. Встановіть Python вручну.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Використовуємо: $($PYTHON_CMD --version)${NC}"

# ==========================================
# [2/5] Системні залежності
# ==========================================
echo -e "${YELLOW}[2/5] Системні залежності...${NC}"
if command -v pacman &> /dev/null; then
    sudo pacman -S --needed --noconfirm gnu-netcat vnstat 2>/dev/null || true
elif command -v apt &> /dev/null; then
    sudo apt update && sudo apt install -y netcat-openbsd vnstat 2>/dev/null || true
fi
echo -e "${GREEN}✅ Готово${NC}"

# ==========================================
# [3/5] Налаштування Python оточення
# ==========================================
echo -e "${YELLOW}[3/5] Налаштування оточення...${NC}"
rm -rf .venv
$PYTHON_CMD -m venv .venv

# Оновлення pip та встановлення залежностей без активації глобального scope
.venv/bin/pip install --upgrade pip --quiet 2>/dev/null

if [ -f requirements.txt ]; then
    .venv/bin/pip install -r requirements.txt --quiet
    echo -e "${GREEN}✅ Залежності встановлено${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt не знайдено, пропускаємо.${NC}"
fi

# ==========================================
# [4/5] Конфігурація середовища
# ==========================================
echo -e "${YELLOW}[4/5] Конфігурація...${NC}"
mkdir -p data temp

if [ ! -f .env ]; then
    echo ""
    echo -e "${BLUE}Токен бота (@BotFather):${NC}"
    read -p "> " BOT_TOKEN
    
    echo ""
    echo -e "${BLUE}Ваш Telegram ID (@userinfobot):${NC}"
    read -p "> " CHAT_ID
    
    echo ""
    echo -e "${BLUE}Пароль для доступу:${NC}"
    read -sp "> " ADMIN_PASSWORD
    echo ""
    
    echo ""
    echo -e "${BLUE}Назва сервера:${NC}"
    read -p "> " SERVER_NAME
    SERVER_NAME=${SERVER_NAME:-"My Server"}
    
    cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
ALLOWED_CHAT_ID=${CHAT_ID}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
SERVER_NAME=${SERVER_NAME}
EOF
    echo -e "${GREEN}✅ .env створено${NC}"
else
    echo -e "${GREEN}✅ .env вже існує${NC}"
fi

# ==========================================
# [5/5] Безпечний тестовий запуск
# ==========================================
echo -e "${YELLOW}[5/5] Перевірка коду...${NC}"
if [ -f bot.py ]; then
    echo -e "${BLUE}Запускаю тест на 5 секунд...${NC}"
    
    set +e
    timeout 5 .venv/bin/python bot.py > temp/test.log 2>&1
    TEST_STATUS=$?
    set -e

    # 124 означає, що таймаут закрив процес (тобто бот успішно запустився і тримав сокет)
    if [ $TEST_STATUS -eq 124 ] || [ $TEST_STATUS -eq 0 ]; then
        echo -e "${GREEN}✅ Бот запускається без помилок!${NC}"
    else
        echo -e "${RED}❌ Помилка запуску бота! Дивись лог: temp/test.log${NC}"
        echo -e "${YELLOW}Останні рядки з логу:${NC}"
        tail -n 10 temp/test.log
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  Файл bot.py не знайдено, тест пропущено.${NC}"
fi

# ==========================================
# Налаштування Systemd сервісу
# ==========================================
echo ""
echo -e "${BLUE}Встановити автозапуск через systemd? (y/n)${NC}"
read -p "> " INSTALL_SERVICE

if [[ "$INSTALL_SERVICE" =~ ^[Yy](es)?$ ]]; then
    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)
    
    sudo tee /etc/systemd/system/server-bot.service > /dev/null << EOF
[Unit]
Description=Server Admin Telegram Bot
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${CURRENT_DIR}
ExecStart=${CURRENT_DIR}/.venv/bin/python ${CURRENT_DIR}/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable server-bot
    
    echo ""
    echo -e "${BLUE}Запустити сервіс прямо зараз? (y/n)${NC}"
    read -p "> " START_NOW
    
    if [[ "$START_NOW" =~ ^[Yy](es)?$ ]]; then
        sudo systemctl start server-bot
        sleep 2
        echo -e "${GREEN}✅ Сервіс запущенний та доданий в автозавантаження!${NC}"
        echo ""
        echo -e "${BLUE}Команди керування:${NC}"
        echo "  sudo systemctl status server-bot"
        echo "  sudo journalctl -u server-bot -f"
    fi
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ Встановлення завершено!     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"