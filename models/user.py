from datetime import datetime
from typing import Dict, Any

class UserModel:
    """Модель пользователя"""
    
    @staticmethod
    def get_default() -> Dict[str, Any]:
        """Возвращает дефолтного пользователя"""
        return {
            "money": 1000000,
            "brcoins": 1000,
            "energy": 100,
            "total_earned": 0,
            "trades_count": 0,
            "role": "user",
            "donate_spent": 0,
            "donate_received": 0,
            "mine_attempts": 100,
            "last_mine_reset": datetime.now().isoformat(),
            "portfolio": {
                "BTC": 0,
                "WETcoin": 0,
                "NotCoin": 0
            },
            "business": {
                "auto_mine": {"owned": False, "last_collect": None, "auto_collect": False},
                "tech_center": {"owned": False, "last_collect": None, "auto_collect": False},
                "tire_center": {"owned": False, "last_collect": None, "auto_collect": False},
                "styling_center": {"owned": False, "last_collect": None, "auto_collect": False},
                "shop_24": {"owned": False, "last_collect": None, "auto_collect": False}
            },
            "farm": {
                "milk": 0,
                "hay": 0,
                "eggs": 0,
                "wheat": 0,
                "meat": 0,
                "last_collect": None
            },
            "casino": {
                "bet": 0,
                "mines_count": 4,
                "field_size": 5
            },
            "banned": False,
            "frozen_balance": 0,
            "referrer": None,
            "referrals": [],
            "referral_count": 0,
            "captcha_passed": False,
            "captcha_code": None,
            "captcha_emojis": []
        }
    
    @staticmethod
    def get_business_count(user_data: Dict) -> int:
        return sum(1 for biz in user_data.get("business", {}).values() 
                  if biz.get("owned", False))
    
    @staticmethod
    def is_banned(user_data: Dict) -> bool:
        return user_data.get("banned", False)
