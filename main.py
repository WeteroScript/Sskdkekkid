#!/usr/bin/env python3
import asyncio
import sys
from config import bot, dp, logger, ADMIN_IDS
from database.file_manager import load_settings
from services.tasks import (
    promo_auto_loop, check_business_loop, 
    update_auction, auction_loop, check_auction_bids
)
from core.handlers import register_handlers

promo_running = False
promo_task = None
business_running = False
business_check_task = None

async def main():
    global promo_running, promo_task, business_running, business_check_task
    
    logger.info("🤖 Бот запущен!")
    logger.info(f"👑 Админы: {ADMIN_IDS}")
    
    # Регистрируем все обработчики
    register_handlers(dp)
    
    try:
        # Запускаем фоновые задачи
        business_running = True
        business_check_task = asyncio.create_task(check_business_loop())
        logger.info("🏢 Цикл проверки бизнесов запущен!")
        
        # Запускаем аукцион
        auction_task = asyncio.create_task(auction_loop())
        logger.info("🔨 Цикл аукциона запущен!")
        
        # Запускаем проверку ставок
        bid_check_task = asyncio.create_task(check_auction_bids())
        logger.info("💰 Проверка ставок аукциона запущена!")
        
        # Первое обновление аукциона
        await update_auction()
        logger.info("🔄 Аукцион обновлен!")
        
        settings = await load_settings()
        
        if settings.get("promo_auto", False):
            promo_running = True
            promo_task = asyncio.create_task(promo_auto_loop())
            logger.info("📢 Авто-промокоды запущены!")
        
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Завершение работы")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
