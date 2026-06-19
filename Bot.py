import os
import json
import random
import asyncio
import string
from datetime import datetime, timedelta
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
CHANNEL_ID = "-1004461974511"
PROMO_CHANNEL_ID = "-1003853479476"
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Файлы
DATA_DIR = '/app/shared' if os.path.exists('/app/shared') else '.'
USERS_FILE = os.path.join(DATA_DIR, 'users_data.json')
PROMOCODES_FILE = os.path.join(DATA_DIR, 'promocodes.json')
BUSINESS_OWNERS_FILE = os.path.join(DATA_DIR, 'business_owners.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory.json')

# Глобальные переменные
promo_task = None
promo_running = False
last_rates_update = datetime.now()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def load_promocodes():
    if os.path.exists(PROMOCODES_FILE):
        with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_promocodes(promocodes):
    os.makedirs(os.path.dirname(PROMOCODES_FILE), exist_ok=True)
    with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(promocodes, f, ensure_ascii=False, indent=4)

def load_business_owners():
    if os.path.exists(BUSINESS_OWNERS_FILE):
        with open(BUSINESS_OWNERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_business_owners(owners):
    os.makedirs(os.path.dirname(BUSINESS_OWNERS_FILE), exist_ok=True)
    with open(BUSINESS_OWNERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(owners, f, ensure_ascii=False, indent=4)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"bot_enabled": True, "promo_auto": False, "coinrun_enabled": False, "coinrun_total": 0}

def save_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

def load_inventory():
    if os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_inventory(inventory):
    os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, ensure_ascii=False, indent=4)

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
        "mine_attempts": 100,  # Осталось ходок в шахте
        "last_mine_reset": datetime.now().isoformat(),
        "portfolio": {
            "BTC": 0,
            "WETcoin": 0,
            "NotCoin": 0
        }
    }

# Курсы валют (обновляются каждые 5 минут)
class CurrencyRates:
    def __init__(self):
        self.rates = {
            "BTC": {"price": 900000000, "min": 700000000, "max": 1000000000, "avg": 900000000},
            "WETcoin": {"price": 290000000, "min": 250000000, "max": 350000000, "avg": 290000000},
            "NotCoin": {"price": 15000000, "min": 10000000, "max": 30000000, "avg": 15000000}
        }
        self.last_update = datetime.now()
    
    def update_rates(self):
        if (datetime.now() - self.last_update).total_seconds() < 300:  # 5 минут
            return
        
        for currency in self.rates:
            rand = random.random()
            if rand < 0.005:
                new_price = self.rates[currency]["min"]
            elif rand < 0.055:
                new_price = self.rates[currency]["max"]
            else:
                new_price = self.rates[currency]["avg"] * random.uniform(0.95, 1.05)
            
            self.rates[currency]["price"] = round(new_price)
        
        self.last_update = datetime.now()
    
    def force_update(self):
        for currency in self.rates:
            rand = random.random()
            if rand < 0.005:
                new_price = self.rates[currency]["min"]
            elif rand < 0.055:
                new_price = self.rates[currency]["max"]
            else:
                new_price = self.rates[currency]["avg"] * random.uniform(0.95, 1.05)
            
            self.rates[currency]["price"] = round(new_price)
        
        self.last_update = datetime.now()
    
    def get_time_until_update(self):
        """Возвращает секунды до следующего обновления"""
        elapsed = (datetime.now() - self.last_update).total_seconds()
        remaining = max(0, 300 - elapsed)  # 300 секунд = 5 минут
        return int(remaining)

currency_rates = CurrencyRates()

# Ресурсы для шахты
MINE_RESOURCES = [
    {"name": "Красный алмаз", "price": 50000000000, "chance": 0.0005},
    {"name": "Цветной алмаз", "price": 10000000000, "chance": 0.001},
    {"name": "Красная шпинель", "price": 5000000000, "chance": 0.004},
    {"name": "Александрит", "price": 2500000000, "chance": 0.007},
    {"name": "Рубин", "price": 1500000000, "chance": 0.015},
    {"name": "Падпараджа", "price": 750000000, "chance": 0.05},
    {"name": "Демантоид", "price": 150000000, "chance": 0.10},
    {"name": "Черный опал", "price": 10000000, "chance": 0.20},
    {"name": "Танзанит", "price": 5000000, "chance": 0.25},
    {"name": "Шпинель", "price": 1500000, "chance": 0.30}
]

# Бизнесы
BUSINESSES = {
    "Технический центр": {
        "price": 1000000000, 
        "income": 200000000, 
        "level_multiplier": 1.1,
        "description": "Ремонт и обслуживание техники",
        "max_owners": 1
    },
    "Шиномонтажный центр": {
        "price": 1000000000, 
        "income": 200000000, 
        "level_multiplier": 1.1,
        "description": "Замена и ремонт шин",
        "max_owners": 1
    },
    "СТО": {
        "price": 500000000, 
        "income": 100000000, 
        "level_multiplier": 1.1,
        "description": "Станция технического обслуживания",
        "max_owners": 1
    },
    "24/7": {
        "price": 100000000, 
        "income": 50000000, 
        "level_multiplier": 1.1,
        "description": "Круглосуточный магазин",
        "max_owners": 25
    }
}

