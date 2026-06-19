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
CHANNEL_ID = "-1004461974511"
PROMO_CHANNEL_ID = "-1003853479476"  # Канал для промокодов
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Файлы
USERS_FILE = 'users_data.json'
PROMOCODES_FILE = 'promocodes.json'
BUSINESS_OWNERS_FILE = 'business_owners.json'
SETTINGS_FILE = 'settings.json'

# Глобальная переменная для задачи отправки промокодов
promo_task = None
promo_running = False

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

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"bot_enabled": True, "promo_auto": False}

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
            "BTC": {"price": 900000, "min": 700000, "max": 1000000, "avg": 900000},
            "WETcoin": {"price": 290000, "min": 250000, "max": 350000, "avg": 290000},
            "BRcoins": {"price": 15000000, "min": 10000000, "max": 30000000, "avg": 15000000}
        }
        self.last_update = datetime.now()
    
    def update_rates(self):
        if (datetime.now() - self.last_update).total_seconds() < 600:
            return
        
        for currency in self.rates:
            rand = random.random()
            if rand < 0.005:
                new_price = self.rates[currency]["min"]
            elif rand < 0.055:
                new_price = self.rates[currency]["max"]
            else:
                new_price = self.rates[currency]["avg"] * random.uniform(0.95, 1.05)
            
            self.rates[currency]["price"] = max(
                self.rates[currency]["min"],
                min(self.rates[currency]["max"], new_price)
            )
            self.rates[currency]["price"] = round(self.rates[currency]["price"], 0)
        
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
            
            self.rates[currency]["price"] = max(
                self.rates[currency]["min"],
                min(self.rates[currency]["max"], new_price)
            )
            self.rates[currency]["price"] = round(self.rates[currency]["price"], 0)
        
        self.last_update = datetime.now()

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

# ========== АВТО-ГЕНЕРАЦИЯ ПРОМОКОДОВ ==========
async def generate_and_send_promo():
    """Генерирует промокод и отправляет в канал"""
    import string
    
    # Случайный выбор: BRcoins (50%) или деньги (50%)
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
    
    # Генерация кода
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # Сохраняем промокод
    promocodes = load_promocodes()
    promocodes[code] = {
        "type": promo_type,
        "uses": uses,
        "used": 0,
        "amount": amount
    }
    save_promocodes(promocodes)
    
    # Отправляем в канал
    try:
        message_text = (
            f"🎁 **Новый промокод!**\n\n"
            f"📌 Код: `{code}`\n"
            f"🎁 Награда: {amount:,} {type_text}\n"
            f"🔄 Активаций: {uses}\n\n"
            f"👉 Забирай быстрее!"
        )
        await bot.send_message(PROMO_CHANNEL_ID, message_text)
        print(f"✅ Промокод отправлен в канал: {code} ({amount} {type_text})")
    except Exception as e:
        print(f"❌ Ошибка отправки промокода: {e}")

async def promo_auto_loop():
    """Фоновый цикл отправки промокодов каждую минуту"""
    global promo_running
    while promo_running:
        try:
            settings = load_settings()
            if settings.get("promo_auto", False):
                await generate_and_send_promo()
            else:
                print("⏸️ Авто-промокоды выключены")
        except Exception as e:
            print(f"❌ Ошибка в цикле промокодов: {e}")
        
        await asyncio.sleep(60)  # Ждем 1 минуту

# ========== АДМИН-КОМАНДЫ ==========

# Команда /promostart (on/off)
@dp.message(Command("promostart"))
async def promo_start_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды!")
        return
    
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Использование: /promostart on  или  /promostart off")
        return
    
    status = parts[1].lower()
    if status not in ["on", "off"]:
        await message.answer("❌ Используйте 'on' или 'off'")
        return
    
    settings = load_settings()
    settings["promo_auto"] = (status == "on")
    save_settings(settings)
    
    global promo_running
    global promo_task
    
    if status == "on":
        if not promo_running:
            promo_running = True
            promo_task = asyncio.create_task(promo_auto_loop())
            await message.answer("✅ Авто-генерация промокодов ЗАПУЩЕНА!\n📢 Промокоды будут отправляться в канал каждую минуту.")
        else:
            await message.answer("ℹ️ Авто-генерация уже запущена!")
    else:
        if promo_running:
            promo_running = False
            if promo_task:
                promo_task.cancel()
                promo_task = None
            await message.answer("❌ Авто-генерация промокодов ОСТАНОВЛЕНА!")
        else:
            await message.answer("ℹ️ Авто-генерация уже остановлена!")

