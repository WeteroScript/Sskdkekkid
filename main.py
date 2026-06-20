#!/usr/bin/env python3
import asyncio
import sys
from config import bot, dp, logger
from database.file_manager import load_settings

# Импортируем из core (НЕ из handlers!)
from core.handlers import register_handlers

async def main():
    logger.info("🤖 Бот запущен!")
    
    # Регистрируем обработчики
    register_handlers(dp)
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Завершение работы")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
