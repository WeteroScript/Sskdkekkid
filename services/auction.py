import random
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from config import AUCTION_CARS, AUCTION_CONFIG, bot, logger
from database.file_manager import (
    load_users, save_users, load_auction_data, save_auction_data, get_active_lots
)
from utils.helpers import is_function_disabled, get_stars_display

# Глобальные переменные
auction_running = False
auction_update_task: Optional[asyncio.Task] = None
auction_timers: Dict[int, asyncio.Task] = {}

RARITY_CHANCES = {
    "Экзотическая": 0.005,
    "Легендарная": 0.05,
    "Очень редкая": 0.01,
    "Редкая": 0.30,
    "Доступная": 0.50
}

def generate_auction_lots(count: int = 15) -> List[Dict]:
    """Генерирует список лотов для аукциона"""
    lots = []
    
    available_cars = []
    for car_name, car_data in AUCTION_CARS.items():
        rarity = car_data.get("rarity", "Доступная")
        chance = RARITY_CHANCES.get(rarity, 0.01)
        available_cars.append((car_name, car_data, chance))
    
    selected_cars = []
    attempts = 0
    while len(selected_cars) < count and attempts < 1000:
        attempts += 1
        total_weight = sum(chance for _, _, chance in available_cars)
        if total_weight == 0:
            break
            
        rand = random.random() * total_weight
        cumulative = 0
        for car_name, car_data, chance in available_cars:
            cumulative += chance
            if rand <= cumulative:
                if (car_name, car_data) not in selected_cars:
                    selected_cars.append((car_name, car_data))
                break
    
    while len(selected_cars) < count and available_cars:
        car_name, car_data, _ = random.choice(available_cars)
        if (car_name, car_data) not in selected_cars:
            selected_cars.append((car_name, car_data))
    
    for car_name, car_data in selected_cars[:count]:
        base_price = car_data.get("base_price", 1000000)
        start_bid = car_data.get("start_bid", int(base_price * random.uniform(0.3, 0.6)))
        start_bid = max(start_bid, 100000)
        
        lots.append({
            "car_name": car_name,
            "car_data": car_data,
            "start_bid": start_bid,
            "current_bid": start_bid,
            "current_bidder": None,
            "stars": car_data.get("stars", 1),
            "rarity": car_data.get("rarity", "Доступная"),
            "last_bid_time": datetime.now().isoformat(),
            "is_active": True,
            "sold": False,
            "added_by_admin": False
        })
    
    return lots

async def update_auction_lots(force: bool = False):
    """Обновляет список лотов аукциона"""
    global auction_timers
    
    data = await load_auction_data()
    lots = data.get("lots", [])
    
    if force:
        for timer in auction_timers.values():
            timer.cancel()
        auction_timers.clear()
        
        lots = generate_auction_lots(AUCTION_CONFIG["max_lots"])
        logger.info(f"🔄 Аукцион полностью обновлён. Создано {len(lots)} новых лотов")
    else:
        lots = [lot for lot in lots if not lot.get("sold", False)]
        
        if len(lots) < AUCTION_CONFIG["max_lots"]:
            new_lots = generate_auction_lots(AUCTION_CONFIG["max_lots"] - len(lots))
            existing_names = [lot["car_name"] for lot in lots]
            for new_lot in new_lots:
                if new_lot["car_name"] not in existing_names:
                    lots.append(new_lot)
                    existing_names.append(new_lot["car_name"])
            
            lots = lots[:AUCTION_CONFIG["max_lots"]]
            logger.info(f"🔄 Аукцион дозаполнен. Лотов: {len(lots)}")
    
    data["lots"] = lots
    data["last_update"] = datetime.now().isoformat()
    await save_auction_data(data)
    
    for i, lot in enumerate(lots):
        if lot.get("is_active", True) and not lot.get("sold", False):
            await start_auction_timer(i)

async def auction_update_loop():
    """Цикл обновления аукциона"""
    global auction_running
    
    logger.info("🚗 AUCTION LOOP STARTED!")
    
    while auction_running:
        logger.info("🔄 Auction loop tick...")
        try:
            await update_auction_lots(force=True)
        except Exception as e:
            logger.error(f"❌ Ошибка обновления аукциона: {e}")
        await asyncio.sleep(AUCTION_CONFIG["update_interval"])

