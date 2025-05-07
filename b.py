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
RESELLERS = {}
bot_access_free = False
attacked_ips = set()
approved_users = {}
user_data = {}
redeem_codes = {}
used_redeem_codes = {}

# Command: /start
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("/attack", callback_data='attack')],
        [InlineKeyboardButton("/login", callback_data='login')],
        [InlineKeyboardButton("/redeem", callback_data='redeem')],
        [InlineKeyboardButton("/help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 Welcome to the Bot!\n\nUse the buttons below to navigate:",
        reply_markup=reply_markup
    )

# Command: /help
async def help_command(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("/attack", callback_data='attack')],
        [InlineKeyboardButton("/login", callback_data='login')],
        [InlineKeyboardButton("/redeem", callback_data='redeem')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Here are the available commands:", reply_markup=reply_markup)

# Command: /login <password>
async def login(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if len(context.args) != 1:
        await context.bot.send_message(chat_id=chat_id, text="Usage: /login <password>")
        return

    password = context.args[0]
    if password == ADMIN_PASSWORD:
        ADMINS.add(user_id)
        keyboard = [
            [InlineKeyboardButton("/approve", callback_data='approve')],
            [InlineKeyboardButton("/genkey", callback_data='genkey')],
            [InlineKeyboardButton("/redeem", callback_data='redeem')],
            [InlineKeyboardButton("/listkeys", callback_data='listkeys')],
            [InlineKeyboardButton("/attack", callback_data='attack')],
            [InlineKeyboardButton("/addreseller", callback_data='addreseller')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text="✅ Logged in as admin!\n\nHere are your admin commands:", reply_markup=reply_markup)
    elif user_id in RESELLERS and RESELLERS[user_id]['password'] == password:
        keyboard = [
            [InlineKeyboardButton("/genresellerkey", callback_data='genresellerkey')],
            [InlineKeyboardButton("/approve", callback_data='approve')],
            [InlineKeyboardButton("/attack", callback_data='attack')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=chat_id, text="✅ Logged in as reseller!\n\nHere are your reseller commands:", reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Incorrect password.")

# Command: /addreseller <telegram_id> <password>
async def add_reseller(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if user_id not in ADMINS:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized")
        return

    if len(context.args) != 2 or not context.args[0].isdigit():
        await context.bot.send_message(chat_id=chat_id, text="Usage: /addreseller <telegram_id> <password>")
        return

    reseller_id = int(context.args[0])
    password = context.args[1]
    RESELLERS[reseller_id] = {'password': password}
    await context.bot.send_message(chat_id=chat_id, text=f"✅ Reseller {reseller_id} added with password: {password}")

# Command: /genresellerkey <days>
async def generate_reseller_key(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in RESELLERS:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized")
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await context.bot.send_message(chat_id=chat_id, text="Usage: /genresellerkey <days>")
        return

    days = int(context.args[0])
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    redeem_codes[code] = datetime.now() + timedelta(days=days)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔑 *Reseller Key Generated!*\n\n🎟️ Code: `{code}`\n🕒 Valid for: *{days}* day(s)",
        parse_mode='Markdown'
    )

# Command: /attack <ip> <port> <duration>
async def attack(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) != 3:
        await context.bot.send_message(chat_id=chat_id, text="Usage: /attack <ip> <port> <duration>")
        return

    ip, port, duration = args

    if not bot_access_free and user_id not in ADMINS and user_id not in RESELLERS:
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

    if user_id not in ADMINS and user_id not in RESELLERS:
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

# Command: /genkey <days>
async def generate_redeem(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ADMINS:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized")
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await context.bot.send_message(chat_id=chat_id, text="Usage: /genkey <days>")
        return

    days = int(context.args[0])
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    redeem_codes[code] = datetime.now() + timedelta(days=days)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔑 *Access Key Generated!*\n\n🎟️ Code: `{code}`\n🕒 Valid for: *{days}* day(s)\n\nUser can activate using: `/redeem {code}`",
        parse_mode='Markdown'
    )

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
    used_redeem_codes[code] = user_id
    approved_users[user_id] = expiration
    if user_id not in user_data:
        user_data[user_id] = {"attacks": 0, "approved_until": expiration}
    else:
        user_data[user_id]["approved_until"] = expiration

    await context.bot.send_message(chat_id=chat_id, text=f"✅ Redeem successful! Access granted until {expiration.strftime('%Y-%m-%d %H:%M:%S')}")

# Command: /listkeys
async def list_redeem_codes(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ADMINS:
        await context.bot.send_message(chat_id=chat_id, text="❌ Unauthorized")
        return

    if not redeem_codes:
        await context.bot.send_message(chat_id=chat_id, text="ℹ️ No active redeem codes.")
        return

    message = "🎟️ *Active Redeem Codes:*\n\n"
    for code, expiry in redeem_codes.items():
        message += f"🔑 `{code}` — valid until *{expiry.strftime('%Y-%m-%d %H:%M:%S')}*\n"

    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

# Run bot
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("approve", approve_user))
    application.add_handler(CommandHandler("genkey", generate_redeem))
    application.add_handler(CommandHandler("redeem", redeem_code))
    application.add_handler(CommandHandler("listkeys", list_redeem_codes))
    application.add_handler(CommandHandler("addreseller", add_reseller))
    application.add_handler(CommandHandler("genresellerkey", generate_reseller_key))
    application.run_polling()
