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

# Перевірка Python
echo -e "${YELLOW}[1/5] Перевірка Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✅ Python $PYTHON_VERSION знайдено${NC}"
else
    echo -e "${RED}❌ Python 3 не знайдено${NC}"
    echo "Встановлюємо..."
    if command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm python python-pip
    elif command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y python3 python3-pip python3-venv
    else
        echo -e "${RED}Не вдалося визначити пакетний менеджер. Встановіть Python вручну${NC}"
        exit 1
    fi
fi

# Встановлення системних залежностей
echo -e "${YELLOW}[2/5] Встановлення системних залежностей...${NC}"
if command -v pacman &> /dev/null; then
    sudo pacman -S --needed --noconfirm netcat vnstat 2>/dev/null || true
elif command -v apt &> /dev/null; then
    sudo apt install -y netcat-openbsd vnstat 2>/dev/null || true
fi
echo -e "${GREEN}✅ Залежності встановлено${NC}"

# Створення віртуального середовища
echo -e "${YELLOW}[3/5] Налаштування Python середовища...${NC}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo -e "${GREEN}✅ Python залежності встановлено${NC}"

# Налаштування конфігурації
echo -e "${YELLOW}[4/5] Налаштування конфігурації...${NC}"
if [ ! -f .env ]; then
    echo ""
    echo -e "${BLUE}Введіть токен бота (отримати у @BotFather):${NC}"
    read -p "> " BOT_TOKEN
    
    echo ""
    echo -e "${BLUE}Введіть ваш Telegram Chat ID (отримати у @userinfobot):${NC}"
    read -p "> " CHAT_ID
    
    echo ""
    echo -e "${BLUE}Введіть пароль для доступу до бота:${NC}"
    read -sp "> " ADMIN_PASSWORD
    echo ""
    
    echo ""
    echo -e "${BLUE}Назва сервера (напр: Home Server):${NC}"
    read -p "> " SERVER_NAME
    SERVER_NAME=${SERVER_NAME:-"My Server"}
    
    cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
ALLOWED_CHAT_ID=${CHAT_ID}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
SERVER_NAME=${SERVER_NAME}
EOF
    
    echo -e "${GREEN}✅ .env файл створено${NC}"
else
    echo -e "${GREEN}✅ .env файл вже існує${NC}"
fi

# Створення директорій
mkdir -p data temp

# Налаштування systemd сервісу
echo ""
echo -e "${YELLOW}[5/5] Налаштування автозапуску...${NC}"
echo -e "${BLUE}Встановити systemd сервіс для автозапуску? (y/n)${NC}"
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
    echo -e "${BLUE}Запустити бота зараз? (y/n)${NC}"
    read -p "> " START_NOW
    
    if [ "$START_NOW" = "y" ] || [ "$START_NOW" = "Y" ]; then
        sudo systemctl start server-bot
        echo -e "${GREEN}✅ Бот запущено${NC}"
        echo ""
        echo -e "${BLUE}Корисні команди:${NC}"
        echo "  sudo systemctl status server-bot   - статус"
        echo "  sudo systemctl restart server-bot  - перезапуск"
        echo "  sudo systemctl stop server-bot     - зупинка"
        echo "  sudo journalctl -u server-bot -f   - логи"
    else
        echo -e "${YELLOW}⚠️  Запустіть бота: sudo systemctl start server-bot${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Пропускаємо встановлення сервісу${NC}"
    echo ""
    echo -e "${BLUE}Для запуску вручну:${NC}"
    echo "  source .venv/bin/activate"
    echo "  python bot.py"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ Встановлення завершено!     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Відправте /start вашому боту в Telegram${NC}"