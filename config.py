import os
import asyncio
import logging
from datetime import datetime

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [5877790074, 1218587495]
CHANNEL_ID = "-1004461974511"
PROMO_CHANNEL_ID = "-1003853479476"

if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен в переменных окружения!")

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== ПУТИ К ФАЙЛАМ ==========
DATA_DIR = os.getenv('SHARED_DIR', '/app/shared')
if not os.path.exists(DATA_DIR):
    DATA_DIR = '.'

USERS_FILE = os.path.join(DATA_DIR, 'users_data.json')
PROMOCODES_FILE = os.path.join(DATA_DIR, 'promocodes.json')
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
BUSINESS_FILE = os.path.join(DATA_DIR, 'business.json')

os.makedirs(DATA_DIR, exist_ok=True)

# ========== ФАЙЛОВЫЕ БЛОКИРОВКИ ==========
file_locks = {
    'users': asyncio.Lock(),
    'promocodes': asyncio.Lock(),
    'inventory': asyncio.Lock(),
    'settings': asyncio.Lock(),
    'business': asyncio.Lock()
}

# ========== КОНСТАНТЫ ДЛЯ ШАХТЫ ==========
MINE_RESOURCES = [
    {"name": "Красный алмаз", "price": 50000000000, "chance": 0.0005},
    {"name": "Цветной алмаз", "price": 10000000000, "chance": 0.001},
    {"name": "Красная шпинель", "price": 5000000000, "chance": 0.004},
    {"name": "Александрит", "price": 2500000000, "chance": 0.007},
    {"name": "Рубин", "price": 1500000000, "chance": 0.015},
    {"name": "Падпараджа", "price": 750000000, "chance": 0.05},
    {"name": "Демантоид", "price": 150000000, "chance": 0.10},
    {"name": "Черный опал", "price": 10000000, "chance": 0.20},
    {"name": "Танзанит", "price": 5000000, "chance": 0.25},
    {"name": "Шпинель", "price": 1500000, "chance": 0.30}
]

FARM_RESOURCES = [
    {"name": "Молоко", "price": 8000000, "min": 1, "max": 5},
    {"name": "Сено", "price": 6000000, "min": 1, "max": 5},
    {"name": "Яйца", "price": 5000000, "min": 1, "max": 5},
    {"name": "Пшеница", "price": 3000000, "min": 1, "max": 5},
    {"name": "Мясо", "price": 10000000, "min": 1, "max": 3}
]

