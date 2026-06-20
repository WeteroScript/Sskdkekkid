from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from core.bot import dp
from data.database import load_users, save_users
from data.models import get_default_user
from keyboards.menu import get_main_menu

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = str(message.from_user.id)
    users = await load_users()
    
    if user_id not in users:
        users[user_id] = get_default_user()
        await save_users(users)
    
    text, keyboard = await get_main_menu(message.from_user.id)
    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data == "back_main")
async def back_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text, keyboard = await get_main_menu(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

# Здесь импортируются остальные хендлеры
from games.casino import *
from games.trading import *
from business.manager import *
from admin.commands import *

def register_handlers(dp):
    # Все хендлеры уже зарегистрированы через декораторы
    pass
