from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from data.database import load_settings, load_users
from config import Config
import logging

logger = logging.getLogger(__name__)

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        
        # Проверка админа
        if user_id in Config.ADMIN_IDS:
            return await handler(event, data)
        
        # Проверка подписки
        if not await self.check_subscription(user_id):
            await self.ask_subscription(event)
            return
        
        # Проверка включения бота
        settings = await load_settings()
        if not settings.get('bot_enabled', True):
            await self.bot_disabled(event)
            return
        
        return await handler(event, data)
    
    async def check_subscription(self, user_id):
        try:
            from core.bot import bot
            member = await bot.get_chat_member(Config.CHANNEL_ID, user_id)
            return member.status in ["member", "administrator", "creator"]
        except:
            return False
    
    async def ask_subscription(self, event):
        text = "📢 Подпишитесь на канал @WeteroRussia!\n\n👉 [Подписаться](https://t.me/+TAhbj7PhoWhhZTQ6)"
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer("📢 Подпишитесь на канал!", show_alert=True)
    
    async def bot_disabled(self, event):
        if isinstance(event, Message):
            await event.answer("🔧 Бот на техническом обслуживании!")
        elif isinstance(event, CallbackQuery):
            await event.answer("🔧 Бот на техобслуживании!", show_alert=True)

def setup_middleware(dp):
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
