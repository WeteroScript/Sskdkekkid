import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F

# Конфигурация
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 5877790074  # ID администратора
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Файл для хранения данных пользователей
USERS_FILE = 'users_data.json'

# Инициализация данных пользователей
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# Стартовые данные для нового пользователя
def get_default_user():
    return {
        "money": 1000000,
        "brcoins": 1000,
        "energy": 100,
        "cases_opened": 0,
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
            "BTC": {"price": 5000000, "change": 0.01},
            "WETcoin": {"price": 1000, "change": 0.02},
            "BRcoins": {"price": 100, "change": 0.03}
        }
    
    def update_rates(self):
        for currency in self.rates:
            change = random.uniform(-0.05, 0.05)
            self.rates[currency]["price"] *= (1 + change)
            self.rates[currency]["price"] = round(self.rates[currency]["price"], 2)
            self.rates[currency]["change"] = change
    
    def get_rate(self, currency):
        return self.rates.get(currency, {})

currency_rates = CurrencyRates()

# Бизнесы
BUSINESSES = {
    "Технический центр": {"price": 1000000000, "income": 200000000, "level_multiplier": 1.1},
    "Шиномонтажный центр": {"price": 1000000000, "income": 200000000, "level_multiplier": 1.1},
    "СТО": {"price": 500000000, "income": 100000000, "level_multiplier": 1.1},
    "24/7": {"price": 100000000, "income": 50000000, "level_multiplier": 1.1, "max_owners": 25}
}

# Контейнеры - оставлен только Особый контейнер
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

# Промокоды
promocodes = {
    "WELCOME": {"bonus": 100, "used": []},
    "GIFT2024": {"bonus": 50, "used": []}
}

# Проверка на админа
def is_admin(user_id):
    return user_id == ADMIN_ID