# Команда /promostatus - проверка статуса
@dp.message(Command("promostatus"))
async def promo_status_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    settings = load_settings()
    status = "✅ Включена" if settings.get("promo_auto", False) else "❌ Выключена"
    await message.answer(f"📢 Статус авто-генерации промокодов: {status}")

@dp.message(Command("technical"))
async def technical_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
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
    await message.answer(f"🔧 Доступ к боту {status_text}!")

@dp.message(Command("status"))
async def status_command(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    
    settings = load_settings()
    status = "✅ Включен" if settings.get("bot_enabled", True) else "❌ Выключен"
    promo_status = "✅ Включена" if settings.get("promo_auto", False) else "❌ Выключена"
    await message.answer(f"🔧 Статус бота: {status}\n📢 Авто-промокоды: {promo_status}")

@dp.message(Command("getdb"))
async def get_db(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды!")
        return
    
    await message.answer("📦 Собираю базу данных...")
    
    files_sent = 0
    for file in [USERS_FILE, PROMOCODES_FILE, BUSINESS_OWNERS_FILE, SETTINGS_FILE]:
        if os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = f.read()
                await message.answer_document(
                    types.BufferedInputFile(
                        data.encode('utf-8'),
                        filename=os.path.basename(file)
                    )
                )
                files_sent += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                await message.answer(f"❌ Ошибка при загрузке {file}: {e}")
    
    if files_sent == 0:
        await message.answer("❌ Файлы базы данных не найдены!")
    else:
        await message.answer(f"✅ Отправлено {files_sent} файлов с данными!")

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

@dp.message(Command("update_rates_admin"))
async def update_rates_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    currency_rates.force_update()
    await message.answer("✅ Курсы валют принудительно обновлены!")

# ========== СТАРТ ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    users = load_users()
    
    if user_id not in users:
        users[user_id] = get_default_user()
        save_users(users)
    
    if not await check_subscription(message.from_user.id):
        channel_link = "https://t.me/+TAhbj7PhoWhhZTQ6"
        channel_username = "@WeteroRussia"
        await message.answer(
            f"📢 Для использования бота подпишитесь на наш канал {channel_username}!\n\n"
            f"👉 [Подписаться]({channel_link})\n\n"
            "После подписки нажмите /start"
        )
        return
    
    if not await check_access(message):
        return
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\nДобро пожаловать!",
        reply_markup=main_menu_keyboard()
    )

# ========== РАБОТЫ ==========
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

@dp.callback_query(F.data == "work_trucker")
async def work_trucker(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    income = random.randint(50000, 150000)
    user["money"] += income
    user["total_earned"] += income
    save_users(users)
    await callback.message.edit_text(f"🚛 +{income:,}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="works")]]))
    await callback.answer()

@dp.callback_query(F.data == "work_diver")
async def work_diver(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    income = random.randint(70000, 200000)
    user["money"] += income
    user["total_earned"] += income
    save_users(users)
    await callback.message.edit_text(f"🤿 +{income:,}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="works")]]))
    await callback.answer()

@dp.callback_query(F.data == "work_farmer")
async def work_farmer(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    income = random.randint(30000, 100000)
    user["money"] += income
    user["total_earned"] += income
    save_users(users)
    await callback.message.edit_text(f"🌾 +{income:,}₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="works")]]))
    await callback.answer()

@dp.callback_query(F.data == "work_miner")
async def work_miner(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    income = random.randint(40000, 120000)
    user["money"] += income
    user["total_earned"] += income
    rare_stone = random.random() < 0.1
    if rare_stone:
        br_bonus = random.randint(10, 50)
        user["brcoins"] += br_bonus
        bonus_text = f"\n💎 +{br_bonus} BRcoins"
    else:
        bonus_text = ""
    save_users(users)
    await callback.message.edit_text(f"⛏️ +{income:,}₽{bonus_text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="works")]]))
    await callback.answer()

# ========== ТРЕЙДИНГ ==========
@dp.callback_query(F.data == "work_trading")
async def work_trading(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    currency_rates.update_rates()
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    keyboard = [
        [InlineKeyboardButton(text=f"₿ BTC: {currency_rates.rates['BTC']['price']:,.0f}₽", callback_data="trade_BTC")],
        [InlineKeyboardButton(text=f"💧 WETcoin: {currency_rates.rates['WETcoin']['price']:,.0f}₽", callback_data="trade_WETcoin")],
        [InlineKeyboardButton(text=f"🪙 BRcoins: {currency_rates.rates['BRcoins']['price']:,.0f}₽", callback_data="trade_BRcoins")],
        [InlineKeyboardButton(text="ℹ️ Инфо о трейдинге", callback_data="trading_info")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
    ]
    
    await callback.message.edit_text(
        f"📈 Трейдинг\n\nБаланс: {user['money']:,.0f}₽\nBRcoins: {user['brcoins']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data == "trading_info")
async def trading_info(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    text = "ℹ️ Информация о курсах валют:\n\n"
    for currency, data in currency_rates.rates.items():
        text += f"**{currency}**\n"
        text += f"💰 Текущая: {data['price']:,.0f}₽\n"
        text += f"📊 Средняя: {data['avg']:,.0f}₽\n"
        text += f"📈 Максимальная: {data['max']:,.0f}₽\n"
        text += f"📉 Минимальная: {data['min']:,.0f}₽\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="work_trading")]])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("trade_"))
async def trade_currency(callback: types.CallbackQuery, state: FSMContext):
    if not await check_access(callback):
        return
    currency = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    price = currency_rates.rates[currency]["price"]
    
    await state.update_data(currency=currency, price=price)
    
    keyboard = [
        [InlineKeyboardButton(text="Купить", callback_data=f"buy_{currency}")],
        [InlineKeyboardButton(text="Продать", callback_data=f"sell_{currency}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="work_trading")]
    ]
    
    await callback.message.edit_text(
        f"📊 {currency}\nЦена: {price:,.0f}₽\nУ вас: {user['portfolio'].get(currency, 0)}\nБаланс: {user['money']:,.0f}₽\n\nСколько хотите купить/продать? Напишите число в чат.",
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
            await message.answer("❌ Количество должно быть положительным!")
            return
        
        data = await state.get_data()
        currency = data.get("currency")
        action = data.get("action")
        price = data.get("price")
        user_id = str(message.from_user.id)
        users = load_users()
        user = users[user_id]
        
        if action == "buy":
            total_cost = amount * price
            if user["money"] < total_cost:
                await message.answer(f"❌ Недостаточно денег! Нужно {total_cost:,.0f}₽")
                await state.clear()
                return
            user["money"] -= total_cost
            user["portfolio"][currency] = user["portfolio"].get(currency, 0) + amount
            user["trades_count"] += amount
            save_users(users)
            await message.answer(f"✅ Куплено {amount} {currency} за {total_cost:,.0f}₽")
        
        elif action == "sell":
            if user["portfolio"].get(currency, 0) < amount:
                await message.answer(f"❌ У вас только {user['portfolio'].get(currency, 0)} {currency}")
                await state.clear()
                return
            total_income = amount * price
            user["money"] += total_income
            user["portfolio"][currency] -= amount
            user["trades_count"] += amount
            save_users(users)
            await message.answer(f"✅ Продано {amount} {currency} за {total_income:,.0f}₽")
        
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
        [InlineKeyboardButton(text="💳 Купить донат", callback_data="donate_buy")],
        [InlineKeyboardButton(text="🎫 Промокод", callback_data="promo")],
        [InlineKeyboardButton(text="💰 Баланс доната", callback_data="donate_balance")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text(
        "💎 Донат\nКурс: 1₽ = 10 BRcoins\n@weterochina",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data == "donate_buy")
async def donate_buy(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    await callback.message.edit_text(
        "💳 Для покупки обратитесь к @weterochina",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]])
    )
    await callback.answer()

@dp.callback_query(F.data == "promo")
async def promo_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    await callback.message.edit_text(
        "🎫 Введите промокод в чат",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]])
    )
    await callback.answer()

@dp.callback_query(F.data == "donate_balance")
async def donate_balance(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
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
        await message.answer(f"✅ Промокод активирован! +{promo['amount']} {'BRcoins' if promo['type'] == 'brcoins' else '₽'}")
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
        keyboard.append([InlineKeyboardButton(
            text=f"🚗 {name} ({data['price']:,.0f}₽)",
            callback_data=f"container_{name}"
        )])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    
    await callback.message.edit_text(
        "🚗 Выберите контейнер для открытия:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("container_"))
async def open_container(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    container_name = callback.data.replace("container_", "")
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    container_data = CONTAINERS.get(container_name)
    if not container_data:
        await callback.answer("❌ Контейнер не найден!")
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
        "type": "car",
        "price": selected_item["price"],
        "from_container": container_name
    })
    
    save_users(users)
    await callback.message.edit_text(
        f"🚗 Открыт {container_name}!\n\n🎉 {selected_item['name']}\n💰 {selected_item['price']:,.0f}₽\n💳 Осталось: {user['money']:,.0f}₽",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="containers")]])
    )
    await callback.answer()

# ========== ГАРАЖ ==========
@dp.callback_query(F.data == "garage")
async def garage_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if not user["inventory"]:
        await callback.message.edit_text(
            "🏠 Ваш гараж пуст!\nОткройте контейнеры, чтобы получить машины.",
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

@dp.callback_query(F.data.startswith("car_"))
async def car_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    
    try:
        car_index = int(callback.data.split("_")[1])
    except:
        await callback.answer("❌ Ошибка!")
        return
    
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if car_index >= len(user["inventory"]):
        await callback.answer("❌ Машина не найдена!")
        return
    
    car = user["inventory"][car_index]
    
    keyboard = [
        [InlineKeyboardButton(text="🔢 Номера", callback_data=f"car_plate_{car_index}")],
        [InlineKeyboardButton(text="💰 Продать государству (50%)", callback_data=f"car_sell_{car_index}")],
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
    
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
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

# ========== БИЗНЕСЫ ==========
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
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if user["business"]:
        await callback.answer("❌ У вас уже есть бизнес!", show_alert=True)
        return
    
    business_owners = load_business_owners()
    keyboard = []
    
    for name, data in BUSINESSES.items():
        if name in business_owners:
            owner_id = business_owners[name]
            try:
                owner = await bot.get_chat(int(owner_id))
                owner_name = f"@{owner.username}" if owner.username else f"User_{owner_id[:5]}"
            except:
                owner_name = "Неизвестно"
            keyboard.append([InlineKeyboardButton(
                text=f"❌ {name} - занят ({owner_name})",
                callback_data=f"biz_info_{name}"
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                text=f"✅ {name} - {data['price']:,.0f}₽",
                callback_data=f"biz_choose_{name}"
            )])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")])
    
    await callback.message.edit_text(
        "🏪 Доступные бизнесы:\n\n⚠️ Каждый бизнес может купить только 1 игрок!\n\n✅ - доступен, ❌ - уже куплен",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("biz_choose_"))
async def biz_buy_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    business_name = callback.data.replace("biz_choose_", "")
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Купить", callback_data=f"biz_buy_confirm_{business_name}")],
        [InlineKeyboardButton(text="ℹ️ Инфо", callback_data=f"biz_info_{business_name}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="buy_business")]
    ]
    
    data = BUSINESSES.get(business_name)
    if not data:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    await callback.message.edit_text(
        f"🏪 {business_name}\n💰 Цена: {data['price']:,.0f}₽\n📈 Доход: {data['income']:,.0f}₽/сутки",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("biz_info_"))
async def biz_info(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    business_name = callback.data.replace("biz_info_", "")
    data = BUSINESSES.get(business_name)
    
    if not data:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    business_owners = load_business_owners()
    owner_text = "Свободен"
    if business_name in business_owners:
        owner_id = business_owners[business_name]
        try:
            owner = await bot.get_chat(int(owner_id))
            owner_text = f"@{owner.username}" if owner.username else f"User_{owner_id[:5]}"
        except:
            owner_text = "Неизвестно"
    
    upgrade_costs = []
    for level in range(1, 6):
        cost = level * 50000
        upgrade_costs.append(f"Ур.{level} → {level+1}: {cost} BRcoins")
    
    text = (
        f"ℹ️ Информация о бизнесе\n\n"
        f"🏪 {business_name}\n"
        f"📝 {data.get('description', 'Нет описания')}\n"
        f"💰 Цена покупки: {data['price']:,.0f}₽\n"
        f"📈 Доход в сутки: {data['income']:,.0f}₽\n"
        f"👤 Владелец: {owner_text}\n\n"
        f"⬆️ Улучшение бизнеса:\n"
        f"Каждый уровень увеличивает доход на 10%\n"
        f"Стоимость улучшения:\n" + "\n".join(upgrade_costs[:3])
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="buy_business")]])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("biz_buy_confirm_"))
async def buy_business(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    business_name = callback.data.replace("biz_buy_confirm_", "")
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if user["business"]:
        await callback.answer("❌ У вас уже есть бизнес!", show_alert=True)
        return
    
    business = BUSINESSES.get(business_name)
    if not business:
        await callback.answer("❌ Бизнес не найден!")
        return
    
    business_owners = load_business_owners()
    if business_name in business_owners:
        await callback.answer("❌ Этот бизнес уже куплен!", show_alert=True)
        return
    
    if user["money"] < business["price"]:
        await callback.answer(f"❌ Нужно {business['price']:,.0f}₽!", show_alert=True)
        return
    
    user["money"] -= business["price"]
    user["business"] = business_name
    user["business_income"] = business["income"]
    user["business_level"] = 1
    user["last_business_collect"] = datetime.now().isoformat()
    
    business_owners[business_name] = user_id
    save_business_owners(business_owners)
    save_users(users)
    
    await callback.message.edit_text(
        f"✅ Куплен {business_name}!\n💰 Доход: {business['income']:,.0f}₽/сутки",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")]])
    )
    await callback.answer()

@dp.callback_query(F.data == "collect_income")
async def collect_income(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if not user["business"]:
        await callback.answer("❌ Нет бизнеса!", show_alert=True)
        return
    
    last_collect = datetime.fromisoformat(user["last_business_collect"])
    hours_passed = (datetime.now() - last_collect).total_seconds() / 3600
    
    if hours_passed < 24:
        await callback.answer(f"⏳ Через {24 - hours_passed:.1f} ч", show_alert=True)
        return
    
    business = BUSINESSES.get(user["business"])
    if not business:
        await callback.answer("❌ Ошибка!")
        return
    
    income = business["income"] * (business.get("level_multiplier", 1.1) ** (user["business_level"] - 1))
    user["money"] += income
    user["last_business_collect"] = datetime.now().isoformat()
    save_users(users)
    
    await callback.message.edit_text(
        f"💰 +{income:,.0f}₽ с {user['business']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")]])
    )
    await callback.answer()

@dp.callback_query(F.data == "upgrade_business")
async def upgrade_business(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
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
        f"⬆️ {user['business']} ур.{user['business_level']}\n💰 Доход: {new_income:,.0f}₽/сутки",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")]])
    )
    await callback.answer()

# ========== СТАТИСТИКА ==========
@dp.callback_query(F.data == "stats")
async def stats_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    text = f"📊 Статистика\n\n💰 {user['money']:,.0f}₽\n💎 {user['brcoins']} BRcoins\n📈 Заработано: {user['total_earned']:,.0f}₽\n🤝 Сделок: {user['trades_count']}\n👤 {'Админ' if user['role'] == 'admin' else 'Игрок'}\n🚗 Машин: {len(user['inventory'])}"
    
    if user["business"]:
        business = BUSINESSES.get(user["business"])
        if business:
            income = business["income"] * (business.get("level_multiplier", 1.1) ** (user["business_level"] - 1))
            text += f"\n🏪 {user['business']} (ур.{user['business_level']}) - {income:,.0f}₽/сутки"
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]]))
    await callback.answer()

# ========== НАЗАД ==========
@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    await callback.message.edit_text("👋 Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    global promo_running
    global promo_task
    
    print("🤖 Бот запущен!")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"📢 Канал: @WeteroRussia")
    
    settings = load_settings()
    print(f"🔧 Статус бота: {'Включен' if settings.get('bot_enabled', True) else 'Выключен'}")
    
    # Автоматически запускаем авто-промокоды, если включены
    if settings.get("promo_auto", False):
        promo_running = True
        promo_task = asyncio.create_task(promo_auto_loop())
        print("📢 Авто-генерация промокодов запущена!")
    else:
        print("📢 Авто-генерация промокодов выключена")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
