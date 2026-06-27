import psutil
from modules.system import run_bash

async def get_disk_text():
    text = "💾 *ДИСКИ*\n\n"
    has = False
    
    for part in psutil.disk_partitions():
        if part.fstype and part.device.startswith('/dev/'):
            try:
                u = psutil.disk_usage(part.mountpoint)
                has = True
                bar = '█' * int(u.percent/10) + '░' * (10-int(u.percent/10))
                text += f"📀 `{part.device.split('/')[-1]}` ({part.fstype})\n"
                text += f"├ `{part.mountpoint}`: {u.used/(1024**3):.1f}/{u.total/(1024**3):.1f}GB\n"
                text += f"└ [{bar}] {u.percent}%\n\n"
            except:
                pass
    
    return text if has else "💾 *ДИСКИ*\n\nНемає змонтованих"

async def get_mounted_list():
    result = await run_bash("mount | grep '^/dev' | awk '{print $1,$3}'")
    if not result:
        return []
    mounts = []
    for line in result.split('\n'):
        parts = line.split()
        if len(parts) >= 2:
            mounts.append({'device': parts[0], 'mount': parts[1]})
    return mounts

async def mount_disk(device, path, options="rw,nofail"):
    return await run_bash(f"sudo mkdir -p {path} && sudo mount -o {options} {device} {path} 2>&1", timeout=30)

async def umount_disk(device):
    return await run_bash(f"sudo umount -l {device} 2>&1", timeout=15)