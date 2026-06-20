from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data.database import load_users
from data.models import get_default_user

async def get_main_menu(user_id):
    users = await load_users()
    user = users.get(str(user_id), get_default_user())
    
    text = (
        f"Главное меню\n\n"
        f"Баланс: {user['money']:,.0f}₽\n"
        f"BRcoins: {user['brcoins']}\n"
        f"BTC: {user['portfolio'].get('BTC', 0)}\n"
        f"WETcoin: {user['portfolio'].get('WETcoin', 0)}\n"
        f"NotCoin: {user['portfolio'].get('NotCoin', 0)}"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="💼 Работы", callback_data="works")],
        [InlineKeyboardButton(text="💎 Донат", callback_data="donate")],
        [InlineKeyboardButton(text="🏆 Форбс", callback_data="forbes")],
        [InlineKeyboardButton(text="🚗 Контейнеры", callback_data="containers")],
        [InlineKeyboardButton(text="🏠 Гараж", callback_data="garage")],
        [InlineKeyboardButton(text="📦 Инвентарь", callback_data="inventory_main")],
        [InlineKeyboardButton(text="🔄 Скупщик", callback_data="buyer")],
        [InlineKeyboardButton(text="🏢 Бизнес", callback_data="business")],
        [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🆘 Тех.поддержка", callback_data="support")]
    ]
    
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)
