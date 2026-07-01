from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger
from database.file_manager import get_active_lots
from utils.helpers import check_access, is_function_disabled, get_stars_display
from services.auction import place_bid
from states import AuctionStates

user_auction_page = {}

# ==========================================
# ===== ФУНКЦИЯ НА ВЕРХНЕМ УРОВНЕ =====
# ==========================================

async def show_auction_lot(message: types.Message, user_id: str, page: int):
    """Показывает конкретный лот аукциона"""
    lots = await get_active_lots()
    
    if not lots:
        await message.edit_text(
            "🚗 АУКЦИОН\n\n"
            "На данный момент нет активных лотов.\n"
            "Загляните позже!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ])
        )
        return
    
    if page < 0:
        page = len(lots) - 1
    elif page >= len(lots):
        page = 0
    
    user_auction_page[user_id] = page
    
    lot = lots[page]
    car_name = lot["car_name"]
    stars = lot.get("stars", 1)
    rarity = lot.get("rarity", "Доступная")
    start_bid = lot.get("start_bid", 0)
    current_bid = lot.get("current_bid", start_bid)
    current_bidder = lot.get("current_bidder")
    
    bidder_info = "Нет ставок"
    if current_bidder:
        try:
            user = await bot.get_chat(int(current_bidder))
            bidder_info = f"@{user.username}" if user.username else f"ID: {current_bidder[:5]}..."
        except:
            bidder_info = f"ID: {current_bidder[:5]}..."
    
    stars_display = get_stars_display(stars)
    
    text = (
        f"🚗 **{car_name}**\n\n"
        f"⭐ {stars_display} ({rarity})\n"
        f"💰 Начальная ставка: {start_bid:,}₽\n"
        f"💵 Текущая ставка: {current_bid:,}₽\n"
        f"👤 Текущий лидер: {bidder_info}\n\n"
        f"📊 Лот {page + 1}/{len(lots)}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="◀", callback_data="auction_prev"),
            InlineKeyboardButton(text="Сделать ставку", callback_data="auction_bid"),
            InlineKeyboardButton(text="▶", callback_data="auction_next")
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
    ]
    
    await message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )

