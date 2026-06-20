import json
import asyncio
import os

DATA_DIR = '/app/shared' if os.path.exists('/app/shared') else '.'

file_locks = {
    'users': asyncio.Lock(),
    'promocodes': asyncio.Lock(),
    'inventory': asyncio.Lock(),
    'settings': asyncio.Lock(),
    'business': asyncio.Lock()
}

USERS_FILE = os.path.join(DATA_DIR, 'users_data.json')
PROMOCODES_FILE = os.path.join(DATA_DIR, 'promocodes.json')
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
BUSINESS_FILE = os.path.join(DATA_DIR, 'business.json')

async def load_users():
    async with file_locks['users']:
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки users: {e}")
        return {}

async def save_users(users):
    async with file_locks['users']:
        try:
            os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения users: {e}")

async def load_promocodes():
    async with file_locks['promocodes']:
        try:
            if os.path.exists(PROMOCODES_FILE):
                with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки promocodes: {e}")
        return {}

async def save_promocodes(promocodes):
    async with file_locks['promocodes']:
        try:
            os.makedirs(os.path.dirname(PROMOCODES_FILE), exist_ok=True)
            with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
                json.dump(promocodes, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения promocodes: {e}")

async def load_inventory():
    async with file_locks['inventory']:
        try:
            if os.path.exists(INVENTORY_FILE):
                with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки inventory: {e}")
        return {}

async def save_inventory(inventory):
    async with file_locks['inventory']:
        try:
            os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)
            with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(inventory, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения inventory: {e}")

async def load_settings():
    async with file_locks['settings']:
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки settings: {e}")
        return {"bot_enabled": True, "promo_auto": False}

async def save_settings(settings):
    async with file_locks['settings']:
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения settings: {e}")

async def load_business():
    async with file_locks['business']:
        try:
            if os.path.exists(BUSINESS_FILE):
                with open(BUSINESS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки business: {e}")
        return {}

async def save_business(business):
    async with file_locks['business']:
        try:
            os.makedirs(os.path.dirname(BUSINESS_FILE), exist_ok=True)
            with open(BUSINESS_FILE, 'w', encoding='utf-8') as f:
                json.dump(business, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения business: {e}")
