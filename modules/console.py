from modules.system import run_bash

async def execute_command(command):
    result = await run_bash(command, timeout=30)
    
    if len(result) > 3500:
        result = result[:3500] + "\n... (обрізано)"
    
    if not result:
        result = "✅ Виконано"
    
    return result

async def get_quick_commands():
    return [
        {"name": "📋 Аптайм", "cmd": "uptime"},
        {"name": "📊 Топ CPU", "cmd": "ps aux --sort=-%cpu | head -8"},
        {"name": "💾 Диски", "cmd": "df -h | grep -E '^/dev|Filesystem'"},
        {"name": "🧠 Пам'ять", "cmd": "free -h"},
        {"name": "🌐 Мережа", "cmd": "ip -br a"},
        {"name": "📝 Логи", "cmd": "journalctl -n 15 --no-pager"},
        {"name": "👥 Who", "cmd": "who"},
        {"name": "📦 Пакети", "cmd": "pacman -Q 2>/dev/null | wc -l || dpkg -l | wc -l"},
    ]