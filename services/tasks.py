import asyncio
import random
import string
from datetime import datetime

from database.file_manager import (
    load_users,
    save_users,
    load_settings,
    save_settings,
    load_business,
    save_business,
    load_inventory,
    save_inventory,
    load_promocodes,
    save_promocodes
)
from config import PROMO_CHANNEL_ID, bot, logger, BUSINESS_CONFIG

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
            "used_by": [],  # ← ДОБАВЛЕНО!
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

# ========== БИЗНЕС (АВТО-СБОР) ==========
async def get_auto_mine_resource():
    """Получает случайный ресурс для авто-шахты"""
    resources = BUSINESS_CONFIG["auto_mine"]["resources"]
    total_chance = sum(r["chance"] for r in resources)
    roll = random.random() * total_chance
    cumulative = 0
    for res in resources:
        cumulative += res["chance"]
        if roll <= cumulative:
            return res["name"]
    return random.choice(resources)["name"]

async def collect_business_for_user(user_id, biz_key, config, data, business, inventory):
    """Собирает доход для одного бизнеса"""
    users_updated = False
    business_updated = False
    inventory_updated = False
    
    try:
        if config.get("profit_type") == "money":
            profit = random.randint(config.get("profit_min", 0), config.get("profit_max", 0))
            data["money"] = data.get("money", 0) + profit
            data["total_earned"] = data.get("total_earned", 0) + profit
            users_updated = True
            
            if biz_key in business:
                business[biz_key]["total_earned"] = business[biz_key].get("total_earned", 0) + profit
                business_updated = True
            
            try:
                await bot.send_message(
                    int(user_id),
                    f"🏢 {config.get('emoji', '')} {config.get('name', biz_key)}\n"
                    f"💰 Авто-сбор: +{profit:,.0f}₽"
                )
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление {user_id}: {e}")
        
        elif config.get("profit_type") == "resources":
            if user_id not in inventory:
                inventory[user_id] = []
            
            if not isinstance(inventory[user_id], list):
                logger.warning(f"⚠️ Инвентарь пользователя {user_id} не список, создаём новый")
                inventory[user_id] = []
            
            num_resources = random.randint(config.get("min_resources", 1), config.get("max_resources", 3))
            resources_text = []
            resources_list = config.get("resources", [])
            
            for _ in range(num_resources):
                if resources_list:
                    total_chance = sum(r.get("chance", 0) for r in resources_list)
                    roll = random.random() * total_chance if total_chance > 0 else 0
                    cumulative = 0
                    selected_resource = resources_list[0]["name"] if resources_list else "Рубин"
                    
                    for res in resources_list:
                        cumulative += res.get("chance", 0)
                        if roll <= cumulative:
                            selected_resource = res["name"]
                            break
                    
                    inventory[user_id].append(selected_resource)
                    resources_text.append(selected_resource)
                    inventory_updated = True
            
            if biz_key in business:
                business[biz_key]["total_earned"] = business[biz_key].get("total_earned", 0) + num_resources
                business_updated = True
            
            try:
                resource_counts = {}
                for res in resources_text:
                    resource_counts[res] = resource_counts.get(res, 0) + 1
                
                text = f"🏢 {config.get('emoji', '')} {config.get('name', biz_key)}\n"
                text += f"📦 Авто-сбор: +{num_resources} ресурсов\n"
                for res_name, count in resource_counts.items():
                    text += f"   • {res_name}: {count} шт.\n"
                text += f"\n📦 Ресурсы сохранены в инвентаре!"
                
                await bot.send_message(int(user_id), text)
                logger.info(f"✅ Авто-сбор для {user_id}: +{num_resources} ресурсов")
            except Exception as e:
                logger.warning(f"Не удалось отправить уведомление {user_id}: {e}")
        
        # Обновляем время
        if "business" not in data:
            data["business"] = {}
        if biz_key not in data["business"]:
            data["business"][biz_key] = {}
        data["business"][biz_key]["last_collect"] = datetime.now().isoformat()
        users_updated = True
        
    except Exception as e:
        logger.error(f"❌ Ошибка в collect_business_for_user: {e}")
        return False, False, False
    
    return users_updated, business_updated, inventory_updated

async def check_business_loop():
    """Цикл автоматического сбора бизнесов"""
    global business_running
    
    logger.info("🔄 CHECK BUSINESS LOOP STARTED!")
    
    while business_running:
        logger.info("🔄 Business loop tick...")
        
        try:
            business = await load_business()
            users = await load_users()
            inventory = await load_inventory()
            
            if not isinstance(users, dict):
                logger.error("❌ users не словарь, пропускаем")
                await asyncio.sleep(10)
                continue
            
            if not isinstance(business, dict):
                logger.error("❌ business не словарь, пропускаем")
                await asyncio.sleep(10)
                continue
            
            if not isinstance(inventory, dict):
                logger.error("❌ inventory не словарь, создаём новый")
                inventory = {}
            
            users_updated = False
            business_updated = False
            inventory_updated = False
            
            logger.info(f"📊 Проверка {len(users)} пользователей...")
            
            for user_id, data in users.items():
                if not isinstance(data, dict):
                    continue
                
                user_business = data.get("business", {})
                if not isinstance(user_business, dict):
                    continue
                
                for biz_key, biz_data in user_business.items():
                    if not isinstance(biz_data, dict):
                        continue
                    
                    if biz_data.get("owned", False) and biz_data.get("auto_collect", False):
                        config = BUSINESS_CONFIG.get(biz_key)
                        
                        if not config:
                            logger.warning(f"⚠️ Бизнес {biz_key} не найден в BUSINESS_CONFIG")
                            continue
                        
                        last_collect = biz_data.get("last_collect")
                        
                        if not last_collect:
                            logger.info(f"🆕 Новый бизнес {biz_key} у {user_id}, собираем сразу")
                            biz_data["last_collect"] = datetime.now().isoformat()
                            user_business[biz_key]["last_collect"] = datetime.now().isoformat()
                            users_updated = True
                            u, b, i = await collect_business_for_user(user_id, biz_key, config, data, business, inventory)
                            users_updated = users_updated or u
                            business_updated = business_updated or b
                            inventory_updated = inventory_updated or i
                            continue
                        
                        try:
                            last_time = datetime.fromisoformat(last_collect)
                            elapsed = (datetime.now() - last_time).total_seconds()
                            cooldown = config.get("cooldown", 600)
                            
                            if elapsed >= cooldown:
                                logger.info(f"⏰ Сбор бизнеса {biz_key} у {user_id} (прошло {elapsed:.0f} сек)")
                                u, b, i = await collect_business_for_user(user_id, biz_key, config, data, business, inventory)
                                users_updated = users_updated or u
                                business_updated = business_updated or b
                                inventory_updated = inventory_updated or i
                        except ValueError:
                            logger.error(f"❌ Неверный формат last_collect у {user_id}: {last_collect}")
                            continue
            
            if users_updated:
                await save_users(users)
                logger.info("💾 Сохранены изменения пользователей")
            if business_updated:
                await save_business(business)
                logger.info("💾 Сохранены изменения бизнесов")
            if inventory_updated:
                await save_inventory(inventory)
                logger.info("💾 Сохранены изменения инвентаря")
            
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле проверки бизнеса: {e}")
            await asyncio.sleep(30)
