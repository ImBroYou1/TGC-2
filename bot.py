import os
import sys
import asyncio
import signal
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

sys.path.insert(0, str(Path(__file__).parent))

from modules.system import get_system_text, run_bash
from modules.disks import get_disk_text, get_mounted_list, mount_disk, umount_disk
from modules.network import get_network_text, check_port, get_traffic
from modules.services import get_services_text, manage_service, load_services, save_services
from modules.commands import load_commands, save_commands
from modules.console import execute_command, get_quick_commands
from modules.notifications import startup_message, save_notify_state, send_shutdown_notification, get_server_name, clear_notify_state

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ALLOWED_CHAT_ID = int(os.getenv('ALLOWED_CHAT_ID', 0))
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
SERVER_NAME = os.getenv('SERVER_NAME', 'Server')

authenticated_users = set()
user_sessions = {}
app = None

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖥️ Система", callback_data='tab_system'),
         InlineKeyboardButton("💾 Диски", callback_data='tab_disks')],
        [InlineKeyboardButton("🌐 Мережа", callback_data='tab_network'),
         InlineKeyboardButton("⚙️ Сервіси", callback_data='tab_services')],
        [InlineKeyboardButton("💻 Консоль", callback_data='tab_console'),
         InlineKeyboardButton("🛠️ Команди", callback_data='tab_commands')],
        [InlineKeyboardButton("⏻ Живлення", callback_data='tab_power'),
         InlineKeyboardButton("🔒 Вийти", callback_data='auth_logout')]
    ])

async def safe_edit(query, text, reply_markup=None, parse_mode=None):
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        if "not modified" not in str(e).lower():
            pass

