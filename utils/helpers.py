from typing import Union
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS, bot, logger
from database.file_manager import load_disabled_functions, load_users, save_users
from models.user import UserModel

def get_default_user():
    """Дефолтный пользователь"""
    return UserModel.get_default()

async def is_admin(user_id: Union[int, str]) -> bool:
    """Проверка на админа"""
    return int(user_id) in ADMIN_IDS

async def check_subscription(user_id: int) -> bool:
    """Проверка подписки на канал"""
    try:
        from config import CHANNEL_ID
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status not in ['left', 'kicked']
    except Exception as e:
        logger.warning(f"Ошибка проверки подписки: {e}")
        return True

async def check_access(message_or_callback: Union[Message, CallbackQuery]) -> bool:
    """Проверяет доступ пользователя"""
    from database.file_manager import load_settings
    
    user_id = str(message_or_callback.from_user.id)
    
    # Проверка бана
    users = await load_users()
    if user_id in users and users[user_id].get("banned", False):
        await message_or_callback.answer("🚫 Вы забанены!", show_alert=True)
        return False
    
    # Проверка включения бота
    settings = await load_settings()
    if not settings.get("bot_enabled", True):
        if not await is_admin(int(user_id)):
            await message_or_callback.answer(
                "🔧 Бот на техническом обслуживании!", 
                show_alert=True
            )
            return False
    
    return True

async def is_function_disabled(function_id: str) -> bool:
    """Проверяет, отключена ли функция"""
    disabled = await load_disabled_functions()
    return function_id in disabled.get("functions", [])

async def get_user_data(user_id: str) -> dict:
    """Получает данные пользователя"""
    users = await load_users()
    return users.get(user_id, get_default_user())

async def save_user_data(user_id: str, user_data: dict):
    """Сохраняет данные пользователя"""
    users = await load_users()
    users[user_id] = user_data
    await save_users(users)

def get_stars_display(stars: int) -> str:
    """Звёзды для аукциона"""
    return "⭐" * stars + "☆" * (5 - stars)

def get_rarity_color(rarity: str) -> str:
    """Цвет для редкости"""
    colors = {
        "Экзотическая": "🟣",
        "Легендарная": "🟠",
        "Очень редкая": "🔴",
        "Редкая": "🟡",
        "Доступная": "🟢"
    }
    return colors.get(rarity, "⚪")
