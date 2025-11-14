import logging
import sqlite3
import requests
import os
import threading
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, PreCheckoutQueryHandler

BOT_TOKEN = "8182256768:AAGY8O8AoDzL0Kj8ZtguoezHW_zimq8vwvM"
ADMIN_ID = 8198714139
CHANNEL_USERNAME = "@PaulDurovGft"
PROVIDER_TOKEN = ""

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            balance INTEGER DEFAULT 0,
            referrer_id INTEGER,
            referral_count INTEGER DEFAULT 0,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gifts (
            gift_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            telegram_gift_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            gift_delivery_enabled BOOLEAN DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            gift_id INTEGER,
            status TEXT DEFAULT 'pending',
            telegram_payment_charge_id TEXT,
            ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            admin_notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (gift_id) REFERENCES gifts (gift_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY,
            username TEXT,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_tokens (
            token_id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM gifts")
    if cursor.fetchone()[0] == 0:
        initial_gifts = [
            ("🧸 Мишка", 15, "Милый плюшевый мишка 🧸", 5170233102089322756, 1, 1),
            ("🎁 Подарочная коробка", 25, "Красивая подарочная коробка 🎁", 5170250947678437525, 1, 1),
            ("💍 Обучальное кольцо", 100, "Обучающее кольцо для развития 💍", 5170690322832818290, 1, 1),
            ("💎 Бриллиант", 100, "Искрящийся бриллиант 💎", 5170521118301225164, 1, 1),
            ("❤️ Сердце", 15, "Символ любви и заботы ❤️", 5170145012310081615, 1, 1),
            ("💐 Букет цветов", 50, "Красивый букет цветов 💐", 5170314324215857265, 1, 1),
            ("🌹 Роза", 25, "Красная роза 🌹", 5168103777563050263, 1, 1),
            ("🍾 Шампанское", 50, "Бутылка шампанского 🍾", 6028601630662853006, 1, 1),
            ("🏆 Кубок", 100, "Победный кубок 🏆", 5168043875654172773, 1, 1),
            ("🚀 Ракета", 50, "Стильная ракета 🚀", 5170564780938756245, 1, 1),
            ("🎂 Торт", 50, "Вкусный торт 🎂", 5170144170496491616, 1, 1),
            ("🎭 Маска", 75, "Загадочная маска 🎭", None, 1, 1),
            ("🎒 Рюкзак", 75, "Стильный рюкзак 🎒", None, 1, 1),
            ("📅 Календарь", 75, "Красивый календарь 📅", None, 1, 1),
            ("🍭 Лолипоп", 75, "Сладкий леденец 🍭", None, 1, 1)
        ]
        cursor.executemany("INSERT INTO gifts (name, price, description, telegram_gift_id, is_active, gift_delivery_enabled) VALUES (?, ?, ?, ?, ?, ?)", initial_gifts)
    
    cursor.execute("INSERT OR IGNORE INTO admins (admin_id, username) VALUES (?, ?)", (ADMIN_ID, "owner"))
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_confirm', 'true')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('referral_gifts_enabled', 'true')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_gift_delivery', 'true')")
    
    conn.commit()
    conn.close()

def get_settings():
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings")
    settings = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return settings

def update_setting(key, value):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_user(user_id):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id, username, first_name, last_name, referrer_id=None):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, referrer_id) VALUES (?, ?, ?, ?, ?)", (user_id, username, first_name, last_name, referrer_id))
    conn.commit()
    conn.close()

def get_gifts():
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gifts WHERE is_active = 1")
    gifts = cursor.fetchall()
    conn.close()
    return gifts

def get_gift(gift_id):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gifts WHERE gift_id = ?", (gift_id,))
    gift = cursor.fetchone()
    conn.close()
    return gift

def safe_get_gift(gift_id):
    gift = get_gift(gift_id)
    if gift and len(gift) < 7:
        gift = gift + (1,) * (7 - len(gift))
    return gift

def update_gift(gift_id, **kwargs):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    updates = []
    params = []
    for key, value in kwargs.items():
        if value is not None:
            updates.append(f"{key} = ?")
            params.append(value)
    if updates:
        params.append(gift_id)
        cursor.execute(f"UPDATE gifts SET {', '.join(updates)} WHERE gift_id = ?", params)
    conn.commit()
    conn.close()

def toggle_gift_delivery(gift_id):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT gift_delivery_enabled FROM gifts WHERE gift_id = ?", (gift_id,))
    result = cursor.fetchone()
    if result:
        new_status = 0 if result[0] else 1
        cursor.execute("UPDATE gifts SET gift_delivery_enabled = ? WHERE gift_id = ?", (new_status, gift_id))
    conn.commit()
    conn.close()
    return new_status if result else None

