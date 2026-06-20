import json
import asyncio
import os
from config import Config

class Database:
    def __init__(self):
        self.locks = {
            'users': asyncio.Lock(),
            'promocodes': asyncio.Lock(),
            'inventory': asyncio.Lock(),
            'settings': asyncio.Lock(),
            'business': asyncio.Lock()
        }
        os.makedirs(Config.DATA_DIR, exist_ok=True)
    
    async def load_json(self, filename, default=None):
        filepath = os.path.join(Config.DATA_DIR, filename)
        async with self.locks[filename.split('.')[0]]:
            try:
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except json.JSONDecodeError:
                # Создаем бэкап
                if os.path.exists(filepath):
                    os.rename(filepath, f"{filepath}.backup")
            except Exception as e:
                print(f"Ошибка загрузки {filename}: {e}")
            return default or {}
    
    async def save_json(self, filename, data):
        filepath = os.path.join(Config.DATA_DIR, filename)
        async with self.locks[filename.split('.')[0]]:
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                return True
            except Exception as e:
                print(f"Ошибка сохранения {filename}: {e}")
                return False

db = Database()

async def load_users():
    return await db.load_json('users_data.json', {})

async def save_users(data):
    return await db.save_json('users_data.json', data)

async def load_promocodes():
    return await db.load_json('promocodes.json', {})

async def save_promocodes(data):
    return await db.save_json('promocodes.json', data)

async def load_inventory():
    return await db.load_json('inventory.json', {})

async def save_inventory(data):
    return await db.save_json('inventory.json', data)

async def load_settings():
    return await db.load_json('settings.json', {"bot_enabled": True, "promo_auto": False})

async def save_settings(data):
    return await db.save_json('settings.json', data)

async def load_business():
    return await db.load_json('business.json', {})

async def save_business(data):
    return await db.save_json('business.json', data)
