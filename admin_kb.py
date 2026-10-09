from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.utils import format_currency

def admin_main_kb():
    k = InlineKeyboardBuilder()
    k.button(text="👥 Пользователи", callback_data="a:users")
    k.button(text="📦 Заказы", callback_data="a:orders")
    k.button(text="💰 Пополнения", callback_data="a:topups")
    k.button(text="⭐ Stars", callback_data="a:stars_price")
    k.button(text="🎁 Подарки", callback_data="a:gifts")
    k.button(text="💎 NFT", callback_data="a:nft")
    k.button(text="🎟 Промокоды", callback_data="a:promos")
    k.button(text="💵 Цены", callback_data="a:prices_menu")
    k.button(text="💳 Реквизиты", callback_data="a:reqs")
    k.button(text="📊 Статистика", callback_data="a:stats")
    k.button(text="📢 Рассылка", callback_data="a:broadcast")
    k.button(text="⚙️ Настройки", callback_data="a:settings")
    k.adjust(2, 2, 2, 2, 2, 2)
    return k.as_markup()

def admin_orders_search_kb(recent_orders=None):
    k = InlineKeyboardBuilder()
    if recent_orders:
        for r in recent_orders:
            st_icon = "✅" if str(r["status"]).lower() in ("completed", "done") else ("⚙️" if str(r["status"]).lower() in ("work", "in_work") else "🆕")
            item_lbl = f"⭐ {r['stars']}" if r["order_type"] == "stars" else "🎁 Подарок"
            k.button(text=f"{st_icon} Заказ #{r['id']} ({item_lbl})", callback_data=f"adm_view_ord:{r['id']}")
        k.adjust(2)

    k.button(text="🆕 Новые", callback_data="a:ord_flt:new")
    k.button(text="⚙️ В работе", callback_data="a:ord_flt:work")
    k.button(text="✅ Завершённые", callback_data="a:ord_flt:done")
    k.button(text="❌ Отменённые", callback_data="a:ord_flt:cancelled")
    k.button(text="📦 Все заказы", callback_data="a:ord_flt:all")
    k.button(text="◀️ Админ-меню", callback_data="a:main")
    k.adjust(2, 2, 2, 1)
    return k.as_markup()

def admin_orders_filter_kb():
    k = InlineKeyboardBuilder()
    k.button(text="🆕 Новые", callback_data="a:ord_flt:new")
    k.button(text="⚙️ В работе", callback_data="a:ord_flt:work")
    k.button(text="✅ Завершённые", callback_data="a:ord_flt:done")
    k.button(text="❌ Отменённые", callback_data="a:ord_flt:cancelled")
    k.button(text="📦 Все заказы", callback_data="a:ord_flt:all")
    k.button(text="◀️ Админ-меню", callback_data="a:main")
    k.adjust(2, 2, 1, 1)
    return k.as_markup()

def admin_order_card_kb(order_id: int, status: str):
    k = InlineKeyboardBuilder()
    s = str(status).lower()
    if s in ("new", "paid"):
        k.button(text="⚙️ В работу", callback_data=f"adm_ord:work:{order_id}")
        k.button(text="✅ Завершить", callback_data=f"adm_ord:done:{order_id}")
        k.button(text="❌ Отменить", callback_data=f"adm_ord:cancel:{order_id}")
        k.adjust(2, 1)
    elif s in ("work", "in_work"):
        k.button(text="✅ Завершить", callback_data=f"adm_ord:done:{order_id}")
        k.button(text="❌ Отменить", callback_data=f"adm_ord:cancel:{order_id}")
        k.adjust(2)
    else:
        k.button(text="⚙️ В работу", callback_data=f"adm_ord:work:{order_id}")
        k.button(text="✅ Завершить", callback_data=f"adm_ord:done:{order_id}")
        k.adjust(2)
    return k.as_markup()

def admin_topup_card_kb(topup_id: int):
    k = InlineKeyboardBuilder()
    k.button(text="✅ Зачислить", callback_data=f"adm_topup:approve:{topup_id}")
    k.button(text="✏️ Изменить сумму", callback_data=f"adm_topup:custom:{topup_id}")
    k.button(text="❌ Отклонить", callback_data=f"adm_topup:reject:{topup_id}")
    k.adjust(2, 1)
    return k.as_markup()

def admin_user_card_kb(user_id: int):
    k = InlineKeyboardBuilder()
    k.button(text="➕ Пополнить вручную", callback_data=f"adm_usr:credit:{user_id}")
    k.button(text="➖ Списать вручную", callback_data=f"adm_usr:debit:{user_id}")
    k.button(text="📋 История операций", callback_data=f"adm_usr:ops:{user_id}")
    k.button(text="◀️ К пользователям", callback_data="a:users")
    k.adjust(2, 1, 1)
    return k.as_markup()

def admin_promo_type_kb():
    k = InlineKeyboardBuilder()
    k.button(text="1. Скидка % (на покупки)", callback_data="promo_type:discount")
    k.button(text="2. Бонус на пополнение %", callback_data="promo_type:deposit_bonus")
    k.button(text="3. Фиксированное пополнение", callback_data="promo_type:fixed_refill")
    k.button(text="❌ Отмена", callback_data="a:cancel_state")
    k.adjust(1)
    return k.as_markup()

def admin_promos_kb(promos):
    k = InlineKeyboardBuilder()
    for pr in promos:
        status_icon = "🟢" if pr["is_active"] == 1 else "🔴"
        type_str = {"discount": "%", "deposit_bonus": "% bonus", "fixed_refill": "сум"}.get(pr["type"], "")
        t = f"{status_icon} {pr['code']} ({pr['value']}{type_str}) [{pr['uses_count']}/{pr['max_uses']}]"
        k.button(text=t, callback_data=f"a_promo:toggle:{pr['id']}")
    k.button(text="🎟 Создать промокод", callback_data="a_promo:add")
    k.button(text="◀️ Админ-меню", callback_data="a:main")
    k.adjust(1)
    return k.as_markup()

def admin_products_kb(products):
    k = InlineKeyboardBuilder()
    for p in products:
        status_icon = "🟢" if p["is_available"] == 1 else "🔴"
        title = f"{status_icon} {p['title']} — {format_currency(p['price'])}"
        k.button(text=title, callback_data=f"a_prod:view:{p['id']}")
    k.button(text="➕ Добавить подарок", callback_data="a_prod:add")
    k.button(text="◀️ Админ-меню", callback_data="a:main")
    k.adjust(1)
    return k.as_markup()

def admin_product_card_kb(product_id: int, is_available: int):
    k = InlineKeyboardBuilder()
    avail_btn = "🔴 Скрыть" if is_available == 1 else "🟢 Показать"
    k.button(text=avail_btn, callback_data=f"a_prod:toggle:{product_id}")
    k.button(text="❌ Удалить подарок", callback_data=f"a_prod:delete:{product_id}")
    k.button(text="◀️ К списку подарков", callback_data="a:gifts")
    k.adjust(2, 1)
    return k.as_markup()

def admin_requisites_menu_kb():
    k = InlineKeyboardBuilder()
    k.button(text="💳 Карта", callback_data="a:edit_req_card")
    k.button(text="💵 Paynet / Наличные", callback_data="a:edit_req_paynet")
    k.button(text="₿ Криптовалюта", callback_data="a:edit_req_crypto")
    k.button(text="◀️ Админ-меню", callback_data="a:main")
    k.adjust(1)
    return k.as_markup()

def admin_cancel_state_kb():
    k = InlineKeyboardBuilder()
    k.button(text="❌ Отменить", callback_data="a:cancel_state")
    return k.as_markup()