# Контейнеры
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
    },
    "Дипломатический контейнер": {
        "price": 1500000000,
        "items": [
            {"name": "Bugatti La Voiture Noire", "price": 2000000000, "chance": 0.17},
            {"name": "Bugatti Centodieci", "price": 1500000000, "chance": 0.23},
            {"name": "Pagani Zonda", "price": 1300000000, "chance": 0.20},
            {"name": "Ford Explorer (ФСБ)", "price": 2500000000, "chance": 0.085},
            {"name": "Bugatti Divo", "price": 1000000000, "chance": 0.16},
            {"name": "Nissan 240NSX", "price": 700000000, "chance": 0.15},
            {"name": "Труповоз", "price": 5000000000, "chance": 0.005}
        ]
    },
    "Мегафон": {
        "price": 75000000,
        "items": [
            {"name": "BMW M5 CS", "price": 150000000, "chance": 0.01},
            {"name": "BMW M1", "price": 75000000, "chance": 0.30},
            {"name": "Rolls-Royce Phantom", "price": 50000000, "chance": 0.25},
            {"name": "Bentley Continental GT", "price": 55000000, "chance": 0.26},
            {"name": "Bentley Mulliner Bacalar", "price": 125000000, "chance": 0.02},
            {"name": "BMW M5 F90 (ППС)", "price": 90000000, "chance": 0.10},
            {"name": "Ocean Yacht", "price": 100000000, "chance": 0.06}
        ]
    }
}

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_bot_enabled():
    settings = load_settings()
    return settings.get("bot_enabled", True)

async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def check_access(message_or_callback):
    user_id = message_or_callback.from_user.id
    
    if is_admin(user_id):
        return True
    
    if not await check_subscription(user_id):
        channel_link = "https://t.me/+TAhbj7PhoWhhZTQ6"
        channel_username = "@WeteroRussia"
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(
                f"📢 Для использования бота подпишитесь на наш канал {channel_username}!\n\n"
                f"👉 [Подписаться]({channel_link})\n\n"
                "После подписки нажмите /start"
            )
        elif isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.answer(
                f"📢 Подпишитесь на канал {channel_username}!", 
                show_alert=True
            )
        return False
    
    if not is_bot_enabled():
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer("🔧 Бот на техническом обслуживании!")
        elif isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.answer("🔧 Бот на техобслуживании!", show_alert=True)
        return False
    
    return True

