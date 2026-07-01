from .admin import register_admin_handlers
from .user import register_user_handlers
from .business import register_business_handlers
from .casino import register_casino_handlers
from .jobs import register_jobs_handlers
from .auction import register_auction_handlers
from .fishing import register_fishing_handlers

__all__ = [
    'register_admin_handlers',
    'register_user_handlers',
    'register_business_handlers',
    'register_casino_handlers',
    'register_jobs_handlers',
    'register_auction_handlers',
    'register_fishing_handlers'
]
