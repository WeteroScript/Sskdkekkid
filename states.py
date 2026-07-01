from aiogram.fsm.state import State, StatesGroup

class PromoStates(StatesGroup):
    waiting_for_promo = State()

class SupportStates(StatesGroup):
    waiting_for_support_message = State()

class AuctionStates(StatesGroup):
    waiting_for_auction_bid = State()

class TradeStates(StatesGroup):
    waiting_for_trade_amount = State()

class CasinoStates(StatesGroup):
    waiting_for_casino_bet = State()
    waiting_for_mines_count = State()
    waiting_for_field_size = State()

class DonateStates(StatesGroup):
    waiting_for_brcoin_convert = State()

class FishingStates(StatesGroup):
    waiting_for_bait_quantity = State()