def add_gift(name, price, description, telegram_gift_id=None):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO gifts (name, price, description, telegram_gift_id, gift_delivery_enabled) VALUES (?, ?, ?, ?, 1)", (name, price, description, telegram_gift_id))
    gift_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return gift_id

def delete_gift(gift_id):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM gifts WHERE gift_id = ?", (gift_id,))
    conn.commit()
    conn.close()

def get_admins():
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins")
    admins = cursor.fetchall()
    conn.close()
    return admins

def add_admin(admin_id, username, added_by):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO admins (admin_id, username, added_by) VALUES (?, ?, ?)", (admin_id, username, added_by))
    conn.commit()
    conn.close()

def remove_admin(admin_id):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE admin_id = ? AND admin_id != ?", (admin_id, ADMIN_ID))
    conn.commit()
    conn.close()

def add_bot_token(token):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bot_tokens (token) VALUES (?)", (token,))
    conn.commit()
    conn.close()

def create_order(user_id, gift_id, telegram_payment_charge_id=None):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, gift_id, telegram_payment_charge_id) VALUES (?, ?, ?)", (user_id, gift_id, telegram_payment_charge_id))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_status(order_id, status, admin_notes=None):
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ?, admin_notes = ? WHERE order_id = ?", (status, admin_notes, order_id))
    conn.commit()
    conn.close()

def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE admin_id = ?", (user_id,))
    admin = cursor.fetchone()
    conn.close()
    return admin is not None

async def send_telegram_gift(context: ContextTypes.DEFAULT_TYPE, user_id: int, telegram_gift_id: int, message_text="🎉Смотри профиль!"):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendGift"
        payload = {"chat_id": user_id, "gift_id": telegram_gift_id, "text": message_text}
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.info(f"✅ Подарок отправлен пользователю {user_id}")
            return True
        else:
            logging.error(f"❌ Ошибка отправки подарка: {response.text}")
            return False
    except Exception as e:
        logging.error(f"❌ Исключение при отправке подарка: {e}")
        return False

