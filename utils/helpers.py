from typing import Union, Dict, Tuple
import random
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS, bot, logger
from database.file_manager import (
    load_disabled_functions, load_users, save_users,
    add_user_car, get_user_cars
)
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
    
    users = await load_users()
    if user_id in users and users[user_id].get("banned", False):
        await message_or_callback.answer("🚫 Вы забанены!", show_alert=True)
        return False
    
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


# ==========================================
# ===== РЕФЕРАЛЬНАЯ СИСТЕМА =====
# ==========================================

async def generate_referral_link(user_id: str) -> str:
    """Генерирует реферальную ссылку"""
    me = await bot.get_me()
    return f"https://t.me/{me.username}?start=ref_{user_id}"

def generate_captcha() -> Tuple[str, list]:
    """Генерирует капчу: (правильный_эмодзи, список_эмодзи)"""
    CAPTCHA_EMOJIS = ["🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍑", "🍒", "🥝", "🍍", "🥭"]
    correct = random.choice(CAPTCHA_EMOJIS)
    others = random.sample([e for e in CAPTCHA_EMOJIS if e != correct], 5)
    emojis = [correct] + others
    random.shuffle(emojis)
    return correct, emojis

def get_referral_reward(user_id: str, users: Dict) -> Tuple[Dict, str]:
    """Выдаёт награду за реферала"""
    from config import AUCTION_CARS, REFERRAL_BONUS, REFERRAL_CAR_CHANCE
    import random
    
    user = users.get(user_id, {})
    reward_text = ""
    
    user["money"] = user.get("money", 0) + REFERRAL_BONUS
    user["total_earned"] = user.get("total_earned", 0) + REFERRAL_BONUS
    reward_text = f"💰 {REFERRAL_BONUS:,}₽"
    
    if random.random() < REFERRAL_CAR_CHANCE:
        available_cars = []
        for name, data in AUCTION_CARS.items():
            stars = data.get("stars", 0)
            if stars in [3, 4, 5]:
                available_cars.append((name, data))
        
        if available_cars:
            weights = []
            for name, data in available_cars:
                stars = data.get("stars", 3)
                weight = stars ** 2
                weights.append(weight)
            
            car_name, car_data = random.choices(available_cars, weights=weights, k=1)[0]
            
            # ✅ Добавляем машину в cars.json
            import asyncio
            from database.file_manager import add_user_car
            asyncio.create_task(add_user_car(user_id, {
                "name": car_name,
                "price": car_data.get("base_price", 0),
                "from_referral": True
            }))
            
            stars = car_data.get("stars", 0)
            stars_display = "⭐" * stars + "☆" * (5 - stars)
            reward_text += f"\n🚗 Получена машина: {car_name} {stars_display}"
    
    return user, reward_text
