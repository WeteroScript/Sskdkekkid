import asyncio
import random
import string
from datetime import datetime
from database.file_manager import (
    load_users, load_settings, save_settings, 
    load_business, save_business, 
    load_inventory, save_inventory, 
    load_promocodes, save_promocodes,
    load_auction, save_auction
)
from config import PROMO_CHANNEL_ID, bot, logger, BUSINESS_CONFIG, AUCTION_CARS

promo_running = False
promo_task = None
business_running = False
business_check_task = None
business_notified = {}

# ========== ПРОМОКОДЫ ==========
async def generate_and_send_promo():
    try:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        is_brcoins = random.choice([True, False])
        
        if is_brcoins:
            amount = random.randint(100, 1000)
            uses = random.randint(1, 3)
            promo_type = "brcoins"
            type_text = "BRcoins"
        else:
            amount = random.randint(20000000, 100000000)
            uses = random.randint(3, 5)
            promo_type = "money"
            type_text = "₽"
        
        promocodes = await load_promocodes()
        promocodes[code] = {
            "type": promo_type,
            "uses": uses,
            "used": 0,
            "amount": amount
        }
        await save_promocodes(promocodes)
        
        message_text = (
            f"🎁 **Новый промокод!**\n\n"
            f"📌 Код: `{code}`\n"
            f"🎁 Награда: {amount:,} {type_text}\n"
            f"🔄 Активаций: {uses}\n\n"
            f"👉 Забирай быстрее!"
        )
        await bot.send_message(
            PROMO_CHANNEL_ID,
            message_text,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Промокод отправлен: {code}")
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации промокода: {e}")

async def promo_auto_loop():
    global promo_running
    while promo_running:
        try:
            settings = await load_settings()
            if settings.get("promo_auto", False):
                await generate_and_send_promo()
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле промокодов: {e}")
        await asyncio.sleep(5400)

# ========== БИЗНЕС ==========
async def check_business_loop():
    global business_running, business_notified
    while business_running:
        try:
            business = await load_business()
            users = await load_users()
            
            for user_id, data in users.items():
                user_business = data.get("business", {})
                notified_biz = business_notified.get(user_id, [])
                
                for biz_key, biz_data in user_business.items():
                    if biz_data.get("owned", False):
                        last_collect = biz_data.get("last_collect")
                        if last_collect:
                            last_time = datetime.fromisoformat(last_collect)
                            elapsed = (datetime.now() - last_time).total_seconds()
                            cooldown = BUSINESS_CONFIG[biz_key]["cooldown"]
                            
                            if elapsed >= cooldown and not biz_data.get("auto_collect", False):
                                if biz_key not in notified_biz:
                                    try:
                                        config = BUSINESS_CONFIG[biz_key]
                                        await bot.send_message(
                                            int(user_id),
                                            f"🏢 {config['emoji']} {config['name']} готов к сбору дохода!\n"
                                            f"Нажмите /start и зайдите в раздел Бизнес"
                                        )
                                        if user_id not in business_notified:
                                            business_notified[user_id] = []
                                        business_notified[user_id].append(biz_key)
                                    except Exception as e:
                                        logger.warning(f"Не удалось уведомить пользователя {user_id}: {e}")
                            else:
                                if biz_key in notified_biz:
                                    business_notified[user_id].remove(biz_key)
            
            business_notified = {k: v for k, v in business_notified.items() if v}
            
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле проверки бизнеса: {e}")
        await asyncio.sleep(60)

# ========== АУКЦИОН ==========
async def auction_loop():
    """Обновление аукциона каждые 30 минут"""
    while True:
        try:
            await update_auction()
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле аукциона: {e}")
        await asyncio.sleep(1800)

async def update_auction():
    """Обновляет список машин на аукционе"""
    try:
        auction = await load_auction()
        
        all_cars = list(AUCTION_CARS.keys())
        selected_cars = []
        
        available_cars = all_cars.copy()
        for _ in range(min(15, len(available_cars))):
            total_chance = sum(AUCTION_CARS[car]["chance"] for car in available_cars)
            roll = random.random() * total_chance
            cumulative = 0
            selected = None
            
            for car in available_cars:
                cumulative += AUCTION_CARS[car]["chance"]
                if roll <= cumulative:
                    selected = car
                    break
            
            if selected:
                selected_cars.append(selected)
                available_cars.remove(selected)
        
        lots = []
        for i, car_name in enumerate(selected_cars):
            car_data = AUCTION_CARS[car_name]
            start_price = int(car_data["base_price"] * 0.5)
            lots.append({
                "id": f"lot_{i+1}",
                "car_name": car_name,
                "stars": car_data["stars"],
                "rarity": car_data["rarity"],
                "base_price": car_data["base_price"],
                "start_price": start_price,
                "current_bid": start_price,
                "highest_bidder": None,
                "time_left": 15,
                "active": True
            })
        
        auction["lots"] = lots
        auction["last_update"] = datetime.now().isoformat()
        await save_auction(auction)
        logger.info(f"🔄 Аукцион обновлен: {len(lots)} лотов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении аукциона: {e}")
        raise

async def check_auction_bids():
    """Проверяет ставки каждую минуту"""
    while True:
        try:
            auction = await load_auction()
            users = await load_users()
            updated = False
            
            for lot in auction.get("lots", []):
                if not lot.get("active", True):
                    continue
                
                lot["time_left"] -= 1
                
                if lot["time_left"] <= 0 and lot.get("highest_bidder"):
                    bidder_id = lot["highest_bidder"]
                    if bidder_id in users:
                        if "inventory" not in users[bidder_id]:
                            users[bidder_id]["inventory"] = []
                        
                        users[bidder_id]["inventory"].append({
                            "name": lot["car_name"],
                            "price": lot["base_price"],
                            "from_auction": True
                        })
                        
                        users[bidder_id]["money"] -= lot["current_bid"]
                        await save_users(users)
                        
                        try:
                            await bot.send_message(
                                int(bidder_id),
                                f"🎉 Вы выиграли аукцион!\n"
                                f"🚗 {lot['car_name']}\n"
                                f"💰 Ставка: {lot['current_bid']:,.0f}₽\n"
                                f"⭐ Редкость: {'⭐' * lot['stars']} ({lot['rarity']})"
                            )
                        except Exception as e:
                            logger.warning(f"Не удалось уведомить {bidder_id}: {e}")
                    
                    lot["active"] = False
                    updated = True
            
            if updated:
                await save_auction(auction)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в check_auction_bids: {e}")
        
        await asyncio.sleep(60)
