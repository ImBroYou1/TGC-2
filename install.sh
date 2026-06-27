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

# Пошук робочого Python
echo -e "${YELLOW}[1/5] Пошук сумісного Python...${NC}"

PYTHON_CMD=""

# Перевіряємо python3.12
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
# Перевіряємо python3.11
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
# Перевіряємо python3.10
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
# Перевіряємо python3
elif command -v python3 &> /dev/null; then
    VER=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [ "$VER" -le 12 ]; then
        PYTHON_CMD="python3"
    else
        echo -e "${RED}Python 3.${VER} не підтримується. Встановлюємо Python 3.12...${NC}"
        if command -v pacman &> /dev/null; then
            sudo pacman -S --noconfirm python312
            PYTHON_CMD="python3.12"
        elif command -v apt &> /dev/null; then
            sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
            sudo apt update
            sudo apt install -y python3.12 python3.12-venv python3.12-pip
            PYTHON_CMD="python3.12"
        fi
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Python не знайдено. Встановлюємо...${NC}"
    if command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm python312
        PYTHON_CMD="python3.12"
    elif command -v apt &> /dev/null; then
        sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
        sudo apt update
        sudo apt install -y python3.12 python3.12-venv python3.12-pip
        PYTHON_CMD="python3.12"
    else
        echo -e "${RED}Не вдалося встановити Python. Встановіть вручну.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Використовуємо: $($PYTHON_CMD --version)${NC}"

# Встановлення системних залежностей
echo -e "${YELLOW}[2/5] Системні залежності...${NC}"
if command -v pacman &> /dev/null; then
    sudo pacman -S --needed --noconfirm netcat vnstat 2>/dev/null || true
elif command -v apt &> /dev/null; then
    sudo apt install -y netcat-openbsd vnstat 2>/dev/null || true
fi
echo -e "${GREEN}✅ Готово${NC}"

# Python середовище
echo -e "${YELLOW}[3/5] Налаштування оточення...${NC}"
rm -rf .venv
$PYTHON_CMD -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet 2>/dev/null
pip install -r requirements.txt --quiet
echo -e "${GREEN}✅ Залежності встановлено${NC}"

# Конфігурація
echo -e "${YELLOW}[4/5] Конфігурація...${NC}"
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

mkdir -p data temp

# Тестовий запуск
echo -e "${YELLOW}[5/5] Перевірка...${NC}"
echo -e "${BLUE}Запускаю тест на 5 секунд...${NC}"

timeout 5 .venv/bin/python bot.py 2>&1 &
TEST_PID=$!
sleep 5
kill $TEST_PID 2>/dev/null || true
wait $TEST_PID 2>/dev/null || true

if [ $? -le 1 ]; then
    echo -e "${GREEN}✅ Бот запускається без помилок!${NC}"
else
    echo -e "${YELLOW}⚠️  Можливі проблеми, але продовжуємо...${NC}"
fi

# Systemd сервіс
echo ""
echo -e "${BLUE}Встановити автозапуск (systemd)? (y/n)${NC}"
read -p "> " INSTALL_SERVICE

if [ "$INSTALL_SERVICE" = "y" ] || [ "$INSTALL_SERVICE" = "Y" ]; then
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
    echo -e "${BLUE}Запустити зараз? (y/n)${NC}"
    read -p "> " START_NOW
    
    if [ "$START_NOW" = "y" ] || [ "$START_NOW" = "Y" ]; then
        sudo systemctl start server-bot
        sleep 2
        echo -e "${GREEN}✅ Бот запущено${NC}"
        echo ""
        echo -e "${BLUE}Корисні команди:${NC}"
        echo "  sudo systemctl status server-bot"
        echo "  sudo journalctl -u server-bot -f"
    fi
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ Встановлення завершено!     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"