# Главное меню
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="💼 Работы", callback_data="works")],
        [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
        [InlineKeyboardButton(text="💎 Донат", callback_data="donate")],
        [InlineKeyboardButton(text="🏆 Форбс", callback_data="forbes")],
        [InlineKeyboardButton(text="🚗 Контейнеры", callback_data="containers")],
        [InlineKeyboardButton(text="🏪 Бизнесы", callback_data="businesses")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ---------- АДМИН-КОМАНДЫ ----------
@dp.message(Command("mailall"))
async def mail_all(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды!")
        return
    
    text = message.text.replace("/mailall", "").strip()
    if not text:
        await message.answer("❌ Укажите текст рассылки!\nПример: /mailall Привет всем!")
        return
    
    users = load_users()
    sent = 0
    
    for user_id in users:
        try:
            await bot.send_message(int(user_id), f"📢 Рассылка от администратора:\n\n{text}")
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    
    await message.answer(f"✅ Рассылка отправлена {sent} пользователям!")

@dp.message(Command("giverub"))
async def give_rub(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды!")
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
                await message.answer(f"✅ Пользователю @{username} выдано {amount:,} рублей!")
                try:
                    await bot.send_message(int(user_id), f"💰 Вам начислено {amount:,} рублей от администратора!")
                except:
                    pass
                break
        except:
            continue
    
    if not found:
        await message.answer(f"❌ Пользователь @{username} не найден!")

@dp.message(Command("givedonate"))
async def give_donate(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды!")
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
                await message.answer(f"✅ Пользователю @{username} выдано {amount} BRcoins!")
                try:
                    await bot.send_message(int(user_id), f"💎 Вам начислено {amount} BRcoins от администратора!")
                except:
                    pass
                break
        except:
            continue
    
    if not found:
        await message.answer(f"❌ Пользователь @{username} не найден!")

# ---------- СТАРТ ----------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    users = load_users()
    
    if user_id not in users:
        users[user_id] = get_default_user()
        save_users(users)
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в экономическую игру! Выберите действие:",
        reply_markup=main_menu_keyboard()
    )

# ---------- РАБОТЫ (БЕЗ УСТАЛОСТИ) ----------
@dp.callback_query(F.data == "works")
async def works_menu(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="🚛 Дальнобойщик", callback_data="work_trucker")],
        [InlineKeyboardButton(text="🤿 Водолаз", callback_data="work_diver")],
        [InlineKeyboardButton(text="📈 Трейдинг", callback_data="work_trading")],
        [InlineKeyboardButton(text="🌾 Фермер", callback_data="work_farmer")],
        [InlineKeyboardButton(text="⛏️ Шахтёр", callback_data="work_miner")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text(
        "💼 Выберите работу:\n\n"
        "Каждая работа приносит доход!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data == "work_trucker")
async def work_trucker(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    income = random.randint(50000, 150000)
    user["money"] += income
    user["total_earned"] += income
    
    save_users(users)
    
    await callback.message.edit_text(
        f"🚛 Вы поработали дальнобойщиком!\n"
        f"💰 Заработано: {income:,.0f} рублей",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к работам", callback_data="works")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "work_diver")
async def work_diver(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    income = random.randint(70000, 200000)
    user["money"] += income
    user["total_earned"] += income
    
    save_users(users)
    
    await callback.message.edit_text(
        f"🤿 Вы поработали водолазом!\n"
        f"💰 Заработано: {income:,.0f} рублей",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к работам", callback_data="works")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "work_trading")
async def work_trading(callback: types.CallbackQuery):
    currency_rates.update_rates()
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    keyboard = [
        [InlineKeyboardButton(text=f"📈 BTC: {currency_rates.rates['BTC']['price']:,.0f}₽", callback_data="trade_BTC")],
        [InlineKeyboardButton(text=f"📈 WETcoin: {currency_rates.rates['WETcoin']['price']:,.0f}₽", callback_data="trade_WETcoin")],
        [InlineKeyboardButton(text=f"📈 BRcoins: {currency_rates.rates['BRcoins']['price']:,.0f}₽", callback_data="trade_BRcoins")],
        [InlineKeyboardButton(text="📊 Обновить курсы", callback_data="update_rates")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
    ]
    
    await callback.message.edit_text(
        f"📈 Торговый терминал\n\n"
        f"Ваш баланс: {user['money']:,.0f}₽\n"
        f"BRcoins: {user['brcoins']}\n\n"
        "Выберите валюту для торговли:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("trade_"))
async def trade_currency(callback: types.CallbackQuery):
    currency = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    price = currency_rates.rates[currency]["price"]
    
    keyboard = [
        [InlineKeyboardButton(text=f"Купить 1 {currency} за {price:,.0f}₽", callback_data=f"buy_{currency}_{price}")],
        [InlineKeyboardButton(text=f"Продать 1 {currency} за {price:,.0f}₽", callback_data=f"sell_{currency}_{price}")],
        [InlineKeyboardButton(text="🔙 Назад к трейдингу", callback_data="work_trading")]
    ]
    
    await callback.message.edit_text(
        f"📊 Торговля {currency}\n"
        f"Текущая цена: {price:,.0f} рублей\n"
        f"Ваш баланс: {user['money']:,.0f}₽\n"
        f"Ваш портфель: {user['portfolio'].get(currency, 0)} {currency}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_currency(callback: types.CallbackQuery):
    _, currency, price_str = callback.data.split("_")
    price = float(price_str)
    
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if user["money"] < price:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return
    
    user["money"] -= price
    user["portfolio"][currency] = user["portfolio"].get(currency, 0) + 1
    user["trades_count"] += 1
    
    save_users(users)
    
    await callback.answer(f"✅ Вы купили 1 {currency} за {price:,.0f}₽", show_alert=True)
    await work_trading(callback)

@dp.callback_query(F.data.startswith("sell_"))
async def sell_currency(callback: types.CallbackQuery):
    _, currency, price_str = callback.data.split("_")
    price = float(price_str)
    
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if user["portfolio"].get(currency, 0) < 1:
        await callback.answer("❌ У вас нет этой валюты!", show_alert=True)
        return
    
    user["money"] += price
    user["portfolio"][currency] -= 1
    user["trades_count"] += 1
    
    save_users(users)
    
    await callback.answer(f"✅ Вы продали 1 {currency} за {price:,.0f}₽", show_alert=True)
    await work_trading(callback)

@dp.callback_query(F.data == "update_rates")
async def update_rates(callback: types.CallbackQuery):
    currency_rates.update_rates()
    await callback.answer("✅ Курсы обновлены!", show_alert=True)
    await work_trading(callback)

@dp.callback_query(F.data == "work_farmer")
async def work_farmer(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    income = random.randint(30000, 100000)
    user["money"] += income
    user["total_earned"] += income
    
    save_users(users)
    
    await callback.message.edit_text(
        f"🌾 Вы поработали фермером!\n"
        f"💰 Заработано: {income:,.0f} рублей",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к работам", callback_data="works")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "work_miner")
async def work_miner(callback: types.CallbackQuery):
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
        bonus_text = f"\n💎 Вы нашли редкий камень! +{br_bonus} BRcoins"
    else:
        bonus_text = ""
    
    save_users(users)
    
    await callback.message.edit_text(
        f"⛏️ Вы поработали шахтёром!\n"
        f"💰 Заработано: {income:,.0f} рублей{bonus_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к работам", callback_data="works")]
        ])
    )
    await callback.answer()

# ---------- КАЗИНО ----------
@dp.callback_query(F.data == "casino")
async def casino_menu(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="🎡 Рулетка", callback_data="roulette")],
        [InlineKeyboardButton(text="🎰 Слоты (50 BRcoins)", callback_data="slots")],
        [InlineKeyboardButton(text="🪙 Коинфлип", callback_data="coinflip")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text(
        "🎰 Добро пожаловать в казино!\n\nВыберите игру:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data == "roulette")
async def roulette_menu(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="🔴 Красное (x2)", callback_data="roulette_red")],
        [InlineKeyboardButton(text="⚫ Чёрное (x2)", callback_data="roulette_black")],
        [InlineKeyboardButton(text="🟢 Чётное (x2)", callback_data="roulette_even")],
        [InlineKeyboardButton(text="🟢 Нечётное (x2)", callback_data="roulette_odd")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
    ]
    await callback.message.edit_text(
        "🎡 Рулетка\nСтавка: 1000 BRcoins\nВыберите ставку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("roulette_"))
async def roulette_play(callback: types.CallbackQuery):
    bet_type = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if user["brcoins"] < 1000:
        await callback.answer("❌ Недостаточно BRcoins! Нужно 1000", show_alert=True)
        return
    
    user["brcoins"] -= 1000
    
    colors = ["red", "black"]
    result_color = random.choice(colors)
    result_number = random.randint(0, 36)
    result_parity = "even" if result_number % 2 == 0 else "odd"
    
    win = False
    if bet_type == "red" and result_color == "red":
        win = True
    elif bet_type == "black" and result_color == "black":
        win = True
    elif bet_type == "even" and result_parity == "even":
        win = True
    elif bet_type == "odd" and result_parity == "odd":
        win = True
    
    if win:
        user["brcoins"] += 2000
        result_text = f"🎉 Вы выиграли! +1000 BRcoins\n(Выпало: {result_number} {result_color})"
    else:
        result_text = f"😞 Вы проиграли! -1000 BRcoins\n(Выпало: {result_number} {result_color})"
    
    save_users(users)
    
    await callback.message.edit_text(
        f"🎡 Результат рулетки:\n{result_text}\n"
        f"Ваш баланс: {user['brcoins']} BRcoins",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎡 Играть ещё", callback_data="roulette")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "slots")
async def slots_play(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if user["brcoins"] < 50:
        await callback.answer("❌ Недостаточно BRcoins! Нужно 50", show_alert=True)
        return
    
    user["brcoins"] -= 50
    
    symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    result = [random.choice(symbols) for _ in range(3)]
    
    win_multiplier = 0
    if result[0] == result[1] == result[2]:
        if result[0] == "7️⃣":
            win_multiplier = 10
        elif result[0] == "💎":
            win_multiplier = 5
        else:
            win_multiplier = 2
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        win_multiplier = 1.5
    
    if win_multiplier > 0:
        win_amount = int(50 * win_multiplier)
        user["brcoins"] += win_amount
        result_text = f"🎉 Вы выиграли {win_amount} BRcoins (x{win_multiplier})!"
    else:
        win_amount = 0
        result_text = "😞 Вы проиграли!"
    
    save_users(users)
    
    await callback.message.edit_text(
        f"🎰 Слоты: {' | '.join(result)}\n\n{result_text}\n"
        f"Ваш баланс: {user['brcoins']} BRcoins",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Крутить ещё (50 BRcoins)", callback_data="slots")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "coinflip")
async def coinflip_menu(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="🦅 Орёл", callback_data="coinflip_heads")],
        [InlineKeyboardButton(text="🪙 Решка", callback_data="coinflip_tails")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
    ]
    await callback.message.edit_text(
        "🪙 Коинфлип\nСтавка: 100 BRcoins\nВыберите сторону:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("coinflip_"))
async def coinflip_play(callback: types.CallbackQuery):
    bet = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if user["brcoins"] < 100:
        await callback.answer("❌ Недостаточно BRcoins! Нужно 100", show_alert=True)
        return
    
    user["brcoins"] -= 100
    
    result = random.choice(["heads", "tails"])
    win = bet == result
    
    if win:
        user["brcoins"] += 200
        result_text = "🎉 Вы выиграли! +100 BRcoins"
    else:
        result_text = "😞 Вы проиграли! -100 BRcoins"
    
    save_users(users)
    
    await callback.message.edit_text(
        f"🪙 Результат: {'Орёл' if result == 'heads' else 'Решка'}\n{result_text}\n"
        f"Ваш баланс: {user['brcoins']} BRcoins",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🪙 Играть ещё", callback_data="coinflip")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
        ])
    )
    await callback.answer()

# ---------- ДОНАТ ----------
@dp.callback_query(F.data == "donate")
async def donate_menu(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="💳 Купить донат", callback_data="donate_buy")],
        [InlineKeyboardButton(text="🎫 Ввести промокод", callback_data="promo")],
        [InlineKeyboardButton(text="💰 Мой баланс доната", callback_data="donate_balance")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text(
        "💎 Донат\n\nКурс: 1 рубль = 10 BRcoins\n"
        "По вопросам доната обращайтесь к @weterochina",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data == "donate_buy")
async def donate_buy(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💳 Покупка доната\n\nДля покупки доната обратитесь к администратору:\n"
        "@weterochina\n\nКурс: 1 рубль = 10 BRcoins",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "promo")
async def promo_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎫 Введите промокод\n\nДоступные промокоды:\n"
        "WELCOME - 100 BRcoins\n"
        "GIFT2024 - 50 BRcoins\n\n"
        "Напишите промокод в чат",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
        ])
    )
    await callback.answer()

@dp.message(F.text)
async def handle_promo(message: types.Message):
    user_id = str(message.from_user.id)
    users = load_users()
    user = users.get(user_id)
    
    if not user:
        return
    
    promo = message.text.upper()
    
    if promo in promocodes:
        if user_id in promocodes[promo]["used"]:
            await message.answer("❌ Вы уже использовали этот промокод!")
            return
        
        user["brcoins"] += promocodes[promo]["bonus"]
        promocodes[promo]["used"].append(user_id)
        save_users(users)
        
        await message.answer(
            f"✅ Промокод активирован!\n"
            f"Вы получили {promocodes[promo]['bonus']} BRcoins!\n"
            f"Ваш баланс: {user['brcoins']} BRcoins"
        )
    else:
        await message.answer("❌ Неверный промокод!")

@dp.callback_query(F.data == "donate_balance")
async def donate_balance(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    await callback.message.edit_text(
        f"💰 Баланс доната\n\n"
        f"Потрачено рублей: {user['donate_spent']}₽\n"
        f"Получено BRcoins: {user['donate_received']}\n"
        f"Текущий баланс: {user['brcoins']} BRcoins",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
        ])
    )
    await callback.answer()

# ---------- ФОРБС ----------
@dp.callback_query(F.data == "forbes")
async def forbes_menu(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="🏆 Список Форбс", callback_data="forbes_rich")],
        [InlineKeyboardButton(text="💎 Топ по BRcoins", callback_data="forbes_br")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text(
        "🏆 Форбс\n\nРейтинг самых богатых игроков:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data == "forbes_rich")
async def forbes_rich(callback: types.CallbackQuery):
    users = load_users()
    sorted_users = sorted(users.items(), key=lambda x: x[1]["money"], reverse=True)[:10]
    
    if not sorted_users:
        await callback.answer("Нет пользователей для рейтинга")
        return
    
    rating_text = "🏆 Топ-10 по деньгам:\n\n"
    for i, (user_id, data) in enumerate(sorted_users, 1):
        try:
            user = await bot.get_chat(int(user_id))
            username = user.username or f"User_{user_id[:5]}"
        except:
            username = f"User_{user_id[:5]}"
        
        rating_text += f"{i}. @{username} — {data['money']:,.0f}₽ (BRcoins: {data['brcoins']})\n"
    
    await callback.message.edit_text(
        rating_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "forbes_br")
async def forbes_br(callback: types.CallbackQuery):
    users = load_users()
    sorted_users = sorted(users.items(), key=lambda x: x[1]["brcoins"], reverse=True)[:10]
    
    if not sorted_users:
        await callback.answer("Нет пользователей для рейтинга")
        return
    
    rating_text = "💎 Топ-10 по BRcoins:\n\n"
    for i, (user_id, data) in enumerate(sorted_users, 1):
        try:
            user = await bot.get_chat(int(user_id))
            username = user.username or f"User_{user_id[:5]}"
        except:
            username = f"User_{user_id[:5]}"
        
        rating_text += f"{i}. @{username} — {data['brcoins']} BRcoins\n"
    
    await callback.message.edit_text(
        rating_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]
        ])
    )
    await callback.answer()

# ---------- КОНТЕЙНЕРЫ (ТОЛЬКО ОСОБЫЙ) ----------
@dp.callback_query(F.data == "containers")
async def containers_menu(callback: types.CallbackQuery):
    keyboard = []
    for name in CONTAINERS:
        data = CONTAINERS[name]
        keyboard.append([InlineKeyboardButton(
            text=f"🚗 {name} ({data['price']:,.0f}₽)",
            callback_data=f"container_{name}"
        )])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
    
    await callback.message.edit_text(
        "🚗 Контейнеры\n\nВыберите контейнер для открытия:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("container_"))
async def open_container(callback: types.CallbackQuery):
    container_name = callback.data.split("container_")[1]
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    container_data = CONTAINERS.get(container_name)
    if not container_data:
        await callback.answer("❌ Контейнер не найден!")
        return
    
    if user["money"] < container_data["price"]:
        await callback.answer(f"❌ Недостаточно средств! Нужно {container_data['price']:,.0f}₽", show_alert=True)
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
        f"🚗 Открыт {container_name}!\n\n"
        f"🎉 Вам выпало: {selected_item['name']}\n"
        f"💰 Стоимость: {selected_item['price']:,.0f}₽\n\n"
        f"Ваш баланс: {user['money']:,.0f}₽",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Посмотреть инвентарь", callback_data="inventory")],
            [InlineKeyboardButton(text="🔙 Назад к контейнерам", callback_data="containers")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "inventory")
async def show_inventory(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if not user["inventory"]:
        await callback.message.edit_text(
            "🎒 Ваш инвентарь пуст.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="containers")]
            ])
        )
        await callback.answer()
        return
    
    items_text = "\n".join([f"• {item['name']} ({item.get('price', 0):,.0f}₽)" for item in user["inventory"]])
    
    await callback.message.edit_text(
        f"🎒 Ваш инвентарь:\n\n{items_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="containers")]
        ])
    )
    await callback.answer()

# ---------- БИЗНЕСЫ ----------
@dp.callback_query(F.data == "businesses")
async def businesses_menu(callback: types.CallbackQuery):
    keyboard = [
        [InlineKeyboardButton(text="🏪 Купить бизнес", callback_data="buy_business")],
        [InlineKeyboardButton(text="💰 Собрать доход", callback_data="collect_income")],
        [InlineKeyboardButton(text="⬆️ Апгрейд бизнеса", callback_data="upgrade_business")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    await callback.message.edit_text(
        "🏪 Бизнесы\n\nУправляйте своим бизнесом:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_business")
async def buy_business_menu(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if user["business"]:
        await callback.answer("❌ У вас уже есть бизнес!", show_alert=True)
        return
    
    keyboard = []
    for name, data in BUSINESSES.items():
        if name == "24/7":
            owners = sum(1 for u in users.values() if u.get("business") == name)
            if owners >= data.get("max_owners", 25):
                continue
        
        keyboard.append([InlineKeyboardButton(
            text=f"{name} - {data['price']:,.0f}₽ (доход: {data['income']:,.0f}₽/сутки)",
            callback_data=f"buy_biz_{name}"
        )])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")])
    
    await callback.message.edit_text(
        "🏪 Выберите бизнес для покупки:\n\n"
        "Каждый пользователь может иметь максимум 1 бизнес.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_biz_"))
async def buy_business(callback: types.CallbackQuery):
    business_name = callback.data.split("buy_biz_")[1]
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
    
    if user["money"] < business["price"]:
        await callback.answer(f"❌ Недостаточно средств! Нужно {business['price']:,.0f}₽", show_alert=True)
        return
    
    if business_name == "24/7":
        owners = sum(1 for u in users.values() if u.get("business") == business_name)
        if owners >= business.get("max_owners", 25):
            await callback.answer("❌ Все 24/7 уже куплены!", show_alert=True)
            return
    
    user["money"] -= business["price"]
    user["business"] = business_name
    user["business_income"] = business["income"]
    user["business_level"] = 1
    user["last_business_collect"] = datetime.now().isoformat()
    
    save_users(users)
    
    await callback.message.edit_text(
        f"✅ Вы успешно купили {business_name}!\n\n"
        f"💰 Доход: {business['income']:,.0f}₽ в сутки\n"
        f"📈 Уровень: 1\n"
        f"💰 Ваш баланс: {user['money']:,.0f}₽",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "collect_income")
async def collect_income(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if not user["business"]:
        await callback.answer("❌ У вас нет бизнеса!", show_alert=True)
        return
    
    last_collect = datetime.fromisoformat(user["last_business_collect"])
    hours_passed = (datetime.now() - last_collect).total_seconds() / 3600
    
    if hours_passed < 24:
        await callback.answer(f"⏳ Доход будет доступен через {24 - hours_passed:.1f} часов", show_alert=True)
        return
    
    business = BUSINESSES.get(user["business"])
    if not business:
        await callback.answer("❌ Ошибка в данных бизнеса!")
        return
    
    income = business["income"] * (business.get("level_multiplier", 1.1) ** (user["business_level"] - 1))
    
    user["money"] += income
    user["last_business_collect"] = datetime.now().isoformat()
    
    save_users(users)
    
    await callback.message.edit_text(
        f"💰 Вы собрали доход с {user['business']}!\n"
        f"Получено: {income:,.0f}₽\n"
        f"Ваш баланс: {user['money']:,.0f}₽",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "upgrade_business")
async def upgrade_business(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    if not user["business"]:
        await callback.answer("❌ У вас нет бизнеса!", show_alert=True)
        return
    
    price = user["business_level"] * 50000
    
    if user["brcoins"] < price:
        await callback.answer(f"❌ Недостаточно BRcoins! Нужно {price}", show_alert=True)
        return
    
    user["brcoins"] -= price
    user["business_level"] += 1
    
    save_users(users)
    
    business = BUSINESSES.get(user["business"])
    new_income = business["income"] * (business.get("level_multiplier", 1.1) ** (user["business_level"] - 1))
    
    await callback.message.edit_text(
        f"⬆️ Бизнес {user['business']} улучшен до уровня {user['business_level']}!\n"
        f"💰 Новый доход: {new_income:,.0f}₽ в сутки\n"
        f"💎 Потрачено: {price} BRcoins\n"
        f"Ваш баланс: {user['brcoins']} BRcoins",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="businesses")]
        ])
    )
    await callback.answer()

# ---------- СТАТИСТИКА ----------
@dp.callback_query(F.data == "stats")
async def stats_menu(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    users = load_users()
    user = users[user_id]
    
    stats_text = (
        f"📊 Статистика\n\n"
        f"💰 Деньги: {user['money']:,.0f}₽\n"
        f"💎 BRcoins: {user['brcoins']}\n"
        f"📈 Всего заработано: {user['total_earned']:,.0f}₽\n"
        f"🤝 Сделок на бирже: {user['trades_count']}\n"
        f"👤 Должность: {'Админ' if user['role'] == 'admin' else 'Игрок'}"
    )
    
    if user["business"]:
        business = BUSINESSES.get(user["business"])
        if business:
            income = business["income"] * (business.get("level_multiplier", 1.1) ** (user["business_level"] - 1))
            stats_text += f"\n\n🏪 Бизнес: {user['business']} (ур. {user['business_level']})\n💰 Доход: {income:,.0f}₽/сутки"
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
        ])
    )
    await callback.answer()

# ---------- НАЗАД ----------
@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 Выберите действие:",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

# ---------- ЗАПУСК ----------
async def main():
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