async def send_startup():
    try:
        clear_notify_state()
        if ALLOWED_CHAT_ID:
            await app.bot.send_message(chat_id=ALLOWED_CHAT_ID, text=startup_message(), parse_mode=ParseMode.MARKDOWN)
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID: return
    chat_id = update.effective_chat.id
    if chat_id not in authenticated_users:
        await update.message.reply_text(f"🔐 *{SERVER_NAME}*\n\nВведіть пароль:", parse_mode=ParseMode.MARKDOWN)
        return
    await update.message.reply_text(f"🏠 *{SERVER_NAME}*", reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ALLOWED_CHAT_ID: return
    chat_id = update.effective_chat.id
    text = update.message.text
    
    if chat_id not in authenticated_users:
        if text == ADMIN_PASSWORD:
            authenticated_users.add(chat_id)
            await update.message.reply_text("✅ Доступ дозволено!")
            await update.message.reply_text(f"🏠 *{SERVER_NAME}*", reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)
        return
    
    if chat_id in user_sessions:
        await handle_session(update, context, user_sessions[chat_id], text)
        return

async def handle_session(update, context, session, text):
    chat_id = update.effective_chat.id
    if text == '/cancel':
        del user_sessions[chat_id]
        await update.message.reply_text("❌ Скасовано")
        return
    
    t = session.get('type')
    
    if t == 'console':
        del user_sessions[chat_id]
        msg = await update.message.reply_text("⏳ Виконання...")
        result = await execute_command(text)
        await msg.delete()
        await update.message.reply_text(f"💻 ```\n{result}\n```", parse_mode=ParseMode.MARKDOWN)
    
    elif t == 'create_command':
        if session['step'] == 1:
            session['name'] = text; session['step'] = 2
            await update.message.reply_text("Крок 2/3: Опис (- якщо не потрібен):")
        elif session['step'] == 2:
            session['desc'] = text if text != '-' else ''; session['step'] = 3
            await update.message.reply_text("Крок 3/3: Bash команда:")
        elif session['step'] == 3:
            cmds = load_commands()
            cmds.append({'id': str(int(datetime.now().timestamp())), 'name': session['name'], 'description': session.get('desc',''), 'bash': text, 'created': datetime.now().isoformat()})
            save_commands(cmds)
            del user_sessions[chat_id]
            await update.message.reply_text(f"✅ `{session['name']}` створено", parse_mode=ParseMode.MARKDOWN)
    
    elif t == 'edit_command':
        cid = session.get('cmd_id')
        if session['step'] == 1:
            session['name'] = text; session['step'] = 2
            await update.message.reply_text("Новий опис (- якщо не потрібен):")
        elif session['step'] == 2:
            session['desc'] = text if text != '-' else ''; session['step'] = 3
            await update.message.reply_text("Нова Bash команда:")
        elif session['step'] == 3:
            cmds = load_commands()
            for c in cmds:
                if c['id'] == cid: c['name'] = session['name']; c['description'] = session.get('desc',''); c['bash'] = text
            save_commands(cmds)
            del user_sessions[chat_id]
            await update.message.reply_text("✅ Оновлено")
    
    elif t == 'mount_disk':
        if session['step'] == 1:
            session['device'] = text; session['step'] = 2
            await update.message.reply_text("📁 Шлях:")
        elif session['step'] == 2:
            session['path'] = text; session['step'] = 3
            await update.message.reply_text("⚙️ Опції (Enter = rw,nofail):")
        elif session['step'] == 3:
            opts = text if text else "rw,nofail"
            result = await mount_disk(session['device'], session['path'], opts)
            del user_sessions[chat_id]
            await update.message.reply_text(f"```\n{result}\n```", parse_mode=ParseMode.MARKDOWN)
    
    elif t == 'check_port':
        del user_sessions[chat_id]
        msg = await update.message.reply_text(f"🔍 Порт {text}...")
        result = await check_port(text)
        await msg.delete()
        await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
    
    elif t == 'add_service':
        services = load_services()
        services.append(text)
        save_services(services)
        del user_sessions[chat_id]
        await update.message.reply_text(f"✅ `{text}` додано")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_chat.id != ALLOWED_CHAT_ID: return
    chat_id = update.effective_chat.id
    if chat_id not in authenticated_users:
        await query.edit_message_text("🔒 /start")
        return
    
    data = query.data
    try:
        if data == 'main_menu':
            await safe_edit(query, f"🏠 *{SERVER_NAME}*", reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'tab_system':
            text = await get_system_text()
            kbd = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Оновити", callback_data='tab_system'), InlineKeyboardButton("🏠 Меню", callback_data='main_menu')]])
            await safe_edit(query, text, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'tab_disks':
            text = await get_disk_text()
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Монтувати", callback_data='disk_mount'), InlineKeyboardButton("❌ Демонтувати", callback_data='disk_umount')],
                [InlineKeyboardButton("🔄 Оновити", callback_data='tab_disks'), InlineKeyboardButton("🏠 Меню", callback_data='main_menu')]
            ])
            await safe_edit(query, text, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'disk_mount':
            user_sessions[chat_id] = {'type': 'mount_disk', 'step': 1}
            await query.message.reply_text("🔗 Пристрій (напр: /dev/sdb1):")
        
        elif data == 'disk_umount':
            mounts = await get_mounted_list()
            if not mounts: await query.message.reply_text("Немає змонтованих"); return
            kbd = [[InlineKeyboardButton(f"❌ {m['mount']}", callback_data=f"disk_umount_{m['device']}")] for m in mounts]
            kbd.append([InlineKeyboardButton("🔙 Назад", callback_data='tab_disks')])
            await query.message.reply_text("❌ *Демонтування*", reply_markup=InlineKeyboardMarkup(kbd), parse_mode=ParseMode.MARKDOWN)
        
        elif data.startswith('disk_umount_'):
            result = await umount_disk(data.replace('disk_umount_', ''))
            await query.message.reply_text(f"```\n{result}\n```", parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'tab_network':
            text = await get_network_text()
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Порти", callback_data='net_ports'), InlineKeyboardButton("📊 Трафік", callback_data='net_traffic')],
                [InlineKeyboardButton("🔄 Оновити", callback_data='tab_network'), InlineKeyboardButton("🏠 Меню", callback_data='main_menu')]
            ])
            await safe_edit(query, text, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'net_ports':
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton("22", callback_data='net_check_22'), InlineKeyboardButton("80", callback_data='net_check_80')],
                [InlineKeyboardButton("443", callback_data='net_check_443'), InlineKeyboardButton("445", callback_data='net_check_445')],
                [InlineKeyboardButton("✏️ Свій", callback_data='net_port_custom'), InlineKeyboardButton("🔙 Назад", callback_data='tab_network')]
            ])
            await safe_edit(query, "🔍 *ПОРТИ*", reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'net_port_custom':
            user_sessions[chat_id] = {'type': 'check_port'}
            await query.message.reply_text("Введіть порт:")
        
        elif data.startswith('net_check_'):
            port = data.replace('net_check_', '')
            msg = await query.message.reply_text(f"🔍 Порт {port}...")
            result = await check_port(port)
            await msg.delete()
            await query.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'net_traffic':
            text = await get_traffic()
            kbd = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Оновити", callback_data='net_traffic'), InlineKeyboardButton("🔙 Назад", callback_data='tab_network')]])
            await safe_edit(query, text, reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'tab_services':
            services = load_services()
            text = await get_services_text()
            kbd = []
            for s in services:
                kbd.append([InlineKeyboardButton(s, callback_data='x'), InlineKeyboardButton("▶️", callback_data=f'srv_start_{s}'), InlineKeyboardButton("⏹️", callback_data=f'srv_stop_{s}'), InlineKeyboardButton("🔄", callback_data=f'srv_restart_{s}')])
            kbd.append([InlineKeyboardButton("➕ Додати", callback_data='srv_add'), InlineKeyboardButton("❌ Видалити", callback_data='srv_delete_menu')])
            kbd.append([InlineKeyboardButton("🔄 Оновити", callback_data='tab_services'), InlineKeyboardButton("🏠 Меню", callback_data='main_menu')])
            await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(kbd), parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'srv_add':
            user_sessions[chat_id] = {'type': 'add_service'}
            await query.message.reply_text("➕ Назва сервісу:")
        
        elif data == 'srv_delete_menu':
            services = load_services()
            if not services: await query.message.reply_text("Немає сервісів"); return
            kbd = [[InlineKeyboardButton(f"❌ {s}", callback_data=f'srv_delete_{s}')] for s in services]
            kbd.append([InlineKeyboardButton("🔙 Назад", callback_data='tab_services')])
            await query.message.reply_text("❌ *ВИДАЛЕННЯ*", reply_markup=InlineKeyboardMarkup(kbd), parse_mode=ParseMode.MARKDOWN)
        
        elif data.startswith('srv_delete_'):
            s = data.replace('srv_delete_', '')
            services = load_services()
            services = [x for x in services if x != s]
            save_services(services)
            await query.message.reply_text(f"✅ `{s}` видалено")
        
        elif data.startswith('srv_start_') or data.startswith('srv_stop_') or data.startswith('srv_restart_'):
            parts = data.split('_')
            result = await manage_service('_'.join(parts[2:]), parts[1])
            await query.message.reply_text(result, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'tab_console':
            quick = await get_quick_commands()
            kbd = []
            for i in range(0, len(quick), 2):
                row = [InlineKeyboardButton(cmd['name'], callback_data=f'console_quick_{cmd["cmd"]}') for cmd in quick[i:i+2]]
                kbd.append(row)
            kbd.append([InlineKeyboardButton("⌨️ Ввести", callback_data='console_input')])
            kbd.append([InlineKeyboardButton("🏠 Меню", callback_data='main_menu')])
            await safe_edit(query, "💻 *КОНСОЛЬ*", reply_markup=InlineKeyboardMarkup(kbd), parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'console_input':
            user_sessions[chat_id] = {'type': 'console'}
            await query.message.reply_text("💻 Команда:")
        
        elif data.startswith('console_quick_'):
            cmd = data.replace('console_quick_', '')
            msg = await query.message.reply_text(f"⏳ `{cmd}`...", parse_mode=ParseMode.MARKDOWN)
            result = await execute_command(cmd)
            await msg.delete()
            await query.message.reply_text(f"💻 ```\n{result}\n```", parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'tab_power':
            kbd = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Перезавантажити", callback_data='power_reboot')],
                [InlineKeyboardButton("⏻ Вимкнути", callback_data='power_shutdown')],
                [InlineKeyboardButton("🏠 Меню", callback_data='main_menu')]
            ])
            await safe_edit(query, "⏻ *ЖИВЛЕННЯ*", reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'power_reboot':
            kbd = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Так", callback_data='power_reboot_confirm'), InlineKeyboardButton("❌ Ні", callback_data='tab_power')]])
            await safe_edit(query, "⚠️ Перезавантажити?", reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'power_reboot_confirm':
            save_notify_state()
            await query.message.reply_text("🔄 Перезавантаження...")
            await run_bash("sudo reboot")
        
        elif data == 'power_shutdown':
            kbd = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Так", callback_data='power_shutdown_confirm'), InlineKeyboardButton("❌ Ні", callback_data='tab_power')]])
            await safe_edit(query, "⚠️ Вимкнути?", reply_markup=kbd, parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'power_shutdown_confirm':
            save_notify_state()
            await query.message.reply_text("⏻ Вимкнення...")
            await run_bash("sudo poweroff")
        
        elif data == 'tab_commands':
            cmds = load_commands()
            kbd = [[InlineKeyboardButton("➕ Створити", callback_data='cmd_create')]]
            if cmds:
                kbd.append([InlineKeyboardButton("📂 Виконати", callback_data='cmd_list')])
                kbd.append([InlineKeyboardButton("✏️ Редагувати", callback_data='cmd_edit_menu')])
                kbd.append([InlineKeyboardButton("❌ Видалити", callback_data='cmd_delete_menu')])
            kbd.append([InlineKeyboardButton("🏠 Меню", callback_data='main_menu')])
            await safe_edit(query, f"🛠️ *КОМАНДИ* ({len(cmds)})", reply_markup=InlineKeyboardMarkup(kbd), parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'cmd_create':
            user_sessions[chat_id] = {'type': 'create_command', 'step': 1}
            await query.message.reply_text("➕ Крок 1/3: Назва:")
        
        elif data == 'cmd_list':
            cmds = load_commands()
            if not cmds: await query.message.reply_text("Немає команд"); return
            kbd = [[InlineKeyboardButton(c['name'], callback_data=f'cmd_exec_{c["id"]}')] for c in cmds]
            kbd.append([InlineKeyboardButton("🔙 Назад", callback_data='tab_commands')])
            await safe_edit(query, "📂 *ВИКОНАННЯ*", reply_markup=InlineKeyboardMarkup(kbd), parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'cmd_edit_menu':
            cmds = load_commands()
            if not cmds: await query.message.reply_text("Немає команд"); return
            kbd = [[InlineKeyboardButton(f"✏️ {c['name']}", callback_data=f'cmd_edit_{c["id"]}')] for c in cmds]
            kbd.append([InlineKeyboardButton("🔙 Назад", callback_data='tab_commands')])
            await safe_edit(query, "✏️ *РЕДАГУВАННЯ*", reply_markup=InlineKeyboardMarkup(kbd), parse_mode=ParseMode.MARKDOWN)
        
        elif data.startswith('cmd_edit_'):
            cid = data.replace('cmd_edit_', '')
            cmds = load_commands()
            cmd = next((c for c in cmds if c['id'] == cid), None)
            if cmd:
                user_sessions[chat_id] = {'type': 'edit_command', 'cmd_id': cid, 'step': 1}
                await query.message.reply_text(f"✏️ `{cmd['name']}`\nПоточна: `{cmd['bash']}`\n\nКрок 1/3: Нова назва:", parse_mode=ParseMode.MARKDOWN)
        
        elif data == 'cmd_delete_menu':
            cmds = load_commands()
            if not cmds: await query.message.reply_text("Немає команд"); return
            kbd = [[InlineKeyboardButton(f"❌ {c['name']}", callback_data=f'cmd_delete_{c["id"]}')] for c in cmds]
            kbd.append([InlineKeyboardButton("🔙 Назад", callback_data='tab_commands')])
            await safe_edit(query, "❌ *ВИДАЛЕННЯ*", reply_markup=InlineKeyboardMarkup(kbd), parse_mode=ParseMode.MARKDOWN)
        
        elif data.startswith('cmd_exec_'):
            cid = data.replace('cmd_exec_', '')
            cmds = load_commands()
            cmd = next((c for c in cmds if c['id'] == cid), None)
            if cmd:
                msg = await query.message.reply_text(f"⏳ {cmd['name']}...")
                result = await execute_command(cmd['bash'])
                await msg.delete()
                await query.message.reply_text(f"✅ *{cmd['name']}*\n```\n{result}\n```", parse_mode=ParseMode.MARKDOWN)
        
        elif data.startswith('cmd_delete_'):
            cid = data.replace('cmd_delete_', '')
            cmds = load_commands()
            cmds = [c for c in cmds if c['id'] != cid]
            save_commands(cmds)
            await query.message.reply_text("✅ Видалено")
        
        elif data == 'auth_logout':
            authenticated_users.discard(chat_id)
            await query.edit_message_text("🔒 Сесію завершено")
    
    except Exception as e:
        if "not modified" not in str(e).lower():
            await query.message.reply_text(f"❌ {e}")

async def shutdown():
    await send_shutdown_notification(app)
    await asyncio.sleep(1)

def main():
    global app
    if not BOT_TOKEN or not ALLOWED_CHAT_ID:
        print("❌ .env не налаштовано")
        sys.exit(1)
    
    Path('data').mkdir(exist_ok=True)
    Path('temp').mkdir(exist_ok=True)
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_once(lambda _: asyncio.create_task(send_startup()), 1)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
    
    print(f"🚀 {SERVER_NAME} бот запущено")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()