# Главное меню (обновлено с балансом)
async def get_main_menu(user_id):
    users = load_users()
    user = users.get(str(user_id), get_default_user())
    
    # Обновляем курсы для отображения
    currency_rates.update_rates()
    
    text = (
        f"👋 Главное меню\n\n"
        f"💰 Баланс: {user['money']:,.0f}₽\n"
        f"💎 BRcoins: {user['brcoins']}\n"
        f"₿ BTC: {user['portfolio'].get('BTC', 0)}\n"
        f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}\n"
        f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}\n"
        f"⛏️ Ходков: {user['mine_attempts']}/100"
    )
    
    keyboard = [
        [InlineKeyboardButton(text="💼 Работы", callback_data="works")],
        [InlineKeyboardButton(text="💎 Донат", callback_data="donate")],
        [InlineKeyboardButton(text="🏆 Форбс", callback_data="forbes")],
        [InlineKeyboardButton(text="🚗 Контейнеры", callback_data="containers")],
        [InlineKeyboardButton(text="🏪 Бизнесы", callback_data="businesses")],
        [InlineKeyboardButton(text="🏠 Гараж", callback_data="garage")],
        [InlineKeyboardButton(text="🏦 Скупщик", callback_data="buyer")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ]
    
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== АВТО-ГЕНЕРАЦИЯ ПРОМОКОДОВ ==========
async def generate_and_send_promo():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    is_brcoins = random.choice([True, False])
    
    if is_brcoins:
        amount = random.randint(100, 1000)
        uses = random.randint(1, 3)
        promo_type = "brcoins"
        type_text = "BRcoins"
    else:
        amount = random.randint(20000000, 100000000)
        uses = random.randint(3, 5)
        promo_type = "money"
        type_text = "₽"
    
    promocodes = load_promocodes()
    promocodes[code] = {
        "type": promo_type,
        "uses": uses,
        "used": 0,
        "amount": amount
    }
    save_promocodes(promocodes)
    
    try:
        message_text = (
            f"🎁 **Новый промокод!**\n\n"
            f"📌 Код: `{code}`\n"
            f"🎁 Награда: {amount:,} {type_text}\n"
            f"🔄 Активаций: {uses}\n\n"
            f"👉 Забирай быстрее!"
        )
        await bot.send_message(PROMO_CHANNEL_ID, message_text)
        print(f"✅ Промокод отправлен: {code}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

async def promo_auto_loop():
    global promo_running
    while promo_running:
        try:
            settings = load_settings()
            if settings.get("promo_auto", False):
                await generate_and_send_promo()
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        await asyncio.sleep(60)

# ========== АДМИН-КОМАНДЫ ==========
@dp.message(Command("promostart"))
async def promo_start_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    parts = message.text.split()
    if len(parts) != 2 or parts[1].lower() not in ["on", "off"]:
        await message.answer("❌ Использование: /promostart on  или  /promostart off")
        return
    
    status = parts[1].lower()
    settings = load_settings()
    settings["promo_auto"] = (status == "on")
    save_settings(settings)
    
    global promo_running, promo_task
    
    if status == "on":
        if not promo_running:
            promo_running = True
            promo_task = asyncio.create_task(promo_auto_loop())
            await message.answer("✅ Авто-генерация промокодов ЗАПУЩЕНА!")
        else:
            await message.answer("ℹ️ Уже запущена")
    else:
        if promo_running:
            promo_running = False
            if promo_task:
                promo_task.cancel()
            await message.answer("❌ Авто-генерация ОСТАНОВЛЕНА!")

@dp.message(Command("promostatus"))
async def promo_status_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    settings = load_settings()
    status = "✅ Включена" if settings.get("promo_auto", False) else "❌ Выключена"
    await message.answer(f"📢 Статус: {status}")

@dp.message(Command("coinrun"))
async def coinrun_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    parts = message.text.split()
    if len(parts) != 2 or parts[1].lower() not in ["on", "off"]:
        await message.answer("❌ Использование: /coinrun on  или  /coinrun off")
        return
    
    settings = load_settings()
    settings["coinrun_enabled"] = (parts[1].lower() == "on")
    save_settings(settings)
    await message.answer(f"🪙 Добыча BRcoins на работах {'ВКЛЮЧЕНА' if settings['coinrun_enabled'] else 'ВЫКЛЮЧЕНА'}!")

@dp.message(Command("coinrunstatus"))
async def coinrun_status_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    settings = load_settings()
    total = settings.get("coinrun_total", 0)
    await message.answer(f"📊 Всего добыто BRcoins через CoinRun: {total:,}")

@dp.message(Command("technical"))
async def technical_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    parts = message.text.split()
    if len(parts) != 2 or parts[1].lower() not in ["on", "off"]:
        await message.answer("❌ Использование: /technical on  или  /technical off")
        return
    
    settings = load_settings()
    settings["bot_enabled"] = (parts[1].lower() == "on")
    save_settings(settings)
    await message.answer(f"🔧 Бот {'ВКЛЮЧЕН' if settings['bot_enabled'] else 'ВЫКЛЮЧЕН'}!")

@dp.message(Command("status"))
async def status_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    settings = load_settings()
    await message.answer(
        f"🔧 Бот: {'✅ Включен' if settings.get('bot_enabled', True) else '❌ Выключен'}\n"
        f"📢 Промокоды: {'✅ Включены' if settings.get('promo_auto', False) else '❌ Выключены'}\n"
        f"🪙 CoinRun: {'✅ Включен' if settings.get('coinrun_enabled', False) else '❌ Выключен'}\n"
        f"📊 Всего добыто BRcoins: {settings.get('coinrun_total', 0):,}"
    )

@dp.message(Command("getdb"))
async def get_db(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    await message.answer("📦 Собираю базу...")
    files_sent = 0
    for file in [USERS_FILE, PROMOCODES_FILE, BUSINESS_OWNERS_FILE, SETTINGS_FILE, INVENTORY_FILE]:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                await message.answer_document(
                    types.BufferedInputFile(
                        f.read().encode('utf-8'),
                        filename=os.path.basename(file)
                    )
                )
                files_sent += 1
                await asyncio.sleep(0.3)
    await message.answer(f"✅ Отправлено {files_sent} файлов!")

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
            await bot.send_message(int(user_id), f"📢 {text}")
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
        await message.answer("❌ /giverub @username кол-во")
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
                save_users(users)
                await message.answer(f"✅ @{username} +{amount:,}₽")
                await bot.send_message(int(user_id), f"💰 +{amount:,}₽ от админа!")
                found = True
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
        await message.answer("❌ /givedonate @username кол-во")
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
                save_users(users)
                await message.answer(f"✅ @{username} +{amount} BRcoins")
                await bot.send_message(int(user_id), f"💎 +{amount} BRcoins от админа!")
                found = True
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
        await message.answer("❌ /createpromo (1/0) (использований) (кол-во)\n1 - BRcoins, 0 - рубли")
        return
    
    promo_type = int(parts[1])
    uses = int(parts[2])
    amount = int(parts[3])
    
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    promocodes = load_promocodes()
    promocodes[code] = {
        "type": "brcoins" if promo_type == 1 else "money",
        "uses": uses,
        "used": 0,
        "amount": amount
    }
    save_promocodes(promocodes)
    await message.answer(f"✅ Промокод создан!\nКод: `{code}`\nТип: {'BRcoins' if promo_type == 1 else 'Рубли'}\nКоличество: {amount}\nИспользований: {uses}")

@dp.message(Command("update_rates_admin"))
async def update_rates_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    currency_rates.force_update()
    await message.answer("✅ Курсы обновлены!")

# ========== СТАРТ ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    users = load_users()
    
    if user_id not in users:
        users[user_id] = get_default_user()
        save_users(users)
    
    if not await check_subscription(message.from_user.id):
        await message.answer(
            f"📢 Подпишитесь на канал @WeteroRussia!\n\n"
            f"👉 [Подписаться](https://t.me/+TAhbj7PhoWhhZTQ6)\n\n"
            "После подписки нажмите /start"
        )
        return
    
    if not await check_access(message):
        return
    
    text, keyboard = await get_main_menu(message.from_user.id)
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!",
        reply_markup=keyboard
    )
    # Отправляем отдельным сообщением с балансом
    await message.answer(text, reply_markup=keyboard)

# ========== РАБОТЫ (С ШАХТОЙ ВНУТРИ) ==========
@dp.callback_query(F.data == "works")
async def works_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    keyboard = [
        [InlineKeyboardButton(text="🤿 Водолаз", callback_data="work_diver")],
        [InlineKeyboardButton(text="📈 Трейдинг", callback_data="work_trading")],
        [InlineKeyboardButton(text="🌾 Фермер", callback_data="work_farmer")],
        [InlineKeyboardButton(text="⛏️ Шахта", callback_data="mine")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text("💼 Выберите работу:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

def add_coinrun_income(user):
    """Добавляет BRcoins за работу, если CoinRun включен"""
    settings = load_settings()
    if settings.get("coinrun_enabled", False):
        br_income = random.randint(1, 10)
        user["brcoins"] += br_income
        settings["coinrun_total"] = settings.get("coinrun_total", 0) + br_income
        save_settings(settings)
        return br_income
    return 0

@dp.callback_query(F.data == "work_diver")
async def work_diver(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    user = users[str(callback.from_user.id)]
    income = random.randint(70000, 200000)
    user["money"] += income
    user["total_earned"] += income
    
    br_income = add_coinrun_income(user)
    br_text = f"\n🪙 +{br_income} BRcoins (CoinRun)" if br_income > 0 else ""
    
    save_users(users)
    await callback.message.edit_text(f"🤿 +{income:,}₽{br_text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="works")]]))
    await callback.answer()

@dp.callback_query(F.data == "work_farmer")
async def work_farmer(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    user = users[str(callback.from_user.id)]
    income = random.randint(30000, 100000)
    user["money"] += income
    user["total_earned"] += income
    
    br_income = add_coinrun_income(user)
    br_text = f"\n🪙 +{br_income} BRcoins (CoinRun)" if br_income > 0 else ""
    
    save_users(users)
    await callback.message.edit_text(f"🌾 +{income:,}₽{br_text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="works")]]))
    await callback.answer()

# ========== ШАХТА ==========
@dp.callback_query(F.data == "mine")
async def mine_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    # Проверяем и обновляем ходки
    last_reset = datetime.fromisoformat(user["last_mine_reset"])
    if (datetime.now() - last_reset).total_seconds() > 3600:  # 1 час
        user["mine_attempts"] = min(100, user["mine_attempts"] + 10)
        user["last_mine_reset"] = datetime.now().isoformat()
        save_users(users)
    
    keyboard = [
        [InlineKeyboardButton(text="⛏️ Копать", callback_data="mine_dig")],
        [InlineKeyboardButton(text="📦 Инвентарь", callback_data="inventory_main")],
        [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="mine_info")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
    ]
    
    await callback.message.edit_text(
        f"⛏️ Шахта\n\n"
        f"🔄 Ходок осталось: {user['mine_attempts']}/100\n"
        f"⏳ Восстанавливается: +10 ходок в час\n\n"
        f"Выберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data == "mine_dig")
async def mine_dig(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if user["mine_attempts"] <= 0:
        await callback.answer("❌ Нет ходок! Подождите восстановления.", show_alert=True)
        return
    
    user["mine_attempts"] -= 1
    
    # Добыча ресурсов (70% шанс ничего не выпадет)
    resource_text = ""
    if random.random() < 0.3:  # 30% шанс найти ресурс
        total_chance = sum(r["chance"] for r in MINE_RESOURCES)
        roll = random.random() * total_chance
        cumulative = 0
        selected_resource = MINE_RESOURCES[-1]
        
        for res in MINE_RESOURCES:
            cumulative += res["chance"]
            if roll <= cumulative:
                selected_resource = res
                break
        
        # Сохраняем ресурс в инвентарь
        inventory = load_inventory()
        if user_id not in inventory:
            inventory[user_id] = []
        inventory[user_id].append(selected_resource["name"])
        save_inventory(inventory)
        
        resource_text = f"\n💎 Найден: {selected_resource['name']}!"
    else:
        resource_text = "\n😔 Ничего не найдено..."
    
    save_users(users)
    
    await callback.message.edit_text(
        f"⛏️ Вы копнули!\n\n{resource_text}\n\n"
        f"🔄 Осталось ходок: {user['mine_attempts']}/100",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛏️ Копать ещё", callback_data="mine_dig")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="mine")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "mine_info")
async def mine_info(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    text = "ℹ️ Ресурсы и шансы выпадения:\n\n"
    for i, res in enumerate(MINE_RESOURCES, 1):
        chance_percent = res["chance"] * 100
        text += f"{i}. {res['name']} - {chance_percent:.2f}% (продажа: {res['price']:,.0f}₽)\n"
    
    text += "\n📊 70% шанс ничего не выпадет"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="mine")]])
    )
    await callback.answer()

# ========== ТРЕЙДИНГ ==========
@dp.callback_query(F.data == "work_trading")
async def work_trading(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    currency_rates.update_rates()
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    # Таймер до следующего обновления
    remaining = currency_rates.get_time_until_update()
    minutes = remaining // 60
    seconds = remaining % 60
    
    keyboard = [
        [InlineKeyboardButton(text=f"₿ BTC: {currency_rates.rates['BTC']['price']:,.0f}₽", callback_data="trade_BTC")],
        [InlineKeyboardButton(text=f"💧 WETcoin: {currency_rates.rates['WETcoin']['price']:,.0f}₽", callback_data="trade_WETcoin")],
        [InlineKeyboardButton(text=f"🪙 NotCoin: {currency_rates.rates['NotCoin']['price']:,.0f}₽", callback_data="trade_NotCoin")],
        [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="trading_info")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
    ]
    
    await callback.message.edit_text(
        f"📈 Трейдинг\n\n"
        f"💰 Баланс: {user['money']:,.0f}₽\n"
        f"🪙 BRcoins: {user['brcoins']}\n\n"
        f"₿ BTC: {user['portfolio'].get('BTC', 0)}\n"
        f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}\n"
        f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}\n\n"
        f"⏳ Следующее обновление курсов: {minutes:02d}:{seconds:02d}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data == "trading_info")
async def trading_info(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    text = "ℹ️ Курсы валют:\n\n"
    for currency, data in currency_rates.rates.items():
        text += f"**{currency}**\n💰 {data['price']:,.0f}₽\n📊 Средняя: {data['avg']:,.0f}₽\n📈 Макс: {data['max']:,.0f}₽\n📉 Мин: {data['min']:,.0f}₽\n\n"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="work_trading")]]))
    await callback.answer()

@dp.callback_query(F.data.startswith("trade_"))
async def trade_currency(callback: types.CallbackQuery, state: FSMContext):
    if not await check_access(callback):
        return
    currency = callback.data.split("_")[1]
    users = load_users()
    user = users[str(callback.from_user.id)]
    price = currency_rates.rates[currency]["price"]
    
    await state.update_data(currency=currency, price=price)
    keyboard = [
        [InlineKeyboardButton(text="Купить", callback_data=f"buy_{currency}")],
        [InlineKeyboardButton(text="Продать", callback_data=f"sell_{currency}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="work_trading")]
    ]
    await callback.message.edit_text(
        f"📊 {currency}\nЦена: {price:,.0f}₽\nУ вас: {user['portfolio'].get(currency, 0)}\nБаланс: {user['money']:,.0f}₽\n\nСколько? Напишите число в чат.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(TradeStates.waiting_for_amount)
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_amount(callback: types.CallbackQuery, state: FSMContext):
    if not await check_access(callback):
        return
    currency = callback.data.split("_")[1]
    await state.update_data(action="buy", currency=currency)
    await callback.message.edit_text(f"✏️ Напишите количество {currency} для покупки:")
    await state.set_state(TradeStates.waiting_for_amount)
    await callback.answer()

@dp.callback_query(F.data.startswith("sell_"))
async def sell_amount(callback: types.CallbackQuery, state: FSMContext):
    if not await check_access(callback):
        return
    currency = callback.data.split("_")[1]
    await state.update_data(action="sell", currency=currency)
    await callback.message.edit_text(f"✏️ Напишите количество {currency} для продажи:")
    await state.set_state(TradeStates.waiting_for_amount)
    await callback.answer()

@dp.message(TradeStates.waiting_for_amount)
async def process_trade_amount(message: types.Message, state: FSMContext):
    if not await check_access(message):
        return
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("❌ Введите положительное число!")
            return
        
        data = await state.get_data()
        currency = data.get("currency")
        action = data.get("action")
        price = data.get("price")
        users = load_users()
        user = users[str(message.from_user.id)]
        
        if action == "buy":
            total = amount * price
            if user["money"] < total:
                await message.answer(f"❌ Нужно {total:,.0f}₽!")
                await state.clear()
                return
            user["money"] -= total
            user["portfolio"][currency] = user["portfolio"].get(currency, 0) + amount
            user["trades_count"] += amount
            await message.answer(f"✅ Куплено {amount} {currency} за {total:,.0f}₽")
        
        elif action == "sell":
            if user["portfolio"].get(currency, 0) < amount:
                await message.answer(f"❌ У вас только {user['portfolio'].get(currency, 0)} {currency}")
                await state.clear()
                return
            total = amount * price
            user["money"] += total
            user["portfolio"][currency] -= amount
            user["trades_count"] += amount
            await message.answer(f"✅ Продано {amount} {currency} за {total:,.0f}₽")
        
        save_users(users)
        await state.clear()
        await work_trading(types.CallbackQuery(
            message=message,
            data="work_trading",
            from_user=message.from_user,
            chat=message.chat,
            message_id=message.message_id,
            inline_message_id=None,
            chat_instance=None
        ))
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

# ========== ДОНАТ ==========
@dp.callback_query(F.data == "donate")
async def donate_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    keyboard = [
        [InlineKeyboardButton(text="💳 Купить", callback_data="donate_buy")],
        [InlineKeyboardButton(text="🎫 Промокод", callback_data="promo")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="donate_balance")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text("💎 Донат\nКурс: 1₽ = 10 BRcoins\n@weterochina", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data == "donate_buy")
async def donate_buy(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    await callback.message.edit_text("💳 Обратитесь к @weterochina", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]]))
    await callback.answer()

@dp.callback_query(F.data == "promo")
async def promo_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    await callback.message.edit_text("🎫 Введите промокод в чат", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]]))
    await callback.answer()

@dp.callback_query(F.data == "donate_balance")
async def donate_balance(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    user = users[str(callback.from_user.id)]
    await callback.message.edit_text(
        f"💰 Баланс доната\nПотрачено: {user['donate_spent']}₽\nПолучено: {user['donate_received']} BRcoins\nБаланс: {user['brcoins']} BRcoins",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]])
    )
    await callback.answer()

@dp.message(F.text)
async def handle_promo(message: types.Message):
    if not await check_access(message):
        return
    user_id = str(message.from_user.id)
    users = load_users()
    user = users.get(user_id)
    if not user:
        return
    
    promocodes = load_promocodes()
    code = message.text.upper()
    
    if code in promocodes:
        promo = promocodes[code]
        if promo["used"] >= promo["uses"]:
            await message.answer("❌ Промокод использован!")
            return
        
        if promo["type"] == "brcoins":
            user["brcoins"] += promo["amount"]
            user["donate_received"] += promo["amount"]
        else:
            user["money"] += promo["amount"]
            user["total_earned"] += promo["amount"]
        
        promo["used"] += 1
        save_promocodes(promocodes)
        save_users(users)
        await message.answer(f"✅ +{promo['amount']} {'BRcoins' if promo['type'] == 'brcoins' else '₽'}!")
    else:
        await message.answer("❌ Неверный промокод!")

# ========== ФОРБС ==========
@dp.callback_query(F.data == "forbes")
async def forbes_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    keyboard = [
        [InlineKeyboardButton(text="🏆 По деньгам", callback_data="forbes_rich")],
        [InlineKeyboardButton(text="💎 По BRcoins", callback_data="forbes_br")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text("🏆 Форбс", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data == "forbes_rich")
async def forbes_rich(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    sorted_users = sorted(users.items(), key=lambda x: x[1]["money"], reverse=True)[:10]
    if not sorted_users:
        await callback.answer("Нет данных")
        return
    text = "🏆 Топ-10 по деньгам:\n\n"
    for i, (user_id, data) in enumerate(sorted_users, 1):
        try:
            user = await bot.get_chat(int(user_id))
            username = user.username or f"User_{user_id[:5]}"
        except:
            username = f"User_{user_id[:5]}"
        text += f"{i}. @{username} — {data['money']:,.0f}₽\n"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]]))
    await callback.answer()

