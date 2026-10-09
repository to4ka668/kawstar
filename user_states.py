from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    waiting_stars = State()
    waiting_topup_amount = State()
    waiting_promo_code = State()
    waiting_recipient_username = State()
    waiting_gift_signature = State()
    waiting_calculator_stars = State()
