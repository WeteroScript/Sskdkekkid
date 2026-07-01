import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== ТОКЕН ==========
API_TOKEN = os.getenv('BOT_TOKEN')
if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен!")

# ========== БОТ ==========
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== АДМИНЫ ==========
ADMIN_IDS = [5877790074, 1218587495]

# ========== ПУТИ ==========
DATA_DIR = os.getenv('SHARED_DIR', '/app/shared')
if not os.path.exists(DATA_DIR):
    DATA_DIR = '.'

os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, 'users_data.json')
BUSINESS_FILE = os.path.join(DATA_DIR, 'business.json')
AUCTION_FILE = os.path.join(DATA_DIR, 'auction.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
PROMOCODES_FILE = os.path.join(DATA_DIR, 'promocodes.json')
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory.json')
DISABLED_FUNCTIONS_FILE = os.path.join(DATA_DIR, 'disabled_functions.json')
CARS_FILE = os.path.join(DATA_DIR, 'cars.json')

# ========== КОНСТАНТЫ ==========
CHANNEL_ID = "-1004461974511"
PROMO_CHANNEL_ID = "-1003853479476"

# ==========================================
# ===== РЕСУРСЫ =====
# ==========================================

# ========== РЕСУРСЫ ДЛЯ ШАХТЫ (ОБЫЧНАЯ) ==========
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

# ========== РЕСУРСЫ ДЛЯ РЫБАЛКИ ==========
FISH_RESOURCES = [
    # Галактические рыбы
    {"name": "Квантовый тунец", "price": 5000000},
    {"name": "Звёздный скат", "price": 15000000},
    {"name": "Чёрная дыра-рыба", "price": 50000000},
    {"name": "Планетарная камбала", "price": 100000000},
    {"name": "Комета-окунь", "price": 150000000},
    {"name": "Астероидная сельдь", "price": 350000000},
    {"name": "Гравитационный сом", "price": 750000000},
    {"name": "Тёмный угорь", "price": 1500000000},
    {"name": "Космический ёрш", "price": 4500000000},
    {"name": "Пульсар-карась", "price": 6300000000},
    # Вулканические рыбы
    {"name": "Лавовый лосось", "price": 75000000},
    {"name": "Огненный карп", "price": 150000000},
    {"name": "Пепельная форель", "price": 250670670},
    {"name": "Магмовый сом", "price": 350000000},
    {"name": "Кратерный окунь", "price": 500000000},
    {"name": "Вулканическая щука", "price": 650000000},
    {"name": "Раскалённая плотва", "price": 666666666},
    {"name": "Серный судак", "price": 750000000},
    {"name": "Извергающий ёрш", "price": 1500000000},
    {"name": "Жар-карась", "price": 2500000000},
    # Легендарные рыбы
    {"name": "Королевский лосось", "price": 3500000},
    {"name": "Серебряный судак", "price": 5000000},
    {"name": "Бриллиантовая щука", "price": 7500000},
    {"name": "Нефритовый окунь", "price": 15000000},
    {"name": "Аметистовый сазан", "price": 750000000},
    {"name": "Рубиновый ёрш", "price": 1500000000},
    # Редкие рыбы
    {"name": "Жемчужный карась", "price": 1200000},
    {"name": "Золотистый ёрш", "price": 7500000},
    {"name": "Медный сом", "price": 15000000},
    {"name": "Стальной окунь", "price": 250000000},
    {"name": "Бирюзовый пескарь", "price": 500000000},
    # Базовые рыбы
    {"name": "Карась", "price": 300000},
    {"name": "Плотва", "price": 330000},
    {"name": "Окунь", "price": 350000},
    {"name": "Ёрш", "price": 450000},
    {"name": "Пескарь", "price": 500000},
    {"name": "Краснопёрка", "price": 1000000},
    {"name": "Линь", "price": 2500000},
    {"name": "Уклейка", "price": 3550000},
    {"name": "Густера", "price": 7500000},
    {"name": "Вьюн", "price": 150000000},
]

# ========== РЕСУРСЫ ДЛЯ АВТО-ШАХТЫ (ЦЕНЫ НА 40% НИЖЕ) ==========
AUTO_MINE_RESOURCES = [
    {"name": "Красный алмаз", "price": int(50000000000 * 0.6), "chance": 0.05},
    {"name": "Цветной алмаз", "price": int(10000000000 * 0.6), "chance": 0.08},
    {"name": "Красная шпинель", "price": int(5000000000 * 0.6), "chance": 0.04},
    {"name": "Александрит", "price": int(2500000000 * 0.6), "chance": 0.10},
    {"name": "Рубин", "price": int(1500000000 * 0.6), "chance": 0.15},
    {"name": "Падпараджа", "price": int(750000000 * 0.6), "chance": 0.12},
    {"name": "Демантоид", "price": int(150000000 * 0.6), "chance": 0.15},
    {"name": "Черный опал", "price": int(10000000 * 0.6), "chance": 0.20},
    {"name": "Танзанит", "price": int(5000000 * 0.6), "chance": 0.25},
    {"name": "Шпинель", "price": int(1500000 * 0.6), "chance": 0.30}
]

# ========== ВСЕ РЕСУРСЫ ДЛЯ СКУПЩИКА ==========
ALL_RESOURCES = MINE_RESOURCES + FISH_RESOURCES + AUTO_MINE_RESOURCES

# ==========================================
# ===== БИЗНЕС =====
# ==========================================

BUSINESS_CONFIG = {
    "auto_mine": {
        "name": "Авто-Шахта",
        "price": 50000000000,
        "max_owners": 4,
        "emoji": "⛏️",
        "profit_type": "resources",
        "resources": [
            {"name": "Красный алмаз", "chance": 0.05},
            {"name": "Цветной алмаз", "chance": 0.08},
            {"name": "Красная шпинель", "chance": 0.04},
            {"name": "Александрит", "chance": 0.10},
            {"name": "Рубин", "chance": 0.15},
            {"name": "Падпараджа", "chance": 0.12},
            {"name": "Демантоид", "chance": 0.15},
            {"name": "Черный опал", "chance": 0.20},
            {"name": "Танзанит", "chance": 0.25},
            {"name": "Шпинель", "chance": 0.30}
        ],
        "min_resources": 1,
        "max_resources": 4,
        "cooldown": 9000
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

# ==========================================
# ===== АУКЦИОН (125 МАШИН) =====
# ==========================================

AUCTION_CARS = {
    # ===== ★★★★★ ЭКЗОТИЧЕСКИЕ (8 шт) =====
    "RcCar": {"stars": 5, "rarity": "Экзотическая", "base_price": 5000000000, "chance": 0.005, "start_bid": 10000000},
    "Игрушечный вертолетик": {"stars": 5, "rarity": "Экзотическая", "base_price": 5000000000, "chance": 0.005, "start_bid": 10000000},
    "Лимузин": {"stars": 5, "rarity": "Экзотическая", "base_price": 120000000, "chance": 0.005, "start_bid": 10000000},
    "Монстр трак": {"stars": 5, "rarity": "Экзотическая", "base_price": 150000000, "chance": 0.005, "start_bid": 10000000},
    "БРДМ": {"stars": 5, "rarity": "Экзотическая", "base_price": 250000000, "chance": 0.005, "start_bid": 10000000},
    "Вертолёт": {"stars": 5, "rarity": "Экзотическая", "base_price": 450000000, "chance": 0.005, "start_bid": 10000000},
    "Танк": {"stars": 5, "rarity": "Экзотическая", "base_price": 1200000000000, "chance": 0.005, "start_bid": 10000000},
    "Истребитель": {"stars": 5, "rarity": "Экзотическая", "base_price": 3500000000000, "chance": 0.005, "start_bid": 10000000},
    
    # ===== ★★★★☆ ЛЕГЕНДАРНЫЕ (20 шт) =====
    "DeLorean DMC-12": {"stars": 4, "rarity": "Легендарная", "base_price": 250000000, "chance": 0.05, "start_bid": 200000000},
    "Zenvo ST1": {"stars": 4, "rarity": "Легендарная", "base_price": 400000000, "chance": 0.05, "start_bid": 200000000},
    "Koenigsegg CCX": {"stars": 4, "rarity": "Легендарная", "base_price": 450000000, "chance": 0.05, "start_bid": 200000000},
    "Jaguar E-Type Lightweight": {"stars": 4, "rarity": "Легендарная", "base_price": 450000000, "chance": 0.05, "start_bid": 200000000},
    "Ferrari 365 GTB/4 Daytona": {"stars": 4, "rarity": "Легендарная", "base_price": 500000000, "chance": 0.05, "start_bid": 200000000},
    "Porsche 959": {"stars": 4, "rarity": "Легендарная", "base_price": 550000000, "chance": 0.05, "start_bid": 200000000},
    "Aston Martin DB4 GT": {"stars": 4, "rarity": "Легендарная", "base_price": 550000000, "chance": 0.05, "start_bid": 200000000},
    "Shelby Cobra 427": {"stars": 4, "rarity": "Легендарная", "base_price": 550000000, "chance": 0.05, "start_bid": 200000000},
    "Lamborghini Miura": {"stars": 4, "rarity": "Легендарная", "base_price": 600000000, "chance": 0.05, "start_bid": 200000000},
    "Ford GT40": {"stars": 4, "rarity": "Легендарная", "base_price": 600000000, "chance": 0.05, "start_bid": 200000000},
    "Lamborghini Reventón": {"stars": 4, "rarity": "Легендарная", "base_price": 650000000, "chance": 0.05, "start_bid": 200000000},
    "McLaren F1 GTR": {"stars": 4, "rarity": "Легендарная", "base_price": 650000000, "chance": 0.05, "start_bid": 200000000},
    "Ferrari F40 Competizione": {"stars": 4, "rarity": "Легендарная", "base_price": 700000000, "chance": 0.05, "start_bid": 200000000},
    "Alfa Romeo 33 Stradale": {"stars": 4, "rarity": "Легендарная", "base_price": 700000000, "chance": 0.05, "start_bid": 200000000},
    "Bugatti Veyron Super Sport": {"stars": 4, "rarity": "Легендарная", "base_price": 750000000, "chance": 0.05, "start_bid": 200000000},
    "Pagani Zonda Cinque": {"stars": 4, "rarity": "Легендарная", "base_price": 800000000, "chance": 0.05, "start_bid": 200000000},
    "Mercedes-Benz 300SL Gullwing": {"stars": 4, "rarity": "Легендарная", "base_price": 850000000, "chance": 0.05, "start_bid": 200000000},
    "Aston Martin Vulcan": {"stars": 4, "rarity": "Легендарная", "base_price": 850000000, "chance": 0.05, "start_bid": 200000000},
    "Pininfarina Battista": {"stars": 4, "rarity": "Легендарная", "base_price": 900000000, "chance": 0.05, "start_bid": 200000000},
    "Rimac Nevera": {"stars": 4, "rarity": "Легендарная", "base_price": 950000000, "chance": 0.05, "start_bid": 200000000},
    
    # ===== ★★★☆☆ ОЧЕНЬ РЕДКИЕ (44 шт) =====
    "Artega GT": {"stars": 3, "rarity": "Очень редкая", "base_price": 60000000, "chance": 0.01, "start_bid": 55000000},
    "Gillet Vertigo": {"stars": 3, "rarity": "Очень редкая", "base_price": 70000000, "chance": 0.01, "start_bid": 55000000},
    "Jensen Interceptor": {"stars": 3, "rarity": "Очень редкая", "base_price": 80000000, "chance": 0.01, "start_bid": 55000000},
    "Bristol Fighter": {"stars": 3, "rarity": "Очень редкая", "base_price": 90000000, "chance": 0.01, "start_bid": 55000000},
    "Maserati Merak": {"stars": 3, "rarity": "Очень редкая", "base_price": 100000000, "chance": 0.01, "start_bid": 55000000},
    "TVR Cerbera": {"stars": 3, "rarity": "Очень редкая", "base_price": 100000000, "chance": 0.01, "start_bid": 55000000},
    "Iso Grifo": {"stars": 3, "rarity": "Очень редкая", "base_price": 110000000, "chance": 0.01, "start_bid": 55000000},
    "Lamborghini Jalpa": {"stars": 3, "rarity": "Очень редкая", "base_price": 120000000, "chance": 0.01, "start_bid": 55000000},
    "Lotus Esprit V8": {"stars": 3, "rarity": "Очень редкая", "base_price": 120000000, "chance": 0.01, "start_bid": 55000000},
    "Morgan Aero 8": {"stars": 3, "rarity": "Очень редкая", "base_price": 120000000, "chance": 0.01, "start_bid": 55000000},
    "Caterham Seven 620R": {"stars": 3, "rarity": "Очень редкая", "base_price": 120000000, "chance": 0.01, "start_bid": 55000000},
    "Donkervoort D8 GTO": {"stars": 3, "rarity": "Очень редкая", "base_price": 120000000, "chance": 0.01, "start_bid": 55000000},
    "Bizzarrini 5300 GT": {"stars": 3, "rarity": "Очень редкая", "base_price": 130000000, "chance": 0.01, "start_bid": 55000000},
    "Radical SR8": {"stars": 3, "rarity": "Очень редкая", "base_price": 130000000, "chance": 0.01, "start_bid": 55000000},
    "De Tomaso Pantera": {"stars": 3, "rarity": "Очень редкая", "base_price": 140000000, "chance": 0.01, "start_bid": 55000000},
    "KTM X-Bow": {"stars": 3, "rarity": "Очень редкая", "base_price": 140000000, "chance": 0.01, "start_bid": 55000000},
    "Ferrari 308 GTB": {"stars": 3, "rarity": "Очень редкая", "base_price": 150000000, "chance": 0.01, "start_bid": 55000000},
    "Ariel Atom 500": {"stars": 3, "rarity": "Очень редкая", "base_price": 150000000, "chance": 0.01, "start_bid": 55000000},
    "Wiesmann MF5": {"stars": 3, "rarity": "Очень редкая", "base_price": 150000000, "chance": 0.01, "start_bid": 55000000},
    "Ascari A10": {"stars": 3, "rarity": "Очень редкая", "base_price": 160000000, "chance": 0.01, "start_bid": 55000000},
    "BAC Mono": {"stars": 3, "rarity": "Очень редкая", "base_price": 160000000, "chance": 0.01, "start_bid": 55000000},
    "Ultima GTR": {"stars": 3, "rarity": "Очень редкая", "base_price": 180000000, "chance": 0.01, "start_bid": 55000000},
    "Caparo T1": {"stars": 3, "rarity": "Очень редкая", "base_price": 180000000, "chance": 0.01, "start_bid": 55000000},
    "Keating Berus": {"stars": 3, "rarity": "Очень редкая", "base_price": 180000000, "chance": 0.01, "start_bid": 55000000},
    "Porsche 930 Turbo": {"stars": 3, "rarity": "Очень редкая", "base_price": 200000000, "chance": 0.01, "start_bid": 55000000},
    "Spyker C8": {"stars": 3, "rarity": "Очень редкая", "base_price": 200000000, "chance": 0.01, "start_bid": 55000000},
    "NIO EP9": {"stars": 3, "rarity": "Очень редкая", "base_price": 200000000, "chance": 0.01, "start_bid": 55000000},
    "Trion Nemesis": {"stars": 3, "rarity": "Очень редкая", "base_price": 200000000, "chance": 0.01, "start_bid": 55000000},
    "Gumpert Apollo": {"stars": 3, "rarity": "Очень редкая", "base_price": 220000000, "chance": 0.01, "start_bid": 55000000},
    "Jaguar XJ220": {"stars": 3, "rarity": "Очень редкая", "base_price": 220000000, "chance": 0.01, "start_bid": 55000000},
    "SCG 003": {"stars": 3, "rarity": "Очень редкая", "base_price": 220000000, "chance": 0.01, "start_bid": 55000000},
    "BMW M1": {"stars": 3, "rarity": "Очень редкая", "base_price": 250000000, "chance": 0.01, "start_bid": 55000000},
    "Drako GTE": {"stars": 3, "rarity": "Очень редкая", "base_price": 250000000, "chance": 0.01, "start_bid": 55000000},
    "Noble M600": {"stars": 3, "rarity": "Очень редкая", "base_price": 280000000, "chance": 0.01, "start_bid": 55000000},
    "Czinger 21C": {"stars": 3, "rarity": "Очень редкая", "base_price": 280000000, "chance": 0.01, "start_bid": 55000000},
    "Mercedes-Benz CLK GTR": {"stars": 3, "rarity": "Очень редкая", "base_price": 300000000, "chance": 0.01, "start_bid": 55000000},
    "Apollo Intensa Emozione": {"stars": 3, "rarity": "Очень редкая", "base_price": 300000000, "chance": 0.01, "start_bid": 55000000},
    "Lamborghini Countach 2022": {"stars": 3, "rarity": "Очень редкая", "base_price": 350000000, "chance": 0.01, "start_bid": 55000000},
    "Aspark Owl": {"stars": 3, "rarity": "Очень редкая", "base_price": 500000000, "chance": 0.01, "start_bid": 55000000},
    "Hispano Suiza Carmen": {"stars": 3, "rarity": "Очень редкая", "base_price": 650000000, "chance": 0.01, "start_bid": 55000000},
    "Lotus Evija": {"stars": 3, "rarity": "Очень редкая", "base_price": 850000000, "chance": 0.01, "start_bid": 55000000},
    "Bugatti La Voiture Noire": {"stars": 3, "rarity": "Очень редкая", "base_price": 500000000, "chance": 0.01, "start_bid": 55000000},
    "Bugatti Divo": {"stars": 3, "rarity": "Очень редкая", "base_price": 4000000000, "chance": 0.01, "start_bid": 55000000},
    "Bugatti Centodieci": {"stars": 3, "rarity": "Очень редкая", "base_price": 4500000000, "chance": 0.01, "start_bid": 55000000},
    
    # ===== ★★☆☆☆ РЕДКИЕ (30 шт) =====
    "Aston Martin DB5": {"stars": 2, "rarity": "Редкая", "base_price": 150000000, "chance": 0.30, "start_bid": 30000000},
    "Aston Martin DBS": {"stars": 2, "rarity": "Редкая", "base_price": 120000000, "chance": 0.30, "start_bid": 25000000},
    "Aston Martin V8 Vantage": {"stars": 2, "rarity": "Редкая", "base_price": 100000000, "chance": 0.30, "start_bid": 20000000},
    "Aston Martin DB7": {"stars": 2, "rarity": "Редкая", "base_price": 80000000, "chance": 0.30, "start_bid": 15000000},
    "Aston Martin V12 Vanquish": {"stars": 2, "rarity": "Редкая", "base_price": 180000000, "chance": 0.30, "start_bid": 35000000},
    "Aston Martin Rapide": {"stars": 2, "rarity": "Редкая", "base_price": 90000000, "chance": 0.30, "start_bid": 18000000},
    "Bentley Continental GT": {"stars": 2, "rarity": "Редкая", "base_price": 350000000, "chance": 0.30, "start_bid": 70000000},
    "Bentley Flying Spur": {"stars": 2, "rarity": "Редкая", "base_price": 300000000, "chance": 0.30, "start_bid": 60000000},
    "Bentley Mulsanne": {"stars": 2, "rarity": "Редкая", "base_price": 400000000, "chance": 0.30, "start_bid": 80000000},
    "Bentley Brooklands": {"stars": 2, "rarity": "Редкая", "base_price": 250000000, "chance": 0.30, "start_bid": 50000000},
    "Bentley Arnage": {"stars": 2, "rarity": "Редкая", "base_price": 200000000, "chance": 0.30, "start_bid": 40000000},
    "Bentley Azure": {"stars": 2, "rarity": "Редкая", "base_price": 220000000, "chance": 0.30, "start_bid": 45000000},
    "Rolls-Royce Phantom": {"stars": 2, "rarity": "Редкая", "base_price": 600000000, "chance": 0.30, "start_bid": 120000000},
    "Rolls-Royce Ghost": {"stars": 2, "rarity": "Редкая", "base_price": 500000000, "chance": 0.30, "start_bid": 100000000},
    "Rolls-Royce Wraith": {"stars": 2, "rarity": "Редкая", "base_price": 550000000, "chance": 0.30, "start_bid": 110000000},
    "Rolls-Royce Dawn": {"stars": 2, "rarity": "Редкая", "base_price": 480000000, "chance": 0.30, "start_bid": 95000000},
    "Rolls-Royce Cullinan": {"stars": 2, "rarity": "Редкая", "base_price": 650000000, "chance": 0.30, "start_bid": 130000000},
    "Rolls-Royce Silver Shadow": {"stars": 2, "rarity": "Редкая", "base_price": 120000000, "chance": 0.30, "start_bid": 25000000},
    "Rolls-Royce Silver Cloud": {"stars": 2, "rarity": "Редкая", "base_price": 150000000, "chance": 0.30, "start_bid": 30000000},
    "Rolls-Royce Corniche": {"stars": 2, "rarity": "Редкая", "base_price": 100000000, "chance": 0.30, "start_bid": 20000000},
    "BMW M5 CS": {"stars": 2, "rarity": "Редкая", "base_price": 800000000, "chance": 0.30, "start_bid": 160000000},
    "BMW M5 F90": {"stars": 2, "rarity": "Редкая", "base_price": 700000000, "chance": 0.30, "start_bid": 140000000},
    "BMW M8 Competition": {"stars": 2, "rarity": "Редкая", "base_price": 900000000, "chance": 0.30, "start_bid": 180000000},
    "BMW M4 CSL": {"stars": 2, "rarity": "Редкая", "base_price": 600000000, "chance": 0.30, "start_bid": 120000000},
    "BMW M3 E46": {"stars": 2, "rarity": "Редкая", "base_price": 300000000, "chance": 0.30, "start_bid": 60000000},
    "BMW M3 E92": {"stars": 2, "rarity": "Редкая", "base_price": 350000000, "chance": 0.30, "start_bid": 70000000},
    "BMW M2 Competition": {"stars": 2, "rarity": "Редкая", "base_price": 400000000, "chance": 0.30, "start_bid": 80000000},
    "BMW Z8": {"stars": 2, "rarity": "Редкая", "base_price": 450000000, "chance": 0.30, "start_bid": 90000000},
    "BMW 507": {"stars": 2, "rarity": "Редкая", "base_price": 500000000, "chance": 0.30, "start_bid": 100000000},
    "BMW M1": {"stars": 2, "rarity": "Редкая", "base_price": 250000000, "chance": 0.30, "start_bid": 50000000},
    
    # ===== ★☆☆☆☆ ДОСТУПНЫЕ (23 шт) =====
    "Zaz 968": {"stars": 1, "rarity": "Доступная", "base_price": 500000, "chance": 0.50, "start_bid": 100000},
    "Lada 2101": {"stars": 1, "rarity": "Доступная", "base_price": 300000, "chance": 0.50, "start_bid": 50000},
    "Lada 2107": {"stars": 1, "rarity": "Доступная", "base_price": 400000, "chance": 0.50, "start_bid": 80000},
    "Lada 2109": {"stars": 1, "rarity": "Доступная", "base_price": 350000, "chance": 0.50, "start_bid": 70000},
    "Lada 2110": {"stars": 1, "rarity": "Доступная", "base_price": 450000, "chance": 0.50, "start_bid": 90000},
    "Lada Niva": {"stars": 1, "rarity": "Доступная", "base_price": 600000, "chance": 0.50, "start_bid": 120000},
    "Lada Vesta": {"stars": 1, "rarity": "Доступная", "base_price": 800000, "chance": 0.50, "start_bid": 150000},
    "Lada XRAY": {"stars": 1, "rarity": "Доступная", "base_price": 700000, "chance": 0.50, "start_bid": 140000},
    "Lada Granta": {"stars": 1, "rarity": "Доступная", "base_price": 500000, "chance": 0.50, "start_bid": 100000},
    "Lada Kalina": {"stars": 1, "rarity": "Доступная", "base_price": 400000, "chance": 0.50, "start_bid": 80000},
    "Lada Priora": {"stars": 1, "rarity": "Доступная", "base_price": 450000, "chance": 0.50, "start_bid": 90000},
    "Moskvich 412": {"stars": 1, "rarity": "Доступная", "base_price": 250000, "chance": 0.50, "start_bid": 50000},
    "Moskvich 2140": {"stars": 1, "rarity": "Доступная", "base_price": 300000, "chance": 0.50, "start_bid": 60000},
    "Moskvich 408": {"stars": 1, "rarity": "Доступная", "base_price": 200000, "chance": 0.50, "start_bid": 40000},
    "GAZ 24 Volga": {"stars": 1, "rarity": "Доступная", "base_price": 800000, "chance": 0.50, "start_bid": 150000},
    "GAZ 21 Volga": {"stars": 1, "rarity": "Доступная", "base_price": 1000000, "chance": 0.50, "start_bid": 200000},
    "GAZ 3102 Volga": {"stars": 1, "rarity": "Доступная", "base_price": 600000, "chance": 0.50, "start_bid": 120000},
    "UAZ 469": {"stars": 1, "rarity": "Доступная", "base_price": 700000, "chance": 0.50, "start_bid": 140000},
    "UAZ Patriot": {"stars": 1, "rarity": "Доступная", "base_price": 900000, "chance": 0.50, "start_bid": 180000},
    "UAZ Hunter": {"stars": 1, "rarity": "Доступная", "base_price": 800000, "chance": 0.50, "start_bid": 160000},
    "VAZ 2101": {"stars": 1, "rarity": "Доступная", "base_price": 300000, "chance": 0.50, "start_bid": 60000},
    "VAZ 2106": {"stars": 1, "rarity": "Доступная", "base_price": 400000, "chance": 0.50, "start_bid": 80000},
    "VAZ 2107": {"stars": 1, "rarity": "Доступная", "base_price": 400000, "chance": 0.50, "start_bid": 80000}
}

# ==========================================
# ===== НАСТРОЙКИ АУКЦИОНА =====
# ==========================================

AUCTION_CONFIG = {
    "max_lots": 15,
    "update_interval": 1800,
    "bid_timeout": 10,
    "default_start_bid": 1000000
}

# ==========================================
# ===== ID ФУНКЦИЙ =====
# ==========================================

FUNCTION_IDS = {
    "job_1": "Шахта",
    "job_2": "Ферма",
    "job_3": "Трейдинг",
    "job_4": "Водолаз",
    "job_5": "Рыболовство",
    "menubutton_1": "Работы",
    "menubutton_2": "Донат",
    "menubutton_3": "Форбс",
    "menubutton_4": "Гараж",
    "menubutton_5": "Инвентарь",
    "menubutton_6": "Скупщик",
    "menubutton_7": "Бизнес",
    "menubutton_8": "Казино",
    "menubutton_9": "Статистика",
    "menubutton_10": "Техподдержка",
    "menubutton_11": "Аукцион",
    "casinogame_1": "Кубик",
    "casinogame_2": "Слоты",
    "casinogame_3": "Мины",
    "trading_1": "BTC",
    "trading_2": "WETcoin",
    "trading_3": "NotCoin",
}

# ==========================================
# ===== РЕФЕРАЛЬНАЯ СИСТЕМА =====
# ==========================================

REFERRAL_BONUS = 150000000
REFERRAL_CAR_CHANCE = 0.20

logger.info(f"📁 Данные хранятся в: {DATA_DIR}")
logger.info(f"👑 Админы: {ADMIN_IDS}")
