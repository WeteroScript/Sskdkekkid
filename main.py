import asyncio
import logging
from config import Config
from core.bot import bot, dp
from core.handlers import register_handlers
from core.middleware import setup_middleware
from business.collector import start_auto_collect_loop
from business.manager import start_business_check_loop
from admin.promocode import start_promo_loop

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Запуск бота...")
    
    # Регистрация хендлеров
    register_handlers(dp)
    setup_middleware(dp)
    
    # Запуск фоновых задач
    await start_auto_collect_loop()
    await start_business_check_loop()
    await start_promo_loop()
    
    # Запуск поллинга
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
