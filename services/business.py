import random
from datetime import datetime
from typing import Dict, Tuple

from config import BUSINESS_CONFIG, MINE_RESOURCES, logger
from database.file_manager import (
    load_users, save_users, load_business, save_business, 
    load_inventory, save_inventory
)

async def get_auto_mine_resource() -> str:
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

async def collect_business(user_id: str) -> Tuple[Dict, str]:
    """
    Собирает доход со всех бизнесов пользователя
    Возвращает: (обновленный пользователь, сообщение для вывода)
    """
    users = await load_users()
    user = users.get(user_id, {})
    business_data = await load_business()
    inventory = await load_inventory()
    
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
        
        if not config:
            continue
        
        if elapsed >= config["cooldown"]:
            if config["profit_type"] == "money":
                profit = random.randint(config["profit_min"], config["profit_max"])
                user["money"] = user.get("money", 0) + profit
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
    
    # Сохраняем изменения
    users[user_id] = user
    await save_users(users)
    await save_business(business_data)
    await save_inventory(inventory)
    
    # Формируем сообщение
    if not collected:
        return user, "❌ Нет готовых бизнесов для сбора!"
    
    message = "✅ Собраны доходы:\n\n"
    message += "\n".join(collected)
    
    if total_money > 0:
        message += f"\n\n💰 Всего денег: +{total_money:,.0f}₽"
    
    if resources_collected:
        resource_counts = {}
        for res in resources_collected:
            resource_counts[res] = resource_counts.get(res, 0) + 1
        
        message += f"\n💎 Всего ресурсов: +{len(resources_collected)} шт."
        message += "\n\n📦 Получены ресурсы:"
        for res_name, count in resource_counts.items():
            price = 0
            for r in MINE_RESOURCES:
                if r["name"] == res_name:
                    price = r["price"]
                    break
            message += f"\n   • {res_name}: {count} шт. (цена: {price:,.0f}₽ за шт.)"
    
    message += f"\n\n💳 Новый баланс: {user['money']:,.0f}₽"
    
    if resources_collected:
        message += "\n\n📦 Ресурсы добавлены в инвентарь!"
    
    return user, message

async def get_business_status(user_id: str) -> Dict:
    """
    Получает статус всех бизнесов пользователя
    """
    users = await load_users()
    user = users.get(user_id, {})
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
                "auto_collect": auto_collect,
                "name": config["name"],
                "emoji": config["emoji"]
            }
        elif owned:
            status[key] = {
                "owned": True,
                "ready": False,
                "remaining": "Неизвестно",
                "last_collect": last_collect,
                "auto_collect": auto_collect,
                "name": config["name"],
                "emoji": config["emoji"]
            }
        else:
            status[key] = {
                "owned": False,
                "ready": False,
                "remaining": "Не куплен",
                "auto_collect": False,
                "name": config["name"],
                "emoji": config["emoji"]
            }
    
    return status

async def get_user_business_count(user_id: str) -> int:
    """
    Получает количество бизнесов у пользователя
    """
    users = await load_users()
    user = users.get(user_id, {})
    return sum(1 for biz in user.get("business", {}).values() if biz.get("owned", False))

async def sell_business(user_id: str, business_key: str) -> Tuple[bool, str, int]:
    """
    Продает бизнес пользователя
    Возвращает: (успех, сообщение, цена продажи)
    """
    users = await load_users()
    user = users.get(user_id, {})
    business_data = await load_business()
    
    if business_key not in user.get("business", {}):
        return False, "❌ У вас нет этого бизнеса!", 0
    
    biz_data = user["business"][business_key]
    if not biz_data.get("owned", False):
        return False, "❌ У вас нет этого бизнеса!", 0
    
    config = BUSINESS_CONFIG.get(business_key)
    if not config:
        return False, "❌ Бизнес не найден!", 0
    
    sell_price = int(config["price"] * 0.5)
    
    # Удаляем бизнес у пользователя
    user["business"][business_key]["owned"] = False
    user["business"][business_key]["last_collect"] = None
    user["business"][business_key]["auto_collect"] = False
    
    # Удаляем из владельцев в бизнес-данных
    if business_key in business_data:
        if user_id in business_data[business_key].get("owners", []):
            business_data[business_key]["owners"].remove(user_id)
    
    user["money"] = user.get("money", 0) + sell_price
    user["total_earned"] = user.get("total_earned", 0) + sell_price
    
    users[user_id] = user
    await save_users(users)
    await save_business(business_data)
    
    return True, f"✅ Бизнес {config['emoji']} {config['name']} продан за {sell_price:,.0f}₽!", sell_price

async def buy_business(user_id: str, business_key: str) -> Tuple[bool, str]:
    """
    Покупает бизнес пользователю
    Возвращает: (успех, сообщение)
    """
    users = await load_users()
    user = users.get(user_id, {})
    business_data = await load_business()
    
    config = BUSINESS_CONFIG.get(business_key)
    if not config:
        return False, "❌ Бизнес не найден!"
    
    # Проверяем количество бизнесов
    user_business_count = await get_user_business_count(user_id)
    if user_business_count >= 1:
        return False, "❌ У вас уже есть 1 бизнес! (максимум 1)"
    
    # Проверяем свободные места
    owners = business_data.get(business_key, {}).get("owners", [])
    if len(owners) >= config["max_owners"]:
        return False, "❌ Все места заняты!"
    
    if user_id in owners:
        return False, "❌ Вы уже владеете этим бизнесом!"
    
    if user.get("money", 0) < config["price"]:
        return False, f"❌ Недостаточно средств! Нужно {config['price']:,.0f}₽"
    
    # Покупаем бизнес
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
    
    return True, f"✅ Вы купили {config['emoji']} {config['name']} за {config['price']:,.0f}₽!"

async def toggle_auto_collect(user_id: str, business_key: str) -> Tuple[bool, str, bool]:
    """
    Включает/выключает авто-сбор бизнеса
    Возвращает: (успех, сообщение, новый статус)
    """
    users = await load_users()
    user = users.get(user_id, {})
    
    config = BUSINESS_CONFIG.get(business_key)
    if not config:
        return False, "❌ Бизнес не найден!", False
    
    if business_key not in user.get("business", {}):
        return False, "❌ У вас нет этого бизнеса!", False
    
    biz_data = user["business"][business_key]
    if not biz_data.get("owned", False):
        return False, "❌ У вас нет этого бизнеса!", False
    
    current_status = biz_data.get("auto_collect", False)
    new_status = not current_status
    user["business"][business_key]["auto_collect"] = new_status
    
    users[user_id] = user
    await save_users(users)
    
    status_text = "включен" if new_status else "выключен"
    return True, f"✅ Авто-сбор для {config['name']} {status_text}!", new_status
