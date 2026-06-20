import os
from datetime import datetime
import logging

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

# ========== ПУТИ К ФАЙЛАМ ==========
DATA_DIR = '/app/shared' if os.path.exists('/app/shared') else '.'
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
