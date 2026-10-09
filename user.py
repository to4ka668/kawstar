import re
from datetime import datetime
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID
from database import (
    get_setting,
    get_user,
    add_or_update_user,
    create_order,
    get_order,
    get_user_orders,
    update_order_status,
    get_all_products,
    get_product,
    get_promocode,
    can_user_use_promo,
    record_promo_use,
    update_user_balance_atomic,
    create_topup_request,
    get_user_operations,
)
from states.user_states import UserStates
from keyboards.user_kb import (
    main_kb,
    back_kb,
    topup_methods_kb,
    paynet_understood_kb,
    topup_confirm_kb,
    recipient_choice_kb,
    anonymity_choice_kb,
    signature_choice_kb,
    calc_result_kb,
    stars_buy_kb,
    products_kb,
    gift_buy_kb,
    profile_kb,
    nft_kb,
)
from services.utils import status_text, format_currency, is_admin

router = Router()

def is_back(text: str) -> bool:
    return bool(text and ("назад" in text.lower() or "◀️" in text))

# ----------------- Start & Back Navigation -----------------
@router.message(Command("start"))
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    add_or_update_user(
        user_id=m.from_user.id,
        username=m.from_user.username,
        first_name=m.from_user.first_name,
    )
    welcome = get_setting("welcome_text", "⭐ <b>Добро пожаловать в KAW Star!</b>")
    await m.answer(welcome, reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

@router.message(F.text.func(is_back))
async def handle_back(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Главное меню:", reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

# ----------------- Profile & History -----------------
@router.message(F.text == "👤 Профиль")
async def show_profile(m: Message, state: FSMContext):
    await state.clear()
    user = get_user(m.from_user.id)
    if not user:
        add_or_update_user(m.from_user.id, m.from_user.username, m.from_user.first_name)
        user = get_user(m.from_user.id)

    orders = get_user_orders(m.from_user.id, limit=500)
    orders_count = len(orders)
    stars_count = user["total_stars"] if user else 0

    first_name = m.from_user.first_name or "Пользователь"
    username_str = f"@{m.from_user.username}" if m.from_user.username else "Не задан"
    balance = user["balance"] if user else 0
    topups = user["total_topups"] if user else 0
    spent = user["total_spent"] if user else 0

    text = (
        f"<b>Ваш профиль</b>\n\n"
        f"Имя: <b>{first_name}</b>\n"
        f"Username: <b>{username_str}</b>\n"
        f"Telegram ID: <code>{m.from_user.id}</code>\n\n"
        f"📦 Заказов: <b>{orders_count}</b>\n"
        f"⭐ Куплено Stars: <b>{stars_count:,}</b>\n"
        f"💰 Баланс: <b>{format_currency(balance)}</b>\n"
        f"💳 Пополнено: <b>{format_currency(topups)}</b>\n"
        f"🛒 Потрачено: <b>{format_currency(spent)}</b>"
    )
    await m.answer(text, reply_markup=profile_kb())

@router.callback_query(F.data == "user_operations_history")
async def cb_user_operations_history(cq: CallbackQuery):
    await cq.answer()
    ops = get_user_operations(cq.from_user.id, limit=20)
    if not ops:
        return await cq.message.answer("📋 <b>История операций пока пуста.</b>")

    text = "📋 <b>История операций:</b>\n\n"
    for o in ops:
        sign = "+" if o["amount"] > 0 else ""
        amount_str = f"{sign}{format_currency(o['amount'])}"
        text += f"• <b>#{o['id']}</b> | {o['created_at']}\n  {o['description']} — <b>{amount_str}</b>\n\n"

    await cq.message.answer(text)

# ----------------- Top-Up Balance Flow -----------------
@router.message(F.text == "💰 Пополнить баланс")
@router.callback_query(F.data == "goto_topup")
async def start_topup(event, state: FSMContext):
    await state.clear()
    text = "💰 <b>Выберите способ пополнения баланса:</b>"
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, reply_markup=topup_methods_kb())
    else:
        await event.answer(text, reply_markup=topup_methods_kb())

@router.callback_query(F.data.startswith("topup_method:"))
async def cb_topup_method(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    method = cq.data.split(":")[1]
    await state.update_data(topup_method=method)

    if method == "card":
        card_num = get_setting("card_requisites", "5614 6835 1296 6896")
        await state.set_state(UserStates.waiting_topup_amount)
        text = (
            f"💳 <b>Пополнение через карту</b>\n\n"
            f"Реквизиты для оплаты:\n<code>{card_num}</code>\n\n"
            f"Комиссия: <b>0%</b>\n\n"
            f"Введите сумму пополнения в сумах (например: <code>10000</code>):"
        )
        await cq.message.edit_text(text)

    elif method == "cash":
        paynet_phone = get_setting("paynet_requisites", "+998881400008")
        manager = get_setting("paynet_manager", "@YaTochka_pan")
        text = (
            f"💵 <b>Пополнение наличными через Paynet</b>\n\n"
            f"Оплата наличными осуществляется через Paynet.\n\n"
            f"Реквизиты для оплаты:\n<code>{paynet_phone}</code>\n\n"
            f"Отправляйте сумму строго через Paynet на указанный номер.\n\n"
            f"⚠️ Если вы случайно отправите деньги непосредственно на сам номер телефона, денежные средства не возвращаются.\n\n"
            f"Если вы не поняли, как правильно пополнять баланс, напишите нам — мы всё объясним:\n{manager}"
        )
        await cq.message.edit_text(text, reply_markup=paynet_understood_kb())

    elif method == "crypto":
        address = get_setting("crypto_address", "UQAfQ6LWkNS7_p7QlTIWgJJd3cvWLrJr8Hl6gqyZ73Zw8j8w")
        network = get_setting("crypto_network", "Gramm (ex. TON)")
        instruction = get_setting("crypto_instruction", "⚠️ ВАЖНО!\nСтрого пополняйте в сети Gramm (ex. TON).")

        await state.set_state(UserStates.waiting_topup_amount)
        text = (
            f"₿ <b>Пополнение криптовалютой</b>\n\n"
            f"Адрес:\n<code>{address}</code>\n\n"
            f"Сеть:\n<b>{network}</b>\n\n"
            f"{instruction}\n\n"
            f"Введите сумму пополнения в сумах:"
        )
        await cq.message.edit_text(text)

@router.callback_query(F.data == "paynet_understood")
async def cb_paynet_understood(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(UserStates.waiting_topup_amount)
    await cq.message.edit_text("💵 Введите сумму пополнения в сумах (например: <code>10000</code>):")

@router.message(UserStates.waiting_topup_amount)
async def process_topup_amount(m: Message, state: FSMContext, bot: Bot):
    if is_back(m.text):
        await state.clear()
        return await m.answer("Главное меню:", reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

    raw_text = m.text.replace(" ", "")
    try:
        amount = int(raw_text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Пожалуйста, введите корректную сумму пополнения в сумах (например: 10000).", reply_markup=back_kb())

    data = await state.get_data()
    method = data.get("topup_method", "card")
    deposit_promo = data.get("deposit_promo_code")
    deposit_bonus_pct = data.get("deposit_bonus_pct", 0)

    fee = 0
    if method == "cash":
        fee = int(amount * 0.02)  # 2% fee ONLY for cash/paynet

    net = amount - fee
    bonus = 0
    if deposit_promo and deposit_bonus_pct > 0:
        bonus = int(net * deposit_bonus_pct / 100)

    final_credit = net + bonus

    tid = create_topup_request(
        user_id=m.from_user.id,
        username=m.from_user.username,
        payment_method=method,
        entered_amount=amount,
        fee_amount=fee,
        net_amount=net,
        bonus_amount=bonus,
        final_credit_amount=final_credit,
        promo_code=deposit_promo,
    )

    await state.clear()

    method_name = {"card": "Карта", "cash": "Наличные (Paynet)", "crypto": "Криптовалюта"}.get(method, method)
    fee_text = f"{format_currency(fee)} (2%)" if fee > 0 else "0 сум"
    bonus_text = f"\n🎁 Бонус по промокоду: +{format_currency(bonus)}" if bonus > 0 else ""

    confirm_text = (
        f"🧾 <b>Заявка на пополнение #{tid}</b>\n\n"
        f"💳 Способ оплаты: <b>{method_name}</b>\n"
        f"💰 Сумма пополнения: <b>{format_currency(amount)}</b>\n"
        f"📉 Комиссия: <b>{fee_text}</b>{bonus_text}\n"
        f"✅ Будет зачислено на баланс: <b>{format_currency(final_credit)}</b>\n\n"
        f"После отправки средств на указанные реквизиты нажмите <b>«✅ Я оплатил»</b>."
    )
    await m.answer(confirm_text, reply_markup=topup_confirm_kb(tid))

@router.callback_query(F.data.startswith("topup_i_paid:"))
async def cb_topup_i_paid(cq: CallbackQuery, bot: Bot):
    await cq.answer()
    tid = int(cq.data.split(":")[1])

    await cq.message.edit_text(
        f"✅ <b>Заявка #{tid} отправлена на проверку!</b>\n\n"
        f"Ожидайте подтверждения администратора. Деньги будут зачислены на баланс сразу после проверки."
    )

    if ADMIN_ID:
        from database import get_topup_request
        from keyboards.admin_kb import admin_topup_card_kb

        req = get_topup_request(tid)
        if req:
            user_tag = f"@{req['username']}" if req['username'] else f"ID: {req['user_id']}"
            method_name = {"card": "💳 Карта", "cash": "💵 Наличные (Paynet)", "crypto": "₿ Криптовалюта"}.get(req["payment_method"], req["payment_method"])

            admin_msg = (
                f"🔔 <b>Новая заявка на пополнение #{tid}!</b>\n\n"
                f"👤 Пользователь: {user_tag}\n"
                f"🆔 Telegram ID: <code>{req['user_id']}</code>\n"
                f"💳 Способ: {method_name}\n"
                f"💰 Введено: <b>{format_currency(req['entered_amount'])}</b>\n"
                f"📉 Комиссия: {format_currency(req['fee_amount'])}\n"
                f"📈 К зачислению: <b>{format_currency(req['final_credit_amount'])}</b>\n"
                f"🕐 Дата: {req['created_at']}"
            )
            try:
                await bot.send_message(ADMIN_ID, admin_msg, reply_markup=admin_topup_card_kb(tid))
            except Exception as e:
                print(f"Failed to notify admin: {e}")

@router.callback_query(F.data.startswith("topup_user_cancel:"))
async def cb_topup_user_cancel(cq: CallbackQuery):
    await cq.answer()
    tid = int(cq.data.split(":")[1])
    await cq.message.edit_text(f"❌ Заявка на пополнение #{tid} отменена.")

# ----------------- Calculator (🧮 Калькулятор) -----------------
@router.message(F.text == "🧮 Калькулятор")
@router.callback_query(F.data == "calc_recalculate")
async def start_calculator(event, state: FSMContext):
    await state.clear()
    await state.set_state(UserStates.waiting_calculator_stars)
    price_val = int(get_setting("price", "220"))

    text = (
        f"🧮 <b>Калькулятор стоимости Stars</b>\n\n"
        f"Текущий курс: <b>1 ⭐ = {format_currency(price_val)}</b>\n\n"
        f"Введите желаемое количество Stars для расчёта (например: <code>150</code>):"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text)
    else:
        await event.answer(text, reply_markup=back_kb())

@router.message(UserStates.waiting_calculator_stars)
async def process_calculator_input(m: Message, state: FSMContext):
    if is_back(m.text):
        await state.clear()
        return await m.answer("Главное меню:", reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

    raw_text = m.text.replace(" ", "").replace("stars", "").replace("Stars", "")
    try:
        n = int(raw_text)
        if n <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Введите положительное целое число Stars.", reply_markup=back_kb())

    price_val = int(get_setting("price", "220"))
    raw_amount = n * price_val

    data = await state.get_data()
    discount_promo = data.get("discount_promo_code")
    discount_pct = data.get("discount_pct", 0)

    disc_amount = 0
    total_amount = raw_amount
    promo_text = ""
    if discount_promo and discount_pct > 0:
        disc_amount = int(raw_amount * discount_pct / 100)
        total_amount = raw_amount - disc_amount
        promo_text = f"\n🎟️ Скидка по промокоду ({discount_pct}%): -{format_currency(disc_amount)}"

    text = (
        f"🧮 <b>Результат расчёта</b>\n\n"
        f"⭐ Количество: <b>{n} Stars</b>\n"
        f"💰 Итоговая стоимость: <b>{format_currency(total_amount)}</b>{promo_text}\n"
        f"📊 Тариф: <b>{format_currency(price_val)} / 1 Star</b>\n\n"
        f"Вы можете сразу перейти к покупке этих Stars или сделать новый расчёт:"
    )
    await m.answer(text, reply_markup=calc_result_kb(n))

@router.callback_query(F.data.startswith("calc_buy:"))
async def cb_calc_buy(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    n = int(cq.data.split(":")[1])

    price_val = int(get_setting("price", "220"))
    raw_amount = n * price_val

    data = await state.get_data()
    discount_promo = data.get("discount_promo_code")
    discount_pct = data.get("discount_pct", 0)

    disc_amount = 0
    total_amount = raw_amount
    if discount_promo and discount_pct > 0:
        disc_amount = int(raw_amount * discount_pct / 100)
        total_amount = raw_amount - disc_amount

    star_cost = int(get_setting("star_cost_price", "180"))
    cost_price = n * star_cost

    await state.update_data(
        order_type="stars",
        stars=n,
        raw_amount=raw_amount,
        amount=total_amount,
        cost_price=cost_price,
        discount_amount=disc_amount,
    )

    await prompt_recipient_choice(cq, state)

# ----------------- Recipient, Anonymity & Signature Helper Steps -----------------
async def prompt_recipient_choice(target_message_or_query, state: FSMContext):
    text = "🎁 <b>Кому предназначен подарок/заказ?</b>"
    kb = recipient_choice_kb()
    if isinstance(target_message_or_query, CallbackQuery):
        await target_message_or_query.message.edit_text(text, reply_markup=kb)
    else:
        await target_message_or_query.answer(text, reply_markup=kb)

@router.callback_query(F.data == "recip:self")
async def cb_recip_self(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.update_data(recipient_type="self", recipient_username=None, is_anonymous=0, gift_signature=None, signature_fee=0)
    data = await state.get_data()
    if data.get("order_type") == "stars":
        await show_final_order_confirmation(cq, state)
    else:
        await prompt_anonymity_choice(cq, state)

@router.callback_query(F.data == "recip:friend")
async def cb_recip_friend(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.update_data(recipient_type="friend")
    await state.set_state(UserStates.waiting_recipient_username)
    await cq.message.answer(
        "Ник пользователя\n\nПример: @1234",
        reply_markup=back_kb()
    )

@router.message(UserStates.waiting_recipient_username)
async def process_recipient_username(m: Message, state: FSMContext):
    if is_back(m.text):
        await state.clear()
        return await m.answer("Главное меню:", reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

    un = m.text.strip()
    if not un.startswith("@") and "t.me" not in un:
        un = "@" + un

    await state.update_data(recipient_username=un, is_anonymous=0, gift_signature=None, signature_fee=0)
    data = await state.get_data()
    if data.get("order_type") == "stars":
        await show_final_order_confirmation(m, state)
    else:
        await prompt_anonymity_choice(m, state)

async def prompt_anonymity_choice(target, state: FSMContext):
    text = "🙈 <b>Желаете сделать подарок/заказ анонимным?</b>"
    kb = anonymity_choice_kb()
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("anon:"))
async def cb_anonymity_selected(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    is_anon = int(cq.data.split(":")[1])
    await state.update_data(is_anonymous=is_anon)
    await prompt_signature_choice(cq, state)

async def prompt_signature_choice(target, state: FSMContext):
    text = "✍️ <b>Желаете добавить подпись к подарку/заказу?</b>"
    kb = signature_choice_kb()
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)

@router.callback_query(F.data == "sig:skip")
async def cb_signature_skip(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.update_data(gift_signature=None, signature_fee=0)
    await show_final_order_confirmation(cq, state)

@router.callback_query(F.data == "sig:add")
async def cb_signature_add(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(UserStates.waiting_gift_signature)
    await cq.message.answer(
        "Введите текст подписи:\n\nПример: Подарок для друга",
        reply_markup=back_kb()
    )

@router.message(UserStates.waiting_gift_signature)
async def process_gift_signature(m: Message, state: FSMContext):
    if is_back(m.text):
        await state.clear()
        return await m.answer("Главное меню:", reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

    await state.update_data(gift_signature=m.text.strip(), signature_fee=1000)
    await show_final_order_confirmation(m, state)

async def show_final_order_confirmation(target, state: FSMContext):
    data = await state.get_data()
    order_type = data.get("order_type", "stars")
    user_id = target.from_user.id if isinstance(target, (Message, CallbackQuery)) else target.from_user.id
    user = get_user(user_id)
    balance = user["balance"] if user else 0

    base_amount = data.get("amount", 0)
    sig_fee = data.get("signature_fee", 0)
    total_amount = base_amount + sig_fee
    has_bal = balance >= total_amount

    recip_type = data.get("recipient_type", "self")
    recip_un = data.get("recipient_username")
    recip_str = "👤 Себе" if recip_type == "self" else f"🎁 Другу ({recip_un or 'Не указан'})"

    if order_type == "stars":
        n = data.get("stars", 0)
        item_desc = f"⭐ <b>{n} Stars</b>"
        kb = stars_buy_kb(has_balance=has_bal, stars=n, price=total_amount, balance=balance)
        extra_details = f"🎁 Получатель: <b>{recip_str}</b>"
    else:
        pid = data.get("product_id")
        product = get_product(pid)
        item_title = product["title"] if product else "Подарок"
        item_desc = f"🎁 <b>{item_title}</b>"
        kb = gift_buy_kb(product_id=pid, has_balance=has_bal)
        anon_str = "🙈 Анонимно" if data.get("is_anonymous") == 1 else "👤 Открыто"
        sig_text = data.get("gift_signature")
        sig_str = f'"{sig_text}" (+1 000 сум)' if sig_text else "Без подписи"
        extra_details = (
            f"🎁 Получатель: <b>{recip_str}</b>\n"
            f"🙈 Отправка: <b>{anon_str}</b>\n"
            f"✍️ Подпись: <b>{sig_str}</b>"
        )

    if not has_bal:
        shortage = total_amount - balance
        text = (
            f"❌ <b>Недостаточно средств на балансе.</b>\n\n"
            f"Товар: {item_desc}\n"
            f"Стоимость: <b>{format_currency(total_amount)}</b>\n"
            f"Ваш баланс: <b>{format_currency(balance)}</b>\n"
            f"Не хватает: <b>{format_currency(shortage)}</b>"
        )
    else:
        text = (
            f"🧾 <b>Подтверждение заказа</b>\n\n"
            f"📦 Состав: {item_desc}\n"
            f"{extra_details}\n\n"
            f"💰 Стоимость: <b>{format_currency(total_amount)}</b>\n"
            f"💰 Ваш баланс: <b>{format_currency(balance)}</b>"
        )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)

# ----------------- Buying Stars (from Balance) -----------------
@router.message(F.text == "⭐ Купить Stars")
async def buy_stars_start(m: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserStates.waiting_stars)

    price_val = int(get_setting("price", "220"))
    min_stars = int(get_setting("min_stars", "50"))
    max_stars = int(get_setting("max_stars", "20000"))

    text = (
        f"⭐ <b>Покупка Telegram Stars</b>\n\n"
        f"Тариф: <b>1 ⭐ = {format_currency(price_val)}</b>\n"
        f"Минимум: <b>{min_stars} Stars</b>\n"
        f"Максимум: <b>{max_stars} Stars</b>\n\n"
        f"Введите желаемое количество Stars (например: <code>123</code>):"
    )
    await m.answer(text, reply_markup=back_kb())

@router.message(UserStates.waiting_stars)
async def process_stars_amount(m: Message, state: FSMContext):
    if is_back(m.text):
        await state.clear()
        return await m.answer("Главное меню:", reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

    raw_text = m.text.replace(" ", "").replace("stars", "").replace("Stars", "")
    try:
        n = int(raw_text)
    except ValueError:
        return await m.answer("❌ Введите целое число Stars.", reply_markup=back_kb())

    min_stars = int(get_setting("min_stars", "50"))
    max_stars = int(get_setting("max_stars", "20000"))

    if not (min_stars <= n <= max_stars):
        return await m.answer(f"❌ Допустимо от {min_stars} до {max_stars} Stars.", reply_markup=back_kb())

    price_val = int(get_setting("price", "220"))
    raw_amount = n * price_val

    data = await state.get_data()
    discount_promo = data.get("discount_promo_code")
    discount_pct = data.get("discount_pct", 0)

    disc_amount = 0
    total_amount = raw_amount
    if discount_promo and discount_pct > 0:
        disc_amount = int(raw_amount * discount_pct / 100)
        total_amount = raw_amount - disc_amount

    star_cost = int(get_setting("star_cost_price", "180"))
    cost_price = n * star_cost

    await state.update_data(
        order_type="stars",
        stars=n,
        raw_amount=raw_amount,
        amount=total_amount,
        cost_price=cost_price,
        discount_amount=disc_amount,
    )

    await prompt_recipient_choice(m, state)

@router.callback_query(F.data == "confirm_buy_stars")
async def cb_confirm_buy_stars(cq: CallbackQuery, state: FSMContext, bot: Bot):
    await cq.answer()
    data = await state.get_data()
    await state.clear()

    stars = data.get("stars", 0)
    base_amount = data.get("amount", 0)
    sig_fee = data.get("signature_fee", 0)
    total_amount = base_amount + sig_fee
    cost_price = data.get("cost_price", 0)
    promo_code = data.get("discount_promo_code")
    discount_amount = data.get("discount_amount", 0)

    recip_type = data.get("recipient_type", "self")
    recip_un = data.get("recipient_username")
    is_anon = data.get("is_anonymous", 0)
    sig = data.get("gift_signature")

    desc = f"Покупка {stars} Stars"
    success = update_user_balance_atomic(
        user_id=cq.from_user.id,
        delta=-total_amount,
        op_type="buy_stars",
        description=desc,
    )

    if not success:
        return await cq.message.edit_text("❌ Недостаточно средств на балансе для совершения покупки.")

    oid = create_order(
        user_id=cq.from_user.id,
        username=cq.from_user.username,
        stars=stars,
        amount=total_amount,
        cost_price=cost_price,
        payment_method="balance",
        status="new",
        promo_code=promo_code,
        discount_amount=discount_amount,
        order_type="stars",
        recipient_type=recip_type,
        recipient_username=recip_un,
        is_anonymous=is_anon,
        gift_signature=sig,
        signature_fee=sig_fee,
    )

    await cq.message.edit_text(
        f"✅ <b>Заказ #{oid} на {stars} Stars успешно оформлен!</b>\n\n"
        f"💰 Списано с баланса: <b>{format_currency(total_amount)}</b>\n"
        f"⚙️ Статус заказа: <b>🆕 Новый</b> (передан оператору)."
    )

    if ADMIN_ID:
        from keyboards.admin_kb import admin_order_card_kb
        user_tag = f"@{cq.from_user.username}" if cq.from_user.username else f"ID: {cq.from_user.id}"
        recip_str = "Себе" if recip_type == "self" else f"Другу ({recip_un or 'Не указан'})"
        anon_str = "🙈 Да" if is_anon == 1 else "👤 Нет"
        sig_str = f'"{sig}" (+1 000 сум)' if sig else "Нет"

        admin_msg = (
            f"🔔 <b>Новый заказ #{oid}!</b>\n\n"
            f"👤 Заказчик: {user_tag}\n"
            f"🎁 Получатель: <b>{recip_str}</b>\n"
            f"🙈 Анонимно: <b>{anon_str}</b>\n"
            f"✍️ Подпись: <b>{sig_str}</b>\n"
            f"⭐ Stars: <b>{stars}</b>\n"
            f"💰 Сумма: <b>{format_currency(total_amount)}</b>\n"
            f"💳 Оплата: Списано с баланса"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_msg, reply_markup=admin_order_card_kb(oid, "new"))
        except Exception as e:
            print(f"Failed to notify admin: {e}")

@router.callback_query(F.data == "cancel_buy_stars")
@router.callback_query(F.data == "cancel_order_flow")
async def cb_cancel_buy_stars(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.clear()
    await cq.message.edit_text("❌ Заказ отменён.")
    await cq.message.answer("Главное меню:", reply_markup=main_kb(is_admin=is_admin(cq.from_user.id)))

# ----------------- Regular Gifts (Подарки) Flow -----------------
@router.message(F.text == "🎁 Купить подарок")
@router.callback_query(F.data == "gifts_list")
async def show_gifts(event, state: FSMContext):
    await state.clear()
    products = get_all_products(available_only=True)
    if not products:
        msg = "🎁 Подарков пока нет в наличии. Зайдите позже!"
        if isinstance(event, CallbackQuery):
            await event.answer()
            return await event.message.edit_text(msg)
        return await event.answer(msg, reply_markup=main_kb(is_admin=is_admin(event.from_user.id)))

    text = "🎁 <b>Выберите подарок для покупки с баланса:</b>"
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, reply_markup=products_kb(products))
    else:
        await event.answer(text, reply_markup=products_kb(products))

@router.callback_query(F.data.startswith("buy_gift:"))
async def cb_buy_gift(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    pid = int(cq.data.split(":")[1])
    product = get_product(pid)
    if not product or product["is_available"] != 1:
        return await cq.message.edit_text("❌ Товар временно недоступен.", reply_markup=main_kb(is_admin=is_admin(cq.from_user.id)))

    stars_match = re.search(r"(\d+)\s*Stars", product["title"], re.IGNORECASE)
    stars_count = int(stars_match.group(1)) if stars_match else 0

    await state.update_data(
        order_type="gift",
        product_id=pid,
        stars=stars_count,
        amount=product["price"],
        cost_price=product["cost_price"],
    )

    await prompt_recipient_choice(cq, state)

@router.callback_query(F.data.startswith("confirm_buy_gift:"))
async def cb_confirm_buy_gift(cq: CallbackQuery, state: FSMContext, bot: Bot):
    await cq.answer()
    data = await state.get_data()
    await state.clear()

    pid = data.get("product_id")
    product = get_product(pid)
    if not product:
        return await cq.message.answer("❌ Товар не найден.")

    stars = data.get("stars", 0)
    base_amount = data.get("amount", product["price"])
    sig_fee = data.get("signature_fee", 0)
    total_amount = base_amount + sig_fee
    cost_price = data.get("cost_price", product["cost_price"])

    recip_type = data.get("recipient_type", "self")
    recip_un = data.get("recipient_username")
    is_anon = data.get("is_anonymous", 0)
    sig = data.get("gift_signature")

    desc = f"Покупка подарка {product['title']}"
    success = update_user_balance_atomic(
        user_id=cq.from_user.id,
        delta=-total_amount,
        op_type="buy_gift",
        description=desc,
    )

    if not success:
        return await cq.message.edit_text("❌ Недостаточно средств на балансе.")

    oid = create_order(
        user_id=cq.from_user.id,
        username=cq.from_user.username,
        stars=stars,
        amount=total_amount,
        cost_price=cost_price,
        payment_method="balance",
        status="new",
        order_type="gift",
        item_id=pid,
        recipient_type=recip_type,
        recipient_username=recip_un,
        is_anonymous=is_anon,
        gift_signature=sig,
        signature_fee=sig_fee,
    )

    await cq.message.edit_text(
        f"✅ <b>Заказ #{oid} на {product['title']} оформлен!</b>\n\n"
        f"💰 Списано с баланса: <b>{format_currency(total_amount)}</b>\n"
        f"⚙️ Статус заказа: <b>🆕 Новый</b>"
    )

    if ADMIN_ID:
        from keyboards.admin_kb import admin_order_card_kb
        user_tag = f"@{cq.from_user.username}" if cq.from_user.username else f"ID: {cq.from_user.id}"
        recip_str = "Себе" if recip_type == "self" else f"Другу ({recip_un or 'Не указан'})"
        anon_str = "🙈 Да" if is_anon == 1 else "👤 Нет"
        sig_str = f'"{sig}" (+1 000 сум)' if sig else "Нет"

        admin_msg = (
            f"🔔 <b>Новый заказ #{oid} (Подарок)!</b>\n\n"
            f"👤 Заказчик: {user_tag}\n"
            f"🎁 Получатель: <b>{recip_str}</b>\n"
            f"🙈 Анонимно: <b>{anon_str}</b>\n"
            f"✍️ Подпись: <b>{sig_str}</b>\n"
            f"🎁 Товар: <b>{product['title']}</b>\n"
            f"💰 Сумма: <b>{format_currency(total_amount)}</b>\n"
            f"💳 Оплата: Списано с баланса"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_msg, reply_markup=admin_order_card_kb(oid, "new"))
        except Exception as e:
            print(f"Failed to notify admin: {e}")

# ----------------- NFT Gifts (💎 Купить NFT-подарок) -----------------
@router.message(F.text == "💎 Купить NFT-подарок")
async def show_nft(m: Message):
    nft_mgr = get_setting("nft_manager", "@YaTochka_pan")
    text = (
        f"Для покупки NFT-подарка напишите нам:\n\n"
        f"<b>{nft_mgr}</b>\n\n"
        f"Цена NFT-подарка определяется индивидуально в переписке.\n\n"
        f"⚠️ Учитывайте, что комиссия за покупку NFT составляет 10% от его стоимости."
    )
    await m.answer(text, reply_markup=nft_kb(nft_mgr))

# ----------------- Promo Codes (🎟 Промокод) -----------------
@router.message(F.text == "🎟 Промокод")
async def menu_promo_start(m: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_promo_code)
    await m.answer("🎟️ <b>Введите промокод для активации:</b>", reply_markup=back_kb())

@router.message(UserStates.waiting_promo_code)
async def process_promo_code(m: Message, state: FSMContext):
    if is_back(m.text):
        await state.clear()
        return await m.answer("Главное меню:", reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

    code = m.text.strip().upper()
    promo = get_promocode(code)

    if not promo or promo["is_active"] != 1:
        return await m.answer("❌ Промокод не существует или отключён.", reply_markup=back_kb())

    if not can_user_use_promo(promo["id"], m.from_user.id):
        return await m.answer("❌ Промокод исчерпал число активаций или уже был использован вами.", reply_markup=back_kb())

    promo_type = promo["type"]
    val = promo["value"]

    if promo_type == "fixed_refill":
        update_user_balance_atomic(
            user_id=m.from_user.id,
            delta=val,
            op_type="fixed_promo",
            description=f"Зачисление по промокоду {code}",
        )
        record_promo_use(promo["id"], code, m.from_user.id)
        await state.clear()
        return await m.answer(
            f"✅ <b>Промокод успешно применён.</b>\n\n"
            f"На ваш баланс зачислено: <b>{format_currency(val)}</b>.",
            reply_markup=main_kb(is_admin=is_admin(m.from_user.id)),
        )

    elif promo_type == "discount":
        await state.update_data(discount_promo_code=code, discount_pct=val)
        await state.clear()
        return await m.answer(
            f"✅ Промокод <code>{code}</code> (Скидка <b>{val}%</b>) успешно активирован! Он будет применён при следующей покупке Stars или подарка.",
            reply_markup=main_kb(is_admin=is_admin(m.from_user.id)),
        )

    elif promo_type == "deposit_bonus":
        await state.update_data(deposit_promo_code=code, deposit_bonus_pct=val)
        await state.clear()
        return await m.answer(
            f"✅ Промокод <code>{code}</code> (Бонус <b>+{val}%</b> на пополнение) активирован! Он будет применён при следующем пополнении баланса.",
            reply_markup=main_kb(is_admin=is_admin(m.from_user.id)),
        )

# ----------------- Orders List & Support -----------------
@router.message(F.text == "📋 Мои заказы")
async def show_my_orders(m: Message):
    orders = get_user_orders(m.from_user.id, limit=20)
    if not orders:
        return await m.answer("📋 У вас пока нет заказов.", reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

    text = "📋 <b>Ваши заказы:</b>\n\n"
    for r in orders:
        item = f"⭐ {r['stars']} Stars" if r["order_type"] == "stars" else "🎁 Подарок"
        recip = "👤 Себе" if r.get("recipient_type") != "friend" else f"🎁 Другу ({r.get('recipient_username') or ''})"
        anon = " (🙈 Анонимно)" if r.get("is_anonymous") == 1 else ""
        text += f"<b>Заказ #{r['id']}</b> — {item}\n"
        text += f"Получатель: {recip}{anon}\n"
        text += f"💰 {format_currency(r['amount'])} | Status: {status_text(r['status'])}\n\n"

    await m.answer(text, reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))

@router.message(F.text == "💬 Поддержка")
async def show_support(m: Message):
    support_username = get_setting("support_username", "@YaTochka_pan")
    hours = get_setting("working_hours", "09:00 - 23:00")
    text = (
        f"💬 <b>Служба поддержки KAW Star</b>\n\n"
        f"Если у вас возникли вопросы по заказам или пополнению баланса, свяжитесь с оператором:\n\n"
        f"👤 Оператор: <b>{support_username}</b>\n"
        f"🕐 Рабочие часы: <b>{hours}</b>"
    )
    await m.answer(text, reply_markup=main_kb(is_admin=is_admin(m.from_user.id)))
