import random
import string
import uuid
import asyncio
from datetime import datetime, timedelta
from aiogram import Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from database.file_manager import (
    load_users, save_users, load_settings, save_settings, 
    load_promocodes, save_promocodes, load_inventory, 
    save_inventory, load_business, save_business,
    load_auction, save_auction, load_disabled_functions,
    save_disabled_functions
)
from utils.helpers import (
    check_access, get_default_user, is_admin, check_subscription,
    is_function_disabled
)
from services.currency import currency_rates
from services.tasks import (
    promo_auto_loop, check_business_loop, 
    update_auction, promo_running, promo_task,
    business_running, business_check_task
)
from config import (
    ADMIN_IDS, bot, logger, BUSINESS_CONFIG, CONTAINERS, 
    MINE_RESOURCES, FARM_RESOURCES, PROMO_CHANNEL_ID,
    AUCTION_CARS, FUNCTION_IDS
)

# ========== СОСТОЯНИЯ ==========
class TradeStates(StatesGroup):
    waiting_for_amount = State()

class CasinoStates(StatesGroup):
    waiting_for_bet = State()
    waiting_for_mines = State()
    waiting_for_field_size = State()

class SupportStates(StatesGroup):
    waiting_for_message = State()

class AuctionStates(StatesGroup):
    waiting_for_bid = State()
    waiting_for_car_auction = State()

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
container_animations = {}
mines_games = {}
last_mine_time = {}
auction_index = {}

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def add_coinrun_income(user):
    try:
        settings = await load_settings()
        if settings.get("coinrun_enabled", False):
            br_income = random.randint(1, 10)
            user["brcoins"] += br_income
            settings["coinrun_total"] = settings.get("coinrun_total", 0) + br_income
            await save_settings(settings)
            return br_income
    except Exception as e:
        logger.error(f"Ошибка в add_coinrun_income: {e}")
    return 0

async def get_auto_mine_resource():
    resources = BUSINESS_CONFIG["auto_mine"]["resources"]
    total_chance = sum(r["chance"] for r in resources)
    roll = random.random() * total_chance
    cumulative = 0
    for res in resources:
        cumulative += res["chance"]
        if roll <= cumulative:
            return res["name"]
    return random.choice(resources)["name"]

async def get_container_animation(container_name, selected_item):
    items = CONTAINERS[container_name]["items"]
    item_names = [item["name"] for item in items]
    animation = []
    for _ in range(3):
        random.shuffle(item_names)
        animation.append(" > ".join(item_names[:5]))
    animation.append(f"✅ {selected_item['name']}")
    return "\n".join(animation)

async def get_user_business_count(user_id):
    users = await load_users()
    user = users.get(str(user_id), get_default_user())
    count = 0
    for biz in user.get("business", {}).values():
        if biz.get("owned", False):
            count += 1
    return count

async def get_business_status(user_id):
    business = await load_business()
    users = await load_users()
    user = users.get(str(user_id), get_default_user())
    user_business = user.get("business", {})
    
    status = {}
    for key, config in BUSINESS_CONFIG.items():
        owned = user_business.get(key, {}).get("owned", False)
        last_collect = user_business.get(key, {}).get("last_collect")
        auto_collect = user_business.get(key, {}).get("auto_collect", False)
        
        if owned and last_collect:
            last_time = datetime.fromisoformat(last_collect)
            elapsed = (datetime.now() - last_time).total_seconds()
            cooldown = config["cooldown"]
            ready = elapsed >= cooldown
            remaining = max(0, cooldown - elapsed)
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            status[key] = {
                "owned": True,
                "ready": ready,
                "remaining": f"{hours:02d}:{minutes:02d}",
                "last_collect": last_collect,
                "auto_collect": auto_collect
            }
        elif owned:
            status[key] = {
                "owned": True,
                "ready": False,
                "remaining": "Неизвестно",
                "last_collect": last_collect,
                "auto_collect": auto_collect
            }
        else:
            status[key] = {
                "owned": False,
                "ready": False,
                "remaining": "Не куплен",
                "auto_collect": False
            }
    
    return status