def register_auction_handlers(dp):
    
    @dp.callback_query(F.data == "auction")
    async def auction_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_11"):
            await callback.answer("⛔ Аукцион временно остановлен администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            
            lots = await get_active_lots()
            
            if not lots:
                await callback.message.edit_text(
                    "🚗 АУКЦИОН\n\n"
                    "На данный момент нет активных лотов.\n"
                    "Загляните позже!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                    ])
                )
                await callback.answer()
                return
            
            user_auction_page[user_id] = 0
            await show_auction_lot(callback.message, user_id, 0)
            
        except Exception as e:
            logger.error(f"Ошибка в auction_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "auction_prev")
    async def auction_prev(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_11"):
            await callback.answer("⛔ Аукцион временно остановлен администратором!", show_alert=True)
            return
        
        user_id = str(callback.from_user.id)
        current_page = user_auction_page.get(user_id, 0)
        new_page = current_page - 1
        await show_auction_lot(callback.message, user_id, new_page)
        await callback.answer()

    @dp.callback_query(F.data == "auction_next")
    async def auction_next(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_11"):
            await callback.answer("⛔ Аукцион временно остановлен администратором!", show_alert=True)
            return
        
        user_id = str(callback.from_user.id)
        current_page = user_auction_page.get(user_id, 0)
        new_page = current_page + 1
        await show_auction_lot(callback.message, user_id, new_page)
        await callback.answer()

    @dp.callback_query(F.data == "auction_bid")
    async def auction_bid(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_11"):
            await callback.answer("⛔ Аукцион временно остановлен администратором!", show_alert=True)
            return
        
        user_id = str(callback.from_user.id)
        page = user_auction_page.get(user_id, 0)
        lots = await get_active_lots()
        
        if page >= len(lots):
            await callback.answer("❌ Лот не найден!", show_alert=True)
            return
        
        lot = lots[page]
        current_bid = lot.get("current_bid", 0)
        
        await state.update_data(auction_page=page)
        await state.set_state(AuctionStates.waiting_for_auction_bid)
        
        await callback.message.edit_text(
            f"✏️ Введите сумму ставки для **{lot['car_name']}**\n\n"
            f"💰 Текущая ставка: {current_bid:,}₽\n"
            f"⚠️ Ставка должна быть выше текущей!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="auction_cancel")]
            ]),
            parse_mode="Markdown"
        )
        await callback.answer()

    @dp.callback_query(F.data == "auction_cancel")
    async def auction_cancel(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        user_id = str(callback.from_user.id)
        page = user_auction_page.get(user_id, 0)
        await show_auction_lot(callback.message, user_id, page)
        await callback.answer()

    # ==========================================
    # ===== ОБРАБОТЧИК ВВОДА СТАВКИ =====
    # ==========================================

    @dp.message(AuctionStates.waiting_for_auction_bid)
    async def process_auction_bid_input(message: types.Message, state: FSMContext):
        """Обрабатывает введенную сумму ставки"""
        if not await check_access(message):
            await state.clear()
            return
        
        if await is_function_disabled("menubutton_11"):
            await message.answer("⛔ Аукцион временно остановлен администратором!")
            await state.clear()
            return
        
        try:
            # Попытка получить число из сообщения
            bid_amount = int(message.text.replace(' ', '').replace(',', ''))
        except ValueError:
            await message.answer(
                "❌ Ошибка! Введите корректную сумму (только цифры).\n\n"
                "Попробуйте еще раз:"
            )
            return
        
        if bid_amount <= 0:
            await message.answer(
                "❌ Ставка должна быть больше нуля!\n\n"
                "Попробуйте еще раз:"
            )
            return
        
        try:
            # Получить данные состояния
            data = await state.get_data()
            lot_index = data.get('auction_page', 0)
            user_id = str(message.from_user.id)
            
            # Размещаем ставку
            success, response_message = await place_bid(user_id, lot_index, bid_amount)
            
            await state.clear()
            
            if success:
                # Успешно размещена ставка
                await message.answer(response_message, parse_mode="Markdown")
                
                # Обновляем вид аукциона
                user_auction_page[user_id] = lot_index
                lots = await get_active_lots()
                
                if lot_index < len(lots):
                    lot = lots[lot_index]
                    
                    bidder_info = user_id
                    try:
                        user = await bot.get_chat(int(user_id))
                        bidder_info = f"@{user.username}" if user.username else f"ID: {user_id[:5]}..."
                    except:
                        bidder_info = f"ID: {user_id[:5]}..."
                    
                    stars_display = get_stars_display(lot.get('stars', 1))
                    
                    # Отправляем обновленный вид лота
                    await message.answer(
                        f"🚗 **{lot['car_name']}**\n\n"
                        f"⭐ {stars_display} ({lot.get('rarity', 'Доступная')})\n"
                        f"💰 Начальная ставка: {lot.get('start_bid', 0):,}₽\n"
                        f"💵 Текущая ставка: {lot.get('current_bid', 0):,}₽\n"
                        f"👤 Текущий лидер: {bidder_info}\n\n"
                        f"📊 Лот {lot_index + 1}/{len(lots)}",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(text="◀", callback_data="auction_prev"),
                                InlineKeyboardButton(text="Сделать ставку", callback_data="auction_bid"),
                                InlineKeyboardButton(text="▶", callback_data="auction_next")
                            ],
                            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                        ]),
                        parse_mode="Markdown"
                    )
            else:
                # Ошибка при размещении ставки
                await message.answer(
                    f"{response_message}\n\n"
                    "Введите другую сумму или отмените операцию:",
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Ошибка при обработке ставки: {e}")
            await message.answer("❌ Произошла ошибка при обработке ставки!")
            await state.clear()


# ==========================================
# ===== ЭКСПОРТ =====
# ==========================================

__all__ = [
    'show_auction_lot',
    'register_auction_handlers'
    ]
