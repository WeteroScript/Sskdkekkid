import json
import os
import asyncio
from typing import Dict, Any, Optional
from config import (
    USERS_FILE, BUSINESS_FILE, AUCTION_FILE, 
    SETTINGS_FILE, PROMOCODES_FILE, INVENTORY_FILE,
    DISABLED_FUNCTIONS_FILE, logger
)

# ========== БЛОКИРОВКИ ==========
_file_locks = {
    'users': asyncio.Lock(),
    'business': asyncio.Lock(),
    'auction': asyncio.Lock(),
    'settings': asyncio.Lock(),
    'promocodes': asyncio.Lock(),
    'inventory': asyncio.Lock(),
    'disabled': asyncio.Lock()
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
        'disabled': DISABLED_FUNCTIONS_FILE
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

# ========== СПЕЦИАЛИЗИРОВАННЫЕ ФУНКЦИИ ==========

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

async def get_active_lots() -> list:
    """Активные лоты аукциона"""
    data = await load_auction_data()
    return [
        lot for lot in data.get("lots", [])
        if lot.get("is_active", True) and not lot.get("sold", False)
    ]
