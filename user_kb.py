from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from services.utils import format_currency

def main_kb(is_admin: bool = False):
    k = ReplyKeyboardBuilder()
    k.button(text="⭐ Купить Stars")
    k.button(text="🎁 Купить подарок")
    k.button(text="💎 Купить NFT-подарок")
    k.button(text="🧮 Калькулятор")
    k.button(text="👤 Профиль")
    k.button(text="💰 Пополнить баланс")
    k.button(text="🎟 Промокод")
    k.button(text="📋 Мои заказы")
    k.button(text="💬 Поддержка")
    if is_admin:
        k.button(text="👨‍💼 Админ-панель")
        k.adjust(2, 2, 2, 2, 1, 1)
    else:
        k.adjust(2, 2, 2, 2, 1)
    return k.as_markup(resize_keyboard=True)

def back_kb():
    k = ReplyKeyboardBuilder()
    k.button(text="◀️ Назад")
    return k.as_markup(resize_keyboard=True)

def topup_methods_kb():
    k = InlineKeyboardBuilder()
    k.button(text="💵 Наличные", callback_data="topup_method:cash")
    k.button(text="💳 Карта", callback_data="topup_method:card")
    k.button(text="₿ Криптовалюта", callback_data="topup_method:crypto")
    k.adjust(1, 1, 1)
    return k.as_markup()

def paynet_understood_kb():
    k = InlineKeyboardBuilder()
    k.button(text="✅ Понял", callback_data="paynet_understood")
    k.button(text="❌ Отменить", callback_data="topup_cancel")
    k.adjust(1, 1)
    return k.as_markup()

def topup_confirm_kb(topup_id: int):
    k = InlineKeyboardBuilder()
    k.button(text="✅ Я оплатил", callback_data=f"topup_i_paid:{topup_id}")
    k.button(text="❌ Отменить заявку", callback_data=f"topup_user_cancel:{topup_id}")
    k.adjust(1, 1)
    return k.as_markup()

def recipient_choice_kb():
    k = InlineKeyboardBuilder()
    k.button(text="👤 Себе", callback_data="recip:self")
    k.button(text="🎁 Другу", callback_data="recip:friend")
    k.button(text="❌ Отмена", callback_data="cancel_order_flow")
    k.adjust(2, 1)
    return k.as_markup()

def anonymity_choice_kb():
    k = InlineKeyboardBuilder()
    k.button(text="🙈 Анонимно", callback_data="anon:1")
    k.button(text="👤 Открыто (без анонимности)", callback_data="anon:0")
    k.adjust(1, 1)
    return k.as_markup()

def signature_choice_kb():
    k = InlineKeyboardBuilder()
    k.button(text="✍️ Добавить подпись (+1 000 сум)", callback_data="sig:add")
    k.button(text="⏩ Без подписи", callback_data="sig:skip")
    k.adjust(1, 1)
    return k.as_markup()

def calc_result_kb(stars_count: int):
    k = InlineKeyboardBuilder()
    k.button(text=f"⭐ Купить {stars_count} Stars", callback_data=f"calc_buy:{stars_count}")
    k.button(text="🧮 Посчитать еще", callback_data="calc_recalculate")
    k.adjust(1, 1)
    return k.as_markup()

def stars_buy_kb(has_balance: bool, stars: int, price: int, balance: int):
    k = InlineKeyboardBuilder()
    if has_balance:
        k.button(text="✅ Купить", callback_data="confirm_buy_stars")
        k.button(text="🎟️ Промокод", callback_data="buy_add_promo")
        k.button(text="❌ Отмена", callback_data="cancel_buy_stars")
        k.adjust(2, 1)
    else:
        k.button(text="💰 Пополнить баланс", callback_data="goto_topup")
        k.button(text="❌ Отмена", callback_data="cancel_buy_stars")
        k.adjust(1, 1)
    return k.as_markup()

def products_kb(products):
    k = InlineKeyboardBuilder()
    for p in products:
        title = f"{p['title']} — {format_currency(p['price'])}"
        k.button(text=title, callback_data=f"buy_gift:{p['id']}")
    k.adjust(1)
    return k.as_markup()

def gift_buy_kb(product_id: int, has_balance: bool):
    k = InlineKeyboardBuilder()
    if has_balance:
        k.button(text="✅ Купить", callback_data=f"confirm_buy_gift:{product_id}")
        k.button(text="◀️ Назад", callback_data="gifts_list")
        k.adjust(1, 1)
    else:
        k.button(text="💰 Пополнить баланс", callback_data="goto_topup")
        k.button(text="◀️ Назад", callback_data="gifts_list")
        k.adjust(1, 1)
    return k.as_markup()

def profile_kb():
    k = InlineKeyboardBuilder()
    k.button(text="💰 Пополнить баланс", callback_data="goto_topup")
    k.button(text="📋 История операций", callback_data="user_operations_history")
    k.adjust(1, 1)
    return k.as_markup()

def nft_kb(manager_username: str = "@YaTochka_pan"):
    clean_url = manager_username.replace("@", "")
    k = InlineKeyboardBuilder()
    k.button(text="💬 Написать менеджеру", url=f"https://t.me/{clean_url}")
    return k.as_markup()