async def start_auction_timer(lot_index: int):
    """Запускает таймер для лота"""
    global auction_timers
    
    if lot_index in auction_timers:
        auction_timers[lot_index].cancel()
    
    auction_timers[lot_index] = asyncio.create_task(
        auction_timer(lot_index)
    )

async def auction_timer(lot_index: int):
    """Таймер ожидания перебития ставки"""
    try:
        await asyncio.sleep(AUCTION_CONFIG["bid_timeout"])
        
        data = await load_auction_data()
        lots = data.get("lots", [])
        
        if lot_index >= len(lots):
            return
        
        lot = lots[lot_index]
        if lot.get("sold", False) or not lot.get("is_active", True):
            return
        
        user_id = lot.get("current_bidder")
        if user_id:
            car_name = lot["car_name"]
            final_price = lot["current_bid"]
            
            users = await load_users()
            if user_id in users:
                frozen = users[user_id].get("frozen_balance", 0)
                
                if frozen < final_price:
                    users[user_id]["frozen_balance"] = 0
                    users[user_id]["money"] += frozen
                    lot["current_bidder"] = None
                    lot["is_active"] = True
                    await save_auction_data(data)
                    await save_users(users)
                    
                    try:
                        await bot.send_message(
                            int(user_id),
                            f"❌ У вас недостаточно замороженных средств для покупки {car_name}!\n"
                            f"💰 Сумма: {final_price:,}₽\n"
                            f"🔒 Заморожено было: {frozen:,}₽\n"
                            f"🔄 Лот возвращен на аукцион."
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось уведомить пользователя {user_id}: {e}")
                    return
                
                users[user_id]["frozen_balance"] = max(0, frozen - final_price)
                
                if "inventory" not in users[user_id]:
                    users[user_id]["inventory"] = []
                
                users[user_id]["inventory"].append({
                    "name": car_name,
                    "price": AUCTION_CARS.get(car_name, {}).get("base_price", 0),
                    "from_auction": True,
                    "bought_at": final_price
                })
                
                await save_users(users)
                
                lot["sold"] = True
                lot["is_active"] = False
                await save_auction_data(data)
                
                try:
                    await bot.send_message(
                        int(user_id),
                        f"🎉 ВЫ ВЫИГРАЛИ АУКЦИОН!\n\n"
                        f"🚗 {car_name}\n"
                        f"⭐ {get_stars_display(lot['stars'])} {lot['rarity']}\n"
                        f"💰 Цена: {final_price:,}₽\n\n"
                        f"💳 Деньги списаны с замороженного баланса.\n"
                        f"🔒 Остаток замороженных средств: {users[user_id]['frozen_balance']:,}₽\n"
                        f"🚗 Машина добавлена в ваш гараж!"
                    )
                except Exception as e:
                    logger.warning(f"Не удалось уведомить пользователя {user_id}: {e}")
                
                logger.info(f"✅ Машина {car_name} продана пользователю {user_id} за {final_price:,}₽")
        
        if lot_index in auction_timers:
            del auction_timers[lot_index]
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"❌ Ошибка в auction_timer: {e}")

