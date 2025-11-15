import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройки
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8182256768:AAGY8O8AoDzL0Kj8ZtguoezHW_zimq8vwvM')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton("🎁 Подарки", callback_data="show_gifts")],
        [InlineKeyboardButton("📊 Профиль", callback_data="show_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n"
        f"Бот работает на Scalingo! 🚀",
        reply_markup=reply_markup
    )

async def show_gifts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🧸 Мишка - 15 ⭐", callback_data="gift_1")],
        [InlineKeyboardButton("🎁 Коробка - 25 ⭐", callback_data="gift_2")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🎁 Выбери подарок:",
        reply_markup=reply_markup
    )

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📊 Твой профиль:\n"
        f"👤 Имя: {user.first_name}\n"
        f"🆔 ID: {user.id}\n"
        f"💰 Баланс: 0 ⭐",
        reply_markup=reply_markup
    )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🎁 Подарки", callback_data="show_gifts")],
        [InlineKeyboardButton("📊 Профиль", callback_data="show_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏠 Главное меню:",
        reply_markup=reply_markup
    )

async def handle_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gift_id = query.data.split('_')[1]
    gifts = {"1": "🧸 Мишка", "2": "🎁 Коробка"}
    prices = {"1": "15", "2": "25"}
    
    gift_name = gifts.get(gift_id, "Подарок")
    price = prices.get(gift_id, "0")
    
    await query.edit_message_text(
        f"🎁 {gift_name}\n"
        f"💰 Цена: {price} ⭐\n\n"
        f"✅ Функция покупки будет добавлена позже!"
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_gifts, pattern="show_gifts"))
    application.add_handler(CallbackQueryHandler(show_profile, pattern="show_profile"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="back_main"))
    application.add_handler(CallbackQueryHandler(handle_gift, pattern="^gift_"))
    
    logging.info("🤖 Бот запускается...")
    application.run_polling()

if __name__ == '__main__':
    main()