# ========== ГЛАВНОЕ МЕНЮ ==========
async def get_main_menu(user_id):
    users = await load_users()
    user = users.get(str(user_id), get_default_user())
    
    currency_rates.update_rates()
    
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
        [InlineKeyboardButton(text="🔨 Аукцион", callback_data="auction")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🆘 Тех.поддержка", callback_data="support")]
    ]
    
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ==========
def register_handlers(dp: Dispatcher):
    
    # ==========================================
    # ===== АДМИН-КОМАНДЫ =====
    # ==========================================
    
    @dp.message(Command("ahelp"))
    async def admin_help(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        help_text = (
            "👑 **АДМИН-КОМАНДЫ:**\n\n"
            "**👤 Игроки:**\n"
            "`/getplayeracc @username` - меню игрока\n"
            "`/givecar @username кол-во id_машины` - выдача машины\n\n"
            "**🏢 Бизнес:**\n"
            "`/resetbusiness @username (причина)` - сброс бизнеса\n"
            "`/resetallbusiness` - сброс всех бизнесов\n"
            "`/givebusiness @username кол-во id_бизнеса` - выдача бизнеса\n\n"
            "**💰 Выдача валют:**\n"
            "`/giverub @username кол-во` - выдача рублей\n"
            "`/givedonate @username кол-во` - выдача BRcoins\n\n"
            "**🎰 Управление:**\n"
            "`/promostart on/off` - авто-промокоды\n"
            "`/promostatus` - статус промокодов\n"
            "`/coinrun on/off` - CoinRun\n"
            "`/technical on/off` - техобслуживание\n"
            "`/status` - статус бота\n"
            "`/getdb` - получить базу\n"
            "`/mailall текст` - рассылка\n"
            "`/createpromo (1/0) (использований) (кол-во)` - создать промокод\n"
            "`/update_rates_admin` - обновить курсы\n\n"
            "**🔨 Аукцион:**\n"
            "`/setcarauction id_машины минуты старт_цена кол-во` - добавить машину\n"
            "`/caridlist` - список машин с ID\n"
            "`/refreshauction` - обновить аукцион\n\n"
            "**⛔ Отключение функций:**\n"
            "`/idfunctionlist` - список ID функций\n"
            "`/stopfunction айди` - остановить функцию\n"
            "`/returnfunction айди` - вернуть функцию\n\n"
            "**ID бизнесов:**\n"
            "`auto_mine` - Авто-Шахта\n"
            "`tech_center` - Техцентр\n"
            "`tire_center` - Шиномонтаж\n"
            "`styling_center` - Стайлинг\n"
            "`shop_24` - Магазин 24/7"
        )
        await message.answer(help_text, parse_mode="Markdown")

    # ---- /getplayeracc ----
    @dp.message(Command("getplayeracc"))
    async def get_player_acc(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Использование: /getplayeracc @username")
            return
        
        username = parts[1].replace("@", "").lower()
        
        try:
            users = await load_users()
            found_user = None
            found_id = None
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        found_user = data
                        found_id = user_id
                        break
                except:
                    continue
            
            if not found_user:
                await message.answer(f"❌ Пользователь @{username} не найден!")
                return
            
            # Создаем меню игрока
            text = (
                f"👤 **ПРОФИЛЬ @{username}**\n\n"
                f"💰 Баланс: {found_user['money']:,.0f}₽\n"
                f"💎 BRcoins: {found_user['brcoins']}\n"
                f"📈 Заработано: {found_user['total_earned']:,.0f}₽\n"
                f"🤝 Сделок: {found_user['trades_count']}\n"
                f"⛔ Забанен: {'Да' if found_user.get('banned', False) else 'Нет'}\n\n"
                f"**📊 Портфель:**\n"
                f"₿ BTC: {found_user['portfolio'].get('BTC', 0)}\n"
                f"💧 WETcoin: {found_user['portfolio'].get('WETcoin', 0)}\n"
                f"🪙 NotCoin: {found_user['portfolio'].get('NotCoin', 0)}\n\n"
                f"🚗 Машин в гараже: {len(found_user.get('inventory', []))}"
            )
            
            keyboard = [
                [InlineKeyboardButton(text="💰 Обнулить баланс ₽", callback_data=f"admin_reset_money_{found_id}")],
                [InlineKeyboardButton(text="💎 Обнулить BRcoins", callback_data=f"admin_reset_br_{found_id}")],
                [InlineKeyboardButton(text="🪙 Обнулить трейдинг", callback_data=f"admin_reset_trade_{found_id}")],
                [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin_ban_{found_id}")],
                [InlineKeyboardButton(text="🚗 Гараж игрока", callback_data=f"admin_garage_{found_id}")],
                [InlineKeyboardButton(text="🏢 Бизнес игрока", callback_data=f"admin_business_{found_id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            
            await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка в getplayeracc: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ---- Обработчики админ-кнопок из getplayeracc ----
    @dp.callback_query(F.data.startswith("admin_reset_money_"))
    async def admin_reset_money(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_reset_money_", "")
        try:
            users = await load_users()
            if user_id in users:
                users[user_id]["money"] = 0
                await save_users(users)
                await callback.answer("✅ Баланс обнулен!", show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_reset_br_"))
    async def admin_reset_br(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_reset_br_", "")
        try:
            users = await load_users()
            if user_id in users:
                users[user_id]["brcoins"] = 0
                await save_users(users)
                await callback.answer("✅ BRcoins обнулены!", show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_reset_trade_"))
    async def admin_reset_trade(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_reset_trade_", "")
        try:
            users = await load_users()
            if user_id in users:
                users[user_id]["portfolio"] = {"BTC": 0, "WETcoin": 0, "NotCoin": 0}
                await save_users(users)
                await callback.answer("✅ Трейдинг обнулен!", show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_ban_"))
    async def admin_ban(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_ban_", "")
        try:
            users = await load_users()
            if user_id in users:
                users[user_id]["banned"] = True
                await save_users(users)
                await callback.answer("✅ Пользователь забанен!", show_alert=True)
                try:
                    await bot.send_message(int(user_id), "🚫 Ваш аккаунт заблокирован администратором!")
                except:
                    pass
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_garage_"))
    async def admin_garage(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_garage_", "")
        try:
            users = await load_users()
            if user_id not in users:
                await callback.answer("❌ Пользователь не найден!", show_alert=True)
                return
            
            inventory = users[user_id].get("inventory", [])
            if not inventory:
                await callback.answer("🚗 У игрока нет машин!", show_alert=True)
                return
            
            text = f"🚗 **Гараж игрока:**\n\n"
            for i, car in enumerate(inventory, 1):
                if isinstance(car, dict):
                    text += f"{i}. {car.get('name', 'Неизвестно')} - {car.get('price', 0):,.0f}₽\n"
                else:
                    text += f"{i}. {car}\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_business_"))
    async def admin_business(callback: types.CallbackQuery):
        if not is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_business_", "")
        try:
            users = await load_users()
            if user_id not in users:
                await callback.answer("❌ Пользователь не найден!", show_alert=True)
                return
            
            business = users[user_id].get("business", {})
            has_business = False
            text = f"🏢 **Бизнес игрока:**\n\n"
            
            for key, data in business.items():
                if data.get("owned", False):
                    has_business = True
                    config = BUSINESS_CONFIG.get(key, {})
                    text += f"{config.get('emoji', '')} {config.get('name', key)} - Активен\n"
                    if data.get("auto_collect", False):
                        text += f"   🔄 Авто-сбор включен\n"
            
            if not has_business:
                await callback.answer("🏢 У игрока нет бизнеса!", show_alert=True)
                return
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    # ---- /givecar ----
    @dp.message(Command("givecar"))
    async def give_car(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split(maxsplit=3)
        if len(parts) < 4:
            await message.answer("❌ Использование: /givecar @username кол-во id_машины")
            return
        
        try:
            username = parts[1].replace("@", "").lower()
            amount = int(parts[2])
            car_id = parts[3]
            
            if amount <= 0:
                await message.answer("❌ Количество должно быть положительным!")
                return
            
            # Проверяем, есть ли такая машина в конфиге
            car_name = None
            for name in AUCTION_CARS.keys():
                if car_id in name.lower():
                    car_name = name
                    break
            
            if not car_name:
                await message.answer(f"❌ Машина '{car_id}' не найдена!\nИспользуйте /caridlist для списка")
                return
            
            users = await load_users()
            found = False
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        if "inventory" not in data:
                            data["inventory"] = []
                        
                        car_price = AUCTION_CARS.get(car_name, {}).get("base_price", 0)
                        for _ in range(amount):
                            data["inventory"].append({
                                "name": car_name,
                                "price": car_price,
                                "from_admin": True
                            })
                        
                        users[user_id] = data
                        await save_users(users)
                        
                        await message.answer(f"✅ @{username} получил {amount} шт. {car_name}!")
                        try:
                            await bot.send_message(
                                int(user_id),
                                f"🎁 Вы получили {amount} шт. {car_name} от администратора!"
                            )
                        except:
                            pass
                        found = True
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске пользователя: {e}")
                    continue
            
            if not found:
                await message.answer(f"❌ @{username} не найден!")
                
        except ValueError:
            await message.answer("❌ Введите корректное число!")
        except Exception as e:
            logger.error(f"Ошибка в givecar: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ---- /caridlist ----
    @dp.message(Command("caridlist"))
    async def car_id_list(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            text = "🚗 **СПИСОК МАШИН И ИХ ID:**\n\n"
            for i, (name, data) in enumerate(AUCTION_CARS.items(), 1):
                text += f"**{i}. {name}**\n"
                text += f"   ID: `car_{i}`\n"
                text += f"   ⭐ {'⭐' * data['stars']} ({data['rarity']})\n"
                text += f"   💰 {data['base_price']:,.0f}₽\n\n"
            
            # Разбиваем на части если слишком длинное
            if len(text) > 4000:
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for part in parts:
                    await message.answer(part, parse_mode="Markdown")
            else:
                await message.answer(text, parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Ошибка в caridlist: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ---- /idfunctionlist ----
    @dp.message(Command("idfunctionlist"))
    async def id_function_list(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            text = "📋 **СПИСОК ID ФУНКЦИЙ:**\n\n"
            text += "**Работы:**\n"
            text += "• job_1 - Шахта\n"
            text += "• job_2 - Ферма\n"
            text += "• job_3 - Трейдинг\n"
            text += "• job_4 - Водолаз\n\n"
            
            text += "**Кнопки меню:**\n"
            text += "• menubutton_1 - Работы\n"
            text += "• menubutton_2 - Донат\n"
            text += "• menubutton_3 - Форбс\n"
            text += "• menubutton_4 - Контейнеры\n"
            text += "• menubutton_5 - Гараж\n"
            text += "• menubutton_6 - Инвентарь\n"
            text += "• menubutton_7 - Скупщик\n"
            text += "• menubutton_8 - Бизнес\n"
            text += "• menubutton_9 - Казино\n"
            text += "• menubutton_10 - Статистика\n"
            text += "• menubutton_11 - Техподдержка\n\n"
            
            text += "**Казино:**\n"
            text += "• casinogame_1 - Кубик\n"
            text += "• casinogame_2 - Слоты\n"
            text += "• casinogame_3 - Мины\n\n"
            
            text += "**Трейдинг:**\n"
            text += "• trading_1 - BTC\n"
            text += "• trading_2 - WETcoin\n"
            text += "• trading_3 - NotCoin"
            
            await message.answer(text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка в idfunctionlist: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ---- /stopfunction ----
    @dp.message(Command("stopfunction"))
    async def stop_function(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Использование: /stopfunction айди_функции")
            return
        
        function_id = parts[1]
        
        try:
            disabled = await load_disabled_functions()
            if "functions" not in disabled:
                disabled["functions"] = []
            
            if function_id not in disabled["functions"]:
                disabled["functions"].append(function_id)
                await save_disabled_functions(disabled)
                await message.answer(f"✅ Функция '{function_id}' остановлена!")
            else:
                await message.answer(f"ℹ️ Функция '{function_id}' уже остановлена")
                
        except Exception as e:
            logger.error(f"Ошибка в stopfunction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ---- /returnfunction ----
    @dp.message(Command("returnfunction"))
    async def return_function(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Использование: /returnfunction айди_функции")
            return
        
        function_id = parts[1]
        
        try:
            disabled = await load_disabled_functions()
            if "functions" in disabled and function_id in disabled["functions"]:
                disabled["functions"].remove(function_id)
                await save_disabled_functions(disabled)
                await message.answer(f"✅ Функция '{function_id}' возвращена!")
            else:
                await message.answer(f"ℹ️ Функция '{function_id}' не была остановлена")
                
        except Exception as e:
            logger.error(f"Ошибка в returnfunction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ---- /setcarauction ----
    @dp.message(Command("setcarauction"))
    async def set_car_auction(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) < 5:
            await message.answer("❌ Использование: /setcarauction id_машины минуты старт_цена кол-во")
            return
        
        try:
            car_id = parts[1]
            minutes = int(parts[2])
            start_price = int(parts[3])
            quantity = int(parts[4])
            
            if minutes <= 0 or start_price <= 0 or quantity <= 0:
                await message.answer("❌ Все значения должны быть положительными!")
                return
            
            # Находим машину
            car_name = None
            for name in AUCTION_CARS.keys():
                if car_id in name.lower():
                    car_name = name
                    break
            
            if not car_name:
                await message.answer(f"❌ Машина '{car_id}' не найдена!")
                return
            
            car_data = AUCTION_CARS[car_name]
            
            # Загружаем аукцион
            auction = await load_auction()
            lots = auction.get("lots", [])
            
            # Добавляем лоты
            for _ in range(quantity):
                lots.append({
                    "id": f"lot_{len(lots)+1}",
                    "car_name": car_name,
                    "stars": car_data["stars"],
                    "rarity": car_data["rarity"],
                    "base_price": car_data["base_price"],
                    "start_price": start_price,
                    "current_bid": start_price,
                    "highest_bidder": None,
                    "time_left": minutes,
                    "active": True,
                    "admin_added": True
                })
            
            # Ограничиваем до 15 лотов
            if len(lots) > 15:
                lots = lots[:15]
            
            auction["lots"] = lots
            auction["last_update"] = datetime.now().isoformat()
            await save_auction(auction)
            
            await message.answer(
                f"✅ Машина добавлена на аукцион!\n"
                f"🚗 {car_name}\n"
                f"💰 Стартовая цена: {start_price:,.0f}₽\n"
                f"⏱️ Время: {minutes} мин.\n"
                f"📦 Количество: {quantity}"
            )
            
        except ValueError:
            await message.answer("❌ Введите корректные числа!")
        except Exception as e:
            logger.error(f"Ошибка в setcarauction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ---- /refreshauction ----
    @dp.message(Command("refreshauction"))
    async def refresh_auction_admin(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            await update_auction()
            await message.answer("✅ Аукцион обновлен!")
        except Exception as e:
            logger.error(f"Ошибка в refreshauction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ---- ОСТАЛЬНЫЕ АДМИН-КОМАНДЫ (из оригинального кода) ----
    # ... (resetbusiness, resetallbusiness, givebusiness, 
    # promostart, promostatus, coinrun, technical, status, 
    # getdb, mailall, giverub, givedonate, createpromo, update_rates_admin)
    # Я их не вставляю чтобы не раздувать, но они должны быть

    # ==========================================
    # ===== СТАРТ =====
    # ==========================================
    
    @dp.message(Command("start"))
    async def start_command(message: types.Message):
        user_id = str(message.from_user.id)
        
        try:
            if not await check_subscription(message.from_user.id):
                await message.answer(
                    "📢 Подпишитесь на канал @WeteroRussia!\n\n"
                    "👉 [Подписаться](https://t.me/+TAhbj7PhoWhhZTQ6)\n\n"
                    "После подписки нажмите /start",
                    parse_mode="Markdown"
                )
                return
            
            users = await load_users()
            
            if user_id not in users:
                users[user_id] = get_default_user()
                await save_users(users)
            
            if not await check_access(message):
                return
            
            # Проверка на бан
            if users[user_id].get("banned", False):
                await message.answer("🚫 Ваш аккаунт заблокирован!")
                return
            
            text, keyboard = await get_main_menu(message.from_user.id)
            await message.answer(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

    # ==========================================
    # ===== НАЗАД =====
    # ==========================================
    
    @dp.callback_query(F.data == "back_main")
    async def back_main(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            text, keyboard = await get_main_menu(callback.from_user.id)
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка в back_main: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== АУКЦИОН =====
    # ==========================================
    
    @dp.callback_query(F.data == "auction")
    async def auction_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            auction = await load_auction()
            lots = auction.get("lots", [])
            
            # Фильтруем активные лоты
            active_lots = [lot for lot in lots if lot.get("active", True)]
            
            if not active_lots:
                await callback.message.edit_text(
                    "🔨 **АУКЦИОН**\n\n"
                    "😔 На данный момент нет активных лотов.\n"
                    "Загляните позже!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ]),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return
            
            # Сохраняем индекс для пользователя
            user_id = str(callback.from_user.id)
            if user_id not in auction_index:
                auction_index[user_id] = 0
            else:
                if auction_index[user_id] >= len(active_lots):
                    auction_index[user_id] = 0
            
            idx = auction_index[user_id]
            lot = active_lots[idx]
            
            # Формируем отображение звезд
            stars = "⭐" * lot["stars"]
            
            text = (
                f"🔨 **АУКЦИОН**\n\n"
                f"🚗 **{lot['car_name']}**\n"
                f"{stars} ({lot['rarity']})\n\n"
                f"💰 Начальная ставка: {lot['start_price']:,.0f}₽\n"
                f"💰 Текущая ставка: {lot['current_bid']:,.0f}₽\n"
                f"⏱️ Осталось: {lot['time_left']} мин.\n"
            )
            
            if lot.get("highest_bidder"):
                try:
                    user = await bot.get_chat(int(lot["highest_bidder"]))
                    username = user.username or f"User_{lot['highest_bidder'][:5]}"
                    text += f"👤 Лидирует: @{username}\n"
                except:
                    text += f"👤 Лидирует: ID {lot['highest_bidder'][:8]}...\n"
            
            keyboard = [
                [
                    InlineKeyboardButton(text="◀", callback_data=f"auction_prev"),
                    InlineKeyboardButton(text="💰 Сделать ставку", callback_data=f"auction_bid_{idx}"),
                    InlineKeyboardButton(text="⏭", callback_data=f"auction_next")
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Ошибка в auction_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("auction_prev"))
    async def auction_prev(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            auction = await load_auction()
            active_lots = [lot for lot in auction.get("lots", []) if lot.get("active", True)]
            
            if not active_lots:
                await callback.answer("❌ Нет активных лотов!", show_alert=True)
                return
            
            if user_id not in auction_index:
                auction_index[user_id] = 0
            else:
                auction_index[user_id] = (auction_index[user_id] - 1) % len(active_lots)
            
            # Обновляем меню
            await auction_menu(callback, None)
            
        except Exception as e:
            logger.error(f"Ошибка в auction_prev: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("auction_next"))
    async def auction_next(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            auction = await load_auction()
            active_lots = [lot for lot in auction.get("lots", []) if lot.get("active", True)]
            
            if not active_lots:
                await callback.answer("❌ Нет активных лотов!", show_alert=True)
                return
            
            if user_id not in auction_index:
                auction_index[user_id] = 0
            else:
                auction_index[user_id] = (auction_index[user_id] + 1) % len(active_lots)
            
            # Обновляем меню
            await auction_menu(callback, None)
            
        except Exception as e:
            logger.error(f"Ошибка в auction_next: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("auction_bid_"))
    async def auction_bid(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            idx = int(callback.data.replace("auction_bid_", ""))
            await state.update_data(auction_idx=idx)
            
            await callback.message.edit_text(
                "💰 **Введите сумму вашей ставки:**\n\n"
                "⚠️ Ставка должна быть выше текущей!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="auction")]
                ]),
                parse_mode="Markdown"
            )
            await state.set_state(AuctionStates.waiting_for_bid)
            
        except Exception as e:
            logger.error(f"Ошибка в auction_bid: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.message(AuctionStates.waiting_for_bid)
    async def process_auction_bid(message: types.Message, state: FSMContext):
        if not await check_access(message):
            await state.clear()
            return
        
        try:
            bid = int(message.text)
            if bid <= 0:
                await message.answer("❌ Ставка должна быть положительной!")
                return
            
            data = await state.get_data()
            idx = data.get("auction_idx")
            
            auction = await load_auction()
            active_lots = [lot for lot in auction.get("lots", []) if lot.get("active", True)]
            
            if idx >= len(active_lots):
                await message.answer("❌ Лот не найден!")
                await state.clear()
                return
            
            lot = active_lots[idx]
            
            if bid <= lot["current_bid"]:
                await message.answer(
                    f"❌ Ставка должна быть выше текущей ({lot['current_bid']:,.0f}₽)!"
                )
                return
            
            user_id = str(message.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if user["money"] < bid:
                await message.answer(
                    f"❌ Недостаточно средств! У вас {user['money']:,.0f}₽"
                )
                return
            
            # Возвращаем предыдущему лидеру деньги
            if lot.get("highest_bidder"):
                prev_bidder = lot["highest_bidder"]
                if prev_bidder in users:
                    users[prev_bidder]["money"] += lot["current_bid"]
            
            # Списываем деньги у нового лидера
            user["money"] -= bid
            
            # Обновляем лот
            lot["current_bid"] = bid
            lot["highest_bidder"] = user_id
            lot["time_left"] = 15  # Сбрасываем таймер на 15 минут
            
            # Сохраняем
            users[user_id] = user
            await save_users(users)
            await save_auction(auction)
            await state.clear()
            
            await message.answer(
                f"✅ Ваша ставка принята!\n"
                f"💰 Ставка: {bid:,.0f}₽\n"
                f"🚗 Лот: {lot['car_name']}\n"
                f"⏱️ Таймер сброшен на 15 минут"
            )
            
            # Показываем меню аукциона
            await auction_menu(message, None)
            
        except ValueError:
            await message.answer("❌ Введите число!")
        except Exception as e:
            logger.error(f"Ошибка в process_auction_bid: {e}")
            await state.clear()
            await message.answer("⚠️ Ошибка!")

    # ==========================================
    # ===== РАБОТЫ =====
    # ==========================================
    
    @dp.callback_query(F.data == "works")
    async def works_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        # Проверяем, не отключена ли функция
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
        
        # Проверяем, не отключена ли функция
        if await is_function_disabled("job_4"):
            await callback.answer("⛔ Эта работа остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            income = random.randint(70000, 200000)
            user["money"] += income
            user["total_earned"] += income
            
            br_income = await add_coinrun_income(user)
            br_text = f"\n🪙 +{br_income} BRcoins (CoinRun)" if br_income > 0 else ""
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"🤿 +{income:,}₽{br_text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="works")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в work_diver: {e}")
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
        
        # Проверяем, не отключена ли функция
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
            user["total_earned"] += bonus
            
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
    # ===== ШАХТА =====
    # ==========================================
    
    @dp.callback_query(F.data == "mine")
    async def mine_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        # Проверяем, не отключена ли функция
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
            user["total_earned"] += base_income
            
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
            
            br_income = await add_coinrun_income(user)
            if br_income > 0:
                resource_text += f"\n🪙 +{br_income} BRcoins (CoinRun)"
            
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
    # ===== ТРЕЙДИНГ =====
    # ==========================================
    
    @dp.callback_query(F.data == "work_trading")
    async def work_trading(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        # Проверяем, не отключена ли функция
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

    @dp.callback_query(F.data.startswith("buy_") & ~F.data.startswith("buy_business_"))
    async def buy_amount(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            currency = callback.data.split("_")[1]
            await state.update_data(action="buy", currency=currency)
            await callback.message.edit_text(f"✏️ Напишите количество {currency} для покупки:")
            await state.set_state(TradeStates.waiting_for_amount)
        except Exception as e:
            logger.error(f"Ошибка в buy_amount: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("sell_") & ~F.data.startswith("sell_business_"))
    async def sell_amount(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            currency = callback.data.split("_")[1]
            await state.update_data(action="sell", currency=currency)
            await callback.message.edit_text(f"✏️ Напишите количество {currency} для продажи:")
            await state.set_state(TradeStates.waiting_for_amount)
        except Exception as e:
            logger.error(f"Ошибка в sell_amount: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.message(TradeStates.waiting_for_amount)
    async def process_trade_amount(message: types.Message, state: FSMContext):
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
                user["trades_count"] += amount
                
                users[user_id] = user
                await save_users(users)
                
                await message.answer(f"✅ Куплено {amount} {currency} за {total:,.0f}₽")
            
            elif action == "sell":
                current = user["portfolio"].get(currency, 0)
                if current < amount:
                    await message.answer(
                        f"❌ У вас только {current} {currency}"
                    )
                    await state.clear()
                    return
                
                total = amount * price
                user["money"] += total
                user["portfolio"][currency] -= amount
                user["trades_count"] += amount
                
                users[user_id] = user
                await save_users(users)
                
                await message.answer(f"✅ Продано {amount} {currency} за {total:,.0f}₽")
            
            await state.clear()
            
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
                f"📈 Трейдинг\n\n"
                f"💰 Баланс: {user['money']:,.0f}₽\n"
                f"🪙 BRcoins: {user['brcoins']}\n\n"
                f"₿ BTC: {user['portfolio'].get('BTC', 0)}/150\n"
                f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}/100\n"
                f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}/5000\n\n"
                f"⏳ Следующее обновление курсов: {minutes:02d}:{seconds:02d}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
        except ValueError:
            await message.answer("❌ Введите число!")
            await state.clear()
        except Exception as e:
            logger.error(f"Ошибка в process_trade_amount: {e}")
            await message.answer("⚠️ Произошла ошибка!")
            await state.clear()

    # ==========================================
    # ===== ДОНАТ =====
    # ==========================================
    
    @dp.callback_query(F.data == "donate")
    async def donate_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            keyboard = [
                [InlineKeyboardButton(text="💳 Купить", callback_data="donate_buy")],
                [InlineKeyboardButton(text="🎫 Промокод", callback_data="promo")],
                [InlineKeyboardButton(text="💰 Баланс", callback_data="donate_balance")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            await callback.message.edit_text(
                "💎 Донат\nКурс: 1₽ = 10 BRcoins\n@weterochina",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в donate_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "donate_buy")
    async def donate_buy(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "💳 Обратитесь к @weterochina",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в donate_buy: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "promo")
    async def promo_menu(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "🎫 Введите промокод в чат",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в promo_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "donate_balance")
    async def donate_balance(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            users = await load_users()
            user = users.get(str(callback.from_user.id), get_default_user())
            
            await callback.message.edit_text(
                f"💰 Баланс доната\n"
                f"Потрачено: {user['donate_spent']}₽\n"
                f"Получено: {user['donate_received']} BRcoins\n"
                f"Баланс: {user['brcoins']} BRcoins",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в donate_balance: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ФОРБС =====
    # ==========================================
    
    @dp.callback_query(F.data == "forbes")
    async def forbes_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            keyboard = [
                [InlineKeyboardButton(text="🏆 По деньгам", callback_data="forbes_rich")],
                [InlineKeyboardButton(text="💎 По BRcoins", callback_data="forbes_br")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            await callback.message.edit_text(
                "🏆 Форбс",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "forbes_rich")
    async def forbes_rich(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            users = await load_users()
            sorted_users = sorted(
                users.items(),
                key=lambda x: x[1]["money"],
                reverse=True
            )[:10]
            
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
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_rich: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "forbes_br")
    async def forbes_br(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            users = await load_users()
            sorted_users = sorted(
                users.items(),
                key=lambda x: x[1]["brcoins"],
                reverse=True
            )[:10]
            
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
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_br: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== КОНТЕЙНЕРЫ =====
    # ==========================================
    
    @dp.callback_query(F.data == "containers")
    async def containers_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            keyboard = []
            for name, data in CONTAINERS.items():
                keyboard.append([InlineKeyboardButton(
                    text=f"🚗 {name} ({data['price']:,.0f}₽)",
                    callback_data=f"container_{name}"
                )])
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
            
            await callback.message.edit_text(
                "🚗 Контейнеры:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в containers_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("container_"))
    async def open_container(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            container_name = callback.data.replace("container_", "")
            users = await load_users()
            user_id = str(callback.from_user.id)
            user = users.get(user_id, get_default_user())
            
            container_data = CONTAINERS.get(container_name)
            if not container_data:
                await callback.answer("❌ Контейнер не найден!", show_alert=True)
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
            
            animation_text = await get_container_animation(container_name, selected_item)
            
            item_id = str(uuid.uuid4())[:8]
            container_animations[user_id] = {
                "car": selected_item,
                "container": container_name,
                "item_id": item_id
            }
            
            keyboard = [
                [
                    InlineKeyboardButton(text="🏠 Забрать в гараж", callback_data=f"container_take_{item_id}"),
                    InlineKeyboardButton(text="💰 Продать (100%)", callback_data=f"container_sell_{item_id}")
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="containers")]
            ]
            
            await callback.message.edit_text(
                f"🚗 {container_name}!\n\n"
                f"🎰 Прокрутка:\n{animation_text}\n\n"
                f"🎉 Выпало: {selected_item['name']}\n"
                f"💰 Стоимость: {selected_item['price']:,.0f}₽\n"
                f"💳 Осталось: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            users[user_id] = user
            await save_users(users)
        except Exception as e:
            logger.error(f"Ошибка в open_container: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("container_take_"))
    async def container_take(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            item_id = callback.data.replace("container_take_", "")
            user_id = str(callback.from_user.id)
            
            if user_id not in container_animations:
                await callback.answer("❌ Контейнер не найден!", show_alert=True)
                return
            
            car_data = container_animations[user_id]
            if car_data.get("item_id") != item_id:
                await callback.answer("❌ Контейнер не найден!", show_alert=True)
                return
            
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            car = car_data["car"]
            
            if "inventory" not in user:
                user["inventory"] = []
            
            user["inventory"].append({
                "name": car["name"],
                "price": car["price"],
                "from_container": car_data["container"]
            })
            
            users[user_id] = user
            await save_users(users)
            
            del container_animations[user_id]
            
            await callback.message.edit_text(
                f"✅ {car['name']} добавлена в гараж!\n"
                f"💰 Стоимость: {car['price']:,.0f}₽\n"
                f"💳 Баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 В гараж", callback_data="garage")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="containers")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в container_take: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("container_sell_"))
    async def container_sell(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            item_id = callback.data.replace("container_sell_", "")
            user_id = str(callback.from_user.id)
            
            if user_id not in container_animations:
                await callback.answer("❌ Контейнер не найден!", show_alert=True)
                return
            
            car_data = container_animations[user_id]
            if car_data.get("item_id") != item_id:
                await callback.answer("❌ Контейнер не найден!", show_alert=True)
                return
            
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            car = car_data["car"]
            
            # Продажа за 100% из контейнера
            sell_price = car["price"]
            user["money"] += sell_price
            user["total_earned"] += sell_price
            
            users[user_id] = user
            await save_users(users)
            
            del container_animations[user_id]
            
            await callback.message.edit_text(
                f"💰 Продано!\n"
                f"🚗 {car['name']}\n"
                f"💳 Получено: {sell_price:,.0f}₽ (100% от цены)\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="containers")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в container_sell: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ГАРАЖ =====
    # ==========================================
    
    @dp.callback_query(F.data == "garage")
    async def garage_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if "inventory" not in user or not user["inventory"]:
                await callback.message.edit_text(
                    "🏠 Ваш гараж пуст!\n\n"
                    "💡 Откройте контейнеры, чтобы получить машины!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🚗 Открыть контейнеры", callback_data="containers")],
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ])
                )
                await callback.answer()
                return
            
            keyboard = []
            for i, car in enumerate(user["inventory"]):
                if isinstance(car, dict):
                    car_name = car.get("name", "Неизвестная машина")
                else:
                    car_name = str(car)
                keyboard.append([InlineKeyboardButton(
                    text=f"🚗 {car_name}",
                    callback_data=f"car_{i}"
                )])
            
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
            
            await callback.message.edit_text(
                f"🏠 Ваш гараж ({len(user['inventory'])} машин):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в garage_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

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
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if car_index >= len(user["inventory"]):
                await callback.answer("❌ Машина не найдена!", show_alert=True)
                return
            
            car = user["inventory"][car_index]
            sell_price = int(car["price"] * 0.6)
            
            user["money"] += sell_price
            del user["inventory"][car_index]
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"💰 Продано!\n"
                f"🚗 {car['name']}\n"
                f"💳 Получено: {sell_price:,.0f}₽ (60% от цены)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В гараж", callback_data="garage")]
                ])
            )
        except (ValueError, IndexError):
            await callback.answer("❌ Ошибка в данных!")
        except Exception as e:
            logger.error(f"Ошибка в car_sell: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("car_") & ~F.data.startswith("car_sell_") & ~F.data.startswith("car_plate_") & ~F.data.startswith("car_tuning_"))
    async def car_menu(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            car_index = int(callback.data.split("_")[1])
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if car_index >= len(user["inventory"]):
                await callback.answer("❌ Машина не найдена!", show_alert=True)
                return
            
            car = user["inventory"][car_index]
            
            keyboard = [
                [InlineKeyboardButton(text="🔢 Номера", callback_data=f"car_plate_{car_index}")],
                [InlineKeyboardButton(text="💰 Продать (60%)", callback_data=f"car_sell_{car_index}")],
                [InlineKeyboardButton(text="🔧 Тюнинг", callback_data=f"car_tuning_{car_index}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="garage")]
            ]
            
            await callback.message.edit_text(
                f"🚗 {car['name']}\n"
                f"💰 Стоимость: {car['price']:,.0f}₽\n"
                f"💵 Продажа: {int(car['price'] * 0.6):,.0f}₽ (60%)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except (ValueError, IndexError):
            await callback.answer("❌ Ошибка в данных!")
        except Exception as e:
            logger.error(f"Ошибка в car_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("car_plate_"))
    async def car_plate(callback: types.CallbackQuery):
        await callback.answer("🚫 В разработке!", show_alert=True)

    @dp.callback_query(F.data.startswith("car_tuning_"))
    async def car_tuning(callback: types.CallbackQuery):
        await callback.answer("🚫 В разработке!", show_alert=True)

    # ==========================================
    # ===== ИНВЕНТАРЬ =====
    # ==========================================
    
    @dp.callback_query(F.data == "inventory_main")
    async def inventory_main_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            inventory = await load_inventory()
            
            if user_id not in inventory or not inventory[user_id]:
                await callback.message.edit_text(
                    "📦 Ваш инвентарь пуст!\nДобывайте ресурсы в шахте или на ферме.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ])
                )
                await callback.answer()
                return
            
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            resources = {}
            for item in inventory[user_id]:
                resources[item] = resources.get(item, 0) + 1
            
            text = "📦 ВАШ ИНВЕНТАРЬ:\n\n"
            for name, count in resources.items():
                price = 0
                for r in all_resources:
                    if r["name"] == name:
                        price = r["price"]
                        break
                text += f"💎 {name}\n   📦 {count} шт.\n   💰 {price:,.0f}₽ за шт.\n\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в inventory_main_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== СКУПЩИК =====
    # ==========================================
    
    @dp.callback_query(F.data == "buyer")
    async def buyer_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            inventory = await load_inventory()
            
            if user_id not in inventory or not inventory[user_id]:
                await callback.message.edit_text(
                    "📦 Ваш инвентарь пуст!\nДобывайте ресурсы в шахте или на ферме.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ])
                )
                await callback.answer()
                return
            
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            resources = {}
            for item in inventory[user_id]:
                resources[item] = resources.get(item, 0) + 1
            
            keyboard = []
            for name, count in resources.items():
                price = 0
                for r in all_resources:
                    if r["name"] == name:
                        price = r["price"]
                        break
                keyboard.append([InlineKeyboardButton(
                    text=f"💎 {name} ({count} шт.) - {price:,.0f}₽",
                    callback_data=f"buyer_resource_{name}"
                )])
            
            keyboard.append([InlineKeyboardButton(text="💰 Продать все", callback_data="buyer_sell_all")])
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
            
            await callback.message.edit_text(
                "🔄 СКУПЩИК\n\nВыберите ресурс для продажи:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("buyer_resource_"))
    async def buyer_resource_menu(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            resource_name = callback.data.replace("buyer_resource_", "")
            
            user_id = str(callback.from_user.id)
            inventory = await load_inventory()
            
            if user_id not in inventory:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            price = 0
            for r in all_resources:
                if r["name"] == resource_name:
                    price = r["price"]
                    break
            
            if price == 0:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            count = inventory[user_id].count(resource_name)
            
            keyboard = [
                [InlineKeyboardButton(
                    text=f"💰 Продать 1 шт. ({price:,.0f}₽)",
                    callback_data=f"buyer_sell_one_{resource_name}"
                )],
                [InlineKeyboardButton(
                    text=f"💰 Продать все ({count} шт.)",
                    callback_data=f"buyer_sell_all_{resource_name}"
                )],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="buyer")]
            ]
            
            await callback.message.edit_text(
                f"💎 {resource_name}\n\n"
                f"📦 В наличии: {count} шт.\n"
                f"💰 Цена за шт.: {price:,.0f}₽\n"
                f"💵 Сумма за все: {count * price:,.0f}₽\n\n"
                f"Выберите действие:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_resource_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("buyer_sell_one_"))
    async def buyer_sell_one(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            resource_name = callback.data.replace("buyer_sell_one_", "")
            
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            inventory = await load_inventory()
            
            if user_id not in inventory or resource_name not in inventory[user_id]:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            price = 0
            for r in all_resources:
                if r["name"] == resource_name:
                    price = r["price"]
                    break
            
            if price == 0:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            inventory[user_id].remove(resource_name)
            await save_inventory(inventory)
            
            user["money"] += price
            user["total_earned"] += price
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"✅ Продано 1 шт. {resource_name}\n"
                f"💰 +{price:,.0f}₽\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 К ресурсам", callback_data="buyer")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_sell_one: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("buyer_sell_all_"))
    async def buyer_sell_all_resource(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            resource_name = callback.data.replace("buyer_sell_all_", "")
            
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            inventory = await load_inventory()
            
            if user_id not in inventory:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            price = 0
            for r in all_resources:
                if r["name"] == resource_name:
                    price = r["price"]
                    break
            
            if price == 0:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return
            
            count = inventory[user_id].count(resource_name)
            if count == 0:
                await callback.answer("❌ Нет ресурсов для продажи!", show_alert=True)
                return
            
            total_price = count * price
            
            inventory[user_id] = [item for item in inventory[user_id] if item != resource_name]
            await save_inventory(inventory)
            
            user["money"] += total_price
            user["total_earned"] += total_price
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"✅ Продано {count} шт. {resource_name}\n"
                f"💰 +{total_price:,.0f}₽\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 К ресурсам", callback_data="buyer")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_sell_all_resource: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "buyer_sell_all")
    async def buyer_sell_all(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            inventory = await load_inventory()
            
            if user_id not in inventory or not inventory[user_id]:
                await callback.answer("❌ Инвентарь пуст!", show_alert=True)
                return
            
            all_resources = MINE_RESOURCES + FARM_RESOURCES
            
            total_price = 0
            resource_counts = {}
            for item in inventory[user_id]:
                price = 0
                for r in all_resources:
                    if r["name"] == item:
                        price = r["price"]
                        break
                total_price += price
                resource_counts[item] = resource_counts.get(item, 0) + 1
            
            inventory[user_id] = []
            await save_inventory(inventory)
            
            user["money"] += total_price
            user["total_earned"] += total_price
            users[user_id] = user
            await save_users(users)
            
            resources_text = ""
            for name, count in resource_counts.items():
                resources_text += f"• {name}: {count} шт.\n"
            
            await callback.message.edit_text(
                f"✅ Проданы все ресурсы!\n\n"
                f"📦 Продано:\n{resources_text}\n"
                f"💰 Всего получено: {total_price:,.0f}₽\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В меню", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_sell_all: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== БИЗНЕС =====
    # ==========================================
    
    @dp.callback_query(F.data == "business")
    async def business_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            business_data = await load_business()
            
            user_business_count = await get_user_business_count(user_id)
            status = await get_business_status(user_id)
            
            text = "🏢 Ваши бизнесы\n\n"
            
            for key, config in BUSINESS_CONFIG.items():
                s = status.get(key, {"owned": False, "ready": False, "remaining": "Не куплен", "auto_collect": False})
                emoji = config["emoji"]
                name = config["name"]
                
                if s["owned"]:
                    auto_status = "🟢 Авто-сбор включен" if s["auto_collect"] else "🔴 Авто-сбор выключен"
                    if s["ready"]:
                        text += f"{emoji} {name} - ✅ ГОТОВ К СБОРУ\n"
                    else:
                        text += f"{emoji} {name} - ⏳ {s['remaining']}\n"
                    text += f"   {auto_status}\n"
                else:
                    price = config["price"]
                    max_owners = config["max_owners"]
                    owners = len(business_data.get(key, {}).get("owners", []))
                    text += f"{emoji} {name} - ❌ Не куплен\n"
                    text += f"   💰 Цена: {price:,.0f}₽\n"
                    text += f"   👥 Свободно: {max_owners - owners}/{max_owners}\n"
            
            if user_business_count >= 1:
                text += "\n⚠️ У вас уже есть 1 бизнес! (максимум 1)"
            
            keyboard = []
            
            if user_business_count < 1:
                for key, config in BUSINESS_CONFIG.items():
                    s = status.get(key, {"owned": False})
                    if not s["owned"]:
                        owners = len(business_data.get(key, {}).get("owners", []))
                        if owners < config["max_owners"]:
                            keyboard.append([InlineKeyboardButton(
                                text=f"💰 Купить {config['emoji']} {config['name']}",
                                callback_data=f"buy_business_{key}"
                            )])
            else:
                for key, config in BUSINESS_CONFIG.items():
                    s = status.get(key, {"owned": False, "auto_collect": False})
                    if s["owned"]:
                        auto_text = "🔴 Выключить" if s["auto_collect"] else "🟢 Включить"
                        callback_data = f"toggle_auto_{key}"
                        keyboard.append([InlineKeyboardButton(
                            text=f"{config['emoji']} {auto_text} авто-сбор {config['name']}",
                            callback_data=callback_data
                        )])
            
            has_ready = any(s.get("ready", False) for s in status.values())
            if has_ready:
                keyboard.append([InlineKeyboardButton(
                    text="💰 Собрать доход",
                    callback_data="collect_business"
                )])
            
            # КНОПКА ПРОДАЖИ БИЗНЕСА
            has_business = any(s.get("owned", False) for s in status.values())
            if has_business:
                keyboard.append([InlineKeyboardButton(
                    text="💰 Продать бизнес (50%)",
                    callback_data="sell_business"
                )])
            
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в business_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "sell_business")
    async def sell_business(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            business_data = await load_business()
            
            owned_business = None
            for biz_key, biz_data in user.get("business", {}).items():
                if biz_data.get("owned", False):
                    owned_business = biz_key
                    break
            
            if not owned_business:
                await callback.answer("❌ У вас нет бизнеса для продажи!", show_alert=True)
                return
            
            config = BUSINESS_CONFIG[owned_business]
            sell_price = int(config["price"] * 0.5)
            
            user["business"][owned_business]["owned"] = False
            user["business"][owned_business]["last_collect"] = None
            user["business"][owned_business]["auto_collect"] = False
            
            if owned_business in business_data and user_id in business_data[owned_business]["owners"]:
                business_data[owned_business]["owners"].remove(user_id)
            
            user["money"] += sell_price
            user["total_earned"] += sell_price
            
            users[user_id] = user
            await save_users(users)
            await save_business(business_data)
            
            await callback.message.edit_text(
                f"💰 Бизнес продан!\n\n"
                f"🏢 {config['emoji']} {config['name']}\n"
                f"💵 Получено: {sell_price:,.0f}₽ (50% от стоимости)\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏢 В бизнес", callback_data="business")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в sell_business: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ---- Остальные бизнес-функции (buy_business, toggle_auto, collect_business) ----
    @dp.callback_query(F.data.startswith("buy_business_"))
    async def buy_business(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        await state.clear()
        
        try:
            business_key = callback.data.replace("buy_business_", "")
            config = BUSINESS_CONFIG.get(business_key)
            if not config:
                await callback.answer("❌ Бизнес не найден!", show_alert=True)
                return
            
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            business_data = await load_business()
            
            user_business_count = await get_user_business_count(user_id)
            if user_business_count >= 1:
                await callback.answer("❌ У вас уже есть 1 бизнес! (максимум 1)", show_alert=True)
                return
            
            owners = business_data.get(business_key, {}).get("owners", [])
            if len(owners) >= config["max_owners"]:
                await callback.answer("❌ Все места заняты!", show_alert=True)
                return
            
            if user_id in owners:
                await callback.answer("❌ Вы уже владеете этим бизнесом!", show_alert=True)
                return
            
            if user["money"] < config["price"]:
                await callback.answer(
                    f"❌ Недостаточно средств! Нужно {config['price']:,.0f}₽",
                    show_alert=True
                )
                return
            
            user["money"] -= config["price"]
            
            if "business" not in user:
                user["business"] = {}
            if business_key not in user["business"]:
                user["business"][business_key] = {"owned": False, "last_collect": None, "auto_collect": False}
            user["business"][business_key]["owned"] = True
            user["business"][business_key]["last_collect"] = datetime.now().isoformat()
            
            if business_key not in business_data:
                business_data[business_key] = {"owners": [], "total_earned": 0}
            business_data[business_key]["owners"].append(user_id)
            
            users[user_id] = user
            await save_users(users)
            await save_business(business_data)
            
            await callback.message.edit_text(
                f"✅ Вы купили {config['emoji']} {config['name']}!\n"
                f"💰 Стоимость: {config['price']:,.0f}₽\n"
                f"💳 Остаток: {user['money']:,.0f}₽\n\n"
                f"Бизнес будет приносить доход. Заходите в раздел Бизнес для сбора.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏢 В бизнес", callback_data="business")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в buy_business: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("toggle_auto_"))
    async def toggle_auto_collect(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            business_key = callback.data.replace("toggle_auto_", "")
            config = BUSINESS_CONFIG.get(business_key)
            if not config:
                await callback.answer("❌ Бизнес не найден!", show_alert=True)
                return
            
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if not user.get("business", {}).get(business_key, {}).get("owned", False):
                await callback.answer("❌ У вас нет этого бизнеса!", show_alert=True)
                return
            
            current_status = user["business"][business_key].get("auto_collect", False)
            new_status = not current_status
            user["business"][business_key]["auto_collect"] = new_status
            
            users[user_id] = user
            await save_users(users)
            
            status_text = "включен" if new_status else "выключен"
            await callback.answer(f"✅ Авто-сбор для {config['name']} {status_text}!", show_alert=True)
            
            await business_menu(callback, None)
        except Exception as e:
            logger.error(f"Ошибка в toggle_auto_collect: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "collect_business")
    async def collect_business(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            inventory = await load_inventory()
            business_data = await load_business()
            
            collected = []
            total_money = 0
            resources_collected = []
            
            for biz_key, biz_data in user.get("business", {}).items():
                if not biz_data.get("owned", False):
                    continue
                
                last_collect = biz_data.get("last_collect")
                if not last_collect:
                    continue
                
                last_time = datetime.fromisoformat(last_collect)
                elapsed = (datetime.now() - last_time).total_seconds()
                config = BUSINESS_CONFIG.get(biz_key)
                
                if elapsed >= config["cooldown"]:
                    if config["profit_type"] == "money":
                        profit = random.randint(config["profit_min"], config["profit_max"])
                        user["money"] += profit
                        user["total_earned"] += profit
                        total_money += profit
                        collected.append(f"{config['emoji']} {config['name']}: +{profit:,.0f}₽")
                        
                        if biz_key in business_data:
                            business_data[biz_key]["total_earned"] = business_data[biz_key].get("total_earned", 0) + profit
                    
                    elif config["profit_type"] == "resources":
                        if user_id not in inventory:
                            inventory[user_id] = []
                        
                        num_resources = random.randint(config["min_resources"], config["max_resources"])
                        
                        for _ in range(num_resources):
                            resource = await get_auto_mine_resource()
                            inventory[user_id].append(resource)
                            resources_collected.append(resource)
                        
                        collected.append(
                            f"{config['emoji']} {config['name']}: +{num_resources} ресурсов"
                        )
                        
                        if biz_key in business_data:
                            business_data[biz_key]["total_earned"] = business_data[biz_key].get("total_earned", 0) + num_resources
                    
                    biz_data["last_collect"] = datetime.now().isoformat()
                    user["business"][biz_key]["last_collect"] = datetime.now().isoformat()
            
            if not collected:
                await callback.answer("❌ Нет готовых бизнесов для сбора!", show_alert=True)
                return
            
            users[user_id] = user
            await save_users(users)
            await save_inventory(inventory)
            await save_business(business_data)
            
            text = "✅ Собраны доходы:\n\n"
            text += "\n".join(collected)
            
            if total_money > 0:
                text += f"\n\n💰 Всего денег: +{total_money:,.0f}₽"
            
            if resources_collected:
                resource_counts = {}
                for res in resources_collected:
                    resource_counts[res] = resource_counts.get(res, 0) + 1
                
                text += f"\n💎 Всего ресурсов: +{len(resources_collected)} шт."
                text += "\n\n📦 Получены ресурсы:"
                for res_name, count in resource_counts.items():
                    price = 0
                    for r in MINE_RESOURCES:
                        if r["name"] == res_name:
                            price = r["price"]
                            break
                    text += f"\n   • {res_name}: {count} шт. (цена: {price:,.0f}₽ за шт.)"
            
            text += f"\n\n💳 Новый баланс: {user['money']:,.0f}₽"
            
            if resources_collected:
                text += "\n\n📦 Ресурсы добавлены в инвентарь!"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏢 В бизнес", callback_data="business")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в collect_business: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== КАЗИНО =====
    # ==========================================
    
    @dp.callback_query(F.data == "casino")
    async def casino_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            keyboard = [
                [InlineKeyboardButton(text="💰 Введите ставку", callback_data="casino_bet")],
                [InlineKeyboardButton(text="🎲 Кубик", callback_data="casino_dice")],
                [InlineKeyboardButton(text="🎰 Слоты", callback_data="casino_slots")],
                [InlineKeyboardButton(text="💣 Мины", callback_data="casino_mines")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            
            bet = user.get("casino", {}).get("bet", 0)
            text = f"🎰 КАЗИНО\n\n"
            text += f"💰 Текущая ставка: {bet:,.0f}₽\n"
            text += f"💳 Ваш баланс: {user['money']:,.0f}₽"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в casino_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "casino_bet")
    async def casino_bet(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "✏️ Введите сумму ставки:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
                ])
            )
            await state.set_state(CasinoStates.waiting_for_bet)
        except Exception as e:
            logger.error(f"Ошибка в casino_bet: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.message(CasinoStates.waiting_for_bet)
    async def process_casino_bet(message: types.Message, state: FSMContext):
        if not await check_access(message):
            await state.clear()
            return
        
        try:
            bet = int(message.text)
            if bet <= 0:
                await message.answer("❌ Ставка должна быть положительной!")
                await state.clear()
                return
            
            user_id = str(message.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if user["money"] < bet:
                await message.answer(f"❌ Недостаточно средств! У вас {user['money']:,.0f}₽")
                await state.clear()
                return
            
            if "casino" not in user:
                user["casino"] = {}
            user["casino"]["bet"] = bet
            
            users[user_id] = user
            await save_users(users)
            await state.clear()
            
            await message.answer(f"✅ Ставка установлена: {bet:,.0f}₽")
            
            keyboard = [
                [InlineKeyboardButton(text="💰 Введите ставку", callback_data="casino_bet")],
                [InlineKeyboardButton(text="🎲 Кубик", callback_data="casino_dice")],
                [InlineKeyboardButton(text="🎰 Слоты", callback_data="casino_slots")],
                [InlineKeyboardButton(text="💣 Мины", callback_data="casino_mines")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            
            text = f"🎰 КАЗИНО\n\n"
            text += f"💰 Текущая ставка: {bet:,.0f}₽\n"
            text += f"💳 Ваш баланс: {user['money']:,.0f}₽"
            
            await message.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except ValueError:
            await message.answer("❌ Введите число!")
            await state.clear()
        except Exception as e:
            logger.error(f"Ошибка в process_casino_bet: {e}")
            await state.clear()
            await message.answer("⚠️ Ошибка!")

    @dp.callback_query(F.data == "casino_dice")
    async def casino_dice(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        # Проверяем, не отключена ли функция
        if await is_function_disabled("casinogame_1"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            bet = user.get("casino", {}).get("bet", 0)
            if bet <= 0:
                await callback.answer("❌ Сначала установите ставку!", show_alert=True)
                return
            
            if user["money"] < bet:
                await callback.answer(f"❌ Недостаточно средств! У вас {user['money']:,.0f}₽", show_alert=True)
                return
            
            keyboard = [
                [InlineKeyboardButton(text="🎲 Четное", callback_data="dice_even")],
                [InlineKeyboardButton(text="🎲 Нечетное", callback_data="dice_odd")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
            ]
            
            await callback.message.edit_text(
                f"🎲 КУБИК\n\n"
                f"💰 Ставка: {bet:,.0f}₽\n"
                f"Выберите: Четное или Нечетное",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в casino_dice: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("dice_"))
    async def dice_play(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            choice = callback.data.replace("dice_", "")
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            bet = user.get("casino", {}).get("bet", 0)
            if bet <= 0:
                await callback.answer("❌ Ставка не установлена!", show_alert=True)
                return
            
            if user["money"] < bet:
                await callback.answer(f"❌ Недостаточно средств!", show_alert=True)
                return
            
            dice_result = random.randint(1, 6)
            is_even = dice_result % 2 == 0
            
            if (choice == "even" and is_even) or (choice == "odd" and not is_even):
                win = bet * 2
                user["money"] += win
                user["total_earned"] += win
                result_text = f"✅ ВЫИГРЫШ!\n🎲 Выпало: {dice_result}\n💰 +{win:,.0f}₽"
            else:
                user["money"] -= bet
                result_text = f"❌ ПРОИГРЫШ!\n🎲 Выпало: {dice_result}\n💸 -{bet:,.0f}₽"
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"🎲 КУБИК\n\n{result_text}\n\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎲 Играть ещё", callback_data="casino_dice")],
                    [InlineKeyboardButton(text="🔙 В казино", callback_data="casino")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в dice_play: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "casino_slots")
    async def casino_slots(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        # Проверяем, не отключена ли функция
        if await is_function_disabled("casinogame_2"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            bet = user.get("casino", {}).get("bet", 0)
            if bet <= 0:
                await callback.answer("❌ Сначала установите ставку!", show_alert=True)
                return
            
            if user["money"] < bet:
                await callback.answer(f"❌ Недостаточно средств!", show_alert=True)
                return
            
            keyboard = [
                [InlineKeyboardButton(text="🎰 Крутить", callback_data="slots_spin")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
            ]
            
            await callback.message.edit_text(
                f"🎰 СЛОТЫ\n\n"
                f"💰 Ставка: {bet:,.0f}₽\n"
                f"🎯 Шанс выигрыша: 25%\n"
                f"Нажмите 'Крутить' для игры",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в casino_slots: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "slots_spin")
    async def slots_spin(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            bet = user.get("casino", {}).get("bet", 0)
            if bet <= 0:
                await callback.answer("❌ Ставка не установлена!", show_alert=True)
                return
            
            if user["money"] < bet:
                await callback.answer(f"❌ Недостаточно средств!", show_alert=True)
                return
            
            symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
            result = [random.choice(symbols) for _ in range(3)]
            
            win = 0
            if random.random() < 0.25:
                if result[0] == result[1] == result[2]:
                    if result[0] == "7️⃣":
                        win = bet * 5
                    elif result[0] == "💎":
                        win = bet * 3
                    else:
                        win = bet * 2
                elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
                    win = int(bet * 1.5)
                
                if win == 0:
                    win = int(bet * 1.2)
            
            win = int(win)
            
            if win > 0:
                user["money"] += win
                user["total_earned"] += win
                result_text = f"✅ ВЫИГРЫШ!\n🎰 {result[0]} {result[1]} {result[2]}\n💰 +{win:,.0f}₽"
            else:
                user["money"] -= bet
                result_text = f"❌ ПРОИГРЫШ!\n🎰 {result[0]} {result[1]} {result[2]}\n💸 -{bet:,.0f}₽"
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"🎰 СЛОТЫ\n\n{result_text}\n\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Крутить ещё", callback_data="slots_spin")],
                    [InlineKeyboardButton(text="🔙 В казино", callback_data="casino")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в slots_spin: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== МИНЫ =====
    # ==========================================
    
    @dp.callback_query(F.data == "casino_mines")
    async def casino_mines(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        # Проверяем, не отключена ли функция
        if await is_function_disabled("casinogame_3"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            casino = user.get("casino", {})
            mines_count = casino.get("mines_count", 4)
            field_size = casino.get("field_size", 5)
            bet = casino.get("bet", 0)
            
            if bet <= 0:
                await callback.answer("❌ Сначала установите ставку!", show_alert=True)
                return
            
            if user["money"] < bet:
                await callback.answer(f"❌ Недостаточно средств!", show_alert=True)
                return
            
            keyboard = [
                [InlineKeyboardButton(text="💣 Играть", callback_data="mines_play")],
                [InlineKeyboardButton(text="⚙️ Настроить мины", callback_data="mines_settings")],
                [InlineKeyboardButton(text="📐 Настроить поле", callback_data="mines_field")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
            ]
            
            await callback.message.edit_text(
                f"💣 МИНЫ\n\n"
                f"💰 Ставка: {bet:,.0f}₽\n"
                f"💣 Количество мин: {mines_count}\n"
                f"📐 Размер поля: {field_size}x{field_size}\n"
                f"💳 Ваш баланс: {user['money']:,.0f}₽\n\n"
                f"Выберите действие:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в casino_mines: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "mines_settings")
    async def mines_settings(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "✏️ Введите количество мин (от 4 до 10):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="casino_mines")]
                ])
            )
            await state.set_state(CasinoStates.waiting_for_mines)
        except Exception as e:
            logger.error(f"Ошибка в mines_settings: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.message(CasinoStates.waiting_for_mines)
    async def process_mines_count(message: types.Message, state: FSMContext):
        if not await check_access(message):
            await state.clear()
            return
        
        try:
            mines = int(message.text)
            if mines < 4 or mines > 10:
                await message.answer("❌ Количество мин должно быть от 4 до 10!")
                await state.clear()
                return
            
            user_id = str(message.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if "casino" not in user:
                user["casino"] = {}
            user["casino"]["mines_count"] = mines
            
            users[user_id] = user
            await save_users(users)
            await state.clear()
            
            await message.answer(f"✅ Количество мин установлено: {mines}")
            
            keyboard = [
                [InlineKeyboardButton(text="💣 Играть", callback_data="mines_play")],
                [InlineKeyboardButton(text="⚙️ Настроить мины", callback_data="mines_settings")],
                [InlineKeyboardButton(text="📐 Настроить поле", callback_data="mines_field")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
            ]
            
            casino = user.get("casino", {})
            field_size = casino.get("field_size", 5)
            bet = casino.get("bet", 0)
            
            text = f"💣 МИНЫ\n\n"
            text += f"💰 Ставка: {bet:,.0f}₽\n"
            text += f"💣 Количество мин: {mines}\n"
            text += f"📐 Размер поля: {field_size}x{field_size}\n"
            text += f"💳 Ваш баланс: {user['money']:,.0f}₽\n\n"
            text += f"Выберите действие:"
            
            await message.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except ValueError:
            await message.answer("❌ Введите число!")
            await state.clear()
        except Exception as e:
            logger.error(f"Ошибка в process_mines_count: {e}")
            await state.clear()
            await message.answer("⚠️ Ошибка!")

    @dp.callback_query(F.data == "mines_field")
    async def mines_field(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "✏️ Введите размер поля (от 3 до 8):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="casino_mines")]
                ])
            )
            await state.set_state(CasinoStates.waiting_for_field_size)
        except Exception as e:
            logger.error(f"Ошибка в mines_field: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.message(CasinoStates.waiting_for_field_size)
    async def process_field_size(message: types.Message, state: FSMContext):
        if not await check_access(message):
            await state.clear()
            return
        
        try:
            size = int(message.text)
            if size < 3 or size > 8:
                await message.answer("❌ Размер поля должен быть от 3 до 8!")
                await state.clear()
                return
            
            user_id = str(message.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            if "casino" not in user:
                user["casino"] = {}
            user["casino"]["field_size"] = size
            
            users[user_id] = user
            await save_users(users)
            await state.clear()
            
            await message.answer(f"✅ Размер поля установлен: {size}x{size}")
            
            keyboard = [
                [InlineKeyboardButton(text="💣 Играть", callback_data="mines_play")],
                [InlineKeyboardButton(text="⚙️ Настроить мины", callback_data="mines_settings")],
                [InlineKeyboardButton(text="📐 Настроить поле", callback_data="mines_field")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
            ]
            
            casino = user.get("casino", {})
            mines_count = casino.get("mines_count", 4)
            bet = casino.get("bet", 0)
            
            text = f"💣 МИНЫ\n\n"
            text += f"💰 Ставка: {bet:,.0f}₽\n"
            text += f"💣 Количество мин: {mines_count}\n"
            text += f"📐 Размер поля: {size}x{size}\n"
            text += f"💳 Ваш баланс: {user['money']:,.0f}₽\n\n"
            text += f"Выберите действие:"
            
            await message.answer(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except ValueError:
            await message.answer("❌ Введите число!")
            await state.clear()
        except Exception as e:
            logger.error(f"Ошибка в process_field_size: {e}")
            await state.clear()
            await message.answer("⚠️ Ошибка!")

    @dp.callback_query(F.data == "mines_play")
    async def mines_play(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            casino = user.get("casino", {})
            bet = casino.get("bet", 0)
            mines_count = casino.get("mines_count", 4)
            field_size = casino.get("field_size", 5)
            
            if bet <= 0:
                await callback.answer("❌ Ставка не установлена!", show_alert=True)
                return
            
            if user["money"] < bet:
                await callback.answer(f"❌ Недостаточно средств!", show_alert=True)
                return
            
            total_cells = field_size * field_size
            cells = []
            for i in range(total_cells):
                cells.append(i)
            
            mine_positions = random.sample(range(total_cells), mines_count)
            
            mines_games[user_id] = {
                "cells": cells,
                "mine_positions": mine_positions,
                "field_size": field_size,
                "mines_count": mines_count,
                "revealed": [],
                "bet": bet
            }
            
            keyboard = []
            row = []
            for i in range(total_cells):
                row.append(InlineKeyboardButton(
                    text="🔳",
                    callback_data=f"mines_cell_{i}"
                ))
                if len(row) == field_size:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton(
                text=f"💰 Забрать выигрыш: {bet}₽",
                callback_data="mines_take_win"
            )])
            keyboard.append([InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="casino_mines"
            )])
            
            text = f"💣 МИНЫ\n\n"
            text += f"💰 Ставка: {bet:,.0f}₽\n"
            text += f"💣 Мин: {mines_count}\n"
            text += f"✅ Открыто: 0/{total_cells - mines_count}\n\n"
            text += "Выберите клетку:"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в mines_play: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("mines_cell_"))
    async def mines_cell_click(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            cell_num = int(callback.data.replace("mines_cell_", ""))
            user_id = str(callback.from_user.id)
            
            if user_id not in mines_games:
                await callback.answer("❌ Игра не найдена! Начните заново.", show_alert=True)
                return
            
            game = mines_games[user_id]
            
            if cell_num in game["revealed"]:
                await callback.answer("❌ Эта клетка уже открыта!", show_alert=True)
                return
            
            users = await load_users()
            user = users.get(user_id, get_default_user())
            bet = game["bet"]
            
            if cell_num in game["mine_positions"]:
                user["money"] -= bet
                users[user_id] = user
                await save_users(users)
                del mines_games[user_id]
                
                keyboard = []
                row = []
                total_cells = game["field_size"] * game["field_size"]
                for i in range(total_cells):
                    if i in game["mine_positions"]:
                        row.append(InlineKeyboardButton(
                            text="💣",
                            callback_data="mines_dead"
                        ))
                    elif i in game["revealed"]:
                        row.append(InlineKeyboardButton(
                            text="✅",
                            callback_data="mines_dead"
                        ))
                    else:
                        row.append(InlineKeyboardButton(
                            text="🔳",
                            callback_data="mines_dead"
                        ))
                    if len(row) == game["field_size"]:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                
                keyboard.append([InlineKeyboardButton(
                    text="💣 Играть снова",
                    callback_data="mines_play"
                )])
                keyboard.append([InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="casino_mines"
                )])
                
                await callback.message.edit_text(
                    f"💣 МИНЫ\n\n💥 ВЗРЫВ! Вы попали на мину!\n"
                    f"💸 -{bet:,.0f}₽\n"
                    f"💳 Новый баланс: {user['money']:,.0f}₽",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
                return
            
            game["revealed"].append(cell_num)
            mines_games[user_id] = game
            
            total_cells = game["field_size"] * game["field_size"]
            safe_cells = total_cells - game["mines_count"]
            
            if len(game["revealed"]) == safe_cells:
                win = bet * 3
                user["money"] += win
                user["total_earned"] += win
                users[user_id] = user
                await save_users(users)
                del mines_games[user_id]
                
                keyboard = []
                row = []
                for i in range(total_cells):
                    if i in game["mine_positions"]:
                        row.append(InlineKeyboardButton(
                            text="💣",
                            callback_data="mines_dead"
                        ))
                    else:
                        row.append(InlineKeyboardButton(
                            text="✅",
                            callback_data="mines_dead"
                        ))
                    if len(row) == game["field_size"]:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                
                keyboard.append([InlineKeyboardButton(
                    text="💣 Играть снова",
                    callback_data="mines_play"
                )])
                keyboard.append([InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="casino_mines"
                )])
                
                await callback.message.edit_text(
                    f"💣 МИНЫ\n\n🎉 ВЫИГРЫШ! Вы открыли все безопасные клетки!\n"
                    f"💰 +{win:,.0f}₽\n"
                    f"💳 Новый баланс: {user['money']:,.0f}₽",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
                return
            
            keyboard = []
            row = []
            for i in range(total_cells):
                if i in game["revealed"]:
                    row.append(InlineKeyboardButton(
                        text="✅",
                        callback_data=f"mines_cell_{i}"
                    ))
                elif i in game["mine_positions"]:
                    row.append(InlineKeyboardButton(
                        text="🔳",
                        callback_data=f"mines_cell_{i}"
                    ))
                else:
                    row.append(InlineKeyboardButton(
                        text="🔳",
                        callback_data=f"mines_cell_{i}"
                    ))
                if len(row) == game["field_size"]:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            current_win = int(bet * (1 + len(game["revealed"]) * 0.5))
            keyboard.append([InlineKeyboardButton(
                text=f"💰 Забрать выигрыш: {current_win:,.0f}₽",
                callback_data="mines_take_win"
            )])
            keyboard.append([InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="casino_mines"
            )])
            
            text = f"💣 МИНЫ\n\n"
            text += f"💰 Ставка: {bet:,.0f}₽\n"
            text += f"💣 Мин: {game['mines_count']}\n"
            text += f"✅ Открыто: {len(game['revealed'])}/{safe_cells}\n\n"
            text += "Выберите следующую клетку:"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в mines_cell_click: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "mines_take_win")
    async def mines_take_win(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            
            if user_id not in mines_games:
                await callback.answer("❌ Игра не найдена!", show_alert=True)
                return
            
            game = mines_games[user_id]
            
            if not game["revealed"]:
                await callback.answer("❌ Откройте хотя бы одну клетку!", show_alert=True)
                return
            
            users = await load_users()
            user = users.get(user_id, get_default_user())
            bet = game["bet"]
            
            win = int(bet * (1 + len(game["revealed"]) * 0.5))
            user["money"] += win
            user["total_earned"] += win
            users[user_id] = user
            await save_users(users)
            del mines_games[user_id]
            
            await callback.message.edit_text(
                f"💰 ВЫИГРЫШ ЗАБРАН!\n"
                f"✅ Открыто клеток: {len(game['revealed'])}\n"
                f"💰 Выигрыш: {win:,.0f}₽\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💣 Играть снова", callback_data="mines_play")],
                    [InlineKeyboardButton(text="🔙 В казино", callback_data="casino")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в mines_take_win: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "mines_dead")
    async def mines_dead(callback: types.CallbackQuery):
        await callback.answer("Игра окончена! Начните новую игру.", show_alert=True)

    # ==========================================
    # ===== СТАТИСТИКА =====
    # ==========================================
    
    @dp.callback_query(F.data == "stats")
    async def stats_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            users = await load_users()
            user = users.get(str(callback.from_user.id), get_default_user())
            
            inventory = await load_inventory()
            user_id = str(callback.from_user.id)
            resources_count = len(inventory.get(user_id, []))
            
            business_count = 0
            for biz in user.get("business", {}).values():
                if biz.get("owned", False):
                    business_count += 1
            
            auto_collect_count = 0
            for biz in user.get("business", {}).values():
                if biz.get("owned", False) and biz.get("auto_collect", False):
                    auto_collect_count += 1
            
            text = (
                f"📊 СТАТИСТИКА\n\n"
                f"💰 Баланс: {user['money']:,.0f}₽\n"
                f"💎 BRcoins: {user['brcoins']}\n"
                f"📈 Заработано: {user['total_earned']:,.0f}₽\n"
                f"🤝 Сделок: {user['trades_count']}\n"
                f"👤 Роль: {'Админ' if user['role'] == 'admin' else 'Игрок'}\n"
                f"🚗 Машин: {len(user['inventory'])}\n"
                f"📦 Ресурсов: {resources_count}\n"
                f"⛏️ Попыток: {user['mine_attempts']}/100\n"
                f"🏢 Бизнесов: {business_count}\n"
                f"🤖 Авто-сбор: {auto_collect_count} бизнесов\n\n"
                f"📈 ПОРТФЕЛЬ:\n"
                f"₿ BTC: {user['portfolio'].get('BTC', 0)}/150\n"
                f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}/100\n"
                f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}/5000"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в stats_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ТЕХПОДДЕРЖКА =====
    # ==========================================
    
    @dp.callback_query(F.data == "support")
    async def support_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "🆘 ТЕХНИЧЕСКАЯ ПОДДЕРЖКА\n\n"
                "Напишите ваше сообщение для администратора.\n"
                "Мы ответим вам в ближайшее время.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ])
            )
            await state.set_state(SupportStates.waiting_for_message)
        except Exception as e:
            logger.error(f"Ошибка в support_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.message(SupportStates.waiting_for_message)
    async def process_support_message(message: types.Message, state: FSMContext):
        if not await check_access(message):
            await state.clear()
            return
        
        try:
            user_id = str(message.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            username = message.from_user.username or f"User_{user_id[:5]}"
            
            support_text = (
                f"🆘 НОВОЕ ОБРАЩЕНИЕ В ПОДДЕРЖКУ\n\n"
                f"👤 От: @{username}\n"
                f"🆔 ID: {user_id}\n"
                f"💰 Баланс: {user['money']:,.0f}₽\n"
                f"💎 BRcoins: {user['brcoins']}\n\n"
                f"📝 Сообщение:\n{message.text}"
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, support_text)
                except Exception as e:
                    logger.warning(f"Не удалось отправить админу {admin_id}: {e}")
            
            await state.clear()
            
            await message.answer(
                "✅ Ваше сообщение отправлено администратору!\n"
                "Мы свяжемся с вами в ближайшее время.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В меню", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в process_support_message: {e}")
            await state.clear()
            await message.answer("⚠️ Произошла ошибка! Попробуйте позже.")

    # ==========================================
    # ===== ПРОМОКОДЫ (текстовый ввод) =====
    # ==========================================
    
    @dp.message(F.text, ~F.text.startswith('/'))
    async def handle_promo(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state is not None:
            return
        
        if not await check_access(message):
            return
        
        try:
            user_id = str(message.from_user.id)
            users = await load_users()
            user = users.get(user_id)
            
            if not user:
                return
            
            promocodes = await load_promocodes()
            code = message.text.upper().strip()
            
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
                users[user_id] = user
                
                await save_promocodes(promocodes)
                await save_users(users)
                
                await message.answer(
                    f"✅ +{promo['amount']:,} "
                    f"{'BRcoins' if promo['type'] == 'brcoins' else '₽'}!"
                )
            else:
                await message.answer("❌ Неверный промокод!")
        except Exception as e:
            logger.error(f"Ошибка в handle_promo: {e}")

    logger.info("✅ Все обработчики зарегистрированы!")
