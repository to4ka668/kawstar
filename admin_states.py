from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_price = State()
    waiting_star_cost_price = State()
    waiting_card_requisites = State()
    waiting_paynet_requisites = State()
    waiting_crypto_address = State()
    waiting_crypto_network = State()
    waiting_custom_topup_amount = State()
    waiting_user_search = State()
    waiting_order_search = State()
    waiting_manual_balance_amount = State()
    waiting_broadcast = State()

    # Product CRUD states
    add_product_title = State()
    add_product_price = State()
    add_product_cost = State()
    add_product_desc = State()

    # Promo CRUD states
    add_promo_code = State()
    add_promo_type = State()
    add_promo_value = State()
    add_promo_max_uses = State()
