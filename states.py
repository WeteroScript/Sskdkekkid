from aiogram.fsm.state import State, StatesGroup

class PromoStates(StatesGroup):
    """Состояния для промокодов"""
    waiting_for_promo = State()

class SupportStates(StatesGroup):
    """Состояния для поддержки"""
    waiting_for_support_message = State()

class AuctionStates(StatesGroup):
    """Состояния для аукциона"""
    waiting_for_auction_bid = State()

class TradeStates(StatesGroup):
    """Состояния для трейдинга"""
    waiting_for_trade_amount = State()

class CasinoStates(StatesGroup):
    """Состояния для казино"""
    waiting_for_casino_bet = State()
    waiting_for_mines_count = State()
    waiting_for_field_size = State()