async def place_bid(user_id: str, lot_index: int, amount: int) -> Tuple[bool, str]:
    """Размещает ставку на лот"""
    if await is_function_disabled("menubutton_11"):
        return False, "⛔ Аукцион временно остановлен администратором!"
    
    lots = await get_active_lots()
    
    if lot_index < 0 or lot_index >= len(lots):
        return False, "❌ Лот не найден!"
    
    lot = lots[lot_index]
    
    if not lot.get("is_active", True) or lot.get("sold", False):
        return False, "❌ Этот лот уже продан или неактивен!"
    
    if amount <= lot["current_bid"]:
        return False, f"❌ Ставка должна быть выше текущей ({lot['current_bid']:,}₽)!"
    
    users = await load_users()
    if user_id not in users:
        return False, "❌ Пользователь не найден!"
    
    available = users[user_id]["money"]
    
    if available < amount:
        return False, f"❌ Недостаточно средств! У вас {available:,}₽ (заморожено: {users[user_id].get('frozen_balance', 0):,}₽)"
    
    # ✅ СПИСЫВАЕМ С ОБЫЧНОГО БАЛАНСА И ДОБАВЛЯЕМ В ЗАМОРОЖЕННЫЙ
    users[user_id]["money"] -= amount
    users[user_id]["frozen_balance"] = users[user_id].get("frozen_balance", 0) + amount
    await save_users(users)
    
    data = await load_auction_data()
    all_lots = data.get("lots", [])
    
    real_index = None
    current_active = 0
    for i, l in enumerate(all_lots):
        if not l.get("sold", False) and l.get("is_active", True):
            if current_active == lot_index:
                real_index = i
                break
            current_active += 1
    
    if real_index is None:
        users[user_id]["money"] += amount
        users[user_id]["frozen_balance"] = max(0, users[user_id].get("frozen_balance", 0) - amount)
        await save_users(users)
        return False, "❌ Ошибка: лот не найден!"
    
    old_bidder = all_lots[real_index].get("current_bidder")
    old_bid = all_lots[real_index].get("current_bid", 0)
    if old_bidder and old_bid > 0:
        if old_bidder in users:
            users[old_bidder]["money"] += old_bid
            users[old_bidder]["frozen_balance"] = max(0, users[old_bidder].get("frozen_balance", 0) - old_bid)
            await save_users(users)
        try:
            await bot.send_message(
                int(old_bidder),
                f"🔄 Вашу ставку на {all_lots[real_index]['car_name']} перебили!\n"
                f"💸 Ваши {old_bid:,}₽ разморожены и возвращены на баланс."
            )
        except Exception as e:
            logger.warning(f"Не удалось уведомить пользователя {old_bidder}: {e}")
    
    all_lots[real_index]["current_bid"] = amount
    all_lots[real_index]["current_bidder"] = user_id
    all_lots[real_index]["last_bid_time"] = datetime.now().isoformat()
    
    await save_auction_data(data)
    await start_auction_timer(real_index)
    
    users = await load_users()
    frozen_amount = users.get(user_id, {}).get("frozen_balance", 0)
    
    car_name = all_lots[real_index]["car_name"]
    
    response_message = (
        f"✅ Ваша ставка принята!\n\n"
        f"🚗 Лот: {car_name}\n"
        f"💰 Сумма ставки: {amount:,}₽\n"
        f"🔒 Заморожено на балансе: {frozen_amount:,}₽\n"
        f"💳 Доступный баланс: {users[user_id]['money']:,}₽\n\n"
        f"⏳ Ставка заморожена на время действия лота.\n"
        f"💰 Деньги спишутся, если вы выиграете лот.\n"
        f"🔄 Деньги разморозятся, если вас перебьют."
    )
    
    return True, response_message

async def refresh_auction_for_all():
    """Обновляет аукцион для всех пользователей"""
    await update_auction_lots(force=True)
    return True, "✅ Аукцион обновлён для всех пользователей!"

async def set_admin_auction_lots_with_slot(car_name: str, start_bid: int, count: int, slot: int) -> Tuple[bool, str]:
    """Устанавливает лоты от админа в конкретный слот"""
    if car_name not in AUCTION_CARS:
        return False, f"❌ Машина '{car_name}' не найдена!"
    
    car_data = AUCTION_CARS[car_name]
    
    new_lots = []
    for _ in range(count):
        new_lots.append({
            "car_name": car_name,
            "car_data": car_data,
            "start_bid": start_bid,
            "current_bid": start_bid,
            "current_bidder": None,
            "stars": car_data.get("stars", 1),
            "rarity": car_data.get("rarity", "Доступная"),
            "last_bid_time": datetime.now().isoformat(),
            "is_active": True,
            "sold": False,
            "added_by_admin": True
        })
    
    data = await load_auction_data()
    lots = data.get("lots", [])
    lots = [lot for lot in lots if not lot.get("sold", False)]
    
    slot_index = slot - 1
    
    if slot_index < len(lots):
        lots[slot_index:slot_index + len(new_lots)] = new_lots
    else:
        lots.extend(new_lots)
    
    lots = lots[:AUCTION_CONFIG["max_lots"]]
    
    data["lots"] = lots
    data["last_update"] = datetime.now().isoformat()
    await save_auction_data(data)
    
    return True, f"✅ Добавлено {count} шт. {car_name} на аукцион в слот {slot}! Стартовая ставка: {start_bid:,}₽"
