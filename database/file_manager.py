import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from config import (
    USERS_FILE, BUSINESS_FILE, AUCTION_FILE, 
    SETTINGS_FILE, PROMOCODES_FILE, INVENTORY_FILE,
    DISABLED_FUNCTIONS_FILE, CARS_FILE, logger
)

# ========== БЛОКИРОВКИ ==========
_file_locks = {
    'users': asyncio.Lock(),
    'business': asyncio.Lock(),
    'auction': asyncio.Lock(),
    'settings': asyncio.Lock(),
    'promocodes': asyncio.Lock(),
    'inventory': asyncio.Lock(),
    'disabled': asyncio.Lock(),
    'cars': asyncio.Lock()
}

def get_file_path(file_type: str) -> str:
    """Возвращает путь к файлу по типу"""
    paths = {
        'users': USERS_FILE,
        'business': BUSINESS_FILE,
        'auction': AUCTION_FILE,
        'settings': SETTINGS_FILE,
        'promocodes': PROMOCODES_FILE,
        'inventory': INVENTORY_FILE,
        'disabled': DISABLED_FUNCTIONS_FILE,
        'cars': CARS_FILE
    }
    return paths.get(file_type)

async def load_json(file_type: str, default: Any = None) -> Any:
    """Универсальная загрузка JSON"""
    file_path = get_file_path(file_type)
    if not file_path:
        return default or {}
    
    async with _file_locks[file_type]:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки {file_type}: {e}")
        return default or {}

async def save_json(file_type: str, data: Any):
    """Универсальное сохранение JSON"""
    file_path = get_file_path(file_type)
    if not file_path:
        return
    
    async with _file_locks[file_type]:
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения {file_type}: {e}")

# ==========================================
# ===== СПЕЦИАЛИЗИРОВАННЫЕ ФУНКЦИИ =====
# ==========================================

async def load_users() -> Dict:
    return await load_json('users', {})

async def save_users(users: Dict):
    await save_json('users', users)

async def load_business() -> Dict:
    return await load_json('business', {})

async def save_business(business: Dict):
    await save_json('business', business)

async def load_auction_data() -> Dict:
    return await load_json('auction', {"lots": [], "last_update": None})

async def save_auction_data(data: Dict):
    await save_json('auction', data)

async def load_settings() -> Dict:
    return await load_json('settings', {
        "bot_enabled": True,
        "promo_auto": False,
        "coinrun_enabled": False,
        "coinrun_total": 0
    })

async def save_settings(settings: Dict):
    await save_json('settings', settings)

async def load_promocodes() -> Dict:
    return await load_json('promocodes', {})

async def save_promocodes(promocodes: Dict):
    await save_json('promocodes', promocodes)

async def load_inventory() -> Dict:
    return await load_json('inventory', {})

async def save_inventory(inventory: Dict):
    await save_json('inventory', inventory)

async def load_disabled_functions() -> Dict:
    return await load_json('disabled', {"functions": []})

async def save_disabled_functions(disabled: Dict):
    await save_json('disabled', disabled)

async def get_active_lots() -> List[Dict]:
    """Активные лоты аукциона"""
    data = await load_auction_data()
    return [
        lot for lot in data.get("lots", [])
        if lot.get("is_active", True) and not lot.get("sold", False)
    ]

async def get_lot_by_index(index: int) -> Optional[Dict]:
    """Возвращает лот по индексу"""
    lots = await get_active_lots()
    if 0 <= index < len(lots):
        return lots[index]
    return None

async def update_lot_status(lot_index: int, sold: bool = True):
    """Обновляет статус лота"""
    data = await load_auction_data()
    lots = data.get("lots", [])
    if 0 <= lot_index < len(lots):
        lots[lot_index]["sold"] = sold
        lots[lot_index]["is_active"] = not sold
        await save_auction_data(data)
        return True
    return False

async def set_auction_lots(lots: List[Dict]):
    """Устанавливает список лотов (для админов)"""
    data = await load_auction_data()
    data["lots"] = lots
    data["last_update"] = datetime.now().isoformat()
    await save_auction_data(data)


# ==========================================
# ===== МАШИНЫ (CARS) =====
# ==========================================

async def load_cars() -> Dict:
    """Загружает машины пользователей"""
    return await load_json('cars', {})

async def save_cars(cars: Dict):
    await save_json('cars', cars)

async def get_user_cars(user_id: str) -> list:
    """Получает машины пользователя"""
    cars = await load_cars()
    return cars.get(user_id, [])

async def add_user_car(user_id: str, car: Dict):
    """Добавляет машину пользователю"""
    cars = await load_cars()
    if user_id not in cars:
        cars[user_id] = []
    cars[user_id].append(car)
    await save_cars(cars)

async def remove_user_car(user_id: str, index: int) -> bool:
    """Удаляет машину пользователя по индексу"""
    cars = await load_cars()
    if user_id in cars and 0 <= index < len(cars[user_id]):
        del cars[user_id][index]
        await save_cars(cars)
        return True
    return False

async def get_user_cars_count(user_id: str) -> int:
    """Получает количество машин пользователя"""
    cars = await get_user_cars(user_id)
    return len(cars)
