def get_default_user():
    return {
        "money": 1000000,
        "brcoins": 1000,
        "energy": 100,
        "total_earned": 0,
        "trades_count": 0,
        "role": "user",
        "donate_spent": 0,
        "donate_received": 0,
        "inventory": [],
        "mine_attempts": 100,
        "last_mine_reset": None,
        "portfolio": {"BTC": 0, "WETcoin": 0, "NotCoin": 0},
        "business": {
            "auto_mine": {"owned": False, "last_collect": None, "auto_collect": False},
            "tech_center": {"owned": False, "last_collect": None, "auto_collect": False},
            "tire_center": {"owned": False, "last_collect": None, "auto_collect": False},
            "styling_center": {"owned": False, "last_collect": None, "auto_collect": False},
            "shop_24": {"owned": False, "last_collect": None, "auto_collect": False}
        },
        "farm": {"milk": 0, "hay": 0, "eggs": 0, "wheat": 0, "meat": 0, "last_collect": None},
        "casino": {"bet": 0, "mines_count": 4, "field_size": 5}
    }
