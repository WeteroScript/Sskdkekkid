from datetime import datetime
from typing import Dict, Any

from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger, ADMIN_IDS, MINE_RESOURCES, ALL_RESOURCES, AUTO_MINE_RESOURCES
from database.file_manager import (
    load_users, save_users, load_inventory, save_inventory,
    load_promocodes, save_promocodes, load_settings,
    get_user_cars, remove_user_car
)
from utils.helpers import (
    check_access, get_default_user, check_subscription,
    is_function_disabled, is_admin, generate_referral_link,
    get_referral_reward, generate_captcha
)
from services.currency import currency_rates

# Импорты из casino
try:
    from handlers.casino import mines_games, mines_games_by_id, get_min_mines_for_size
except ImportError:
    mines_games = {}
    mines_games_by_id = {}
    def get_min_mines_for_size(size: int) -> int:
        min_mines = {3: 2, 4: 3, 5: 5, 6: 7, 7: 9, 8: 13}
        return min_mines.get(size, 2)

from handlers.auction import show_auction_lot

# States
from states import (
    SupportStates, AuctionStates, TradeStates, CasinoStates, DonateStates
)

# ==========================================
# ===== КОНСТАНТА КОНВЕРТЕРА BRcoins =====
# ==========================================

BRCOIN_TO_RUB_RATE = 5_000_000  # 1 BRcoin = 5,000,000 ₽


