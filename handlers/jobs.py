import random
from datetime import datetime

from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger, MINE_RESOURCES, FARM_RESOURCES
from database.file_manager import (
    load_users, save_users, load_inventory, save_inventory
)
from utils.helpers import check_access, get_default_user, is_function_disabled
from services.currency import currency_rates
from states import TradeStates

last_mine_time = {}

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
                [InlineKeyboardButton(text="🌾 Фермер", callback_data="work_farmer")],
                [InlineKeyboardButton(text="⛏️ Шахта", callback_data="mine")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            await callback.message.edit_text(
                "Выберите работу:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
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
            user["money"] += income
            user["total_earned"] = user.get("total_earned", 0) + income
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"🤿 +{income:,}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
                ])
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
                f"⛏️ Шахта\n\n"
                f"💰 +80,000 - 150,000₽ за ходку\n"
                f"🔄 Попыток осталось: {user['mine_attempts']}/100\n"
                f"⏳ Восстанавливается: +10 попыток в час\n\n"
                f"⏱️ КД между попытками: 3 секунды\n\n"
                f"Выберите действие:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
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
                f"⛏️ Вы копнули!\n\n{resource_text}\n\n"
                f"🔄 Осталось попыток: {user['mine_attempts']}/100",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⛏️ Копать ещё", callback_data="mine_dig")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="mine")]
                ])
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
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в mine_info: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ФЕРМА =====
    # ==========================================
    
    @dp.callback_query(F.data == "work_farmer")
    async def work_farmer_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("job_2"):
            await callback.answer("⛔ Эта работа остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            last_collect = user.get("farm", {}).get("last_collect")
            ready = True
            remaining_text = ""
            
            if last_collect:
                last_time = datetime.fromisoformat(last_collect)
                elapsed = (datetime.now() - last_time).total_seconds()
                if elapsed < 900:
                    ready = False
                    remaining = 900 - elapsed
                    minutes = int(remaining // 60)
                    seconds = int(remaining % 60)
                    remaining_text = f"⏳ До следующего сбора: {minutes:02d}:{seconds:02d}"
            
            keyboard = [
                [InlineKeyboardButton(text="🌾 Собрать урожай" + (" ✅" if ready else ""), callback_data="farm_harvest")],
                [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="farm_info")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
            ]
            
            text = "🌾 Ферма\n\n"
            if not ready and remaining_text:
                text += remaining_text + "\n\n"
            elif ready:
                text += "✅ Урожай готов к сбору!\n\n"
            else:
                text += "⏳ Подождите перед сбором урожая...\n\n"
            
            text += "📦 Ваше хозяйство:\n"
            text += f"🥛 Молоко: {user.get('farm', {}).get('milk', 0)} л.\n"
            text += f"🌿 Сено: {user.get('farm', {}).get('hay', 0)} кг.\n"
            text += f"🥚 Яйца: {user.get('farm', {}).get('eggs', 0)} шт.\n"
            text += f"🌾 Пшеница: {user.get('farm', {}).get('wheat', 0)} кг.\n"
            text += f"🥩 Мясо: {user.get('farm', {}).get('meat', 0)} кг."
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в work_farmer_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "farm_harvest")
    async def farm_harvest(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            last_collect = user.get("farm", {}).get("last_collect")
            if last_collect:
                last_time = datetime.fromisoformat(last_collect)
                elapsed = (datetime.now() - last_time).total_seconds()
                if elapsed < 900:
                    remaining = 900 - elapsed
                    minutes = int(remaining // 60)
                    seconds = int(remaining % 60)
                    await callback.answer(f"⏳ Подождите {minutes:02d}:{seconds:02d}!", show_alert=True)
                    return
            
            farm_data = user.get("farm", {})
            
            milk = random.randint(FARM_RESOURCES[0]["min"], FARM_RESOURCES[0]["max"])
            hay = random.randint(FARM_RESOURCES[1]["min"], FARM_RESOURCES[1]["max"])
            eggs = random.randint(FARM_RESOURCES[2]["min"], FARM_RESOURCES[2]["max"])
            wheat = random.randint(FARM_RESOURCES[3]["min"], FARM_RESOURCES[3]["max"])
            meat = random.randint(FARM_RESOURCES[4]["min"], FARM_RESOURCES[4]["max"])
            
            farm_data["milk"] = farm_data.get("milk", 0) + milk
            farm_data["hay"] = farm_data.get("hay", 0) + hay
            farm_data["eggs"] = farm_data.get("eggs", 0) + eggs
            farm_data["wheat"] = farm_data.get("wheat", 0) + wheat
            farm_data["meat"] = farm_data.get("meat", 0) + meat
            farm_data["last_collect"] = datetime.now().isoformat()
            
            user["farm"] = farm_data
            
            inventory = await load_inventory()
            if user_id not in inventory:
                inventory[user_id] = []
            
            for _ in range(milk):
                inventory[user_id].append("Молоко")
            for _ in range(hay):
                inventory[user_id].append("Сено")
            for _ in range(eggs):
                inventory[user_id].append("Яйца")
            for _ in range(wheat):
                inventory[user_id].append("Пшеница")
            for _ in range(meat):
                inventory[user_id].append("Мясо")
            
            await save_inventory(inventory)
            
            bonus = random.randint(5000, 15000)
            user["money"] += bonus
            user["total_earned"] = user.get("total_earned", 0) + bonus
            
            users[user_id] = user
            await save_users(users)
            
            text = "🌾 Собран урожай!\n\n"
            text += f"🥛 Вы собрали {milk} л. молока\n"
            text += f"🌿 Вы собрали {hay} кг. сена\n"
            text += f"🥚 Вы собрали {eggs} шт. яиц\n"
            text += f"🌾 Вы собрали {wheat} кг. пшеницы\n"
            text += f"🥩 Вы собрали {meat} кг. мяса\n"
            text += f"💰 +{bonus:,}₽ за сбор\n\n"
            text += "📦 Ресурсы добавлены в инвентарь!\n"
            text += "🔄 Продать их можно у Скупщика."
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 На ферму", callback_data="work_farmer")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в farm_harvest: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "farm_info")
    async def farm_info(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            text = "ℹ️ Ферма\n\n"
            text += "🌾 Вы можете собирать урожай каждые 15 минут.\n\n"
            text += "📦 Ресурсы, которые можно получить:\n"
            text += f"🥛 Молоко - {FARM_RESOURCES[0]['min']}-{FARM_RESOURCES[0]['max']} л. (Цена: {FARM_RESOURCES[0]['price']:,}₽/л.)\n"
            text += f"🌿 Сено - {FARM_RESOURCES[1]['min']}-{FARM_RESOURCES[1]['max']} кг. (Цена: {FARM_RESOURCES[1]['price']:,}₽/кг.)\n"
            text += f"🥚 Яйца - {FARM_RESOURCES[2]['min']}-{FARM_RESOURCES[2]['max']} шт. (Цена: {FARM_RESOURCES[2]['price']:,}₽/шт.)\n"
            text += f"🌾 Пшеница - {FARM_RESOURCES[3]['min']}-{FARM_RESOURCES[3]['max']} кг. (Цена: {FARM_RESOURCES[3]['price']:,}₽/кг.)\n"
            text += f"🥩 Мясо - {FARM_RESOURCES[4]['min']}-{FARM_RESOURCES[4]['max']} кг. (Цена: {FARM_RESOURCES[4]['price']:,}₽/кг.)\n\n"
            text += "🔄 Продать ресурсы можно в разделе Скупщик."
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 На ферму", callback_data="work_farmer")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в farm_info: {e}")
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
                f"📈 Трейдинг\n\n"
                f"💰 Баланс: {user['money']:,.0f}₽\n"
                f"🪙 BRcoins: {user['brcoins']}\n\n"
                f"₿ BTC: {user['portfolio'].get('BTC', 0)}/150\n"
                f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}/100\n"
                f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}/5000\n\n"
                f"⏳ Следующее обновление курсов: {minutes:02d}:{seconds:02d}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
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
                f"📊 {currency}\n"
                f"Цена: {price:,.0f}₽\n"
                f"Макс. покупка/продажа: {limits[currency]['max_trade']}\n"
                f"Макс. хранение: {limits[currency]['max_storage']}\n\n"
                f"Выберите действие:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
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
            await state.set_state(TradeStates.waiting_for_trade_amount)
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
            await state.set_state(TradeStates.waiting_for_trade_amount)
        except Exception as e:
            logger.error(f"Ошибка в sell_amount: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