@dp.callback_query(F.data == "forbes_br")
async def forbes_br(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    sorted_users = sorted(users.items(), key=lambda x: x[1]["brcoins"], reverse=True)[:10]
    if not sorted_users:
        await callback.answer("Нет данных")
        return
    text = "💎 Топ-10 по BRcoins:\n\n"
    for i, (user_id, data) in enumerate(sorted_users, 1):
        try:
            user = await bot.get_chat(int(user_id))
            username = user.username or f"User_{user_id[:5]}"
        except:
            username = f"User_{user_id[:5]}"
        text += f"{i}. @{username} — {data['brcoins']} BRcoins\n"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]]))
    await callback.answer()

# ========== КОНТЕЙНЕРЫ ==========
@dp.callback_query(F.data == "containers")
async def containers_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    keyboard = []
    for name, data in CONTAINERS.items():
        keyboard.append([InlineKeyboardButton(text=f"🚗 {name} ({data['price']:,.0f}₽)", callback_data=f"container_{name}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    await callback.message.edit_text("🚗 Контейнеры:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data.startswith("container_"))
async def open_container(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    container_name = callback.data.replace("container_", "")
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    container_data = CONTAINERS.get(container_name)
    if not container_data:
        await callback.answer("❌ Не найден!")
        return
    
    if user["money"] < container_data["price"]:
        await callback.answer(f"❌ Нужно {container_data['price']:,.0f}₽!", show_alert=True)
        return
    
    user["money"] -= container_data["price"]
    
    items = container_data["items"]
    total_chance = sum(item["chance"] for item in items)
    roll = random.random() * total_chance
    cumulative = 0
    selected_item = items[-1]
    
    for item in items:
        cumulative += item["chance"]
        if roll <= cumulative:
            selected_item = item
            break
    
    user["inventory"].append({
        "name": selected_item["name"],
        "price": selected_item["price"],
        "from_container": container_name
    })
    
    save_users(users)
    await callback.message.edit_text(
        f"🚗 {container_name}!\n\n🎉 {selected_item['name']}\n💰 {selected_item['price']:,.0f}₽\n💳 Осталось: {user['money']:,.0f}₽",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="containers")]])
    )
    await callback.answer()