async def check_subscription(user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name
    
    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id == user_id:
                referrer_id = None
        except:
            pass
    
    add_user(user_id, username, first_name, last_name, referrer_id)
    
    if referrer_id:
        conn = sqlite3.connect('gift_bot.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))
        conn.commit()
        conn.close()
    
    if await check_subscription(user_id, context):
        await show_main_menu(update, context)
    else:
        await show_subscription_request(update, context)

async def show_subscription_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋 Подпишитесь на канал чтобы использовать бота!", reply_markup=reply_markup)

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if await check_subscription(user_id, context):
        await query.edit_message_text("✅ Отлично! Загрузка меню...")
        await show_main_menu(update, context)
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Канал", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("❌ Вы еще не подписались. Подпишитесь и нажмите проверку.", reply_markup=reply_markup)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎁 Подарки", callback_data="show_gifts")],
        [InlineKeyboardButton("🎮 Игры", callback_data="show_games")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🏠 Главное меню\n\nВыбери категорию:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def show_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🎮 Игры скоро будут доступны!", reply_markup=reply_markup)

async def show_gifts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎁 Купить для себя", callback_data="buy_for_self")],
        [InlineKeyboardButton("🎁 Подарить другу", callback_data="gift_to_friend")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🎁 Выберите действие:", reply_markup=reply_markup)

async def buy_for_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gifts = get_gifts()
    keyboard = []
    for gift in gifts:
        gift_id = gift[0]
        name = gift[1]
        price = gift[2]
        keyboard.append([InlineKeyboardButton(f"{name} — {price} ⭐", callback_data=f"gift_self_{gift_id}")])
    
    keyboard.append([InlineKeyboardButton("🎁 БЕСПЛАТНЫЙ МИШКА", callback_data="free_bear")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_gifts")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🎁 Выбери подарок:", reply_markup=reply_markup)

async def gift_to_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gifts = get_gifts()
    keyboard = []
    for gift in gifts:
        gift_id = gift[0]
        name = gift[1]
        price = gift[2]
        keyboard.append([InlineKeyboardButton(f"{name} — {price} ⭐", callback_data=f"gift_friend_{gift_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_gifts")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🎁 Выбери подарок для друга:", reply_markup=reply_markup)

async def gift_friend_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gift_id = int(query.data.split('_')[2])
    gift = safe_get_gift(gift_id)
    
    if not gift:
        await query.edit_message_text("❌ Подарок не найден.")
        return
    
    context.user_data['gift_friend_id'] = gift_id
    context.user_data['gift_friend_data'] = gift
    
    await query.edit_message_text(
        f"🎁 Вы выбрали: {gift[1]}\n\n"
        f"📝 Отправьте ID друга:\n\n"
        f"💡 ID можно получить с помощью @userinfobot"
    )

async def handle_friend_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'gift_friend_id' not in context.user_data:
        return
    
    try:
        friend_id = int(update.message.text)
        gift_id = context.user_data['gift_friend_id']
        gift = context.user_data['gift_friend_data']
        
        context.user_data['target_friend_id'] = friend_id
        
        from datetime import datetime
        current_time = datetime.now().strftime('%H:%M')
        
        keyboard = [
            [InlineKeyboardButton(f"💳 Заплатить {gift[2]} ⭐", callback_data=f"pay_friend_{gift_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="gift_to_friend")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎁 Подарок для друга (ID: {friend_id})\n"
            f"💎 {gift[1]} за {gift[2]} ⭐\n"
            f"💰 {gift[2]} СЧЁТ    {current_time}\n\n"
            f"💳 Заплатить {gift[2]} ⭐",
            reply_markup=reply_markup
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Отправьте числовой ID:")

async def gift_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gift_id = int(query.data.split('_')[2])  # Исправлено: теперь берем из 2-го элемента
    gift = safe_get_gift(gift_id)
    
    if not gift:
        await query.edit_message_text("❌ Подарок не найден.")
        return
    
    from datetime import datetime
    current_time = datetime.now().strftime('%H:%M')
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Заплатить {gift[2]} ⭐", callback_data=f"pay_self_{gift_id}")],  # Исправлено: pay_self_
        [InlineKeyboardButton("🔙 Назад", callback_data="buy_for_self")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"🎁 {gift[1]}\n💎 {gift[1]} за {gift[2]} ⭐\n💰 {gift[2]} СЧЁТ    {current_time}\n\n💳 Заплатить {gift[2]} ⭐", reply_markup=reply_markup)

async def pay_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    
    # Исправленная логика обработки callback данных
    if len(data) == 3 and data[1] == 'self':
        # Для себя: pay_self_{gift_id}
        gift_id = int(data[2])
        is_for_friend = False
    elif len(data) == 3 and data[1] == 'friend':
        # Для друга: pay_friend_{gift_id}
        gift_id = int(data[2])
        is_for_friend = True
    else:
        await query.edit_message_text("❌ Ошибка обработки запроса.")
        return
    
    gift = safe_get_gift(gift_id)
    
    if not gift:
        await query.edit_message_text("❌ Подарок не найден.")
        return
    
    user_id = query.from_user.id
    
    if is_for_friend and 'target_friend_id' in context.user_data:
        payload = f"gift_friend_{gift_id}_{context.user_data['target_friend_id']}"
    else:
        payload = f"gift_self_{gift_id}"
    
    try:
        await context.bot.send_invoice(
            chat_id=user_id,
            title=gift[1],
            description=gift[3],
            payload=payload,
            provider_token=PROVIDER_TOKEN,
            currency="XTR",
            prices=[{"label": "Stars", "amount": gift[2]}],
            start_parameter="gift-purchase"
        )
        
        target_text = "для друга" if is_for_friend else "для себя"
        await query.edit_message_text(f"💎 Для оплаты {gift[1]} {target_text} проверьте инвойс выше!\n💰 Стоимость: {gift[2]} ⭐")
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка создания инвойса: {e}")

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment
    payload = payment_info.invoice_payload
    
    if payload.startswith('gift_friend_'):
        parts = payload.split('_')
        gift_id = int(parts[2])
        friend_id = int(parts[3])
        target_user_id = friend_id
        purchase_type = "friend"
    else:
        gift_id = int(payload.split('_')[2])
        target_user_id = user_id
        purchase_type = "self"
    
    gift = safe_get_gift(gift_id)
    if not gift:
        await update.message.reply_text("❌ Ошибка: подарок не найден.")
        return
    
    order_id = create_order(user_id, gift_id, payment_info.telegram_payment_charge_id)
    update_order_status(order_id, 'confirmed', 'Оплачено через Telegram Stars')
    
    await context.bot.send_message(
        ADMIN_ID,
        f"🆕 НОВАЯ ПОКУПКА!\n\n"
        f"🆔 Заказ: #{order_id}\n"
        f"👤 Покупатель: @{update.effective_user.username or 'N/A'} (ID: {user_id})\n"
        f"🎁 Подарок: {gift[1]}\n"
        f"💰 Стоимость: {gift[2]} ⭐\n"
        f"🎯 Получатель: {'Друг (ID: ' + str(target_user_id) + ')' if purchase_type == 'friend' else 'Себя'}"
    )
    
    settings = get_settings()
    auto_delivery = settings.get('auto_gift_delivery', 'true') == 'true'
    
    if gift[6] and gift[4] and auto_delivery:
        success = await send_telegram_gift(context, target_user_id, gift[4], "🎉Смотри профиль!")
        if success:
            if purchase_type == "friend":
                await update.message.reply_text(f"🎉 Заказ #{order_id} подтвержден! Подарок отправлен другу!")
            else:
                await update.message.reply_text(f"🎉 Заказ #{order_id} подтвержден! Подарок отправлен вам!")
        else:
            await update.message.reply_text(f"✅ Заказ #{order_id} подтвержден! Подарок будет доставлен скоро.")
    else:
        delivery_status = "будет доставлен вручную" if not auto_delivery else "активирован"
        if purchase_type == "friend":
            await update.message.reply_text(f"✅ Заказ #{order_id} подтвержден! Подарок для друга {delivery_status}!")
        else:
            await update.message.reply_text(f"✅ Заказ #{order_id} подтвержден! Подарок {delivery_status}!")

async def free_bear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    
    settings = get_settings()
    referral_gifts_enabled = settings.get('referral_gifts_enabled', 'true') == 'true'
    
    if not referral_gifts_enabled:
        await query.edit_message_text("❌ Бесплатные подарки временно отключены.")
        return
    
    if user and user[6] >= 5:
        gifts = get_gifts()
        bear_id = None
        for gift in gifts:
            if "🧸" in gift[1]:
                bear_id = gift[0]
                break
        
        if bear_id:
            gift_data = safe_get_gift(bear_id)
            if gift_data:
                order_id = create_order(user_id, bear_id)
                update_order_status(order_id, 'confirmed', 'Бесплатный мишка за рефералов')
                
                settings = get_settings()
                auto_delivery = settings.get('auto_gift_delivery', 'true') == 'true'
                
                if gift_data[6] and gift_data[4] and auto_delivery:
                    await send_telegram_gift(context, user_id, gift_data[4], "🎉Смотри профиль!")
                    await query.edit_message_text(f"🎉 Вы получили бесплатного мишку за приглашение друзей!\n\n🆔 Заказ: #{order_id}")
                else:
                    await query.edit_message_text(f"🎉 Вы получили бесплатного мишку за приглашение друзей!\n\n🆔 Заказ: #{order_id}")
        else:
            await query.edit_message_text("❌ Ошибка. Попробуйте позже.")
    else:
        current_refs = user[6] if user else 0
        keyboard = [
            [InlineKeyboardButton("👥 Пригласить друзей", callback_data="invite_friends")],
            [InlineKeyboardButton("🔙 Назад", callback_data="buy_for_self")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"🎁 Получите бесплатного мишку!\n\n👥 Пригласите 5 друзей\n\n📊 Ваши приглашенные: {current_refs}/5", reply_markup=reply_markup)

async def invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="free_bear")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"👥 Приглашайте друзей!\n\n🔗 Ваша ссылка:\n`{referral_link}`\n\n💎 За 5 приглашенных - бесплатный мишка!", parse_mode="Markdown", reply_markup=reply_markup)

# РАССЫЛКА
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Нет доступа.")
        return
    
    context.user_data['awaiting_broadcast'] = True
    context.user_data['broadcast_admin'] = user_id
    
    await update.message.reply_text(
        "📢 РАССЫЛКА\n\n"
        "Ответьте на это сообщение тем, что хотите разослать.\n\n"
        "❌ Для отмены: /cancel"
    )

async def handle_broadcast_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if (not context.user_data.get('awaiting_broadcast') or 
        context.user_data.get('broadcast_admin') != user_id):
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на мое сообщение.")
        return
    
    context.user_data['broadcast_message'] = update.message
    context.user_data['awaiting_broadcast'] = False
    
    total_users = len(get_all_users())
    
    preview_text = "📋 ПРЕДПРОСМОТР:\n\n"
    
    if update.message.text:
        preview_text += f"📝 {update.message.text[:100]}"
        if len(update.message.text) > 100:
            preview_text += "..."
    elif update.message.caption:
        preview_text += f"📝 {update.message.caption[:100]}"
        if len(update.message.caption) > 100:
            preview_text += "..."
    
    preview_text += f"\n\n👥 Получателей: {total_users}"
    
    keyboard = [
        [InlineKeyboardButton("✅ Начать рассылку", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=user_id,
            photo=update.message.photo[-1].file_id,
            caption=preview_text,
            reply_markup=reply_markup
        )
    elif update.message.video:
        await context.bot.send_video(
            chat_id=user_id,
            video=update.message.video.file_id,
            caption=preview_text,
            reply_markup=reply_markup
        )
    elif update.message.document:
        await context.bot.send_document(
            chat_id=user_id,
            document=update.message.document.file_id,
            caption=preview_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(preview_text, reply_markup=reply_markup)

async def confirm_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Нет доступа.")
        return
    
    if 'broadcast_message' not in context.user_data:
        await query.edit_message_text("❌ Сообщение не найдено.")
        return
    
    await query.edit_message_text("🔄 Начинаю рассылку...")
    asyncio.create_task(run_broadcast(context, query.message.chat_id))

async def run_broadcast(context: ContextTypes.DEFAULT_TYPE, admin_chat_id: int):
    try:
        broadcast_message = context.user_data.get('broadcast_message')
        if not broadcast_message:
            await context.bot.send_message(admin_chat_id, "❌ Ошибка.")
            return
        
        users = get_all_users()
        total_users = len(users)
        successful = 0
        failed = 0
        failed_users = []
        
        progress_message = await context.bot.send_message(
            admin_chat_id,
            f"📤 Рассылка...\n👥 Всего: {total_users}\n✅ Успешно: 0\n❌ Ошибок: 0\n📊 0%"
        )
        
        for i, user_id in enumerate(users):
            try:
                if broadcast_message.text:
                    await context.bot.send_message(user_id, text=broadcast_message.text)
                elif broadcast_message.photo:
                    await context.bot.send_photo(user_id, photo=broadcast_message.photo[-1].file_id, caption=broadcast_message.caption)
                elif broadcast_message.video:
                    await context.bot.send_video(user_id, video=broadcast_message.video.file_id, caption=broadcast_message.caption)
                elif broadcast_message.document:
                    await context.bot.send_document(user_id, document=broadcast_message.document.file_id, caption=broadcast_message.caption)
                
                successful += 1
                
            except Exception as e:
                failed += 1
                failed_users.append(user_id)
            
            if (i + 1) % 10 == 0 or (i + 1) == total_users:
                progress = int((i + 1) / total_users * 100)
                try:
                    await context.bot.edit_message_text(
                        chat_id=admin_chat_id,
                        message_id=progress_message.message_id,
                        text=f"📤 Рассылка...\n👥 Всего: {total_users}\n✅ Успешно: {successful}\n❌ Ошибок: {failed}\n📊 {progress}%"
                    )
                except:
                    pass
            
            await asyncio.sleep(0.1)
        
        report_text = (
            f"🎉 РАССЫЛКА ЗАВЕРШЕНА!\n\n"
            f"📊 СТАТИСТИКА:\n"
            f"👥 Всего: {total_users}\n"
            f"✅ Успешно: {successful}\n"
            f"❌ Ошибок: {failed}\n"
            f"📈 Эффективность: {int(successful/total_users*100) if total_users > 0 else 0}%\n\n"
        )
        
        if failed > 0:
            report_text += f"📋 Ошибки у {failed} пользователей\n"
        
        report_text += "\n📨 ОТПРАВЛЕНО:\n"
        if broadcast_message.text:
            preview = broadcast_message.text[:50] + "..." if len(broadcast_message.text) > 50 else broadcast_message.text
            report_text += f"📝 {preview}"
        elif broadcast_message.caption:
            preview = broadcast_message.caption[:50] + "..." if len(broadcast_message.caption) > 50 else broadcast_message.caption
            report_text += f"📝 {preview}"
        else:
            report_text += "📎 Медиа-сообщение"
        
        try:
            await context.bot.edit_message_text(
                chat_id=admin_chat_id,
                message_id=progress_message.message_id,
                text=report_text
            )
        except:
            await context.bot.send_message(admin_chat_id, report_text)
        
        context.user_data.pop('broadcast_message', None)
        context.user_data.pop('awaiting_broadcast', None)
        context.user_data.pop('broadcast_admin', None)
        
    except Exception as e:
        await context.bot.send_message(admin_chat_id, f"❌ Ошибка: {e}")

async def cancel_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    context.user_data.pop('awaiting_broadcast', None)
    context.user_data.pop('broadcast_message', None)
    context.user_data.pop('broadcast_admin', None)
    
    await query.edit_message_text("❌ Рассылка отменена.")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    if context.user_data.get('awaiting_broadcast'):
        context.user_data.pop('awaiting_broadcast', None)
        context.user_data.pop('broadcast_message', None)
        context.user_data.pop('broadcast_admin', None)
        await update.message.reply_text("❌ Рассылка отменена.")

# АДМИН ПАНЕЛЬ
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Нет доступа.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📦 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton("🎁 Подарки", callback_data="admin_gifts")],
        [InlineKeyboardButton("🎯 Выдача", callback_data="admin_gift_delivery")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_system_settings")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Админы", callback_data="admin_admins")],
        [InlineKeyboardButton("🤖 Создать бота", callback_data="admin_create_bot")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👨‍💻 Админ-панель:", reply_markup=reply_markup)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'confirmed'")
    confirmed_orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(price) FROM orders JOIN gifts ON orders.gift_id = gifts.gift_id WHERE status = 'confirmed'")
    total_revenue = cursor.fetchone()[0] or 0
    conn.close()
    
    stats_text = (
        f"📊 Статистика:\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"📦 Заказов: {total_orders}\n"
        f"⏳ Ожидают: {pending_orders}\n"
        f"✅ Подтверждено: {confirmed_orders}\n"
        f"💰 Доход: {total_revenue} ⭐"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(stats_text, reply_markup=reply_markup)

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.order_id, u.user_id, u.username, g.name, g.price
        FROM orders o 
        JOIN users u ON o.user_id = u.user_id 
        JOIN gifts g ON o.gift_id = g.gift_id 
        WHERE o.status = 'pending'
    ''')
    pending_orders = cursor.fetchall()
    conn.close()
    
    if not pending_orders:
        text = "📦 Нет заказов."
    else:
        text = "📦 Ожидают подтверждения:\n\n"
        for order in pending_orders:
            order_id, user_id, username, gift_name, price = order
            text += f"🆔 #{order_id}\n👤 @{username or 'N/A'} (ID: {user_id})\n🎁 {gift_name} ({price} ⭐)\n⚡ /confirm_{order_id}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def admin_gifts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    gifts = get_gifts()
    
    text = "🎁 Подарки:\n\n"
    for gift in gifts:
        text += f"{gift[1]} - {gift[2]} ⭐\nID: {gift[0]} | TG ID: {gift[4] or 'Нет'}\n\n"
    
    text += "🔧 Команды:\n/add_gift <название> <цена> <описание>\n/edit_gift_price <id> <цена>\n/delete_gift <id>"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def admin_gift_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    gifts = get_gifts()
    
    text = "🎯 Управление выдачей:\n\n"
    keyboard = []
    
    for gift in gifts:
        gift_id = gift[0]
        name = gift[1]
        delivery_status = "✅ Вкл" if gift[6] else "❌ Выкл"
        button_text = f"{name} - {delivery_status}"
        callback_data = f"toggle_delivery_{gift_id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def admin_system_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    settings = get_settings()
    auto_delivery = settings.get('auto_gift_delivery', 'true')
    referral_gifts = settings.get('referral_gifts_enabled', 'true')
    
    text = (
        f"⚙️ Настройки:\n\n"
        f"• Автовыдача: {'✅ ВКЛ' if auto_delivery == 'true' else '❌ ВЫКЛ'}\n"
        f"• Реферальные подарки: {'✅ ВКЛ' if referral_gifts == 'true' else '❌ ВЫКЛ'}\n\n"
        f"🔧 Команды:\n"
        f"/toggle_auto_delivery\n"
        f"/toggle_referral_gifts"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 Автовыдача", callback_data="toggle_auto_delivery")],
        [InlineKeyboardButton("🎁 Реферальные", callback_data="toggle_referral_gifts")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    total_users = len(get_all_users())
    
    text = (
        f"📢 Рассылка\n\n"
        f"👥 Пользователей: {total_users}\n\n"
        f"⚡ Для начала: /broadcast"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Начать", callback_data="start_broadcast_callback")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def start_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    context.user_data['awaiting_broadcast'] = True
    context.user_data['broadcast_admin'] = user_id
    
    await query.edit_message_text(
        "📢 Ответьте на это сообщение тем, что хотите разослать.\n\n"
        "❌ /cancel для отмены"
    )

async def admin_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    admins = get_admins()
    
    text = "👥 Админы:\n\n"
    for admin in admins:
        text += f"🆔 {admin[0]}\n👤 @{admin[1] or 'N/A'}\n\n"
    
    text += "🔧 Команды:\n/add_admin <id> <username>\n/remove_admin <id>"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def admin_create_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    text = "🤖 Создать бота:\n\nОтправьте: /create_bot <token>\n\n📝 Получите токен у @BotFather"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup)

async def toggle_auto_delivery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    settings = get_settings()
    current_status = settings.get('auto_gift_delivery', 'true')
    new_status = 'false' if current_status == 'true' else 'true'
    update_setting('auto_gift_delivery', new_status)
    status_text = "включена" if new_status == 'true' else "отключена"
    await query.edit_message_text(f"✅ Автовыдача {status_text}!")
    await admin_system_settings(update, context)

async def toggle_referral_gifts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    settings = get_settings()
    current_status = settings.get('referral_gifts_enabled', 'true')
    new_status = 'false' if current_status == 'true' else 'true'
    update_setting('referral_gifts_enabled', new_status)
    status_text = "включены" if new_status == 'true' else "отключены"
    await query.edit_message_text(f"✅ Реферальные подарки {status_text}!")
    await admin_system_settings(update, context)

async def toggle_gift_delivery_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    gift_id = int(query.data.split('_')[2])
    new_status = toggle_gift_delivery(gift_id)
    
    if new_status is not None:
        gift = get_gift(gift_id)
        if gift:
            status_text = "включена" if new_status else "отключена"
            await query.edit_message_text(f"✅ Выдача '{gift[1]}' {status_text}!")
            await admin_gift_delivery(update, context)

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    await admin_panel_callback(update, context)

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📦 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton("🎁 Подарки", callback_data="admin_gifts")],
        [InlineKeyboardButton("🎯 Выдача", callback_data="admin_gift_delivery")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_system_settings")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 Админы", callback_data="admin_admins")],
        [InlineKeyboardButton("🤖 Создать бота", callback_data="admin_create_bot")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("👨‍💻 Админ-панель:", reply_markup=reply_markup)

# КОМАНДЫ АДМИНА
async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /add_admin <user_id> <username>")
        return
    
    try:
        new_admin_id = int(context.args[0])
        username = context.args[1]
        add_admin(new_admin_id, username, user_id)
        await update.message.reply_text(f"✅ Админ {new_admin_id} добавлен!")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID")

async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /remove_admin <user_id>")
        return
    
    try:
        admin_id = int(context.args[0])
        if admin_id == ADMIN_ID:
            await update.message.reply_text("❌ Нельзя удалить главного админа!")
            return
        remove_admin(admin_id)
        await update.message.reply_text(f"✅ Админ {admin_id} удален!")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID")

async def add_gift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    if len(context.args) < 3:
        await update.message.reply_text("❌ Использование: /add_gift <название> <цена> <описание>")
        return
    
    try:
        name = ' '.join(context.args[:-2])
        price = int(context.args[-2])
        description = context.args[-1]
        gift_id = add_gift(name, price, description)
        await update.message.reply_text(f"✅ Подарок добавлен! ID: {gift_id}")
    except ValueError:
        await update.message.reply_text("❌ Неверная цена")

async def edit_gift_price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("❌ Использование: /edit_gift_price <id> <цена>")
        return
    
    try:
        gift_id = int(context.args[0])
        new_price = int(context.args[1])
        update_gift(gift_id, price=new_price)
        await update.message.reply_text(f"✅ Цена подарка #{gift_id} изменена на {new_price} ⭐!")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID или цена")

async def delete_gift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /delete_gift <id>")
        return
    
    try:
        gift_id = int(context.args[0])
        delete_gift(gift_id)
        await update.message.reply_text(f"✅ Подарок #{gift_id} удален!")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID")

async def toggle_auto_delivery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    settings = get_settings()
    current_status = settings.get('auto_gift_delivery', 'true')
    new_status = 'false' if current_status == 'true' else 'true'
    update_setting('auto_gift_delivery', new_status)
    status_text = "включена" if new_status == 'true' else "отключена"
    await update.message.reply_text(f"✅ Автовыдача {status_text}!")

async def toggle_referral_gifts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    settings = get_settings()
    current_status = settings.get('referral_gifts_enabled', 'true')
    new_status = 'false' if current_status == 'true' else 'true'
    update_setting('referral_gifts_enabled', new_status)
    status_text = "включены" if new_status == 'true' else "отключены"
    await update.message.reply_text(f"✅ Реферальные подарки {status_text}!")

async def create_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ Использование: /create_bot <token>")
        return
    
    token = context.args[0]
    
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe")
        if response.status_code == 200:
            add_bot_token(token)
            
            def run_new_bot():
                try:
                    new_app = Application.builder().token(token).build()
                    setup_bot_handlers(new_app)
                    new_app.run_polling()
                except Exception as e:
                    logging.error(f"❌ Ошибка запуска бота: {e}")
            
            threading.Thread(target=run_new_bot, daemon=True).start()
            
            await update.message.reply_text("✅ Новый бот создан и запущен!")
        else:
            await update.message.reply_text("❌ Неверный токен.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def admin_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    
    order_id = int(context.args[0])
    update_order_status(order_id, 'confirmed', f'Подтверждено админом {user_id}')
    
    conn = sqlite3.connect('gift_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.user_id, g.name, g.telegram_gift_id, g.gift_delivery_enabled 
        FROM orders o 
        JOIN gifts g ON o.gift_id = g.gift_id 
        WHERE o.order_id = ?
    ''', (order_id,))
    order_info = cursor.fetchone()
    conn.close()
    
    if order_info:
        target_user_id, gift_name, telegram_gift_id, gift_delivery_enabled = order_info
        
        settings = get_settings()
        auto_delivery = settings.get('auto_gift_delivery', 'true') == 'true'
        
        if gift_delivery_enabled and telegram_gift_id and auto_delivery:
            await send_telegram_gift(context, target_user_id, telegram_gift_id, "🎉Смотри профиль!")
            await context.bot.send_message(target_user_id, f"🎉 Заказ #{order_id} подтвержден! Подарок отправлен!")
    
    await update.message.reply_text(f"✅ Заказ #{order_id} подтвержден!")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Ошибка: {context.error}")

def setup_bot_handlers(application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("add_admin", add_admin_command))
    application.add_handler(CommandHandler("remove_admin", remove_admin_command))
    application.add_handler(CommandHandler("add_gift", add_gift_command))
    application.add_handler(CommandHandler("edit_gift_price", edit_gift_price_command))
    application.add_handler(CommandHandler("delete_gift", delete_gift_command))
    application.add_handler(CommandHandler("toggle_auto_delivery", toggle_auto_delivery_command))
    application.add_handler(CommandHandler("toggle_referral_gifts", toggle_referral_gifts_command))
    application.add_handler(CommandHandler("create_bot", create_bot_command))
    application.add_handler(CommandHandler("broadcast", start_broadcast))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_friend_id))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_broadcast_reply))
    
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="check_subscription"))
    application.add_handler(CallbackQueryHandler(show_main_menu, pattern="back_to_main"))
    application.add_handler(CallbackQueryHandler(show_gifts_menu, pattern="show_gifts"))
    application.add_handler(CallbackQueryHandler(show_games, pattern="show_games"))
    application.add_handler(CallbackQueryHandler(show_gifts_menu, pattern="back_to_gifts"))
    application.add_handler(CallbackQueryHandler(buy_for_self, pattern="buy_for_self"))
    application.add_handler(CallbackQueryHandler(gift_to_friend, pattern="gift_to_friend"))
    application.add_handler(CallbackQueryHandler(gift_friend_selected, pattern="^gift_friend_"))
    application.add_handler(CallbackQueryHandler(gift_selected, pattern="^gift_self_"))
    application.add_handler(CallbackQueryHandler(pay_gift, pattern="^pay_"))
    application.add_handler(CallbackQueryHandler(free_bear, pattern="free_bear"))
    application.add_handler(CallbackQueryHandler(invite_friends, pattern="invite_friends"))
    application.add_handler(CallbackQueryHandler(toggle_gift_delivery_callback, pattern="^toggle_delivery_"))
    application.add_handler(CallbackQueryHandler(toggle_auto_delivery_callback, pattern="toggle_auto_delivery"))
    application.add_handler(CallbackQueryHandler(toggle_referral_gifts_callback, pattern="toggle_referral_gifts"))
    application.add_handler(CallbackQueryHandler(confirm_broadcast_callback, pattern="confirm_broadcast"))
    application.add_handler(CallbackQueryHandler(cancel_broadcast_callback, pattern="cancel_broadcast"))
    application.add_handler(CallbackQueryHandler(start_broadcast_callback, pattern="start_broadcast_callback"))
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="admin_back"))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern="admin_stats"))
    application.add_handler(CallbackQueryHandler(admin_orders, pattern="admin_orders"))
    application.add_handler(CallbackQueryHandler(admin_gifts, pattern="admin_gifts"))
    application.add_handler(CallbackQueryHandler(admin_gift_delivery, pattern="admin_gift_delivery"))
    application.add_handler(CallbackQueryHandler(admin_system_settings, pattern="admin_system_settings"))
    application.add_handler(CallbackQueryHandler(admin_broadcast, pattern="admin_broadcast"))
    application.add_handler(CallbackQueryHandler(admin_admins, pattern="admin_admins"))
    application.add_handler(CallbackQueryHandler(admin_create_bot, pattern="admin_create_bot"))
    
    application.add_handler(MessageHandler(filters.Regex(r'^/confirm_\d+'), admin_confirm_order))
    application.add_error_handler(error_handler)

def main():
    if os.path.exists('gift_bot.db'):
        os.remove('gift_bot.db')
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    setup_bot_handlers(application)
    application.run_polling()

if __name__ == '__main__':
    main()