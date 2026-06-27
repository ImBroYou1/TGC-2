import asyncio
import psutil
from datetime import datetime

async def run_bash(command, timeout=15):
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode().strip() or stderr.decode().strip()
    except asyncio.TimeoutError:
        return "⏰ Таймаут"
    except Exception as e:
        return f"❌ {e}"

async def get_system_text():
    cpu_model = await run_bash("cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d':' -f2 | xargs")
    cpu_cores = psutil.cpu_count(logical=False)
    cpu_threads = psutil.cpu_count(logical=True)
    cpu_percent = psutil.cpu_percent(interval=0.3)
    cpu_freq = psutil.cpu_freq()
    
    temp = await run_bash("cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -1")
    temp_c = f"{int(temp)/1000:.1f}°C" if temp and temp.lstrip('-').isdigit() else "Н/Д"
    
    ram = psutil.virtual_memory()
    ram_bar = '█' * int(ram.percent / 10) + '░' * (10 - int(ram.percent / 10))
    
    gpu = await run_bash("lspci | grep -iE 'vga|3d|display' | sed 's/.*controller: //' | sed 's/.*Compatible: //' | head -1 | xargs")
    
    uptime = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
    d = uptime.days
    h, rem = divmod(uptime.seconds, 3600)
    m = rem // 60
    uptime_str = f"{d}д {h}г {m}хв" if d else f"{h}г {m}хв"
    
    load = psutil.getloadavg()
    
    text = "🖥️ *СИСТЕМА*\n\n"
    text += f"🔥 *Процесор*\n"
    text += f"├ `{cpu_model or 'Невідомо'}`\n"
    text += f"├ Ядра/Потоки: `{cpu_cores}`/`{cpu_threads}`\n"
    if cpu_freq:
        text += f"├ Частота: `{cpu_freq.current:.0f} MHz`\n"
    text += f"├ Використання: `{cpu_percent}%`\n"
    text += f"└ Температура: `{temp_c}`\n\n"
    
    text += f"🧠 *Пам'ять*\n"
    text += f"├ [{ram_bar}] {ram.percent}%\n"
    text += f"├ `{ram.used/(1024**3):.1f}` / `{ram.total/(1024**3):.1f}` GB\n"
    text += f"└ Доступно: `{ram.available/(1024**3):.1f}` GB\n\n"
    
    text += f"📊 *Загальне*\n"
    text += f"├ Аптайм: `{uptime_str}`\n"
    text += f"├ Load: `{load[0]:.1f} {load[1]:.1f} {load[2]:.1f}`\n"
    text += f"├ Процесів: `{len(psutil.pids())}`\n"
    text += f"└ GPU: `{gpu or 'Не виявлено'}`"
    
    return text