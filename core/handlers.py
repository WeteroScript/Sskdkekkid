import random
import string
import uuid
from datetime import datetime
from aiogram import Dispatcher, types  # ← ДОБАВИТЬ types!
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from database.file_manager import (
    load_users, save_users, load_settings, save_settings, 
    load_promocodes, save_promocodes, load_inventory, 
    save_inventory, load_business, save_business
)
from utils.helpers import check_access, get_default_user, is_admin, check_subscription
from services.currency import currency_rates
from services.tasks import promo_auto_loop, check_business_loop
from config import (
    ADMIN_IDS, bot, logger, BUSINESS_CONFIG, CONTAINERS, 
    MINE_RESOURCES, FARM_RESOURCES, PROMO_CHANNEL_ID
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

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
container_animations = {}
mines_games = {}
last_mine_time = {}
promo_running = False
promo_task = None
business_running = False
business_check_task = None

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
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🆘 Тех.поддержка", callback_data="support")]
    ]
    
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== РЕГИСТРАЦИЯ ВСЕХ ОБРАБОТЧИКОВ ==========
def register_handlers(dp: Dispatcher):
    
    # ===== АДМИН-КОМАНДЫ =====
    @dp.message(Command("ahelp"))
    async def admin_help(message: types.Message):  # ← types теперь определен
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        help_text = (
            "👑 **Админ-команды:**\n\n"
            "**Бизнесы:**\n"
            "`/resetbusiness @username (причина)` - сброс бизнесов у пользователя\n"
            "`/resetallbusiness` - сброс всех бизнесов у всех пользователей\n"
            "`/givebusiness @username кол-во id_бизнеса` - выдача бизнеса\n\n"
            "**ID бизнесов:**\n"
            "`auto_mine` - Авто-Шахта (2 места)\n"
            "`tech_center` - Технический центр (5 мест)\n"
            "`tire_center` - Шиномонтажный центр (5 мест)\n"
            "`styling_center` - Стайлинг центр (5 мест)\n"
            "`shop_24` - Магазин 24/7 (20 мест)\n\n"
            "**Выдача валют:**\n"
            "`/giverub @username кол-во (сообщение)` - выдача рублей\n"
            "`/givedonate @username кол-во (сообщение)` - выдача BRcoins\n\n"
            "**Управление ботом:**\n"
            "`/promostart on/off` - авто-промокоды\n"
            "`/promostatus` - статус промокодов\n"
            "`/coinrun on/off` - CoinRun\n"
            "`/technical on/off` - техобслуживание\n"
            "`/status` - статус бота\n"
            "`/getdb` - получить базу данных\n"
            "`/mailall текст` - рассылка\n"
            "`/createpromo (1/0) (использований) (кол-во)` - создать промокод\n"
            "`/update_rates_admin` - обновить курсы"
        )
        
        await message.answer(help_text, parse_mode="Markdown")

    # ===== СТАРТ =====
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
            
            text, keyboard = await get_main_menu(message.from_user.id)
            await message.answer(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

    # ===== НАЗАД =====
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

    # ===== ОБРАБОТЧИК ПРОМОКОДОВ =====
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

    # ===== ОСТАЛЬНЫЕ ОБРАБОТЧИКИ =====
    # Здесь будут все остальные функции (works, donate, forbes, etc.)
    # Они добавляются аналогично

    logger.info("✅ Все обработчики зарегистрированы!")
