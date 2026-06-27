import os
from pathlib import Path

NOTIFY_FILE = Path(__file__).parent.parent / 'data' / '.shutdown_pending'

def get_server_name():
    return os.getenv('SERVER_NAME', 'Server')

def startup_message():
    return f"🟢 *{get_server_name()}* запущено!\nБот активний."

def shutdown_message():
    return f"🔴 *{get_server_name()}* вимикається..."

def save_notify_state():
    NOTIFY_FILE.parent.mkdir(parents=True, exist_ok=True)
    NOTIFY_FILE.write_text('1')

def clear_notify_state():
    if NOTIFY_FILE.exists():
        NOTIFY_FILE.unlink()

def is_shutdown_pending():
    return NOTIFY_FILE.exists()

async def send_shutdown_notification(app):
    try:
        chat_id = int(os.getenv('ALLOWED_CHAT_ID', 0))
        if chat_id:
            await app.bot.send_message(
                chat_id=chat_id,
                text=shutdown_message(),
                parse_mode='Markdown'
            )
    except:
        pass