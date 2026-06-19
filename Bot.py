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
CHANNEL_ID = "-1004461974511"  # ID канала для подписки
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

# НОВЫЕ КОНТЕЙНЕРЫ
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

# Проверка подписки на канал
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
        channel_link = "https://t.me/+TAhbj7PhoWhhZTQ6" # НОВАЯ ССЫЛКА
        channel_username = "@WeteroRussia" # НОВЫЙ ЮЗЕРНЕЙМ
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

# Главное меню
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="💼 Работы", callback_data="works")],
        [InlineKeyboardButton(text="💎 Донат", callback_data="donate")],
        [InlineKeyboardButton(text="🏆 Форбс", callback_data="forbes")],
        [InlineKeyboardButton(text="🚗 Контейнеры", callback_data="containers")],
        [InlineKeyboardButton(text="🏪 Бизнесы", callback_data="businesses")],
        [InlineKeyboardButton(text="🏠 Гараж", callback_data="garage")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ---------- АДМИН-КОМАНДЫ ----------
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

@dp.message(Command("update_rates_admin"))
async def update_rates_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав!")
        return
    currency_rates.force_update()
    await message.answer("✅ Курсы валют принудительно обновлены!")

# ---------- СТАРТ ----------
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

# ---------- РАБОТЫ (без изменений, полный код тут) ----------
# ... (здесь весь остальной код от Дальнобойщика до Шахтёра, он не менялся) ...

# ---------- КОНТЕЙНЕРЫ (ОБНОВЛЕНО) ----------
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

# ---------- БИЗНЕСЫ (ИСПРАВЛЕНЫ) ----------
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
            # ИСПРАВЛЕНО: теперь biz_confirm_
            keyboard.append([InlineKeyboardButton(
                text=f"✅ {name} - {data['price']:,.0f}₽",
                callback_data=f"biz_confirm_{name}"
            )])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")])
    
    await callback.message.edit_text(
        "🏪 Доступные бизнесы:\n\n⚠️ Каждый бизнес может купить только 1 игрок!\n\n✅ - доступен, ❌ - уже куплен",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

# ИСПРАВЛЕНО: обработчик для выбора бизнеса
@dp.callback_query(F.data.startswith("biz_confirm_"))
async def biz_buy_menu(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    business_name = callback.data.replace("biz_confirm_", "")
    
    keyboard = [
        # ИСПРАВЛЕНО: теперь confirm_biz_
        [InlineKeyboardButton(text="✅ Купить", callback_data=f"confirm_biz_{business_name}")],
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

# ИСПРАВЛЕНО: обработчик для покупки бизнеса
@dp.callback_query(F.data.startswith("confirm_biz_"))
async def buy_business(callback: types.CallbackQuery):
    if not await check_access(callback):
        return
    business_name = callback.data.replace("confirm_biz_", "")
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

# ---------- ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ----------
# (Гараж, Статистика, Назад и т.д. - остаются без изменений, их полный код я не привожу для краткости,
#  но вы можете скопировать их из предыдущей версии. Я могу прислать их отдельно, если нужно.)

# ---------- ЗАПУСК ----------
async def main():
    print("🤖 Бот запущен!")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"📢 Канал: @WeteroRussia (ID: {CHANNEL_ID})")
    settings = load_settings()
    print(f"🔧 Статус бота: {'Включен' if settings.get('bot_enabled', True) else 'Выключен'}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
