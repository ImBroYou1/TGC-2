import json
import asyncio
from pathlib import Path
from modules.system import run_bash

SERVICES_FILE = Path(__file__).parent.parent / 'data' / 'custom_services.json'
DEFAULT_SERVICES = ['sshd', 'smb', 'nmb', 'nginx', 'docker', 'cron']

def load_services():
    try:
        if SERVICES_FILE.exists():
            with open(SERVICES_FILE, 'r') as f:
                return json.load(f).get('services', DEFAULT_SERVICES)
    except:
        pass
    return DEFAULT_SERVICES.copy()

def save_services(services):
    SERVICES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SERVICES_FILE, 'w') as f:
        json.dump({'services': services}, f, indent=2, ensure_ascii=False)

async def get_services_text():
    services = load_services()
    text = "⚙️ *СЕРВІСИ*\n\n"
    
    for service in services:
        status = await run_bash(f"systemctl is-active {service} 2>/dev/null")
        enabled = await run_bash(f"systemctl is-enabled {service} 2>/dev/null")
        
        if status == 'active':
            icon = "🟢"
            state = "працює"
        elif status == 'inactive':
            icon = "🔴"
            state = "зупинено"
        else:
            icon = "⚪"
            state = "не знайдено"
        
        auto = " 🔁" if enabled == 'enabled' else ""
        text += f"{icon} `{service}` — {state}{auto}\n"
    
    return text

async def manage_service(service, action):
    actions = {
        'start': '▶️ Запуск',
        'stop': '⏹️ Зупинка',
        'restart': '🔄 Перезапуск',
        'enable': '🔁 Автозапуск',
        'disable': '🚫 Без автозапуску'
    }
    desc = actions.get(action, action)
    result = await run_bash(f"sudo systemctl {action} {service} 2>&1", timeout=15)
    
    await asyncio.sleep(0.5)
    status = await run_bash(f"systemctl is-active {service} 2>/dev/null")
    status_text = "🟢 працює" if status == 'active' else "🔴 зупинено"
    
    return f"{desc} `{service}`: {status_text}\n```\n{result if result else '✅ OK'}\n```"