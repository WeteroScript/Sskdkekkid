import random
from datetime import datetime

from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import bot, logger, BUSINESS_CONFIG, MINE_RESOURCES
from database.file_manager import (
    load_users, save_users, load_business, save_business, load_inventory, save_inventory
)
from utils.helpers import check_access, get_default_user, is_function_disabled
from services.business import collect_business, get_auto_mine_resource

def register_business_handlers(dp):
    
    async def get_user_business_count(user_id):
        users = await load_users()
        user = users.get(str(user_id), get_default_user())
        return sum(1 for biz in user.get("business", {}).values() if biz.get("owned", False))
    
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
    
    @dp.callback_query(F.data == "business")
    async def business_menu(callback: types.CallbackQuery, state: FSMContext):
        if state:
            await state.clear()
        if not await check_access(callback):
            return
        
        if await is_function_disabled("menubutton_7"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            business_data = await load_business()
            
            user_business_count = await get_user_business_count(user_id)
            status = await get_business_status(user_id)
            
            # ==========================================
            # ===== ТЕКСТ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ БЕЗ БИЗНЕСА =====
            # ==========================================
            if user_business_count == 0:
                text = "🏢 **Доступные бизнесы для покупки:**\n\n"
                
                for key, config in BUSINESS_CONFIG.items():
                    emoji = config["emoji"]
                    name = config["name"]
                    price = config["price"]
                    max_owners = config["max_owners"]
                    owners = len(business_data.get(key, {}).get("owners", []))
                    
                    free_slots = max_owners - owners  # ← ИСПРАВЛЕНО!
                    
                    text += f"{emoji} {name} - ❌ Не куплен\n"
                    text += f"   💰 Цена: {price:,.0f}₽\n"
                    text += f"   👥 Свободно: {free_slots}/{max_owners}\n\n"
                
                text += "⚠️ У вас нет бизнеса. Купите один из доступных!"
            
            # ==========================================
            # ===== ТЕКСТ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ С БИЗНЕСОМ =====
            # ==========================================
            else:
                text = "🏢 **Ваш бизнес:**\n\n"
                
                for key, config in BUSINESS_CONFIG.items():
                    s = status.get(key, {"owned": False, "ready": False, "remaining": "Не куплен", "auto_collect": False})
                    
                    if s["owned"]:
                        emoji = config["emoji"]
                        name = config["name"]
                        price = config["price"]
                        auto_status = "🟢 Включен" if s["auto_collect"] else "🔴 Выключен"
                        ready_status = "✅ Готов к сбору" if s["ready"] else f"⏳ {s['remaining']}"
                        
                        text += f"{emoji} {name}\n"
                        text += f"   💰 Цена: {price:,.0f}₽\n"
                        text += f"   🔄 Авто-сбор: {auto_status}\n"
                        text += f"   📊 Статус: {ready_status}\n\n"
            
            # ==========================================
            # ===== КНОПКИ =====
            # ==========================================
            keyboard = []
            
            if user_business_count == 0:
                # Показываем кнопки покупки всех бизнесов
                for key, config in BUSINESS_CONFIG.items():
                    owners = len(business_data.get(key, {}).get("owners", []))
                    if owners < config["max_owners"]:
                        keyboard.append([InlineKeyboardButton(
                            text=f"💰 Купить {config['emoji']} {config['name']}",
                            callback_data=f"buy_business_{key}"
                        )])
            else:
                # Показываем кнопки управления для каждого бизнеса
                for key, config in BUSINESS_CONFIG.items():
                    s = status.get(key, {"owned": False, "auto_collect": False})
                    if s["owned"]:
                        auto_text = "🔴 Выключить" if s["auto_collect"] else "🟢 Включить"
                        keyboard.append([InlineKeyboardButton(
                            text=f"{config['emoji']} {auto_text} авто-сбор {config['name']}",
                            callback_data=f"toggle_auto_{key}"
                        )])
                
                # Кнопка сбора дохода
                has_ready = any(s.get("ready", False) for s in status.values())
                if has_ready:
                    keyboard.append([InlineKeyboardButton(
                        text="💰 Собрать доход",
                        callback_data="collect_business"
                    )])
                
                # Кнопка продажи бизнеса
                keyboard.append([InlineKeyboardButton(
                    text="💰 Продать бизнес (50%)",
                    callback_data="sell_business"
                )])
            
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка в business_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "sell_business")
    async def sell_business(callback: types.CallbackQuery):
        """Продажа бизнеса за 50% стоимости"""
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
            user["total_earned"] = user.get("total_earned", 0) + sell_price
            
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

    @dp.callback_query(F.data.startswith("buy_business_"))
    async def buy_business(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        if state:
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
    async def toggle_auto_collect(callback: types.CallbackQuery, state: FSMContext):
        if not await check_access(callback):
            return
        
        try:
            if state:
                await state.clear()
            
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
            
            if not user["business"][business_key].get("last_collect"):
                user["business"][business_key]["last_collect"] = datetime.now().isoformat()
            
            users[user_id] = user
            await save_users(users)
            
            status_text = "включен" if new_status else "выключен"
            await callback.answer(f"✅ Авто-сбор для {config['name']} {status_text}!", show_alert=True)
            
            await business_menu(callback, state)
        except Exception as e:
            logger.error(f"Ошибка в toggle_auto_collect: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data == "collect_business")
    async def collect_business(callback: types.CallbackQuery, state: FSMContext):
        if state:
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
                        user["total_earned"] = user.get("total_earned", 0) + profit
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