# ========== КОНСТАНТЫ ДЛЯ КОНТЕЙНЕРОВ ==========
CONTAINERS = {
    "Особый контейнер": {
        "price": 240000000,
        "items": [
            {"name": "BMW M5 CS", "price": 150000000, "chance": 0.34},
            {"name": "BUGATTI BOLIDE", "price": 555000000, "chance": 0.25},
            {"name": "SSG 003", "price": 1500000000, "chance": 0.10},
            {"name": "Zaz 968", "price": 10000, "chance": 0.70},
            {"name": "Rolls Royce Cullinan", "price": 100000000, "chance": 0.50}
        ]
    },
    "Дипломатический контейнер": {
        "price": 1500000000,
        "items": [
            {"name": "Bugatti La Voiture Noire", "price": 2000000000, "chance": 0.17},
            {"name": "Bugatti Centodieci", "price": 1500000000, "chance": 0.23},
            {"name": "Pagani Zonda", "price": 1300000000, "chance": 0.20},
            {"name": "Ford Explorer (ФСБ)", "price": 2500000000, "chance": 0.085},
            {"name": "Bugatti Divo", "price": 1000000000, "chance": 0.16},
            {"name": "Nissan 240NSX", "price": 700000000, "chance": 0.15},
            {"name": "Труповоз", "price": 5000000000, "chance": 0.005}
        ]
    },
    "Мегафон": {
        "price": 75000000,
        "items": [
            {"name": "BMW M5 CS", "price": 150000000, "chance": 0.01},
            {"name": "BMW M1", "price": 75000000, "chance": 0.30},
            {"name": "Rolls-Royce Phantom", "price": 50000000, "chance": 0.25},
            {"name": "Bentley Continental GT", "price": 55000000, "chance": 0.26},
            {"name": "Bentley Mulliner Bacalar", "price": 125000000, "chance": 0.02},
            {"name": "BMW M5 F90 (ППС)", "price": 90000000, "chance": 0.10},
            {"name": "Ocean Yacht", "price": 100000000, "chance": 0.06}
        ]
    },
    "Американский контейнер": {
        "price": 500000000,
        "items": [
            {"name": "Lamborghini Centenario", "price": 400000000, "chance": 0.23},
            {"name": "Audi R8 LMS GT2", "price": 500000000, "chance": 0.18},
            {"name": "Hot-Road F132", "price": 600000000, "chance": 0.19},
            {"name": "Koenigsegg Sadair's Spear", "price": 350000000, "chance": 0.17},
            {"name": "Bugatti Chiron", "price": 210000000, "chance": 0.16},
            {"name": "Marussia B2", "price": 2000000000, "chance": 0.003},
            {"name": "Nissan 240SX", "price": 700000000, "chance": 0.067}
        ]
    },
    "Базовый контейнер": {
        "price": 3000000,
        "items": [
            {"name": "UAZ Patriot", "price": 1200000, "chance": 0.15},
            {"name": "Toyota Camry 3.5", "price": 2000000, "chance": 0.20},
            {"name": "Ford Mustang GT", "price": 2000000, "chance": 0.20},
            {"name": "Land Rover Range Rover III", "price": 3200000, "chance": 0.23},
            {"name": "Volvo XC90", "price": 4200000, "chance": 0.09},
            {"name": "BMW 3-Series G20", "price": 4000000, "chance": 0.10},
            {"name": "BMW M5 F90", "price": 9500000, "chance": 0.03}
        ]
    }
}

# ========== КОНСТАНТЫ ДЛЯ БИЗНЕСА ==========
BUSINESS_CONFIG = {
    "auto_mine": {
        "name": "Авто-Шахта",
        "price": 30000000000,
        "max_owners": 2,
        "emoji": "⛏️",
        "profit_type": "resources",
        "resources": [
            {"name": "Красный алмаз", "chance": 0.05},
            {"name": "Цветной алмаз", "chance": 0.08},
            {"name": "Рубин", "chance": 0.15},
            {"name": "Александрит", "chance": 0.10},
            {"name": "Падпараджа", "chance": 0.12},
            {"name": "Демантоид", "chance": 0.15},
            {"name": "Черный опал", "chance": 0.20},
            {"name": "Танзанит", "chance": 0.25},
            {"name": "Шпинель", "chance": 0.30}
        ],
        "min_resources": 1,
        "max_resources": 3,
        "cooldown": 600
    },
    "tech_center": {
        "name": "Технический центр",
        "price": 20000000000,
        "max_owners": 5,
        "emoji": "🔧",
        "profit_type": "money",
        "profit_min": 100000000,
        "profit_max": 350000000,
        "cooldown": 12600
    },
    "tire_center": {
        "name": "Шиномонтажный центр",
        "price": 15000000000,
        "max_owners": 5,
        "emoji": "🛞",
        "profit_type": "money",
        "profit_min": 75000000,
        "profit_max": 150000000,
        "cooldown": 9000
    },
    "styling_center": {
        "name": "Стайлинг центр",
        "price": 15000000000,
        "max_owners": 5,
        "emoji": "🎨",
        "profit_type": "money",
        "profit_min": 75000000,
        "profit_max": 150000000,
        "cooldown": 9000
    },
    "shop_24": {
        "name": "Магазин 24/7",
        "price": 1000000000,
        "max_owners": 20,
        "emoji": "🏪",
        "profit_type": "money",
        "profit_min": 30000000,
        "profit_max": 70000000,
        "cooldown": 3600
    }
}

logger.info(f"📁 Данные хранятся в: {DATA_DIR}")
logger.info(f"👑 Админы: {ADMIN_IDS}")
