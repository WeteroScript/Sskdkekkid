import os
import json
import random
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Конфигурация
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 5877790074
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Файлы
USERS_FILE = 'users_data.json'
PROMOCODES_FILE = 'promocodes.json'
BUSINESS_OWNERS_FILE = 'business_owners.json'
SETTINGS_FILE = 'settings.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def load_promocodes():
    if os.path.exists(PROMOCODES_FILE):
        with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_promocodes(promocodes):
    with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(promocodes, f, ensure_ascii=False, indent=4)

def load_business_owners():
    if os.path.exists(BUSINESS_OWNERS_FILE):
        with open(BUSINESS_OWNERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_business_owners(owners):
    with open(BUSINESS_OWNERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(owners, f, ensure_ascii=False, indent=4)

# Загрузка настроек
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"bot_enabled": True}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

# Состояния
class TradeStates(StatesGroup):
    waiting_for_amount = State()

# Стартовые данные
def get_default_user():
    return {
        "money": 1000000,
        "brcoins": 1000,
        "energy": 100,
        "total_earned": 0,
        "trades_count": 0,
        "role": "user",
        "donate_spent": 0,
        "donate_received": 0,
        "inventory": [],
        "business": None,
        "business_income": 0,
        "business_level": 1,
        "last_business_collect": datetime.now().isoformat(),
        "portfolio": {
            "BTC": 0,
            "WETcoin": 0,
            "BRcoins": 0
        }
    }

# Курсы валют
class CurrencyRates:
    def __init__(self):
        self.rates = {
            "BTC": {"price": 150000, "min": 100000, "max": 300000, "avg": 150000},
            "WETcoin": {"price": 600000, "min": 500000, "max": 5000000, "avg": 600000},
            "BRcoins": {"price": 50000000, "min": 10000000, "max": 150000000, "avg": 50000000}
        }
    
    def update_rates(self):
        for currency in self.rates:
            rand = random.random()
            if rand < 0.10:
                new_price = 0
            elif rand < 0.50:
                new_price = self.rates[currency]["avg"] * random.uniform(0.3, 0.9)
            else:
                new_price = self.rates[currency]["max"] * random.uniform(0.8, 1.0)
            
            self.rates[currency]["price"] = max(0, min(self.rates[currency]["max"], new_price))
            self.rates[currency]["price"] = round(self.rates[currency]["price"], 0)

currency_rates = CurrencyRates()

# Бизнесы
BUSINESSES = {
    "Технический центр": {
        "price": 1000000000, 
        "income": 200000000, 
        "level_multiplier": 1.1,
        "description": "Ремонт и обслуживание техники"
    },
    "Шиномонтажный центр": {
        "price": 1000000000, 
        "income": 200000000, 
        "level_multiplier": 1.1,
        "description": "Замена и ремонт шин"
    },
    "СТО": {
        "price": 500000000, 
        "income": 100000000, 
        "level_multiplier": 1.1,
        "description": "Станция технического обслуживания"
    },
    "24/7": {
        "price": 100000000, 
        "income": 50000000, 
        "level_multiplier": 1.1,
        "description": "Круглосуточный магазин"
    }
}

# Контейнер
CONTAINERS = {
    "Особый контейнер": {
        "price": 240000000,
        "items": [
            {"name": "BMW M5 CS", "price": 150000000, "chance": 0.34},
            {"name": "BUGATTI BOLIDE", "price": 555000000, "chance": 0.25},
            {"name": "SSG 003", "price": 1500000000, "chance": 0.10},
            {"name": "Zaz 968", "price": 10000, "chance": 0.70},
            {"name": "Rolls Royce Cullinan", "price": 100000000, "chance": 0.50}
        ]
    }
}

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_bot_enabled():
    settings = load_settings()
    return settings.get("bot_enabled", True)

# Проверка доступа (декоратор для команд и колбэков)
async def check_access(message_or_callback):
    """Проверяет, имеет ли пользователь доступ к боту"""
    user_id = message_or_callback.from_user.id
    
    # Админы всегда имеют доступ
    if is_admin(user_id):
        return True
    
    # Проверяем включен ли бот
    if not is_bot_enabled():
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer("🔧 Бот на техническом обслуживании! Доступ временно ограничен.")
        elif isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.answer("🔧 Бот на техническом обслуживании!", show_alert=True)
        return False
    
    return True

# Главное меню
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="💼 Работы", callback_data="works")],
        [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
        [InlineKeyboardButton(text="💎 Донат", callback_data="donate")],
        [InlineKeyboardButton(text="🏆 Форбс", callback_data="forbes")],
        [InlineKeyboardButton(text="🚗 Контейнеры", callback_data="containers")],
        [InlineKeyboardButton(text="🏪 Бизнесы", callback_data="businesses")],
        [InlineKeyboardButton(text="🏠 Гараж", callback_data="garage")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ---------- АДМИН-КОМАНДЫ ----------

# Команда /technical (on/off) - включение/выключение бота
@dp.message(Command("technical"))
async def technical_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды!")
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Использование: /technical on  или  /technical off")
        return
    
    status = parts[1].lower()
    if status not in ["on", "off"]:
        await message.answer("❌ Используйте 'on' или 'off'")
        return
    
    settings = load_settings()
    settings["bot_enabled"] = (status == "on")
    save_settings(settings)
    
    status_text = "✅ ВКЛЮЧЕН" if status == "on" else "❌ ВЫКЛЮЧЕН"
    await message.answer(f"🔧 Доступ к боту {status_text}!\n\nАдмины всегда имеют доступ.")

# Проверка статуса бота (для админов)
@dp.message(Command("status"))
async def status_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    settings = load_settings()
    status = "✅ Включен" if settings.get("bot_enabled", True) else "❌ Выключен"
    await message.answer(f"🔧 Статус бота: {status}")

@dp.message(Command("mailall"))
async def mail_all(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    text = message.text.replace("/mailall", "").strip()
    if not text:
        await message.answer("❌ Пример: /mailall Привет всем!")
        return
    
    users = load_users()
    sent = 0
    for user_id in users:
        try:
            await bot.send_message(int(user_id), f"📢 Рассылка:\n\n{text}")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    
    await message.answer(f"✅ Отправлено {sent} пользователям!")

@dp.message(Command("giverub"))
async def give_rub(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Использование: /giverub @username кол-во")
        return
    
    username = parts[1].replace("@", "")
    amount = int(parts[2])
    
    users = load_users()
    found = False
    for user_id, data in users.items():
        try:
            user = await bot.get_chat(int(user_id))
            if user.username and user.username.lower() == username.lower():
                data["money"] += amount
                data["total_earned"] += amount
                found = True
                save_users(users)
                await message.answer(f"✅ @{username} +{amount:,}₽")
                try:
                    await bot.send_message(int(user_id), f"💰 +{amount:,}₽ от админа!")
                except:
                    pass
                break
        except:
            continue
    
    if not found:
        await message.answer(f"❌ @{username} не найден!")

@dp.message(Command("givedonate"))
async def give_donate(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Использование: /givedonate @username кол-во")
        return
    
    username = parts[1].replace("@", "")
    amount = int(parts[2])
    
    users = load_users()
    found = False
    for user_id, data in users.items():
        try:
            user = await bot.get_chat(int(user_id))
            if user.username and user.username.lower() == username.lower():
                data["brcoins"] += amount
                data["donate_received"] += amount
                found = True
                save_users(users)
                await message.answer(f"✅ @{username} +{amount} BRcoins")
                try:
                    await bot.send_message(int(user_id), f"💎 +{amount} BRcoins от админа!")
                except:
                    pass
                break
        except:
            continue
    
    if not found:
        await message.answer(f"❌ @{username} не найден!")

@dp.message(Command("createpromo"))
async def create_promo(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("❌ Использование: /createpromo (1/0) (кол-во использований) (кол-во валюты)\n1 - BRcoins, 0 - рубли")
        return
    
    promo_type = int(parts[1])
    uses = int(parts[2])
    amount = int(parts[3])
    
    import string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    promocodes = load_promocodes()
    promocodes[code] = {
        "type": "brcoins" if promo_type == 1 else "money",
        "uses": uses,
        "used": 0,
        "amount": amount
    }
    save_promocodes(promocodes)
    
    await message.answer(f"✅ Промокод создан!\n\nКод: `{code}`\nТип: {'BRcoins' if promo_type == 1 else 'Рубли'}\nКоличество: {amount}\nИспользований: {uses}")

# ---------- СТАРТ ----------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    # Проверка доступа
    if not await check_access(message):
        return
    
    user_id = str(message.from_user.id)
    users = load_users()
    
    if user_id not in users:
        users[user_id] = get_default_user()
        save_users(users)
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\nДобро пожаловать!",
        reply_markup=main_menu_keyboard()
    )

# ---------- ВСЕ КОЛБЭКИ С ПРОВЕРКОЙ ДОСТУПА ----------
@dp.callback_query(F.data == "works")
async def works_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    keyboard = [
        [InlineKeyboardButton(text="🚛 Дальнобойщик", callback_data="work_trucker")],
        [InlineKeyboardButton(text="🤿 Водолаз", callback_data="work_diver")],
        [InlineKeyboardButton(text="📈 Трейдинг", callback_data="work_trading")],
        [InlineKeyboardButton(text="🌾 Фермер", callback_data="work_farmer")],
        [InlineKeyboardButton(text="⛏️ Шахтёр", callback_data="work_miner")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text("💼 Выберите работу:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

# ... (остальные обработчики остаются без изменений, 
# но в каждый нужно добавить проверку if not await check_access(callback): return)

# ---------- НАЗАД ----------
@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    await callback.message.edit_text("👋 Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()

# ---------- ЗАПУСК ----------
async def main():
    print("🤖 Бот запущен!")
    print(f"👑 Админ ID: {ADMIN_ID}")
    settings = load_settings()
    print(f"🔧 Статус бота: {'Включен' if settings.get('bot_enabled', True) else 'Выключен'}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
