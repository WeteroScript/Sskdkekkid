import random
from datetime import datetime

from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger, MINE_RESOURCES
from database.file_manager import (
    load_users, save_users, load_inventory, save_inventory
)
from utils.helpers import check_access, get_default_user, is_function_disabled
from services.currency import currency_rates

last_mine_time = {}
last_reseller_time = {}

# ==========================================
# ===== КОНФИГ ПЕРЕКУПА =====
# ==========================================

RESELLER_ITEMS = [
    {"name": "Рубин", "buy_price": 75000000, "sell_price": 120000000, "profit": 45000000},
    {"name": "Алмаз", "buy_price": 250000000, "sell_price": 400000000, "profit": 150000000},
    {"name": "Изумруд", "buy_price": 150000000, "sell_price": 250000000, "profit": 100000000},
    {"name": "Сапфир", "buy_price": 200000000, "sell_price": 320000000, "profit": 120000000},
    {"name": "Топаз", "buy_price": 80000000, "sell_price": 130000000, "profit": 50000000},
    {"name": "Жемчуг", "buy_price": 50000000, "sell_price": 85000000, "profit": 35000000},
    {"name": "Золото", "buy_price": 30000000, "sell_price": 55000000, "profit": 25000000},
    {"name": "Серебро", "buy_price": 15000000, "sell_price": 28000000, "profit": 13000000},
    {"name": "Платина", "buy_price": 100000000, "sell_price": 160000000, "profit": 60000000},
    {"name": "Падпараджа", "buy_price": 400000000, "sell_price": 650000000, "profit": 250000000},
]

RESELLER_COOLDOWN = 300  # 5 минут