def register_user_handlers(dp):

    async def get_main_menu(user_id: str):
        """Главное меню"""
        users = await load_users()
        user = users.get(user_id, get_default_user())

        currency_rates.update_rates()

        text = (
            f"👋 **Главное меню**\n\n"
            f"💰 Баланс: {user['money']:,.0f}₽\n"
            f"🔒 Заморожено: {user.get('frozen_balance', 0):,.0f}₽\n"
            f"💎 BRcoins: {user['brcoins']}\n"
            f"₿ BTC: {user['portfolio'].get('BTC', 0)}\n"
            f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}\n"
            f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}"
        )

        keyboard = [
            [
                InlineKeyboardButton(text="👨 Профиль", callback_data="profile_menu"),
                InlineKeyboardButton(text="💼 Работы", callback_data="works"),
                InlineKeyboardButton(text="💎 Донат", callback_data="donate")
            ],
            [
                InlineKeyboardButton(text="🚀 Развлечения", callback_data="entertainment_menu"),
                InlineKeyboardButton(text="🧙‍♀️ Скупщик", callback_data="buyer"),
                InlineKeyboardButton(text="🏢 Бизнес", callback_data="business")
            ]
        ]

        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)

    # ==========================================
    # ===== START С КАПЧЕЙ =====
    # ==========================================

    @dp.message(Command("start"))
    async def start_command(message: types.Message, state: FSMContext):
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

            # Проверяем реферальную ссылку
            referrer_id = None
            if " " in message.text:
                parts = message.text.split()
                if len(parts) > 1 and parts[1].startswith("ref_"):
                    referrer_id = parts[1].replace("ref_", "")

            if user_id not in users:
                correct_emoji, emojis = generate_captcha()

                await state.update_data(
                    captcha_correct=correct_emoji,
                    captcha_referrer=referrer_id
                )

                keyboard = []
                row = []
                for i, e in enumerate(emojis):
                    row.append(InlineKeyboardButton(
                        text=e,
                        callback_data=f"captcha_{e}"
                    ))
                    if len(row) == 3:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)

                await message.answer(
                    f"🛡️ **Добро пожаловать в WeteroRussia!** 😉\n\n"
                    f"Чтобы пользоваться ботом, пройдите капчу.\n"
                    f"Выберите верный эмодзи: **{correct_emoji}**",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                    parse_mode="Markdown"
                )
                return

            if not await check_access(message):
                return

            # Проверяем незавершенную игру в казино
            if user_id in mines_games:
                game = mines_games[user_id]
                total_cells = game["field_size"] * game["field_size"]
                safe_cells = total_cells - game["mines_count"]

                if len(game["revealed"]) == safe_cells:
                    del mines_games[user_id]
                else:
                    await message.answer(
                        "⚠️ У вас есть незавершённая игра в казино!\n"
                        "Завершите игру прежде чем перейти в главное меню.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="💣 Продолжить игру", callback_data="mines_play")],
                            [InlineKeyboardButton(text="❌ Завершить игру", callback_data="mines_cancel")]
                        ])
                    )
                    return

            text, keyboard = await get_main_menu(user_id)
            await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

    # ==========================================
    # ===== КАПЧА =====
    # ==========================================

    @dp.callback_query(F.data.startswith("captcha_"))
    async def captcha_handler(callback: types.CallbackQuery, state: FSMContext):
        user_id = str(callback.from_user.id)

        try:
            selected_emoji = callback.data.replace("captcha_", "")

            data = await state.get_data()
            correct_emoji = data.get("captcha_correct")
            referrer_id = data.get("captcha_referrer")

            if selected_emoji == correct_emoji:
                users = await load_users()

                new_user = get_default_user()
                new_user["captcha_passed"] = True

                if referrer_id and referrer_id in users:
                    new_user["referrer"] = referrer_id
                    users[referrer_id]["referrals"].append(user_id)
                    users[referrer_id]["referral_count"] += 1

                    referrer, reward_text = get_referral_reward(referrer_id, users)
                    users[referrer_id] = referrer

                    await save_users(users)

                    try:
                        await bot.send_message(
                            int(referrer_id),
                            f"🎉 **Новый реферал!**\n\n"
                            f"👤 @{callback.from_user.username or 'Игрок'} присоединился по вашей ссылке!\n"
                            f"🎁 Награда: {reward_text}",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось уведомить реферера: {e}")

                users[user_id] = new_user
                await save_users(users)
                await state.clear()

                await callback.message.edit_text(
                    "✅ **Капча пройдена!** Добро пожаловать в WeteroRussia! 🎉\n\n"
                    "Теперь у вас есть доступ ко всем функциям бота.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🚀 В главное меню", callback_data="back_main")]
                    ]),
                    parse_mode="Markdown"
                )
            else:
                await callback.answer("❌ Неверный эмодзи! Попробуйте ещё раз.", show_alert=True)

                correct_emoji, emojis = generate_captcha()
                await state.update_data(captcha_correct=correct_emoji)

                keyboard = []
                row = []
                for i, e in enumerate(emojis):
                    row.append(InlineKeyboardButton(
                        text=e,
                        callback_data=f"captcha_{e}"
                    ))
                    if len(row) == 3:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)

                await callback.message.edit_text(
                    f"🛡️ **Попробуйте ещё раз!**\n\n"
                    f"Выберите верный эмодзи: **{correct_emoji}**",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                    parse_mode="Markdown"
                )

            await callback.answer()

        except Exception as e:
            logger.error(f"Ошибка в captcha_handler: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

    # ==========================================
    # ===== НАЗАД =====
    # ==========================================

    @dp.callback_query(F.data == "back_main")
    async def back_main(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        try:
            text, keyboard = await get_main_menu(str(callback.from_user.id))
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка в back_main: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== ПРОФИЛЬ =====
    # ==========================================

    @dp.callback_query(F.data == "profile_menu")
    async def profile_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        try:
            keyboard = [
                [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
                [InlineKeyboardButton(text="🏠 Гараж", callback_data="garage")],
                [InlineKeyboardButton(text="📦 Инвентарь", callback_data="inventory_main")],
                [InlineKeyboardButton(text="🏆 Форбс", callback_data="forbes")],
                [InlineKeyboardButton(text="👥 Реф.Система", callback_data="referral_system")],
                [InlineKeyboardButton(text="🆘 Тех.поддержка", callback_data="support")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]

            await callback.message.edit_text(
                "👨 **Профиль**\n\nВыберите раздел:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в profile_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== РЕФЕРАЛЬНАЯ СИСТЕМА =====
    # ==========================================

    @dp.callback_query(F.data == "referral_system")
    async def referral_system(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())

            referrals = user.get("referrals", [])
            referral_count = user.get("referral_count", 0)

            referral_names = []
            for ref_id in referrals[:10]:
                try:
                    ref_user = await bot.get_chat(int(ref_id))
                    name = f"@{ref_user.username}" if ref_user.username else f"ID: {ref_id[:5]}"
                    referral_names.append(name)
                except:
                    referral_names.append(f"ID: {ref_id[:5]}")

            referral_list = "\n".join([f"• {name}" for name in referral_names]) if referral_names else "Нет приглашённых"

            link = await generate_referral_link(user_id)

            text = (
                f"👥 **Реферальная система**\n\n"
                f"📊 Приглашено: {referral_count} чел.\n"
                f"💰 Награда за 1 реферала: 150,000,000₽ + 🚗 (шанс 20%)\n\n"
                f"📋 **Ваши рефералы:**\n{referral_list}\n\n"
                f"🔗 **Ваша ссылка:**\n`{link}`\n\n"
                f"Отправьте эту ссылку друзьям и получайте награды!"
            )

            keyboard = [
                [InlineKeyboardButton(text="📤 Поделиться ссылкой", callback_data="share_referral")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
            ]

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в referral_system: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data == "share_referral")
    async def share_referral(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            user_id = str(callback.from_user.id)
            link = await generate_referral_link(user_id)

            await callback.message.answer(
                f"🔗 **Ваша реферальная ссылка:**\n\n"
                f"`{link}`\n\n"
                f"📤 Отправьте её друзьям! За каждого приглашённого вы получите 150,000,000₽ и шанс на машину!",
                parse_mode="Markdown"
            )
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка в share_referral: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== СТАТИСТИКА =====
    # ==========================================

    @dp.callback_query(F.data == "stats")
    async def stats_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        if await is_function_disabled("menubutton_9"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return

        try:
            users = await load_users()
            user = users.get(str(callback.from_user.id), get_default_user())

            inventory = await load_inventory()
            user_id = str(callback.from_user.id)
            resources_count = len(inventory.get(user_id, []))

            cars = await get_user_cars(user_id)

            business_count = sum(1 for biz in user.get("business", {}).values() if biz.get("owned", False))
            auto_collect_count = sum(1 for biz in user.get("business", {}).values()
                                     if biz.get("owned", False) and biz.get("auto_collect", False))

            text = (
                f"📊 **СТАТИСТИКА**\n\n"
                f"💰 Баланс: {user['money']:,.0f}₽\n"
                f"🔒 Заморожено: {user.get('frozen_balance', 0):,.0f}₽\n"
                f"💎 BRcoins: {user['brcoins']}\n"
                f"📈 Заработано: {user['total_earned']:,.0f}₽\n"
                f"🤝 Сделок: {user['trades_count']}\n"
                f"👤 Роль: {'Админ' if user['role'] == 'admin' else 'Игрок'}\n"
                f"🚗 Машин: {len(cars)}\n"
                f"📦 Ресурсов: {resources_count}\n"
                f"⛏️ Попыток: {user['mine_attempts']}/100\n"
                f"🏢 Бизнесов: {business_count}\n"
                f"🤖 Авто-сбор: {auto_collect_count} бизнесов\n"
                f"👥 Рефералов: {user.get('referral_count', 0)}\n\n"
                f"📈 **Портфель:**\n"
                f"₿ BTC: {user['portfolio'].get('BTC', 0)}/150\n"
                f"💧 WETcoin: {user['portfolio'].get('WETcoin', 0)}/100\n"
                f"🪙 NotCoin: {user['portfolio'].get('NotCoin', 0)}/5000"
            )

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в stats_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== ПОДДЕРЖКА =====
    # ==========================================

    @dp.callback_query(F.data == "support")
    async def support_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        if await is_function_disabled("menubutton_10"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return

        try:
            await callback.message.edit_text(
                "🆘 **ТЕХНИЧЕСКАЯ ПОДДЕРЖКА**\n\n"
                "Напишите ваше сообщение для администратора.\n"
                "Мы ответим вам в ближайшее время.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                ]),
                parse_mode="Markdown"
            )
            await state.set_state(SupportStates.waiting_for_support_message)
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка в support_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== ГАРАЖ =====
    # ==========================================

    @dp.callback_query(F.data == "garage")
    async def garage_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        if await is_function_disabled("menubutton_4"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return

        try:
            user_id = str(callback.from_user.id)
            cars = await get_user_cars(user_id)

            if not cars:
                await callback.message.edit_text(
                    "🏠 **Ваш гараж пуст!**\n\n"
                    "💡 Получайте машины через админов, аукцион или реферальную систему!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                    ]),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return

            keyboard = []
            for i, car in enumerate(cars):
                car_name = car.get("name", "Неизвестная машина")
                keyboard.append([InlineKeyboardButton(
                    text=f"🚗 {car_name}",
                    callback_data=f"car_{i}"
                )])

            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")])

            await callback.message.edit_text(
                f"🏠 **Ваш гараж** ({len(cars)} машин):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в garage_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data.startswith("car_") & ~F.data.startswith("car_sell_"))
    async def car_menu(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            car_index = int(callback.data.split("_")[1])
            user_id = str(callback.from_user.id)
            cars = await get_user_cars(user_id)

            if car_index >= len(cars):
                await callback.answer("❌ Машина не найдена!", show_alert=True)
                return

            car = cars[car_index]

            keyboard = [
                [InlineKeyboardButton(text="💰 Продать (60%)", callback_data=f"car_sell_{car_index}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="garage")]
            ]

            await callback.message.edit_text(
                f"🚗 **{car.get('name', 'Неизвестная')}**\n\n"
                f"💰 Стоимость: {car.get('price', 0):,.0f}₽\n"
                f"💵 Продажа: {int(car.get('price', 0) * 0.6):,.0f}₽ (60%)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except (ValueError, IndexError):
            await callback.answer("❌ Ошибка в данных!")
        except Exception as e:
            logger.error(f"Ошибка в car_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data.startswith("car_sell_"))
    async def car_sell(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            car_index = int(callback.data.split("_")[2])
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            cars = await get_user_cars(user_id)

            if car_index >= len(cars):
                await callback.answer("❌ Машина не найдена!", show_alert=True)
                return

            car = cars[car_index]
            sell_price = int(car.get("price", 0) * 0.6)

            user["money"] += sell_price
            users[user_id] = user
            await save_users(users)

            await remove_user_car(user_id, car_index)

            await callback.message.edit_text(
                f"💰 **Продано!**\n\n"
                f"🚗 {car.get('name', 'Неизвестная')}\n"
                f"💳 Получено: {sell_price:,.0f}₽ (60% от цены)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В гараж", callback_data="garage")]
                ]),
                parse_mode="Markdown"
            )
        except (ValueError, IndexError):
            await callback.answer("❌ Ошибка в данных!")
        except Exception as e:
            logger.error(f"Ошибка в car_sell: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== ИНВЕНТАРЬ =====
    # ==========================================

    @dp.callback_query(F.data == "inventory_main")
    async def inventory_main_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        if await is_function_disabled("menubutton_5"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return

        try:
            user_id = str(callback.from_user.id)
            inventory = await load_inventory()

            if user_id not in inventory or not inventory[user_id]:
                await callback.message.edit_text(
                    "📦 **Ваш инвентарь пуст!**\n\n"
                    "Добывайте ресурсы в шахте или на рыбалке.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                    ]),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return

            resources = {}
            for item in inventory[user_id]:
                resources[item] = resources.get(item, 0) + 1

            text = "📦 **ВАШ ИНВЕНТАРЬ:**\n\n"
            for name, count in resources.items():
                price = 0
                for r in ALL_RESOURCES:
                    if r["name"] == name:
                        price = r["price"]
                        break
                text += f"💎 {name}\n   📦 {count} шт.\n   💰 {price:,.0f}₽ за шт.\n\n"

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в inventory_main_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== ФОРБС =====
    # ==========================================

    @dp.callback_query(F.data == "forbes")
    async def forbes_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        if await is_function_disabled("menubutton_3"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return

        try:
            keyboard = [
                [InlineKeyboardButton(text="🏆 По деньгам", callback_data="forbes_rich")],
                [InlineKeyboardButton(text="💎 По BRcoins", callback_data="forbes_br")],
                [InlineKeyboardButton(text="👥 Топ рефералов", callback_data="forbes_referrals")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="profile_menu")]
            ]

            await callback.message.edit_text(
                "🏆 **Форбс**\n\nВыберите категорию:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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

            text = "🏆 **Топ-10 по деньгам:**\n\n"
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
                ]),
                parse_mode="Markdown"
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

            text = "💎 **Топ-10 по BRcoins:**\n\n"
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
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_br: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data == "forbes_referrals")
    async def forbes_referrals(callback: types.CallbackQuery):
        if not await check_access(callback):
            return

        try:
            users = await load_users()
            sorted_users = sorted(
                users.items(),
                key=lambda x: x[1].get("referral_count", 0),
                reverse=True
            )[:10]

            if not sorted_users:
                await callback.answer("Нет данных")
                return

            text = "👥 **Топ-10 рефералов:**\n\n"
            for i, (user_id, data) in enumerate(sorted_users, 1):
                try:
                    user = await bot.get_chat(int(user_id))
                    username = user.username or f"User_{user_id[:5]}"
                except:
                    username = f"User_{user_id[:5]}"
                text += f"{i}. @{username} — {data.get('referral_count', 0)} чел.\n"

            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="forbes")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в forbes_referrals: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== ДОНАТ С КОНВЕРТЕРОМ BRcoins =====
    # ==========================================

    @dp.callback_query(F.data == "donate")
    async def donate_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        if await is_function_disabled("menubutton_2"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return

        try:
            keyboard = [
                [InlineKeyboardButton(text="💳 Купить BRcoins", callback_data="donate_buy")],
                [InlineKeyboardButton(text="💱 Конвертировать BRcoins → ₽", callback_data="convert_brcoins")],
                [InlineKeyboardButton(text="🎫 Промокод", callback_data="promo")],
                [InlineKeyboardButton(text="💰 Баланс доната", callback_data="donate_balance")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            await callback.message.edit_text(
                "💎 **Донат**\n\n"
                "Курс покупки: 1₽ = 10 BRcoins\n"
                f"Курс конвертации: 1 BRcoin = {BRCOIN_TO_RUB_RATE:,}₽\n\n"
                "Обратитесь к @weterochina для покупки BRcoins.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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
                "💳 **Обратитесь к @weterochina**\n\n"
                "Курс: 1₽ = 10 BRcoins",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ]),
                parse_mode="Markdown"
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
                "🎫 **Введите промокод в чат**",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ]),
                parse_mode="Markdown"
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
                f"💰 **Баланс доната**\n\n"
                f"Потрачено: {user.get('donate_spent', 0)}₽\n"
                f"Получено: {user.get('donate_received', 0)} BRcoins\n"
                f"Баланс: {user['brcoins']} BRcoins",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="donate")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в donate_balance: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== КОНВЕРТЕР BRcoins → РУБЛИ =====
    # ==========================================

    @dp.callback_query(F.data == "convert_brcoins")
    async def convert_brcoins_menu(callback: types.CallbackQuery, state: FSMContext):
        """Меню конвертации BRcoins в рубли"""
        try:
            # Проверяем доступ
            if not await check_access(callback):
                return

            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())

            # Проверяем наличие BRcoins
            user_brcoins = user.get("brcoins", 0)
            if user_brcoins <= 0:
                await callback.answer("❌ У вас нет BRcoins для конвертации!", show_alert=True)
                return

            # Очищаем старое состояние
            await state.clear()

            # Отправляем сообщение с информацией
            sent_message = await callback.message.edit_text(
                f"💱 **КОНВЕРТЕР BRcoins → РУБЛИ**\n\n"
                f"💰 Курс: 1 BRcoin = {BRCOIN_TO_RUB_RATE:,}₽\n"
                f"💎 Ваш баланс BRcoins: {user_brcoins}\n"
                f"💳 Ваш баланс: {user['money']:,.0f}₽\n"
                f"📈 Максимум можно конвертировать: {user_brcoins * BRCOIN_TO_RUB_RATE:,.0f}₽\n\n"
                f"✏️ Напишите количество BRcoins для конвертации в чат.\n"
                f"⚠️ Минимум: 1 BRcoin\n"
                f"⚠️ Максимум: {user_brcoins} BRcoins",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="donate")]
                ]),
                parse_mode="Markdown"
            )

            # Запоминаем сообщение-меню, чтобы корректно "закрыть" его после конвертации
            await state.update_data(
                convert_menu_chat_id=callback.message.chat.id,
                convert_menu_message_id=callback.message.message_id
            )

            # Устанавливаем состояние
            await state.set_state(DonateStates.waiting_for_brcoin_convert)
            logger.info(f"✅ Меню конвертации открыто для пользователя {user_id}")
            await callback.answer()
            
        except Exception as e:
            logger.error(f"❌ Ошибка в convert_brcoins_menu: {e}", exc_info=True)
            try:
                await callback.answer("⚠️ Ошибка при открытии меню!", show_alert=True)
            except:
                pass

    # ==========================================
    # ===== ОБРАБОТЧИК КОНВЕРТАЦИИ BRcoins =====
    # ==========================================

    @dp.message(DonateStates.waiting_for_brcoin_convert)
    async def handle_brcoin_convert(message: types.Message, state: FSMContext):
        """
        Обработчик конвертации BRcoins в рубли.
        Преобразует введённое количество BRcoins в денежный эквивалент.
        """
        try:
            if not await check_access(message):
                await state.clear()
                return

            user_id = str(message.from_user.id)
            
            # Парсим введённое число
            raw = message.text.strip().replace(" ", "").replace(",", "")
            
            # Проверяем, что это число
            if not raw.isdigit():
                await message.answer(
                    "❌ Введите корректное число!\n"
                    "Например: 1, 5, 10\n\n"
                    "Пробелы и запятые допустимы.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Отмена", callback_data="donate")]
                    ])
                )
                return
            
            amount = int(raw)

            # Проверяем, что число положительное
            if amount <= 0:
                await message.answer(
                    "❌ Введите положительное число!\n"
                    "Например: 1, 5, 10\n\n"
                    "Пробелы и запятые допустимы.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Отмена", callback_data="donate")]
                    ])
                )
                return

            # Загружаем данные пользователя
            users = await load_users()
            user = users.get(user_id, get_default_user())
            user_brcoins = user.get("brcoins", 0)

            # Достаём данные о сообщении-меню (чтобы закрыть его после конвертации)
            state_data = await state.get_data()
            menu_chat_id = state_data.get("convert_menu_chat_id")
            menu_message_id = state_data.get("convert_menu_message_id")

            # Проверяем, достаточно ли BRcoins
            if amount > user_brcoins:
                await message.answer(
                    f"❌ Недостаточно BRcoins!\n\n"
                    f"💎 У вас: {user_brcoins} BRcoins\n"
                    f"💱 Вы хотите конвертировать: {amount} BRcoins\n\n"
                    f"Введите меньшее количество.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Отмена", callback_data="donate")],
                        [InlineKeyboardButton(text="💱 Попробовать снова", callback_data="convert_brcoins")]
                    ])
                )
                return

            # Выполняем конвертацию
            rub_amount = amount * BRCOIN_TO_RUB_RATE

            # Обновляем баланс
            user["brcoins"] = user.get("brcoins", 0) - amount
            user["money"] = user.get("money", 0) + rub_amount
            user["total_earned"] = user.get("total_earned", 0) + rub_amount
            user["donate_received"] = user.get("donate_received", 0) + amount

            # Сохраняем изменения
            users[user_id] = user
            await save_users(users)

            # Очищаем состояние
            await state.clear()

            # Закрываем (удаляем) исходное сообщение-меню конвертера, чтобы оно не "висело" открытым
            if menu_chat_id and menu_message_id:
                try:
                    await bot.delete_message(chat_id=menu_chat_id, message_id=menu_message_id)
                except Exception as close_err:
                    logger.warning(f"Не удалось закрыть меню конвертера: {close_err}")

            logger.info(
                f"✅ Конвертация BRcoins выполнена: "
                f"пользователь {user_id} конвертировал {amount} BRcoins "
                f"({amount} × {BRCOIN_TO_RUB_RATE:,} = {rub_amount:,.0f}₽)"
            )

            # Отправляем сообщение об успехе
            await message.answer(
                f"✅ **Конвертация выполнена успешно!**\n\n"
                f"💎 -{amount} BRcoins\n"
                f"💰 +{rub_amount:,.0f}₽\n\n"
                f"📊 **Ваш новый баланс:**\n"
                f"💳 Деньги: {user['money']:,.0f}₽\n"
                f"💎 BRcoins: {user['brcoins']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💱 Конвертировать ещё", callback_data="convert_brcoins")],
                    [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_main")]
                ]),
                parse_mode="Markdown"
            )

        except ValueError as e:
            logger.error(f"❌ Ошибка парсинга числа: {e}")
            await message.answer(
                "❌ Введите корректное число!\n"
                "Примеры: 1, 10, 100"
            )
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка конвертации: {e}", exc_info=True)
            try:
                state_data = await state.get_data()
                menu_chat_id = state_data.get("convert_menu_chat_id")
                menu_message_id = state_data.get("convert_menu_message_id")
                if menu_chat_id and menu_message_id:
                    await bot.delete_message(chat_id=menu_chat_id, message_id=menu_message_id)
            except Exception:
                pass
            await state.clear()
            await message.answer(
                "⚠️ Произошла ошибка при конвертации!\n"
                "Пожалуйста, попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_main")]
                ])
            )

    # ==========================================
    # ===== СКУПЩИК =====
    # ==========================================

    @dp.callback_query(F.data == "buyer")
    async def buyer_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        if await is_function_disabled("menubutton_6"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return

        try:
            user_id = str(callback.from_user.id)
            inventory = await load_inventory()

            if user_id not in inventory or not inventory[user_id]:
                await callback.message.edit_text(
                    "📦 **Ваш инвентарь пуст!**\n\n"
                    "Добывайте ресурсы в шахте или на рыбалке.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ]),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return

            from config import ALL_RESOURCES, AUTO_MINE_RESOURCES
            auto_mine_names = [r["name"] for r in AUTO_MINE_RESOURCES]

            resources = {}
            for item in inventory[user_id]:
                resources[item] = resources.get(item, 0) + 1

            keyboard = []
            for name, count in resources.items():
                price = 0
                for r in ALL_RESOURCES:
                    if r["name"] == name:
                        if name in auto_mine_names:
                            price = int(r["price"] * 0.6)
                        else:
                            price = r["price"]
                        break
                keyboard.append([InlineKeyboardButton(
                    text=f"💎 {name} ({count} шт.) - {price:,.0f}₽",
                    callback_data=f"buyer_resource_{name}"
                )])

            keyboard.append([InlineKeyboardButton(text="💰 Продать все", callback_data="buyer_sell_all")])
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])

            await callback.message.edit_text(
                "🧙‍♀️ **СКУПЩИК**\n\n"
                "⚠️ Ресурсы из авто-шахты продаются со скидкой 40%!\n"
                "✅ Ресурсы из обычной шахты и рыбалки — по полной цене!\n\n"
                "Выберите ресурс для продажи:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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

            from config import ALL_RESOURCES, AUTO_MINE_RESOURCES
            auto_mine_names = [r["name"] for r in AUTO_MINE_RESOURCES]

            price = 0
            is_auto_mine = False
            for r in ALL_RESOURCES:
                if r["name"] == resource_name:
                    if resource_name in auto_mine_names:
                        price = int(r["price"] * 0.6)
                        is_auto_mine = True
                    else:
                        price = r["price"]
                    break

            if price == 0:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return

            count = inventory[user_id].count(resource_name)

            price_text = f"{price:,.0f}₽ (скидка 40% для авто-шахты)" if is_auto_mine else f"{price:,.0f}₽ (полная цена)"

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
                f"💎 **{resource_name}**\n\n"
                f"📦 В наличии: {count} шт.\n"
                f"💰 Цена за шт.: {price_text}\n"
                f"💵 Сумма за все: {count * price:,.0f}₽\n\n"
                f"Выберите действие:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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

            from config import ALL_RESOURCES, AUTO_MINE_RESOURCES
            auto_mine_names = [r["name"] for r in AUTO_MINE_RESOURCES]

            price = 0
            is_auto_mine = False
            for r in ALL_RESOURCES:
                if r["name"] == resource_name:
                    if resource_name in auto_mine_names:
                        price = int(r["price"] * 0.6)
                        is_auto_mine = True
                    else:
                        price = r["price"]
                    break

            if price == 0:
                await callback.answer("❌ Ресурс не найден!", show_alert=True)
                return

            inventory[user_id].remove(resource_name)
            await save_inventory(inventory)

            user["money"] += price
            user["total_earned"] = user.get("total_earned", 0) + price
            users[user_id] = user
            await save_users(users)

            price_text = f"{price:,.0f}₽ (скидка 40% для авто-шахты)" if is_auto_mine else f"{price:,.0f}₽ (полная цена)"

            await callback.message.edit_text(
                f"✅ **Продано 1 шт. {resource_name}**\n\n"
                f"💰 +{price:,.0f}₽ ({price_text})\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 К ресурсам", callback_data="buyer")]
                ]),
                parse_mode="Markdown"
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

            from config import ALL_RESOURCES, AUTO_MINE_RESOURCES
            auto_mine_names = [r["name"] for r in AUTO_MINE_RESOURCES]

            price = 0
            is_auto_mine = False
            for r in ALL_RESOURCES:
                if r["name"] == resource_name:
                    if resource_name in auto_mine_names:
                        price = int(r["price"] * 0.6)
                        is_auto_mine = True
                    else:
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
            user["total_earned"] = user.get("total_earned", 0) + total_price
            users[user_id] = user
            await save_users(users)

            price_text = f"{price:,.0f}₽/шт (скидка 40% для авто-шахты)" if is_auto_mine else f"{price:,.0f}₽/шт (полная цена)"

            await callback.message.edit_text(
                f"✅ **Продано {count} шт. {resource_name}**\n\n"
                f"💰 +{total_price:,.0f}₽ ({price_text})\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 К ресурсам", callback_data="buyer")]
                ]),
                parse_mode="Markdown"
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

            from config import ALL_RESOURCES, AUTO_MINE_RESOURCES
            auto_mine_names = [r["name"] for r in AUTO_MINE_RESOURCES]

            total_price = 0
            resource_counts = {}
            for item in inventory[user_id]:
                price = 0
                for r in ALL_RESOURCES:
                    if r["name"] == item:
                        if item in auto_mine_names:
                            price = int(r["price"] * 0.6)
                        else:
                            price = r["price"]
                        break
                total_price += price
                resource_counts[item] = resource_counts.get(item, 0) + 1

            inventory[user_id] = []
            await save_inventory(inventory)

            user["money"] += total_price
            user["total_earned"] = user.get("total_earned", 0) + total_price
            users[user_id] = user
            await save_users(users)

            resources_text = ""
            for name, count in resource_counts.items():
                is_auto = name in auto_mine_names
                price_text = "скидка 40% для авто-шахты" if is_auto else "полная цена"
                resources_text += f"• {name}: {count} шт. ({price_text})\n"

            await callback.message.edit_text(
                f"✅ **Проданы все ресурсы!**\n\n"
                f"📦 Продано:\n{resources_text}\n"
                f"💰 Всего получено: {total_price:,.0f}₽\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В меню", callback_data="back_main")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в buyer_sell_all: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    # ==========================================
    # ===== РАЗВЛЕЧЕНИЯ =====
    # ==========================================

    @dp.callback_query(F.data == "entertainment_menu")
    async def entertainment_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return

        try:
            keyboard = [
                [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
                [InlineKeyboardButton(text="🚗 Аукцион", callback_data="auction")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]

            await callback.message.edit_text(
                "🚀 **Развлечения**\n\nВыберите игру:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в entertainment_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)

        await callback.answer()

    @dp.callback_query(F.data == "mines_play")
    async def continue_mines_game(callback: types.CallbackQuery):
        """Продолжает игру в мины после /start"""
        if not await check_access(callback):
            return

        user_id = str(callback.from_user.id)

        if user_id not in mines_games:
            await callback.answer("❌ Нет активной игры!", show_alert=True)
            return

        game = mines_games[user_id]
        total_cells = game["field_size"] * game["field_size"]
        safe_cells = total_cells - game["mines_count"]

        def get_mines_multiplier(cells_opened):
            if cells_opened <= 0:
                return 0.0
            multipliers = {1: 0.8, 2: 1.0, 3: 1.1, 4: 1.25, 5: 1.35, 6: 1.50}
            if cells_opened <= 6:
                return multipliers.get(cells_opened, 1.0)
            return 1.50 + (cells_opened - 6) * 0.15

        keyboard = []
        row = []
        for i in range(total_cells):
            if i in game["revealed"]:
                row.append(InlineKeyboardButton(
                    text="✅",
                    callback_data=f"mines_cell_{i}"
                ))
            else:
                row.append(InlineKeyboardButton(
                    text="⬜",
                    callback_data=f"mines_cell_{i}"
                ))
            if len(row) == game["field_size"]:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        multiplier = get_mines_multiplier(len(game["revealed"]))
        current_win = int(game["bet"] * multiplier)

        keyboard.append([InlineKeyboardButton(
            text=f"💰 Забрать выигрыш: {current_win:,.0f}₽ (x{multiplier})",
            callback_data="mines_take_win"
        )])

        text = f"💣 **МИНЫ**\n\n"
        text += f"💰 Ставка: {game['bet']:,.0f}₽\n"
        text += f"💣 Мин: {game['mines_count']}\n"
        text += f"✅ Открыто: {len(game['revealed'])}/{safe_cells}\n"
        text += f"📊 Текущий множитель: x{multiplier}\n\n"
        text += "Выберите следующую клетку:"

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
        await callback.answer()

    # ==========================================
    # ===== ГЛАВНЫЙ ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ =====
    # ==========================================

    @dp.message(F.text, ~F.text.startswith('/'))
    async def handle_all_messages(message: types.Message, state: FSMContext):
        """
        Главный обработчик текстовых сообщений.
        ВАЖНО: handle_brcoin_convert зарегистрирован выше с фильтром состояния
        и имеет приоритет над этим обработчиком при активном состоянии конвертации.
        """
        if not await check_access(message):
            return

        current_state = await state.get_state()
        user_id = str(message.from_user.id)

        logger.info(f"📩 Сообщение: {message.text}, Состояние: {current_state}")

        # ==========================================
        # ===== 1. АУКЦИОН =====
        # ==========================================
        if current_state == AuctionStates.waiting_for_auction_bid.state:
            try:
                amount = int(message.text.strip())
                if amount <= 0:
                    await message.answer("❌ Введите положительное число!")
                    return

                data = await state.get_data()
                page = data.get("auction_page", 0)

                from services.auction import place_bid
                from database.file_manager import get_active_lots

                success, msg = await place_bid(user_id, page, amount)

                if success:
                    await state.clear()
                    try:
                        await show_auction_lot(message, user_id, page)
                    except Exception as e:
                        logger.warning(f"Не удалось обновить лот: {e}")
                    await message.answer(msg)
                    return
                else:
                    await message.answer(msg)
                    lots = await get_active_lots()
                    if page < len(lots):
                        lot = lots[page]
                        await message.answer(
                            f"✏️ Введите новую сумму ставки для **{lot['car_name']}**\n\n"
                            f"💰 Текущая ставка: {lot['current_bid']:,}₽",
                            parse_mode="Markdown"
                        )
                        await state.set_state(AuctionStates.waiting_for_auction_bid)
                        await state.update_data(auction_page=page)
                    return
            except ValueError:
                await message.answer("❌ Введите число!")
                return
            except Exception as e:
                logger.error(f"Ошибка аукциона: {e}")
                await message.answer("⚠️ Ошибка!")
                await state.clear()
                return

        # ==========================================
        # ===== 2. ТРЕЙДИНГ =====
        # ==========================================
        if current_state == TradeStates.waiting_for_trade_amount.state:
            try:
                amount = int(message.text.strip())
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
                            f"❌ Превышен лимит хранения! Максимум {limit['max_storage']} {currency}."
                        )
                        await state.clear()
                        return

                    user["money"] -= total
                    user["portfolio"][currency] = current + amount
                    user["trades_count"] = user.get("trades_count", 0) + amount

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

                    await message.answer(f"✅ Продано {amount} {currency} за {total:,.0f}₽")

                users[user_id] = user
                await save_users(users)
                await state.clear()

                currency_rates.update_rates()
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
                return

            except ValueError:
                await message.answer("❌ Введите число!")
                await state.clear()
                return
            except Exception as e:
                logger.error(f"Ошибка трейдинга: {e}")
                await message.answer("⚠️ Ошибка!")
                await state.clear()
                return

        # ==========================================
        # ===== 3. КАЗИНО - СТАВКА =====
        # ==========================================
        if current_state == CasinoStates.waiting_for_casino_bet.state:
            try:
                amount = int(message.text.strip())
                if amount <= 0:
                    await message.answer("❌ Введите положительное число!")
                    return

                users = await load_users()
                user = users.get(user_id, get_default_user())

                if amount > user["money"]:
                    await message.answer(f"❌ Недостаточно средств! У вас {user['money']:,.0f}₽")
                    return

                if "casino" not in user:
                    user["casino"] = {}
                user["casino"]["bet"] = amount
                users[user_id] = user
                await save_users(users)
                await state.clear()

                await message.answer(
                    f"✅ Ставка установлена: {amount:,.0f}₽",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🎰 В казино", callback_data="casino")]
                    ])
                )
                return

            except ValueError:
                await message.answer("❌ Введите число!")
                await state.clear()
                return
            except Exception as e:
                logger.error(f"Ошибка установки ставки: {e}")
                await message.answer("⚠️ Ошибка!")
                await state.clear()
                return

        # ==========================================
        # ===== 4. КАЗИНО - МИНЫ (настройка) =====
        # ==========================================
        if current_state == CasinoStates.waiting_for_mines_count.state:
            try:
                amount = int(message.text.strip())
                if amount <= 0:
                    await message.answer("❌ Введите положительное число!")
                    return

                users = await load_users()
                user = users.get(user_id, get_default_user())
                field_size = user.get("casino", {}).get("field_size", 5)
                min_mines = get_min_mines_for_size(field_size)

                if amount < min_mines or amount > 10:
                    await message.answer(f"❌ Введите число от {min_mines} до 10!")
                    return

                if "casino" not in user:
                    user["casino"] = {}
                user["casino"]["mines_count"] = amount
                users[user_id] = user
                await save_users(users)
                await state.clear()

                await message.answer(
                    f"✅ Количество мин установлено: {amount}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💣 В мины", callback_data="casino_mines")]
                    ])
                )
                return

            except ValueError:
                await message.answer("❌ Введите число!")
                await state.clear()
                return
            except Exception as e:
                logger.error(f"Ошибка настройки мин: {e}")
                await message.answer("⚠️ Ошибка!")
                await state.clear()
                return

        # ==========================================
        # ===== 5. КАЗИНО - ПОЛЕ =====
        # ==========================================
        if current_state == CasinoStates.waiting_for_field_size.state:
            try:
                amount = int(message.text.strip())
                if amount < 3 or amount > 8:
                    await message.answer("❌ Введите число от 3 до 8!")
                    return

                users = await load_users()
                user = users.get(user_id, get_default_user())

                if "casino" not in user:
                    user["casino"] = {}
                user["casino"]["field_size"] = amount
                users[user_id] = user
                await save_users(users)
                await state.clear()

                await message.answer(
                    f"✅ Размер поля установлен: {amount}x{amount}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💣 В мины", callback_data="casino_mines")]
                    ])
                )
                return

            except ValueError:
                await message.answer("❌ Введите число!")
                await state.clear()
                return
            except Exception as e:
                logger.error(f"Ошибка настройки поля: {e}")
                await message.answer("⚠️ Ошибка!")
                await state.clear()
                return

        # ==========================================
        # ===== 6. ПОДДЕРЖКА =====
        # ==========================================
        if current_state == SupportStates.waiting_for_support_message.state:
            try:
                users = await load_users()
                user = users.get(user_id, get_default_user())

                username = message.from_user.username or f"User_{user_id[:5]}"

                support_text = (
                    f"🆘 **НОВОЕ ОБРАЩЕНИЕ В ПОДДЕРЖКУ**\n\n"
                    f"👤 От: @{username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"💰 Баланс: {user['money']:,.0f}₽\n"
                    f"🔒 Заморожено: {user.get('frozen_balance', 0):,.0f}₽\n"
                    f"💎 BRcoins: {user['brcoins']}\n\n"
                    f"📝 Сообщение:\n{message.text}"
                )

                sent_to = 0
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, support_text)
                        sent_to += 1
                    except Exception as e:
                        logger.warning(f"Не удалось отправить админу {admin_id}: {e}")

                await state.clear()

                if sent_to > 0:
                    await message.answer(
                        "✅ **Ваше сообщение отправлено администратору!**\n\n"
                        "Мы свяжемся с вами в ближайшее время.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 В меню", callback_data="back_main")]
                        ]),
                        parse_mode="Markdown"
                    )
                else:
                    await message.answer(
                        "❌ Не удалось отправить сообщение. Попробуйте позже.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔙 В меню", callback_data="back_main")]
                        ]),
                        parse_mode="Markdown"
                    )
                return
            except Exception as e:
                logger.error(f"Ошибка поддержки: {e}")
                await state.clear()
                await message.answer("⚠️ Ошибка!")
                return

        # ==========================================
        # ===== 7. ПРОМОКОДЫ (ЕСЛИ НЕТ СОСТОЯНИЯ) =====
        # ==========================================
        if current_state is None:
            try:
                users = await load_users()
                user = users.get(user_id)

                if not user:
                    return

                promocodes = await load_promocodes()
                code = message.text.upper().strip()

                logger.info(f"🔍 Проверка промокода: {code}")
                logger.info(f"📦 Доступные промокоды: {list(promocodes.keys())}")

                if not promocodes:
                    await message.answer("❌ В системе нет активных промокодов!")
                    return

                if code not in promocodes:
                    await message.answer("❌ Промокод не найден!")
                    return

                promo = promocodes[code]

                if not all(key in promo for key in ["used", "uses", "type", "amount", "used_by"]):
                    logger.error(f"❌ Некорректная структура промокода: {promo}")
                    await message.answer("⚠️ Ошибка в структуре промокода!")
                    return

                used_by = promo.get("used_by", [])
                if user_id in used_by:
                    await message.answer("❌ Вы уже использовали этот промокод!")
                    return

                if promo["used"] >= promo["uses"]:
                    await message.answer("❌ Промокод использован!")
                    return

                if promo["type"] == "brcoins":
                    user["brcoins"] += promo["amount"]
                    user["donate_received"] = user.get("donate_received", 0) + promo["amount"]
                else:
                    user["money"] += promo["amount"]
                    user["total_earned"] = user.get("total_earned", 0) + promo["amount"]

                promo["used"] += 1
                promo["used_by"] = used_by + [user_id]

                users[user_id] = user

                await save_promocodes(promocodes)
                await save_users(users)

                logger.info(f"✅ Промокод {code} активирован пользователем {user_id}")

                await message.answer(
                    f"✅ +{promo['amount']:,} "
                    f"{'BRcoins' if promo['type'] == 'brcoins' else '₽'}!"
                )
                return
            except Exception as e:
                logger.error(f"❌ Ошибка промокода: {e}")
                await message.answer("⚠️ Ошибка при применении промокода!")
                return

        # ==========================================
        # ===== 8. ЕСЛИ НИЧЕГО НЕ ПОДОШЛО =====
        # ==========================================
        logger.info(f"⚠️ Сообщение не обработано: {message.text}, состояние: {current_state}")