# ========== ГАРАЖ ==========
@dp.callback_query(F.data.startswith("car_sell_"))
async def car_sell(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    try:
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Ошибка в данных!")
            return
        car_index = int(parts[2])
    except:
        await callback.answer("❌ Ошибка в данных!")
        return
    
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    if car_index >= len(user["inventory"]):
        await callback.answer("❌ Машина не найдена!", show_alert=True)
        return
    
    car = user["inventory"][car_index]
    sell_price = int(car["price"] * 0.5)
    
    user["money"] += sell_price
    del user["inventory"][car_index]
    save_users(users)
    
    await callback.message.edit_text(
        f"💰 Продано!\n🚗 {car['name']}\n💳 Получено: {sell_price:,.0f}₽ (50% от цены)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 В гараж", callback_data="garage")]])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("car_"))
async def car_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    try:
        car_index = int(callback.data.split("_")[1])
    except:
        await callback.answer("❌ Ошибка!")
        return
    
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    if car_index >= len(user["inventory"]):
        await callback.answer("❌ Машина не найдена!")
        return
    
    car = user["inventory"][car_index]
    
    keyboard = [
        [InlineKeyboardButton(text="🔢 Номера", callback_data=f"car_plate_{car_index}")],
        [InlineKeyboardButton(text="💰 Продать (50%)", callback_data=f"car_sell_{car_index}")],
        [InlineKeyboardButton(text="🔧 Тюнинг", callback_data=f"car_tuning_{car_index}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="garage")]
    ]
    
    await callback.message.edit_text(
        f"🚗 {car['name']}\n💰 Стоимость: {car['price']:,.0f}₽\n💵 Продажа: {int(car['price'] * 0.5):,.0f}₽ (50%)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("car_plate_"))
async def car_plate(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    await callback.answer("🚫 В разработке!", show_alert=True)

@dp.callback_query(F.data.startswith("car_tuning_"))
async def car_tuning(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    await callback.answer("🚫 В разработке!", show_alert=True)

@dp.callback_query(F.data == "garage")
async def garage_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    if not user["inventory"]:
        await callback.message.edit_text(
            "🏠 Ваш гараж пуст!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]])
        )
        await callback.answer()
        return
    
    keyboard = []
    for i, car in enumerate(user["inventory"]):
        keyboard.append([InlineKeyboardButton(text=f"🚗 {car['name']}", callback_data=f"car_{i}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    
    await callback.message.edit_text(
        f"🏠 Ваш гараж ({len(user['inventory'])} машин):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

# ========== СКУПЩИК ==========
@dp.callback_query(F.data == "buyer")
async def buyer_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    user_id = str(callback.from_user.id)
    inventory = load_inventory()
    
    if user_id not in inventory or not inventory[user_id]:
        await callback.message.edit_text(
            "🏦 Скупщик\n\n"
            "❌ У вас нет ресурсов для продажи!\n"
            "Добывайте ресурсы в шахте.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]])
        )
        await callback.answer()
        return
    
    # Группируем ресурсы
    resources = {}
    for item in inventory[user_id]:
        resources[item] = resources.get(item, 0) + 1
    
    keyboard = []
    for name, count in resources.items():
        # Находим цену
        price = 0
        for r in MINE_RESOURCES:
            if r["name"] == name:
                price = r["price"]
                break
        keyboard.append([InlineKeyboardButton(
            text=f"💎 {name} — {count} шт. (продажа: {price:,.0f}₽)",
            callback_data=f"sell_resource_{name}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    
    await callback.message.edit_text(
        "🏦 Скупщик драгоценностей\n\n"
        "Выберите ресурс для продажи:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("sell_resource_"))
async def sell_resource_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    resource_name = callback.data.replace("sell_resource_", "")
    user_id = str(callback.from_user.id)
    inventory = load_inventory()
    
    if user_id not in inventory or resource_name not in inventory[user_id]:
        await callback.answer("❌ У вас нет этого ресурса!", show_alert=True)
        return
    
    # Находим цену
    price = 0
    for r in MINE_RESOURCES:
        if r["name"] == resource_name:
            price = r["price"]
            break
    
    count = inventory[user_id].count(resource_name)
    
    keyboard = [
        [InlineKeyboardButton(text="💰 Продать всё", callback_data=f"sell_all_{resource_name}")],
        [InlineKeyboardButton(text="💰 Продать 1 шт.", callback_data=f"sell_one_{resource_name}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="buyer")]
    ]
    
    await callback.message.edit_text(
        f"💎 {resource_name}\n"
        f"📦 Количество: {count} шт.\n"
        f"💰 Цена за 1 шт.: {price:,.0f}₽\n"
        f"💵 Всего: {price * count:,.0f}₽",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("sell_all_"))
async def sell_all_resources(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    resource_name = callback.data.replace("sell_all_", "")
    user_id = str(callback.from_user.id)
    inventory = load_inventory()
    users = load_users()
    user = users[user_id]
    
    if user_id not in inventory or resource_name not in inventory[user_id]:
        await callback.answer("❌ У вас нет этого ресурса!", show_alert=True)
        return
    
    count = inventory[user_id].count(resource_name)
    
    # Находим цену
    price = 0
    for r in MINE_RESOURCES:
        if r["name"] == resource_name:
            price = r["price"]
            break
    
    total = price * count
    
    # Удаляем все
    inventory[user_id] = [item for item in inventory[user_id] if item != resource_name]
    user["money"] += total
    user["total_earned"] += total
    
    save_inventory(inventory)
    save_users(users)
    
    await callback.message.edit_text(
        f"💰 Продано {count} шт. {resource_name}\n"
        f"💳 Получено: {total:,.0f}₽",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="buyer")]])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("sell_one_"))
async def sell_one_resource(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    resource_name = callback.data.replace("sell_one_", "")
    user_id = str(callback.from_user.id)
    inventory = load_inventory()
    users = load_users()
    user = users[user_id]
    
    if user_id not in inventory or resource_name not in inventory[user_id]:
        await callback.answer("❌ У вас нет этого ресурса!", show_alert=True)
        return
    
    # Находим цену
    price = 0
    for r in MINE_RESOURCES:
        if r["name"] == resource_name:
            price = r["price"]
            break
    
    # Удаляем 1 штуку
    inventory[user_id].remove(resource_name)
    user["money"] += price
    user["total_earned"] += price
    
    save_inventory(inventory)
    save_users(users)
    
    count = inventory[user_id].count(resource_name)
    
    await callback.message.edit_text(
        f"💰 Продана 1 шт. {resource_name}\n"
        f"💳 Получено: {price:,.0f}₽\n"
        f"📦 Осталось: {count} шт.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="buyer")]])
    )
    await callback.answer()

# ========== ИНВЕНТАРЬ ==========
@dp.callback_query(F.data == "inventory_main")
async def inventory_main_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    user_id = str(callback.from_user.id)
    inventory = load_inventory()
    
    if user_id not in inventory or not inventory[user_id]:
        await callback.message.edit_text(
            "📦 Ваш инвентарь пуст! Добывайте ресурсы в шахте.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]])
        )
        await callback.answer()
        return
    
    # Группируем ресурсы
    resources = {}
    for item in inventory[user_id]:
        resources[item] = resources.get(item, 0) + 1
    
    text = "📦 Ваш инвентарь:\n\n"
    for name, count in resources.items():
        price = 0
        for r in MINE_RESOURCES:
            if r["name"] == name:
                price = r["price"]
                break
        text += f"• {name} — {count} шт. (продажа: {price:,.0f}₽)\n"
    
    text += "\n💰 Для продажи используйте вкладку 'Скупщик'"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦 Перейти в Скупщик", callback_data="buyer")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
        ])
    )
    await callback.answer()

# ========== БИЗНЕСЫ (ИСПРАВЛЕНЫ) ==========
@dp.callback_query(F.data == "businesses")
async def businesses_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    keyboard = [
        [InlineKeyboardButton(text="🏪 Купить бизнес", callback_data="buy_business")],
        [InlineKeyboardButton(text="💰 Собрать доход", callback_data="collect_income")],
        [InlineKeyboardButton(text="⬆️ Апгрейд бизнеса", callback_data="upgrade_business")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text("🏪 Бизнесы", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@dp.callback_query(F.data == "buy_business")
async def buy_business_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    if user["business"]:
        await callback.answer("❌ У вас уже есть бизнес!", show_alert=True)
        return
    
    business_owners = load_business_owners()
    keyboard = []
    
    for name, data in BUSINESSES.items():
        owner_count = len(business_owners.get(name, []))
        max_owners = data.get("max_owners", 1)
        
        status = "✅" if owner_count < max_owners else "❌"
        keyboard.append([InlineKeyboardButton(
            text=f"{status} {name} - {data['price']:,.0f}₽ ({owner_count}/{max_owners})",
            callback_data=f"biz_show_{name}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")])
    await callback.message.edit_text(
        "🏪 Доступные бизнесы:\n\n"
        "⚠️ Технический центр, Шиномонтаж, СТО - по 1 владельцу\n"
        "⚠️ 24/7 - максимум 25 владельцев\n"
        "✅ доступен, ❌ занят",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("biz_show_"))
async def biz_show_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    business_name = callback.data.replace("biz_show_", "")
    data = BUSINESSES.get(business_name)
    
    business_owners = load_business_owners()
    owner_count = len(business_owners.get(business_name, []))
    max_owners = data.get("max_owners", 1)
    available = owner_count < max_owners
    
    keyboard = []
    if available:
        keyboard.append([InlineKeyboardButton(text="✅ Купить", callback_data=f"biz_buy_{business_name}")])
    keyboard.append([InlineKeyboardButton(text="ℹ️ Инфо", callback_data=f"biz_info_{business_name}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="buy_business")])
    
    await callback.message.edit_text(
        f"🏪 {business_name}\n"
        f"💰 Цена: {data['price']:,.0f}₽\n"
        f"📈 Доход: {data['income']:,.0f}₽/сутки\n"
        f"👤 Владельцев: {owner_count}/{max_owners}\n"
        f"📌 {'✅ Доступен' if available else '❌ Занят'}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("biz_buy_"))
async def buy_business(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    business_name = callback.data.replace("biz_buy_", "")
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    if user["business"]:
        await callback.answer("❌ У вас уже есть бизнес!", show_alert=True)
        return
    
    business = BUSINESSES.get(business_name)
    if not business:
        await callback.answer("❌ Не найден!")
        return
    
    business_owners = load_business_owners()
    owner_count = len(business_owners.get(business_name, []))
    max_owners = business.get("max_owners", 1)
    
    if owner_count >= max_owners:
        await callback.answer("❌ Все места заняты!", show_alert=True)
        return
    
    if user["money"] < business["price"]:
        await callback.answer(f"❌ Нужно {business['price']:,.0f}₽!", show_alert=True)
        return
    
    user["money"] -= business["price"]
    user["business"] = business_name
    user["business_income"] = business["income"]
    user["business_level"] = 1
    user["last_business_collect"] = datetime.now().isoformat()
    
    if business_name not in business_owners:
        business_owners[business_name] = []
    business_owners[business_name].append(str(callback.from_user.id))
    save_business_owners(business_owners)
    save_users(users)
    
    await callback.message.edit_text(
        f"✅ Куплен {business_name}!\n💰 Доход: {business['income']:,.0f}₽/сутки",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")]])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("biz_info_"))
async def biz_info(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    business_name = callback.data.replace("biz_info_", "")
    data = BUSINESSES.get(business_name)
    if not data:
        await callback.answer("❌ Не найден!")
        return
    
    business_owners = load_business_owners()
    owner_count = len(business_owners.get(business_name, []))
    max_owners = data.get("max_owners", 1)
    
    text = (
        f"ℹ️ {business_name}\n"
        f"📝 {data.get('description')}\n"
        f"💰 {data['price']:,.0f}₽\n"
        f"📈 {data['income']:,.0f}₽/сутки\n"
        f"👤 Владельцев: {owner_count}/{max_owners}\n\n"
        f"⬆️ Улучшение: +10% дохода за 50к BRcoins/ур."
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="buy_business")]]))
    await callback.answer()

@dp.callback_query(F.data == "collect_income")
async def collect_income(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    if not user["business"]:
        await callback.answer("❌ Нет бизнеса!", show_alert=True)
        return
    
    last_collect = datetime.fromisoformat(user["last_business_collect"])
    hours_passed = (datetime.now() - last_collect).total_seconds() / 3600
    
    if hours_passed < 24:
        await callback.answer(f"⏳ Через {24 - hours_passed:.1f} ч", show_alert=True)
        return
    
    business = BUSINESSES.get(user["business"])
    income = business["income"] * (business.get("level_multiplier", 1.1) ** (user["business_level"] - 1))
    user["money"] += income
    user["last_business_collect"] = datetime.now().isoformat()
    save_users(users)
    
    await callback.message.edit_text(f"💰 +{income:,.0f}₽ с {user['business']}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")]]))
    await callback.answer()

@dp.callback_query(F.data == "upgrade_business")
async def upgrade_business(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    if not user["business"]:
        await callback.answer("❌ Нет бизнеса!", show_alert=True)
        return
    
    price = user["business_level"] * 50000
    if user["brcoins"] < price:
        await callback.answer(f"❌ Нужно {price} BRcoins!", show_alert=True)
        return
    
    user["brcoins"] -= price
    user["business_level"] += 1
    save_users(users)
    
    business = BUSINESSES.get(user["business"])
    new_income = business["income"] * (business.get("level_multiplier", 1.1) ** (user["business_level"] - 1))
    
    await callback.message.edit_text(
        f"⬆️ {user['business']} ур.{user['business_level']}\n💰 {new_income:,.0f}₽/сутки",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")]])
    )
    await callback.answer()

# ========== СТАТИСТИКА (ИСПРАВЛЕНА) ==========
@dp.callback_query(F.data == "stats")
async def stats_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    users = load_users()
    user = users[str(callback.from_user.id)]
    
    text = (
        f"📊 Статистика\n\n"
        f"💰 Баланс: {user['money']:,.0f}₽\n"
        f"💎 BRcoins: {user['brcoins']}\n"
        f"📈 Заработано всего: {user['total_earned']:,.0f}₽\n"
        f"🤝 Сделок: {user['trades_count']}\n"
        f"👤 Роль: {'Админ' if user['role'] == 'admin' else 'Игрок'}\n"
        f"🚗 Машин в гараже: {len(user['inventory'])}\n"
        f"⛏️ Ходков в шахте: {user['mine_attempts']}/100\n\n"
        f"📈 Портфель:\n"
        f"₿ BTC: {user['portfolio'].get('BTC', 0)}\n"
        f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}\n"
        f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}"
    )
    
    if user["business"]:
        business = BUSINESSES.get(user["business"])
        if business:
            income = business["income"] * (business.get("level_multiplier", 1.1) ** (user["business_level"] - 1))
            text += f"\n\n🏪 Бизнес: {user['business']} (ур.{user['business_level']})\n💰 Доход: {income:,.0f}₽/сутки"
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]]))
    await callback.answer()

# ========== НАЗАД ==========
@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    text, keyboard = await get_main_menu(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    global promo_running, promo_task
    
    print("🤖 Бот запущен!")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"📢 Путь к данным: {DATA_DIR}")
    
    settings = load_settings()
    
    if settings.get("promo_auto", False):
        promo_running = True
        promo_task = asyncio.create_task(promo_auto_loop())
        print("📢 Авто-промокоды запущены!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