def register_jobs_handlers(dp):
    
    # ==========================================
    # ===== МЕНЮ РАБОТ =====
    # ==========================================
    
    @dp.callback_query(F.data == "works")
    async def works_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_1"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            keyboard = [
                [InlineKeyboardButton(text="🤿 Водолаз", callback_data="work_diver")],
                [InlineKeyboardButton(text="📈 Трейдинг", callback_data="work_trading")],
                [InlineKeyboardButton(text="🎣 Рыболовство", callback_data="work_fishing")],
                [InlineKeyboardButton(text="⛏️ Шахта", callback_data="mine")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            await callback.message.edit_text(
                "💼 **Выберите работу:**",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в works_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ВОДОЛАЗ =====
    # ==========================================
    
    @dp.callback_query(F.data == "work_diver")
    async def work_diver(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        if await is_function_disabled("job_4"):
            await callback.answer("⛔ Эта работа остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            income = random.randint(70000, 200000)
            
            # ✅ Бонус: шанс найти клад (10%)
            bonus_text = ""
            if random.random() < 0.1:
                bonus = random.randint(50000, 150000)
                income += bonus
                bonus_text = f"\n💎 Найден клад! +{bonus:,}₽"
            
            # ✅ Бонус: шанс найти BRcoins (5%)
            if random.random() < 0.05:
                br_bonus = random.randint(1, 5)
                user["brcoins"] += br_bonus
                bonus_text += f"\n🪙 Найдены BRcoins! +{br_bonus}"
            
            user["money"] += income
            user["total_earned"] = user.get("total_earned", 0) + income
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"🤿 **ВОДОЛАЗ**\n\n"
                f"💰 +{income:,}₽{bonus_text}\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🤿 Нырять ещё", callback_data="work_diver")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в work_diver: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ШАХТА =====
    # ==========================================
    
    @dp.callback_query(F.data == "mine")
    async def mine_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("job_1"):
            await callback.answer("⛔ Эта работа остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            last_reset = datetime.fromisoformat(user["last_mine_reset"])
            hours_passed = int((datetime.now() - last_reset).total_seconds() // 3600)
            
            if hours_passed > 0:
                user["mine_attempts"] = min(100, user["mine_attempts"] + hours_passed * 10)
                user["last_mine_reset"] = datetime.now().isoformat()
                users[user_id] = user
                await save_users(users)
            
            keyboard = [
                [InlineKeyboardButton(text="⛏️ Копать", callback_data="mine_dig")],
                [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="mine_info")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
            ]
            
            await callback.message.edit_text(
                f"⛏️ **ШАХТА**\n\n"
                f"💰 +80,000 - 150,000₽ за ходку\n"
                f"🔄 Попыток осталось: {user['mine_attempts']}/100\n"
                f"⏳ Восстанавливается: +10 попыток в час\n\n"
                f"⏱️ КД между попытками: 3 секунды\n\n"
                f"Выберите действие:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в mine_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "mine_dig")
    async def mine_dig(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            
            current_time = datetime.now()
            if user_id in last_mine_time:
                time_diff = (current_time - last_mine_time[user_id]).total_seconds()
                if time_diff < 3:
                    await callback.answer(
                        f"⏳ Подождите {3 - int(time_diff)} сек!",
                        show_alert=True
                    )
                    return
            
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if user["mine_attempts"] <= 0:
                await callback.answer(
                    "❌ Нет попыток! Подождите восстановления.",
                    show_alert=True
                )
                return
            
            last_mine_time[user_id] = current_time
            user["mine_attempts"] -= 1
            
            base_income = random.randint(80000, 150000)
            user["money"] += base_income
            user["total_earned"] = user.get("total_earned", 0) + base_income
            
            resource_text = f"\n💰 +{base_income:,}₽ за работу"
            
            if random.random() < 0.3:
                total_chance = sum(r["chance"] for r in MINE_RESOURCES)
                roll = random.random() * total_chance
                cumulative = 0
                selected_resource = MINE_RESOURCES[-1]
                
                for res in MINE_RESOURCES:
                    cumulative += res["chance"]
                    if roll <= cumulative:
                        selected_resource = res
                        break
                
                inventory = await load_inventory()
                if user_id not in inventory:
                    inventory[user_id] = []
                inventory[user_id].append(selected_resource["name"])
                await save_inventory(inventory)
                
                resource_text += f"\n💎 Найден: {selected_resource['name']}!"
            else:
                resource_text += "\n😔 Ресурс не найден..."
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"⛏️ **ШАХТА**\n\n{resource_text}\n\n"
                f"🔄 Осталось попыток: {user['mine_attempts']}/100",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⛏️ Копать ещё", callback_data="mine_dig")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="mine")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в mine_dig: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "mine_info")
    async def mine_info(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            text = "ℹ️ Ресурсы и шансы выпадения:\n\n"
            for i, res in enumerate(MINE_RESOURCES, 1):
                chance_percent = res["chance"] * 100
                text += f"{i}. {res['name']} - {chance_percent:.2f}% (продажа: {res['price']:,.0f}₽)\n"
            
            text += "\n📊 70% шанс ничего не выпадет"
            text += "\n💰 +80,000 - 150,000₽ за ходку"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="mine")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в mine_info: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ТРЕЙДИНГ =====
    # ==========================================
    
    @dp.callback_query(F.data == "work_trading")
    async def work_trading(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("job_3"):
            await callback.answer("⛔ Эта работа остановлена администратором!", show_alert=True)
            return
        
        try:
            currency_rates.update_rates()
            users = await load_users()
            user = users.get(str(callback.from_user.id), get_default_user())
            
            remaining = currency_rates.get_time_until_update()
            minutes = remaining // 60
            seconds = remaining % 60
            
            keyboard = [
                [InlineKeyboardButton(
                    text=f"BTC: {currency_rates.rates['BTC']['price']:,.0f}₽ (макс: 15)",
                    callback_data="trade_BTC"
                )],
                [InlineKeyboardButton(
                    text=f"WETcoin: {currency_rates.rates['WETcoin']['price']:,.0f}₽ (макс: 75)",
                    callback_data="trade_WETcoin"
                )],
                [InlineKeyboardButton(
                    text=f"NotCoin: {currency_rates.rates['NotCoin']['price']:,.0f}₽ (макс: 2500)",
                    callback_data="trade_NotCoin"
                )],
                [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="trading_info")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
            ]
            
            await callback.message.edit_text(
                f"📈 **Трейдинг**\n\n"
                f"💰 Баланс: {user['money']:,.0f}₽\n"
                f"🪙 BRcoins: {user['brcoins']}\n\n"
                f"₿ BTC: {user['portfolio'].get('BTC', 0)}/150\n"
                f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}/100\n"
                f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}/5000\n\n"
                f"⏳ Следующее обновление курсов: {minutes:02d}:{seconds:02d}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в work_trading: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "trading_info")
    async def trading_info(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            text = "ℹ️ Курсы валют:\n\n"
            for currency, data in currency_rates.rates.items():
                text += (
                    f"**{currency}**\n"
                    f"💰 {data['price']:,.0f}₽\n"
                    f"📊 Средняя: {data['avg']:,.0f}₽\n"
                    f"📈 Макс: {data['max']:,.0f}₽\n"
                    f"📉 Мин: {data['min']:,.0f}₽\n\n"
                )
            
            text += "📊 Лимиты:\n"
            text += "BTC - макс. покупка/продажа: 15 шт., хранение: 150\n"
            text += "WETcoin - макс. покупка/продажа: 75 шт., хранение: 100\n"
            text += "NotCoin - макс. покупка/продажа: 2500 шт., хранение: 5000"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="work_trading")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в trading_info: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("trade_"))
    async def trade_currency(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            currency = callback.data.split("_")[1]
            price = currency_rates.rates[currency]["price"]
            
            limits = {
                "BTC": {"max_trade": 15, "max_storage": 150},
                "WETcoin": {"max_trade": 75, "max_storage": 100},
                "NotCoin": {"max_trade": 2500, "max_storage": 5000}
            }
            
            await state.update_data(currency=currency, price=price, limit=limits[currency])
            
            keyboard = [
                [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{currency}")],
                [InlineKeyboardButton(text="🛍️ Продать", callback_data=f"sell_{currency}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="work_trading")]
            ]
            
            await callback.message.edit_text(
                f"📊 **{currency}**\n"
                f"💰 Цена: {price:,.0f}₽\n"
                f"📊 Макс. покупка/продажа: {limits[currency]['max_trade']}\n"
                f"📦 Макс. хранение: {limits[currency]['max_storage']}\n\n"
                f"Выберите действие:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в trade_currency: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ПОКУПКА/ПРОДАЖА ВАЛЮТЫ =====
    # ==========================================
    
    @dp.callback_query(F.data.startswith("buy_") & ~F.data.startswith("buy_business_"))
    async def buy_amount(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            currency = callback.data.replace("buy_", "")
            await state.update_data(action="buy", currency=currency)
            await callback.message.edit_text(f"✏️ Напишите количество {currency} для покупки:")
            await state.set_state("waiting_for_trade_amount")
        except Exception as e:
            logger.error(f"Ошибка в buy_amount: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(
        F.data.startswith("sell_") &
        ~F.data.startswith("sell_business_") &
        (F.data != "sell_business")
    )
    async def sell_amount(callback: types.CallbackQuery, state: FSMContext):
        """Обработчик продажи валюты в трейдинге"""
        if not await check_access(callback):
            return
        
        try:
            currency = callback.data.replace("sell_", "")
            await state.update_data(action="sell", currency=currency)
            await callback.message.edit_text(f"✏️ Напишите количество {currency} для продажи:")
            await state.set_state("waiting_for_trade_amount")
        except Exception as e:
            logger.error(f"Ошибка в sell_amount: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ОБРАБОТЧИК ТРЕЙДИНГА =====
    # ==========================================
    
    @dp.message(StateFilter("waiting_for_trade_amount"), F.text, ~F.text.startswith('/'))
    async def process_trade_amount(message: types.Message, state: FSMContext):
        """Обработчик сумм для трейдинга"""
        current_state = await state.get_state()
        if current_state != "waiting_for_trade_amount":
            return
        
        if not await check_access(message):
            await state.clear()
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
            limit = data.get("limit", {"max_trade": 15, "max_storage": 150})
            
            if not currency or not action:
                await message.answer("❌ Ошибка сессии. Начните заново.")
                await state.clear()
                return
            
            if amount > limit["max_trade"]:
                await message.answer(f"❌ Максимум можно {action} {limit['max_trade']} {currency}")
                return
            
            user_id = str(message.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if action == "buy":
                total = amount * price
                if user["money"] < total:
                    await message.answer(f"❌ Недостаточно средств! Нужно {total:,.0f}₽")
                    await state.clear()
                    return
                
                current = user["portfolio"].get(currency, 0)
                if current + amount > limit["max_storage"]:
                    await message.answer(
                        f"❌ Превышен лимит хранения! Максимум {limit['max_storage']} {currency}. "
                        f"Сейчас: {current}"
                    )
                    await state.clear()
                    return
                
                user["money"] -= total
                user["portfolio"][currency] = user["portfolio"].get(currency, 0) + amount
                user["trades_count"] = user.get("trades_count", 0) + amount
                
                users[user_id] = user
                await save_users(users)
                
                await message.answer(f"✅ Куплено {amount} {currency} за {total:,.0f}₽")
            
            elif action == "sell":
                current = user["portfolio"].get(currency, 0)
                if current < amount:
                    await message.answer(f"❌ У вас только {current} {currency}")
                    await state.clear()
                    return
                
                total = amount * price
                user["money"] += total
                user["portfolio"][currency] -= amount
                user["trades_count"] = user.get("trades_count", 0) + amount
                
                users[user_id] = user
                await save_users(users)
                
                await message.answer(f"✅ Продано {amount} {currency} за {total:,.0f}₽")
            
            await state.clear()
            
            # Возвращаем в меню трейдинга
            currency_rates.update_rates()
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            remaining = currency_rates.get_time_until_update()
            minutes = remaining // 60
            seconds = remaining % 60
            
            keyboard = [
                [InlineKeyboardButton(
                    text=f"BTC: {currency_rates.rates['BTC']['price']:,.0f}₽ (макс: 15)",
                    callback_data="trade_BTC"
                )],
                [InlineKeyboardButton(
                    text=f"WETcoin: {currency_rates.rates['WETcoin']['price']:,.0f}₽ (макс: 75)",
                    callback_data="trade_WETcoin"
                )],
                [InlineKeyboardButton(
                    text=f"NotCoin: {currency_rates.rates['NotCoin']['price']:,.0f}₽ (макс: 2500)",
                    callback_data="trade_NotCoin"
                )],
                [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="trading_info")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
            ]
            
            await message.answer(
                f"📈 **Трейдинг**\n\n"
                f"💰 Баланс: {user['money']:,.0f}₽\n"
                f"🪙 BRcoins: {user['brcoins']}\n\n"
                f"₿ BTC: {user['portfolio'].get('BTC', 0)}/150\n"
                f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}/100\n"
                f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}/5000\n\n"
                f"⏳ Следующее обновление курсов: {minutes:02d}:{seconds:02d}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
            
        except ValueError:
            await message.answer("❌ Введите число!")
            await state.clear()
        except Exception as e:
            logger.error(f"Ошибка в process_trade_amount: {e}")
            await message.answer("⚠️ Произошла ошибка!")
            await state.clear()
