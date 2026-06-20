import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    CHANNEL_ID = os.getenv('CHANNEL_ID')
    PROMO_CHANNEL_ID = os.getenv('PROMO_CHANNEL_ID')
    DATA_DIR = os.getenv('DATA_DIR', '/app/shared')
    
    # Константы
    MINE_RESOURCES = [...]
    FARM_RESOURCES = [...]
    CONTAINERS = {...}
    BUSINESS_CONFIG = {...}
