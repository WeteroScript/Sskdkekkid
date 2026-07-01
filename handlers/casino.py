import random
import string
from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger
from database.file_manager import load_users, save_users
from utils.helpers import check_access, get_default_user, is_function_disabled, is_admin
from states import CasinoStates

mines_games = {}          # user_id -> game_data
mines_games_by_id = {}    # game_id -> game_data

def generate_game_id() -> str:
    """Генерирует уникальный ID для игры в мины"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def register_casino_handlers(dp):
    
    def get_mines_multiplier(cells_opened):
        """Возвращает коэффициент для мин по количеству открытых клеток"""
        if cells_opened <= 0:
            return 0.0
        multipliers = {
            1: 0.8,
            2: 1.0,
            3: 1.1,
            4: 1.25,
            5: 1.35,
            6: 1.50
        }
        if cells_opened <= 6:
            return multipliers.get(cells_opened, 1.0)
        return 1.50 + (cells_opened - 6) * 0.15
    
    def get_min_mines_for_size(size: int) -> int:
        """Возвращает минимальное количество мин для размера поля"""
        min_mines = {
            3: 2,
            4: 3,
            5: 5,
            6: 7,
            7: 9,
            8: 13
        }
        return min_mines.get(size, 2)
    
    # ==========================================
    # ===== ГЛАВНОЕ МЕНЮ КАЗИНО =====
    # ==========================================
    
    @dp.callback_query(F.data == "casino")
    async def casino_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_8"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
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
            text = f"🎰 **КАЗИНО**\n\n"
            text += f"💰 Текущая ставка: {bet:,.0f}₽\n"
            text += f"💳 Ваш баланс: {user['money']:,.0f}₽"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в casino_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== УСТАНОВКА СТАВКИ =====
    # ==========================================
    
    @dp.callback_query(F.data == "casino_bet")
    async def casino_bet(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "✏️ **Введите сумму ставки:**",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
                ]),
                parse_mode="Markdown"
            )
            await state.set_state(CasinoStates.waiting_for_casino_bet)
        except Exception as e:
            logger.error(f"Ошибка в casino_bet: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== КУБИК =====
    # ==========================================
    
    @dp.callback_query(F.data == "casino_dice")
    async def casino_dice(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
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
            
            user["money"] -= bet
            users[user_id] = user
            await save_users(users)
            
            keyboard = [
                [InlineKeyboardButton(text="🎲 Четное", callback_data="dice_even")],
                [InlineKeyboardButton(text="🎲 Нечетное", callback_data="dice_odd")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
            ]
            
            await callback.message.edit_text(
                f"🎲 **КУБИК**\n\n"
                f"💰 Ставка: {bet:,.0f}₽ (списана)\n"
                f"💳 Ваш баланс: {user['money']:,.0f}₽\n"
                f"📊 Коэффициент: 1.3x\n\n"
                f"Выберите: Четное или Нечетное",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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
            
            win_chance = 0.45
            multiplier = 1.3
            
            dice_result = random.randint(1, 6)
            is_even = dice_result % 2 == 0
            
            is_win = (choice == "even" and is_even) or (choice == "odd" and not is_even)
            
            if is_win:
                win = int(bet * multiplier)
                user["money"] += win
                user["total_earned"] = user.get("total_earned", 0) + win
                result_text = f"✅ **ВЫИГРЫШ!**\n🎲 Выпало: {dice_result}\n💰 +{win:,.0f}₽ (x{multiplier})\n💳 Новый баланс: {user['money']:,.0f}₽"
            else:
                result_text = f"❌ **ПРОИГРЫШ!**\n🎲 Выпало: {dice_result}\n💸 -{bet:,.0f}₽\n💳 Новый баланс: {user['money']:,.0f}₽"
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"🎲 **КУБИК**\n\n{result_text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎲 Играть ещё", callback_data="casino_dice")],
                    [InlineKeyboardButton(text="🔙 В казино", callback_data="casino")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в dice_play: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== СЛОТЫ =====
    # ==========================================
    
    @dp.callback_query(F.data == "casino_slots")
    async def casino_slots(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
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
            
            await callback.message.edit_text(
                f"🎰 **СЛОТЫ**\n\n"
                f"💰 Ставка: {bet:,.0f}₽\n"
                f"💳 Ваш баланс: {user['money']:,.0f}₽\n\n"
                f"Нажмите 'Крутить' для игры",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Крутить", callback_data="slots_spin")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
                ]),
                parse_mode="Markdown"
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
                await callback.answer("❌ Недостаточно средств!", show_alert=True)
                return
            
            user["money"] -= bet
            users[user_id] = user
            await save_users(users)
            
            symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
            result = [random.choice(symbols) for _ in range(3)]
            
            win = 0
            win_text = ""
            
            if random.random() < 0.05:
                if result[0] == "7️⃣" and result[1] == "7️⃣" and result[2] == "7️⃣":
                    win = bet * 3
                    win_text = "🎰 ДЖЕКПОТ! 7️⃣7️⃣7️⃣"
                else:
                    result = [random.choice(symbols) for _ in range(3)]
                    if result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
                        win = bet * 2
                        win_text = "🎰 ДВЕ ОДИНАКОВЫХ!"
            
            elif random.random() < 0.35:
                if result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
                    win = bet * 2
                    win_text = "🎰 ДВЕ ОДИНАКОВЫХ!"
            
            if result[0] == result[1] == result[2] and result[0] != "7️⃣":
                win = bet * 3
                win_text = "🎰 ТРИ ОДИНАКОВЫХ!"
            
            win = int(win)
            
            if win > 0:
                user["money"] += win
                user["total_earned"] = user.get("total_earned", 0) + win
                result_text = f"✅ {win_text}\n🎰 {result[0]} {result[1]} {result[2]}\n💰 +{win:,.0f}₽\n💳 Новый баланс: {user['money']:,.0f}₽"
            else:
                result_text = f"❌ **ПРОИГРЫШ!**\n🎰 {result[0]} {result[1]} {result[2]}\n💸 -{bet:,.0f}₽\n💳 Новый баланс: {user['money']:,.0f}₽"
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"🎰 **СЛОТЫ**\n\n{result_text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Крутить ещё", callback_data="slots_spin")],
                    [InlineKeyboardButton(text="🔙 В казино", callback_data="casino")]
                ]),
                parse_mode="Markdown"
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
        if state:
            await state.clear()
        if not await check_access(callback):
            return
        
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
                f"💣 **МИНЫ**\n\n"
                f"💰 Ставка: {bet:,.0f}₽\n"
                f"💣 Количество мин: {mines_count}\n"
                f"📐 Размер поля: {field_size}x{field_size}\n"
                f"💳 Ваш баланс: {user['money']:,.0f}₽\n\n"
                f"📊 Коэффициенты:\n"
                f"1 клетка - 0.8x | 2 - 1.0x | 3 - 1.1x\n"
                f"4 - 1.25x | 5 - 1.35x | 6 - 1.5x\n"
                f"Далее +0.15x за клетку\n\n"
                f"Выберите действие:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            field_size = user.get("casino", {}).get("field_size", 5)
            min_mines = get_min_mines_for_size(field_size)
            
            await callback.message.edit_text(
                f"✏️ **Введите количество мин** (от {min_mines} до 10):\n"
                f"📐 Текущий размер поля: {field_size}x{field_size} (минимум {min_mines} мин)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="casino_mines")]
                ]),
                parse_mode="Markdown"
            )
            await state.set_state(CasinoStates.waiting_for_mines_count)
        except Exception as e:
            logger.error(f"Ошибка в mines_settings: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "mines_field")
    async def mines_field(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            await callback.message.edit_text(
                "✏️ **Введите размер поля** (от 3 до 8):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="casino_mines")]
                ]),
                parse_mode="Markdown"
            )
            await state.set_state(CasinoStates.waiting_for_field_size)
        except Exception as e:
            logger.error(f"Ошибка в mines_field: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

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
            
            min_mines = get_min_mines_for_size(field_size)
            if mines_count < min_mines:
                mines_count = min_mines
                user["casino"]["mines_count"] = mines_count
                users[user_id] = user
                await save_users(users)
            
            user["money"] -= bet
            users[user_id] = user
            await save_users(users)
            
            total_cells = field_size * field_size
            mine_positions = random.sample(range(total_cells), mines_count)
            
            # ✅ ГЕНЕРИРУЕМ УНИКАЛЬНЫЙ ID
            game_id = generate_game_id()
            while game_id in mines_games_by_id:
                game_id = generate_game_id()
            
            game_data = {
                "mine_positions": mine_positions,
                "field_size": field_size,
                "mines_count": mines_count,
                "revealed": [],
                "bet": bet,
                "user_id": user_id,
                "game_id": game_id,
                "finished": False
            }
            
            mines_games[user_id] = game_data
            mines_games_by_id[game_id] = game_data
            
            keyboard = []
            row = []
            for i in range(total_cells):
                row.append(InlineKeyboardButton(
                    text="⬜",
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
            
            text = f"💣 **МИНЫ**\n🆔 ID: `{game_id}`\n\n"
            text += f"💰 Ставка: {bet:,.0f}₽ (списана)\n"
            text += f"💳 Ваш баланс: {user['money']:,.0f}₽\n"
            text += f"💣 Мин: {mines_count}\n"
            text += f"✅ Открыто: 0/{total_cells - mines_count}\n\n"
            text += "Выберите клетку:"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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
            game_id = game.get("game_id", "???")
            
            if cell_num in game["revealed"]:
                await callback.answer("❌ Эта клетка уже открыта!", show_alert=True)
                return
            
            users = await load_users()
            user = users.get(user_id, get_default_user())
            bet = game["bet"]
            total_cells = game["field_size"] * game["field_size"]
            
            if cell_num in game["mine_positions"]:
                # 💥 ВЗРЫВ
                game["finished"] = True
                if game_id in mines_games_by_id:
                    mines_games_by_id[game_id]["finished"] = True
                del mines_games[user_id]
                
                keyboard = []
                row = []
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
                            text="⬜",
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
                    text="🔙 В казино",
                    callback_data="casino"
                )])
                
                await callback.message.edit_text(
                    f"💣 **МИНЫ**\n🆔 ID: `{game_id}`\n\n"
                    f"💥 **ВЗРЫВ!** Вы попали на мину!\n"
                    f"💸 -{bet:,.0f}₽\n"
                    f"💳 Новый баланс: {user['money']:,.0f}₽",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                    parse_mode="Markdown"
                )
                return
            
            game["revealed"].append(cell_num)
            mines_games[user_id] = game
            if game_id in mines_games_by_id:
                mines_games_by_id[game_id]["revealed"] = game["revealed"]
            
            safe_cells = total_cells - game["mines_count"]
            
            if len(game["revealed"]) == safe_cells:
                # 🎉 ПОБЕДА
                game["finished"] = True
                if game_id in mines_games_by_id:
                    mines_games_by_id[game_id]["finished"] = True
                
                multiplier = get_mines_multiplier(len(game["revealed"]))
                win = int(bet * multiplier)
                user["money"] += win
                user["total_earned"] = user.get("total_earned", 0) + win
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
                    text="🔙 В казино",
                    callback_data="casino"
                )])
                
                await callback.message.edit_text(
                    f"💣 **МИНЫ**\n🆔 ID: `{game_id}`\n\n"
                    f"🎉 **ВЫИГРЫШ!** Вы открыли все безопасные клетки!\n"
                    f"💰 +{win:,.0f}₽ (x{multiplier})\n"
                    f"💳 Новый баланс: {user['money']:,.0f}₽",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                    parse_mode="Markdown"
                )
                return
            
            # Обновляем игровое поле
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
            current_win = int(bet * multiplier)
            
            keyboard.append([InlineKeyboardButton(
                text=f"💰 Забрать выигрыш: {current_win:,.0f}₽ (x{multiplier})",
                callback_data="mines_take_win"
            )])
            
            text = f"💣 **МИНЫ**\n🆔 ID: `{game_id}`\n\n"
            text += f"💰 Ставка: {bet:,.0f}₽\n"
            text += f"💳 Ваш баланс: {user['money']:,.0f}₽\n"
            text += f"💣 Мин: {game['mines_count']}\n"
            text += f"✅ Открыто: {len(game['revealed'])}/{safe_cells}\n"
            text += f"📊 Текущий множитель: x{multiplier}\n\n"
            text += "Выберите следующую клетку:"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
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
            game_id = game.get("game_id", "???")
            
            if not game["revealed"]:
                await callback.answer("❌ Откройте хотя бы одну клетку!", show_alert=True)
                return
            
            users = await load_users()
            user = users.get(user_id, get_default_user())
            bet = game["bet"]
            
            multiplier = get_mines_multiplier(len(game["revealed"]))
            win = int(bet * multiplier)
            
            user["money"] += win
            user["total_earned"] = user.get("total_earned", 0) + win
            users[user_id] = user
            await save_users(users)
            
            game["finished"] = True
            if game_id in mines_games_by_id:
                mines_games_by_id[game_id]["finished"] = True
            del mines_games[user_id]
            
            await callback.message.edit_text(
                f"💰 **ВЫИГРЫШ ЗАБРАН!**\n\n"
                f"🆔 ID: `{game_id}`\n"
                f"✅ Открыто клеток: {len(game['revealed'])}\n"
                f"📊 Множитель: x{multiplier}\n"
                f"💰 Выигрыш: {win:,.0f}₽\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💣 Играть снова", callback_data="mines_play")],
                    [InlineKeyboardButton(text="🔙 В казино", callback_data="casino")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в mines_take_win: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "mines_dead")
    async def mines_dead(callback: types.CallbackQuery):
        await callback.answer("Игра окончена! Начните новую игру.", show_alert=True)

    @dp.callback_query(F.data == "mines_cancel")
    async def mines_cancel(callback: types.CallbackQuery):
        """Завершает игру в мины и возвращает деньги"""
        user_id = str(callback.from_user.id)
        
        if user_id in mines_games:
            game = mines_games[user_id]
            game_id = game.get("game_id", "???")
            bet = game.get("bet", 0)
            
            users = await load_users()
            user = users.get(user_id, get_default_user())
            user["money"] += bet
            users[user_id] = user
            await save_users(users)
            
            game["finished"] = True
            if game_id in mines_games_by_id:
                mines_games_by_id[game_id]["finished"] = True
            del mines_games[user_id]
            
            await callback.message.edit_text(
                f"❌ **Игра завершена!**\n"
                f"🆔 ID: `{game_id}`\n"
                f"💰 Ставка {bet:,.0f}₽ возвращена на баланс.\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 В казино", callback_data="casino")]
                ]),
                parse_mode="Markdown"
            )
        else:
            await callback.answer("❌ Нет активной игры!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== КОМАНДА /minestatus (ДЛЯ АДМИНОВ) =====
    # ==========================================
    
    @dp.message(Command("minestatus"))
    async def mine_status_command(message: types.Message):
        """Показывает поле игры с минами (только для админов)"""
        
        # ✅ ПРОВЕРКА НА АДМИНА
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer(
                "❌ Использование: `/minestatus ID_игры`\n\n"
                "Пример: `/minestatus ABC123`",
                parse_mode="Markdown"
            )
            return
        
        game_id = parts[1].upper().strip()
        
        if game_id not in mines_games_by_id:
            await message.answer(f"❌ Игра с ID `{game_id}` не найдена!", parse_mode="Markdown")
            return
        
        game = mines_games_by_id[game_id]
        user_id = game.get("user_id")
        
        if game.get("finished", False):
            await message.answer(f"❌ Игра с ID `{game_id}` уже завершена!", parse_mode="Markdown")
            return
        
        field_size = game["field_size"]
        total_cells = field_size * field_size
        mine_positions = game["mine_positions"]
        revealed = game.get("revealed", [])
        
        users = await load_users()
        user = users.get(user_id, get_default_user())
        
        # ✅ СТРОИМ ПОЛЕ С МИНАМИ
        field_lines = []
        for row in range(field_size):
            line = ""
            for col in range(field_size):
                cell_index = row * field_size + col
                if cell_index in mine_positions:
                    line += "💣"  # ← ПОКАЗЫВАЕМ МИНЫ
                elif cell_index in revealed:
                    line += "✅"
                else:
                    line += "⬜"
            field_lines.append(line)
        
        field_text = "\n".join(field_lines)
        
        safe_cells = total_cells - game["mines_count"]
        revealed_count = len(revealed)
        
        # Получаем username игрока
        try:
            player = await bot.get_chat(int(user_id))
            player_name = f"@{player.username}" if player.username else f"ID: {user_id[:5]}"
        except:
            player_name = f"ID: {user_id[:5]}"
        
        text = (
            f"💣 **МИНЫ**\n"
            f"🆔 ID: `{game_id}`\n"
            f"👤 Игрок: {player_name}\n"
            f"📐 Размер: {field_size}x{field_size}\n"
            f"💣 Мин: {game['mines_count']}\n"
            f"✅ Открыто: {revealed_count}/{safe_cells}\n"
            f"💰 Ставка: {game['bet']:,}₽\n\n"
            f"```\n{field_text}\n```"
        )
        
        await message.answer(text, parse_mode="Markdown")


# ==========================================
# ===== ЭКСПОРТ =====
# ==========================================

__all__ = [
    'mines_games',
    'mines_games_by_id',
    'get_min_mines_for_size',
    'register_casino_handlers'
            ]
