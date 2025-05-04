import os
import subprocess
import random
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler

# Config
TOKEN = '8015992695:AAGwkJ0yVARaAH8KRKLOQ2I9ou5ruseCPcU'
ADMIN_PASSWORD = 'shisak67'
ADMINS = set()
bot_access_free = False
attacked_ips = set()
approved_users = {}
user_data = {}
redeem_codes = {}

# Command: /login <password>
async def login(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="Usage: /login <password>")
        return
    if context.args[0] == ADMIN_PASSWORD:
        ADMINS.add(user_id)
        await context.bot.send_message(chat_id=chat_id, text="✅ Logged in as admin!")
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Incorrect password.")

# Command: /start
async def start(update: Update, context: CallbackContext):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome! Use /attack <ip> <port> <duration> to launch an attack.")

# Command: /attack <ip> <port> <duration>
async def attack(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="Usage: /attack <ip> <port> <duration>")
        return

    ip, port, duration = args

    if not bot_access_free and user_id not in ADMINS:
        expiration = approved_users.get(user_id)
        if not expiration or expiration < datetime.now():
            await context.bot.send_message(chat_id=chat_id, text="❌ You are not authorized to use this command right now.")
            return

    if ip in attacked_ips:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ This IP has already been attacked.")
        return

    attacked_ips.add(ip)

    if user_id not in user_data:
        user_data[user_id] = {"attacks": 0, "approved_until": approved_users.get(user_id)}

    user_data[user_id]["attacks"] += 1

    await context.bot.send_message(chat_id=chat_id, text=f"🚀 Launching attack on {ip}:{port} for {duration}s")
    subprocess.Popen(['ping', '-c', duration, ip])
    await context.bot.send_message(chat_id=chat_id, text="✅ Attack completed")

# Command: /approve <user_id> <days>
async def approve_user(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ADMINS:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized")
        return

    if len(context.args) != 2 or not context.args[0].isdigit() or not context.args[1].isdigit():
        await context.bot.send_message(chat_id=chat_id, text="Usage: /approve <user_id> <days>")
        return

    target_id = int(context.args[0])
    days = int(context.args[1])
    expiration = datetime.now() + timedelta(days=days)
    approved_users[target_id] = expiration
    if target_id not in user_data:
        user_data[target_id] = {"attacks": 0, "approved_until": expiration}
    else:
        user_data[target_id]["approved_until"] = expiration

    await context.bot.send_message(chat_id=chat_id, text=f"✅ Approved user {target_id} for {days} day(s).")

# Command: /genredeem <days>
async def generate_redeem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ADMINS:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized")
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await context.bot.send_message(chat_id=chat_id, text="Usage: /genredeem <days>")
        return

    days = int(context.args[0])
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    redeem_codes[code] = datetime.now() + timedelta(days=days)

    await context.bot.send_message(chat_id=chat_id, text=f"🎟️ Redeem code generated: `{code}`\n📆 Valid for {days} day(s)", parse_mode='Markdown')

# Command: /redeem <code>
async def redeem_code(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="Usage: /redeem <code>")
        return

    code = context.args[0]
    if code not in redeem_codes:
        await context.bot.send_message(chat_id=chat_id, text="❌ Invalid redeem code.")
        return

    expiration = redeem_codes.pop(code)
    approved_users[user_id] = expiration
    if user_id not in user_data:
        user_data[user_id] = {"attacks": 0, "approved_until": expiration}
    else:
        user_data[user_id]["approved_until"] = expiration

    await context.bot.send_message(chat_id=chat_id, text=f"✅ Redeem successful! Access granted until {expiration.strftime('%Y-%m-%d %H:%M:%S')}")

# Command: /userinfo <user_id>
async def user_info(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ADMINS:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized")
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await context.bot.send_message(chat_id=chat_id, text="Usage: /userinfo <user_id>")
        return

    target_id = int(context.args[0])
    info = user_data.get(target_id, {"attacks": 0, "approved_until": approved_users.get(target_id)})
    approved_until = info.get("approved_until")
    now = datetime.now()
    status = f"✅ Until {approved_until.strftime('%Y-%m-%d %H:%M:%S')}" if approved_until and approved_until > now else "❌ Not approved"
    message = f"👤 User ID: `{target_id}`\n🎯 Attacks: {info['attacks']}\n🛂 Status: {status}"
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

# Command: /allusers
async def all_users(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if user_id not in ADMINS:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized")
        return

    if not user_data:
        await context.bot.send_message(chat_id=chat_id, text="ℹ️ No users found yet.")
        return

    now = datetime.now()
    message = "📋 *All Users Overview:*\n\n"
    for uid, info in user_data.items():
        approved_until = info.get("approved_until")
        status = f"✅ Until {approved_until.strftime('%Y-%m-%d %H:%M:%S')}" if approved_until and approved_until > now else "❌ Not approved"
        message += f"👤 *User ID:* `{uid}`\n   ├─ *Attacks:* {info.get('attacks', 0)}\n   └─ *Approval:* {status}\n\n"

    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

# Admin Panel (/admin)
async def admin_panel(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await context.bot.send_message(chat_id=chat_id, text="❌ Access denied.")
        return

    keyboard = [
        [InlineKeyboardButton("🔄 Toggle Access", callback_data='toggle_access')],
        [InlineKeyboardButton("🧹 Clear Attacks", callback_data='clear_attacks')],
        [InlineKeyboardButton("📋 Show All Users", callback_data='show_all_users')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="⚙️ Admin Panel", reply_markup=reply_markup)

# Handle button presses
async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id not in ADMINS:
        await query.edit_message_text(text="❌ Unauthorized")
        return

    if query.data == 'toggle_access':
        global bot_access_free
        bot_access_free = not bot_access_free
        await query.edit_message_text(text=f"Bot access is now {'✅ Enabled for all' if bot_access_free else '🔒 Restricted to admins/approved'}.")

    elif query.data == 'clear_attacks':
        attacked_ips.clear()
        await query.edit_message_text(text="🧹 Cleared attacked IPs list.")

    elif query.data == 'show_all_users':
        if not user_data:
            await context.bot.send_message(chat_id=query.message.chat_id, text="ℹ️ No users found.")
            return

        message = "📋 *All Users Overview:*\n\n"
        now = datetime.now()
        for uid, info in user_data.items():
            approved_until = info.get("approved_until")
            status = f"✅ Until {approved_until.strftime('%Y-%m-%d %H:%M:%S')}" if approved_until and approved_until > now else "❌ Not approved"
            message += f"👤 *User ID:* `{uid}`\n   ├─ *Attacks:* {info.get('attacks', 0)}\n   └─ *Approval:* {status}\n\n"

        await context.bot.send_message(chat_id=query.message.chat_id, text=message, parse_mode='Markdown')

# Run bot
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("approve", approve_user))
    application.add_handler(CommandHandler("genredeem", generate_redeem))
    application.add_handler(CommandHandler("redeem", redeem_code))
    application.add_handler(CommandHandler("userinfo", user_info))
    application.add_handler(CommandHandler("allusers", all_users))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()
    
