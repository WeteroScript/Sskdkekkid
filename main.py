#!/usr/bin/env python3
import asyncio
import os
import sys
from config import API_TOKEN, bot, dp, logger
from services.tasks import promo_running, promo_task, business_running, business_check_task, promo_auto_loop, check_business_loop
from database.file_manager import load_settings

# Импортируем все хендлеры
from handlers.admin import register_admin_handlers
from handlers.user import register_user_handlers
from handlers.business import register_business_handlers
from handlers.casino import register_casino_handlers
from handlers.containers import register_container_handlers
from handlers.farm import register_farm_handlers
from handlers.mine import register_mine_handlers
from handlers.trading import register_trading_handlers
from handlers.support import register_support_handlers

async def main():
    global promo_running, promo_task, business_running, business_check_task
    
    logger.info("🤖 Бот запущен!")
    logger.info(f"👑 Админы: {ADMIN_IDS}")
    
    # Регистрируем хендлеры
    register_admin_handlers(dp)
    register_user_handlers(dp)
    register_business_handlers(dp)
    register_casino_handlers(dp)
    register_container_handlers(dp)
    register_farm_handlers(dp)
    register_mine_handlers(dp)
    register_trading_handlers(dp)
    register_support_handlers(dp)
    
    try:
        # Запускаем цикл проверки бизнесов
        business_running = True
        business_check_task = asyncio.create_task(check_business_loop())
        logger.info("🏢 Цикл проверки бизнесов запущен!")
        
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
