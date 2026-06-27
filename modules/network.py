import asyncio
import json
import psutil
from modules.system import run_bash

async def get_network_text():
    local_ip = await run_bash("ip -4 route get 1.1.1.1 | awk '{print $7}' | head -1")
    if not local_ip:
        local_ip = await run_bash("hostname -I | awk '{print $1}'")
    
    pub_ip = ""
    for cmd in [
        "curl -s --max-time 3 ifconfig.me 2>/dev/null",
        "curl -s --max-time 3 icanhazip.com 2>/dev/null",
    ]:
        try:
            proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=4)
            pub_ip = stdout.decode().strip()
            if pub_ip and pub_ip.count('.') == 3:
                break
        except:
            continue
    
    net_io = psutil.net_io_counters()
    
    ssh_raw = await run_bash("ss -tnp 2>/dev/null | grep ':22 ' | grep ESTAB | awk '{print $5}' | cut -d':' -f1")
    ssh_ips = [ip.strip() for ip in ssh_raw.split('\n') if ip.strip() and ip.strip() not in ('0.0.0.0', '*')]
    
    text = "🌐 *МЕРЕЖА*\n\n"
    text += f"📡 Локальна: `{local_ip or 'Н/Д'}`\n"
    text += f"🌍 Публічна: `{pub_ip or 'Недоступний'}`\n\n"
    text += f"📊 Трафік: ↓`{net_io.bytes_recv/(1024**2):.0f}MB` ↑`{net_io.bytes_sent/(1024**2):.0f}MB`\n\n"
    text += "👤 *SSH:*\n"
    
    if ssh_ips:
        for ip in sorted(set(ssh_ips)):
            text += f"├ `{ip}`\n"
    else:
        text += "└ ✅ Немає\n"
    
    return text

async def check_port(port):
    ss_result = await run_bash(f"ss -tlnp 2>/dev/null | grep ':{port} '")
    if ss_result:
        service = await run_bash(f"ss -tlnp 2>/dev/null | grep ':{port} ' | grep -oP 'users:\\(\\(\"\\K[^\"]+'")
        return f"✅ Порт `{port}` відкритий\nСлужба: `{service or 'невідомо'}`"
    
    nc_result = await run_bash(f"nc -z -w 2 localhost {port} 2>&1 && echo 'OPEN' || echo 'CLOSED'")
    if 'OPEN' in nc_result:
        return f"✅ Порт `{port}` відкритий"
    
    return f"❌ Порт `{port}` закритий"

async def get_traffic():
    result = await run_bash("vnstat --json d 2>/dev/null")
    try:
        data = json.loads(result)
        today = data.get('interfaces', [{}])[0].get('traffic', {}).get('day', [{}])[0]
        if today:
            rx = today.get('rx', 0) / 1024 / 1024
            tx = today.get('tx', 0) / 1024 / 1024
            return f"📥 `{rx:.2f} MB`\n📤 `{tx:.2f} MB`"
    except:
        pass
    return "vnstat не встановлено"