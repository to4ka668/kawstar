import asyncio
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import (
    get_setting,
    set_setting,
    get_user,
    get_user_by_username,
    get_all_users,
    get_order,
    get_orders_by_status,
    update_order_status,
    get_statistics,
    get_all_products,
    get_product,
    add_product,
    update_product_availability,
    delete_product,
    get_all_promocodes,
    add_promocode,
    toggle_promocode,
    get_all_user_ids,
    get_pending_topups,
    get_topup_request,
    approve_topup_request,
    reject_topup_request,
    update_user_balance_atomic,
    get_user_operations,
    get_user_orders,
)
from states.admin_states import AdminStates
from keyboards.admin_kb import (
    admin_main_kb,
    admin_orders_filter_kb,
    admin_orders_search_kb,
    admin_order_card_kb,
    admin_topup_card_kb,
    admin_user_card_kb,
    admin_promo_type_kb,
    admin_promos_kb,
    admin_products_kb,
    admin_product_card_kb,
    admin_requisites_menu_kb,
    admin_cancel_state_kb,
)
from services.utils import status_text, format_currency, is_admin

router = Router()

def check_admin(event) -> bool:
    user_id = event.from_user.id
    return is_admin(user_id)

def build_order_card_text(r) -> str:
    user_tag = f"@{r['username']}" if r["username"] else f"ID: {r['user_id']}"
    item_str = f"⭐ {r['stars']} Stars" if r["order_type"] == "stars" else f"🎁 Подарок #{r['item_id'] or ''}"
    recip_type = r.get("recipient_type") or "self"
    recip_un = r.get("recipient_username")
    recip_str = "👤 Себе" if recip_type == "self" else f"🎁 Другу ({recip_un or 'Не указан'})"
    anon_str = "🙈 Да" if r.get("is_anonymous") == 1 else "👤 Нет"
    sig_val = r.get("gift_signature")
    sig_str = f'"{sig_val}"' if sig_val else "Нет"

    return (
        f"<b>Заказ #{r['id']}</b>\n"
        f"👤 Заказчик: {user_tag}\n"
        f"🆔 Telegram ID: <code>{r['user_id']}</code>\n"
        f"🎁 Получатель: <b>{recip_str}</b>\n"
        f"🙈 Анонимно: <b>{anon_str}</b>\n"
        f"✍️ Подпись: <b>{sig_str}</b>\n"
        f"📦 Состав: {item_str}\n"
        f"💰 Сумма: <b>{format_currency(r['amount'])}</b>\n"
        f"🕐 Создан: {r['created_at']}\n"
        f"📦 Статус: <b>{status_text(r['status'])}</b>"
    )

# ----------------- Command /admin & Main Navigation -----------------
@router.message(Command("admin"))
@router.message(F.text == "👨‍💼 Админ-панель")
async def cmd_admin(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    await state.clear()
    await m.answer("<b>👨‍💼 KAW Star — Панель администратора</b>", reply_markup=admin_main_kb())

@router.callback_query(F.data == "a:main")
async def cb_admin_main(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.clear()
    await cq.message.edit_text("<b>👨‍💼 KAW Star — Панель администратора</b>", reply_markup=admin_main_kb())

@router.callback_query(F.data == "a:cancel_state")
async def cb_cancel_state(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.clear()
    await cq.message.edit_text("Действие отменено.", reply_markup=admin_main_kb())

# ----------------- Top-Ups Management (💰 Пополнения) -----------------
@router.callback_query(F.data == "a:topups")
async def cb_admin_topups(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)

    topups = get_pending_topups(limit=20)
    if not topups:
        return await cq.message.edit_text("💰 <b>Активных заявок на пополнение нет.</b>", reply_markup=admin_main_kb())

    await cq.message.edit_text(f"💰 <b>Заявки на пополнение ({len(topups)}):</b>")
    for r in topups:
        user_tag = f"@{r['username']}" if r["username"] else f"ID: {r['user_id']}"
        method_lbl = {"card": "💳 Карта", "cash": "💵 Paynet (Наличные)", "crypto": "₿ Криптовалюта"}.get(r["payment_method"], r["payment_method"])

        text = (
            f"<b>Заявка на пополнение #{r['id']}</b>\n"
            f"👤 Пользователь: {user_tag}\n"
            f"🆔 Telegram ID: <code>{r['user_id']}</code>\n"
            f"💳 Способ: {method_lbl}\n"
            f"💰 Введённая сумма: <b>{format_currency(r['entered_amount'])}</b>\n"
            f"📉 Комиссия: {format_currency(r['fee_amount'])}\n"
            f"📈 К зачислению: <b>{format_currency(r['final_credit_amount'])}</b>\n"
            f"🕐 Время: {r['created_at']}"
        )
        await cq.message.answer(text, reply_markup=admin_topup_card_kb(r["id"]))
    await cq.answer()

@router.callback_query(F.data.startswith("adm_topup:"))
async def cb_adm_topup_action(cq: CallbackQuery, state: FSMContext, bot: Bot):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)

    _, action, tid_str = cq.data.split(":")
    tid = int(tid_str)

    req = get_topup_request(tid)
    if not req or req["status"] != "pending":
        return await cq.answer("Заявка уже обработана или не найдена.", show_alert=True)

    if action == "approve":
        success = approve_topup_request(tid, admin_id=cq.from_user.id)
        if success:
            await cq.answer("Заявка одобрена, средства зачислены.")
            await cq.message.edit_text(f"✅ <b>Заявка #{tid} одобрена!</b> Зачислено: <b>{format_currency(req['final_credit_amount'])}</b>")
            try:
                await bot.send_message(
                    req["user_id"],
                    f"✅ <b>Баланс успешно пополнен!</b>\n\nНа ваш баланс зачислено: <b>{format_currency(req['final_credit_amount'])}</b>."
                )
            except Exception as e:
                print(f"Failed to notify user {req['user_id']}: {e}")
        else:
            await cq.answer("Ошибка при зачислении.", show_alert=True)

    elif action == "reject":
        reject_topup_request(tid, admin_id=cq.from_user.id)
        await cq.answer("Заявка отклонена.")
        await cq.message.edit_text(f"❌ <b>Заявка #{tid} отклонена.</b>")
        try:
            await bot.send_message(req["user_id"], f"❌ Ваша заявка на пополнение #{tid} была отклонена администратором.")
        except Exception:
            pass

    elif action == "custom":
        await state.update_data(custom_topup_id=tid)
        await state.set_state(AdminStates.waiting_custom_topup_amount)
        await cq.message.edit_text(
            f"✏️ <b>Изменение суммы зачисления для заявки #{tid}</b>\n\n"
            f"Текущая сумма пополнения: {format_currency(req['entered_amount'])}\n"
            f"Рассчитанная сумма: {format_currency(req['final_credit_amount'])}\n\n"
            f"Введите сумму, которая ФАКТИЧЕСКИ будет зачислена на баланс (в сумах):",
            reply_markup=admin_cancel_state_kb()
        )

@router.message(AdminStates.waiting_custom_topup_amount)
async def process_custom_topup_amount(m: Message, state: FSMContext, bot: Bot):
    if not check_admin(m):
        return
    try:
        amt = int(m.text.replace(" ", ""))
        if amt <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Введите положительное целое число.", reply_markup=admin_cancel_state_kb())

    data = await state.get_data()
    tid = data.get("custom_topup_id")
    req = get_topup_request(tid)

    if not req or req["status"] != "pending":
        await state.clear()
        return await m.answer("❌ Заявка не найдена или уже обработана.", reply_markup=admin_main_kb())

    approve_topup_request(tid, custom_credit_amount=amt, admin_id=m.from_user.id)
    await state.clear()
    await m.answer(f"✅ <b>Заявка #{tid} одобрена!</b> Зачислено: <b>{format_currency(amt)}</b>", reply_markup=admin_main_kb())

    try:
        await bot.send_message(
            req["user_id"],
            f"✅ <b>Баланс успешно пополнен!</b>\n\nНа ваш баланс зачислено: <b>{format_currency(amt)}</b>."
        )
    except Exception:
        pass

# ----------------- Users Management (👥 Пользователи) -----------------
@router.callback_query(F.data == "a:users")
async def cb_admin_users(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.clear()

    users = get_all_users(limit=20)
    text = (
        f"👥 <b>Управление пользователями</b>\n\n"
        f"Всего пользователей в базе: {len(users)}\n\n"
        f"Чтобы найти конкретного пользователя, отправьте его Telegram ID или @username."
    )
    await state.set_state(AdminStates.waiting_user_search)
    await cq.message.edit_text(text, reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.waiting_user_search)
async def process_user_search(m: Message, state: FSMContext):
    if not check_admin(m):
        return

    query = m.text.strip()
    user = None
    if query.isdigit():
        user = get_user(int(query))
    else:
        user = get_user_by_username(query)

    if not user:
        return await m.answer("❌ Пользователь не найден. Попробуйте еще раз или нажмите отмена.", reply_markup=admin_cancel_state_kb())

    await state.clear()

    orders = get_user_orders(user["user_id"], limit=500)
    user_tag = f"@{user['username']}" if user["username"] else "Не задан"

    card_text = (
        f"👤 <b>Карточка пользователя #{user['user_id']}</b>\n\n"
        f"Имя: <b>{user['first_name']}</b>\n"
        f"Username: <b>{user_tag}</b>\n"
        f"Telegram ID: <code>{user['user_id']}</code>\n\n"
        f"💰 Баланс: <b>{format_currency(user['balance'])}</b>\n"
        f"📦 Заказов: <b>{len(orders)}</b>\n"
        f"⭐ Куплено Stars: <b>{user['total_stars']:,}</b>\n"
        f"💳 Пополнено: <b>{format_currency(user['total_topups'])}</b>\n"
        f"🛒 Потрачено: <b>{format_currency(user['total_spent'])}</b>\n"
        f"Дата регистрации: {user['created_at']}"
    )
    await m.answer(card_text, reply_markup=admin_user_card_kb(user["user_id"]))

@router.callback_query(F.data.startswith("adm_usr:"))
async def cb_adm_usr_action(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)

    _, action, uid_str = cq.data.split(":")
    uid = int(uid_str)
    user = get_user(uid)

    if not user:
        return await cq.answer("Пользователь не найден.", show_alert=True)

    if action == "credit":
        await state.update_data(target_user_id=uid, manual_mode="credit")
        await state.set_state(AdminStates.waiting_manual_balance_amount)
        await cq.message.edit_text(
            f"➕ <b>Ручное пополнение баланса</b> для {user['first_name']} (ID: {uid})\n\n"
            f"Текущий баланс: {format_currency(user['balance'])}\n\n"
            f"Введите сумму пополнения в сумах:",
            reply_markup=admin_cancel_state_kb()
        )

    elif action == "debit":
        await state.update_data(target_user_id=uid, manual_mode="debit")
        await state.set_state(AdminStates.waiting_manual_balance_amount)
        await cq.message.edit_text(
            f"➖ <b>Ручное списание с баланса</b> для {user['first_name']} (ID: {uid})\n\n"
            f"Текущий баланс: {format_currency(user['balance'])}\n\n"
            f"Введите сумму списания в сумах:",
            reply_markup=admin_cancel_state_kb()
        )

    elif action == "ops":
        ops = get_user_operations(uid, limit=20)
        if not ops:
            return await cq.message.answer(f"📋 У пользователя ID {uid} пока нет операций.")

        text = f"📋 <b>История операций пользователя ID {uid}:</b>\n\n"
        for o in ops:
            sign = "+" if o["amount"] > 0 else ""
            text += f"• <b>#{o['id']}</b> | {o['created_at']}\n  {o['description']} — <b>{sign}{format_currency(o['amount'])}</b>\n\n"
        await cq.message.answer(text)

@router.message(AdminStates.waiting_manual_balance_amount)
async def process_manual_balance(m: Message, state: FSMContext, bot: Bot):
    if not check_admin(m):
        return

    try:
        amt = int(m.text.replace(" ", ""))
        if amt <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Введите положительное целое число.", reply_markup=admin_cancel_state_kb())

    data = await state.get_data()
    uid = data["target_user_id"]
    mode = data["manual_mode"]

    delta = amt if mode == "credit" else -amt
    op_type = "admin_credit" if mode == "credit" else "admin_debit"
    desc = f"Ручное {'пополнение' if mode == 'credit' else 'списание'} администратором"

    success = update_user_balance_atomic(
        user_id=uid,
        delta=delta,
        op_type=op_type,
        description=desc,
        admin_id=m.from_user.id,
    )

    await state.clear()
    if not success:
        return await m.answer("❌ Ошибка: Недостаточно баланса для списания.", reply_markup=admin_main_kb())

    action_name = "пополнен" if mode == "credit" else "уменьшен"
    await m.answer(f"✅ Баланс пользователя ID {uid} успешно {action_name} на <b>{format_currency(amt)}</b>!", reply_markup=admin_main_kb())

    try:
        msg = f"💳 Администратор {action_name} ваш баланс на <b>{format_currency(amt)}</b>."
        await bot.send_message(uid, msg)
    except Exception:
        pass

# ----------------- Orders Section (📦 Заказы) -----------------
@router.callback_query(F.data == "a:orders")
async def cb_admin_orders_menu(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.waiting_order_search)
    recent = get_orders_by_status(limit=10)
    text = (
        "<b>📦 Управление заказами</b>\n\n"
        "Какой заказ вы хотите посмотреть?\n\n"
        "Отправьте номер заказа в чат (например: <code>1</code>) или выберите из списка ниже:"
    )
    await cq.message.edit_text(text, reply_markup=admin_orders_search_kb(recent))

@router.message(AdminStates.waiting_order_search)
async def process_order_search(m: Message, state: FSMContext):
    if not check_admin(m):
        return

    query = m.text.strip().replace("#", "")
    if not query.isdigit():
        return await m.answer("❌ Пожалуйста, введите числовой номер заказа (например: 1).", reply_markup=admin_cancel_state_kb())

    oid = int(query)
    order = get_order(oid)
    if not order:
        return await m.answer(f"❌ Заказ #{oid} не найден.", reply_markup=admin_cancel_state_kb())

    await state.clear()
    card_text = build_order_card_text(order)
    await m.answer(card_text, reply_markup=admin_order_card_kb(order["id"], order["status"]))

@router.callback_query(F.data.startswith("adm_view_ord:"))
async def cb_admin_view_order(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.clear()
    oid = int(cq.data.split(":")[1])
    order = get_order(oid)
    if not order:
        return await cq.answer("Заказ не найден.", show_alert=True)

    card_text = build_order_card_text(order)
    await cq.message.answer(card_text, reply_markup=admin_order_card_kb(order["id"], order["status"]))
    await cq.answer()

@router.callback_query(F.data.startswith("a:ord_flt:"))
async def cb_admin_orders_filter(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.clear()

    flt = cq.data.split(":")[2]
    status_map = {
        "new": "new",
        "work": "in_work",
        "done": "completed",
        "cancelled": "cancelled",
        "all": None,
    }

    status_filter = status_map.get(flt)
    orders = get_orders_by_status(status_filter=status_filter, limit=20)

    if not orders:
        return await cq.message.edit_text("Заказов по выбранному фильтру не найдено.", reply_markup=admin_orders_filter_kb())

    await cq.message.edit_text(f"<b>📦 Заказы ({len(orders)}):</b>")
    for r in orders:
        card_text = build_order_card_text(r)
        await cq.message.answer(card_text, reply_markup=admin_order_card_kb(r["id"], r["status"]))
    await cq.answer()

@router.callback_query(F.data.startswith("adm_ord:"))
async def cb_change_order_status(cq: CallbackQuery, bot: Bot):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)

    _, action, oid_str = cq.data.split(":")
    oid = int(oid_str)

    new_status_map = {
        "work": "in_work",
        "done": "completed",
        "cancel": "cancelled",
    }
    new_status = new_status_map.get(action, "new")

    order = get_order(oid)
    if not order:
        return await cq.answer("Заказ не найден", show_alert=True)

    update_order_status(oid, new_status)

    item_str = f"⭐ {order['stars']} Stars" if order["order_type"] == "stars" else "🎁 Подарок"
    notify_text = (
        f"📦 <b>Заказ #{oid} ({item_str})</b>\n\n"
        f"Статус вашего заказа изменён:\n"
        f"👉 <b>{status_text(new_status)}</b>"
    )
    try:
        await bot.send_message(order["user_id"], notify_text)
    except Exception as e:
        print(f"Failed to send status update: {e}")

    if action == "done":
        await cq.answer(f"✅ Заказ #{oid} завершён и удалён из чата.", show_alert=True)
        try:
            await cq.message.delete()
        except Exception:
            pass
    else:
        await cq.answer(f"Статус заказа #{oid} обновлён: {status_text(new_status)}")
        try:
            await cq.message.edit_reply_markup(reply_markup=admin_order_card_kb(oid, new_status))
        except Exception:
            pass

# ----------------- Stars & Prices Management (⭐ Stars, 💵 Цены) -----------------
@router.callback_query(F.data.in_({"a:stars_price", "a:prices_menu"}))
async def cb_admin_price(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)

    cur_price = get_setting("price", "220")
    cur_cost = get_setting("star_cost_price", "180")

    text = (
        f"💵 <b>Управление ценами</b>\n\n"
        f"⭐ Цена продажи 1 ⭐: <b>{format_currency(int(cur_price))}</b>\n"
        f"📈 Себестоимость 1 ⭐: <b>{format_currency(int(cur_cost))}</b>\n\n"
        f"<i>Себестоимость используется для автоматического расчёта затрат на Stars и подарки при подсчёте чистой прибыли.</i>"
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    k = InlineKeyboardBuilder()
    k.button(text="✏️ Изменить цену продажи ⭐", callback_data="a:edit_price")
    k.button(text="📈 Изменить себестоимость ⭐", callback_data="a:edit_star_cost")
    k.button(text="🎁 Изменить цены подарков", callback_data="a:gifts")
    k.button(text="◀️ Админ-меню", callback_data="a:main")
    k.adjust(1, 1, 1, 1)

    await cq.message.edit_text(text, reply_markup=k.as_markup())

@router.callback_query(F.data == "a:edit_price")
async def cb_edit_price(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.waiting_price)
    await cq.message.edit_text("⭐ Введите новую цену продажи 1 Star в сумах (сейчас 220):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.waiting_price)
async def process_new_price(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    try:
        v = int(m.text.replace(" ", ""))
        if v <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Введите положительное число.", reply_markup=admin_cancel_state_kb())

    set_setting("price", str(v))
    await state.clear()
    await m.answer(f"✅ Цена продажи 1 Star установлена: <b>{format_currency(v)}</b>", reply_markup=admin_main_kb())

@router.callback_query(F.data == "a:edit_star_cost")
async def cb_edit_star_cost(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.waiting_star_cost_price)
    await cq.message.edit_text("📈 Введите себестоимость 1 Star в сумах (сейчас 180):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.waiting_star_cost_price)
async def process_new_star_cost(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    try:
        v = int(m.text.replace(" ", ""))
        if v <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Введите положительное число.", reply_markup=admin_cancel_state_kb())

    set_setting("star_cost_price", str(v))
    await state.clear()
    await m.answer(f"✅ Себестоимость 1 Star установлена: <b>{format_currency(v)}</b>", reply_markup=admin_main_kb())

# ----------------- Gifts (Products) CRUD -----------------
@router.callback_query(F.data == "a:gifts")
async def cb_admin_gifts(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.clear()
    products = get_all_products(available_only=False)
    await cq.message.edit_text("🎁 <b>Управление подарками:</b>", reply_markup=admin_products_kb(products))

@router.callback_query(F.data.startswith("a_prod:view:"))
async def cb_admin_product_view(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    pid = int(cq.data.split(":")[2])
    p = get_product(pid)
    if not p:
        return await cq.answer("Товар не найден", show_alert=True)

    status_str = "🟢 Доступен" if p["is_available"] == 1 else "🔴 Скрыт"
    text = (
        f"🎁 <b>Товар #{p['id']} — {p['title']}</b>\n\n"
        f"💰 Цена продажи: <b>{format_currency(p['price'])}</b>\n"
        f"📈 Себестоимость: <b>{format_currency(p['cost_price'])}</b>\n"
        f"📦 Статус: <b>{status_str}</b>\n"
        f"📝 Описание: {p['description'] or 'Отсутствует'}"
    )
    await cq.message.edit_text(text, reply_markup=admin_product_card_kb(pid, p["is_available"]))

@router.callback_query(F.data.startswith("a_prod:toggle:"))
async def cb_admin_product_toggle(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    pid = int(cq.data.split(":")[2])
    p = get_product(pid)
    if p:
        new_avail = 0 if p["is_available"] == 1 else 1
        update_product_availability(pid, new_avail)
        await cq.answer("Статус подарка изменён.")
        products = get_all_products(available_only=False)
        await cq.message.edit_text("🎁 <b>Управление подарками:</b>", reply_markup=admin_products_kb(products))

@router.callback_query(F.data.startswith("a_prod:delete:"))
async def cb_admin_product_delete(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    pid = int(cq.data.split(":")[2])
    delete_product(pid)
    await cq.answer("Товар удалён.")
    products = get_all_products(available_only=False)
    await cq.message.edit_text("🎁 <b>Управление подарками:</b>", reply_markup=admin_products_kb(products))

@router.callback_query(F.data == "a_prod:add")
async def cb_admin_product_add(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.add_product_title)
    await cq.message.edit_text("🎁 Введите название подарка (например: <code>🎁 150 Stars</code>):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.add_product_title)
async def process_prod_title(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    await state.update_data(title=m.text.strip())
    await state.set_state(AdminStates.add_product_price)
    await m.answer("💰 Введите цену продажи подарка в сумах (например: <code>54000</code>):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.add_product_price)
async def process_prod_price(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    try:
        p = int(m.text.replace(" ", ""))
    except ValueError:
        return await m.answer("❌ Введите целое число.", reply_markup=admin_cancel_state_kb())
    await state.update_data(price=p)
    await state.set_state(AdminStates.add_product_cost)
    await m.answer("📈 Введите себестоимость подарка в сумах (например: <code>27000</code>):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.add_product_cost)
async def process_prod_cost(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    try:
        cp = int(m.text.replace(" ", ""))
    except ValueError:
        return await m.answer("❌ Введите целое число.", reply_markup=admin_cancel_state_kb())
    await state.update_data(cost_price=cp)
    await state.set_state(AdminStates.add_product_desc)
    await m.answer("📝 Введите описание подарка (или `-` для пропуска):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.add_product_desc)
async def process_prod_desc(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    desc = m.text.strip() if m.text.strip() != "-" else ""
    data = await state.get_data()

    pid = add_product(
        title=data["title"],
        price=data["price"],
        cost_price=data["cost_price"],
        description=desc,
        image_id=None,
        is_available=1,
    )
    await state.clear()
    await m.answer(f"✅ Подарок <b>{data['title']}</b> успешно добавлен (ID #{pid})!", reply_markup=admin_main_kb())

# ----------------- NFT Settings (💎 NFT) -----------------
@router.callback_query(F.data == "a:nft")
async def cb_admin_nft(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    nft_mgr = get_setting("nft_manager", "@YaTochka_pan")
    text = (
        f"💎 <b>Управление NFT-подарками</b>\n\n"
        f"Текущий менеджер для NFT заявок: <b>{nft_mgr}</b>\n"
        f"Комиссия на NFT: <b>10%</b>\n\n"
        f"Покупка NFT осуществляется через личную переписку с менеджером."
    )
    await cq.message.edit_text(text, reply_markup=admin_main_kb())

# ----------------- Promocodes (🎟 Промокоды) -----------------
@router.callback_query(F.data == "a:promos")
async def cb_admin_promos(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.clear()
    promos = get_all_promocodes()
    await cq.message.edit_text("🎟 <b>Управление промокодами:</b>", reply_markup=admin_promos_kb(promos))

@router.callback_query(F.data.startswith("a_promo:toggle:"))
async def cb_admin_promo_toggle(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    pid = int(cq.data.split(":")[2])
    toggle_promocode(pid)
    await cq.answer("Статус промокода изменён.")
    promos = get_all_promocodes()
    await cq.message.edit_text("🎟 <b>Управление промокодами:</b>", reply_markup=admin_promos_kb(promos))

@router.callback_query(F.data == "a_promo:add")
async def cb_admin_promo_add(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.add_promo_code)
    await cq.message.edit_text("🎟 Введите название промокода (например: <code>BALANCE10K</code> или <code>STAR10</code>):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.add_promo_code)
async def process_promo_code_name(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    await state.update_data(code=m.text.strip().upper())
    await state.set_state(AdminStates.add_promo_type)
    await m.answer("Выберите тип промокода:", reply_markup=admin_promo_type_kb())

@router.callback_query(F.data.startswith("promo_type:"))
async def cb_promo_type_selected(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    ptype = cq.data.split(":")[1]
    await state.update_data(promo_type=ptype)
    await state.set_state(AdminStates.add_promo_value)

    if ptype == "discount":
        prompt = "📊 Введите процент скидки на покупку (1-100, например: <code>10</code>):"
    elif ptype == "deposit_bonus":
        prompt = "🎁 Введите процент бонуса при пополнении (1-100, например: <code>10</code>):"
    else:  # fixed_refill
        prompt = "💰 Введите сумму зачисления на баланс в сумах (например: <code>10000</code>):"

    await cq.message.edit_text(prompt, reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.add_promo_value)
async def process_promo_value(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    try:
        val = int(m.text.strip())
        if val <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Введите положительное число.", reply_markup=admin_cancel_state_kb())

    await state.update_data(value=val)
    await state.set_state(AdminStates.add_promo_max_uses)
    await m.answer("🔢 Введите максимальное число активаций промокода (например: <code>100</code>):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.add_promo_max_uses)
async def process_promo_max_uses(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    try:
        mu = int(m.text.strip())
        if mu <= 0:
            raise ValueError
    except ValueError:
        return await m.answer("❌ Введите положительное число.", reply_markup=admin_cancel_state_kb())

    data = await state.get_data()
    add_promocode(
        code=data["code"],
        promo_type=data["promo_type"],
        value=data["value"],
        max_uses=mu,
    )
    await state.clear()
    await m.answer(f"✅ Промокод <code>{data['code']}</code> успешно создан!", reply_markup=admin_main_kb())

# ----------------- Requisites Management (💳 Реквизиты) -----------------
@router.callback_query(F.data == "a:reqs")
async def cb_admin_requisites(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)

    card = get_setting("card_requisites", "5614 6835 1296 6896")
    paynet = get_setting("paynet_requisites", "+998881400008")
    crypto_addr = get_setting("crypto_address", "UQAfQ6LWkNS7_p7QlTIWgJJd3cvWLrJr8Hl6gqyZ73Zw8j8w")
    crypto_net = get_setting("crypto_network", "Gramm (ex. TON)")

    text = (
        f"💳 <b>Настройка реквизитов для пополнения</b>\n\n"
        f"<b>1. Карта:</b>\n<code>{card}</code>\n\n"
        f"<b>2. Paynet / Наличные:</b>\n<code>{paynet}</code>\n\n"
        f"<b>3. Криптовалюта:</b>\nАдрес: <code>{crypto_addr}</code>\nСеть: <b>{crypto_net}</b>"
    )
    await cq.message.edit_text(text, reply_markup=admin_requisites_menu_kb())

@router.callback_query(F.data == "a:edit_req_card")
async def cb_edit_req_card(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.waiting_card_requisites)
    await cq.message.edit_text("💳 Отправьте новый номер карты (например: <code>5614 6835 1296 6896</code>):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.waiting_card_requisites)
async def process_req_card(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    set_setting("card_requisites", m.text.strip())
    await state.clear()
    await m.answer("✅ Реквизиты карты обновлены!", reply_markup=admin_main_kb())

@router.callback_query(F.data == "a:edit_req_paynet")
async def cb_edit_req_paynet(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.waiting_paynet_requisites)
    await cq.message.edit_text("💵 Отправьте новый номер телефона для Paynet (например: <code>+998881400008</code>):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.waiting_paynet_requisites)
async def process_req_paynet(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    set_setting("paynet_requisites", m.text.strip())
    await state.clear()
    await m.answer("✅ Реквизиты Paynet обновлены!", reply_markup=admin_main_kb())

@router.callback_query(F.data == "a:edit_req_crypto")
async def cb_edit_req_crypto(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.waiting_crypto_address)
    await cq.message.edit_text("₿ Отправьте новый адрес крипто-кошелька:", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.waiting_crypto_address)
async def process_req_crypto_address(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    set_setting("crypto_address", m.text.strip())
    await state.set_state(AdminStates.waiting_crypto_network)
    await m.answer("₿ Введите название сети (например: <code>Gramm (ex. TON)</code>):", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.waiting_crypto_network)
async def process_req_crypto_network(m: Message, state: FSMContext):
    if not check_admin(m):
        return
    set_setting("crypto_network", m.text.strip())
    await state.clear()
    await m.answer("✅ Крипто-реквизиты и сеть обновлены!", reply_markup=admin_main_kb())

# ----------------- Statistics (📊 Статистика) -----------------
@router.callback_query(F.data == "a:stats")
async def cb_admin_stats(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)

    stats = get_statistics()
    text = (
        f"📊 <b>Статистика магазина KAW Star</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"📦 Всего заказов: <b>{stats['total_orders']}</b>\n"
        f"✅ Выполнено: <b>{stats['completed_orders']}</b>\n"
        f"❌ Отменено: <b>{stats['cancelled_orders']}</b>\n"
        f"⭐ Продано Stars: <b>{stats['total_stars']:,}</b>\n"
        f"🎁 Продано подарков: <b>{stats['gifts_count']}</b>\n\n"
        f"💳 Всего пополнений: <b>{format_currency(stats['total_topups'])}</b>\n"
        f"💰 Выручка: <b>{format_currency(stats['revenue'])}</b>\n"
        f"📈 Себестоимость: <b>{format_currency(stats['cost'])}</b>\n"
        f"🔥 <b>Прибыль: {format_currency(stats['profit'])}</b>"
    )
    await cq.message.edit_text(text, reply_markup=admin_main_kb())

# ----------------- Broadcast & Settings -----------------
@router.callback_query(F.data == "a:broadcast")
async def cb_admin_broadcast(cq: CallbackQuery, state: FSMContext):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminStates.waiting_broadcast)
    await cq.message.edit_text("📢 Отправьте текст сообщения для рассылки всем пользователям:", reply_markup=admin_cancel_state_kb())

@router.message(AdminStates.waiting_broadcast)
async def process_broadcast(m: Message, state: FSMContext, bot: Bot):
    if not check_admin(m):
        return
    await state.clear()
    user_ids = get_all_user_ids()
    if not user_ids:
        return await m.answer("❌ Пользователей нет.", reply_markup=admin_main_kb())

    success = 0
    failed = 0
    await m.answer(f"⏳ Запуск рассылки по {len(user_ids)} пользователям...")
    for uid in user_ids:
        try:
            await bot.send_message(uid, m.text)
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1

    await m.answer(f"📢 <b>Рассылка завершена!</b>\n\nУспешно: <b>{success}</b>\nОшибок: <b>{failed}</b>", reply_markup=admin_main_kb())

@router.callback_query(F.data == "a:settings")
async def cb_admin_settings(cq: CallbackQuery):
    if not check_admin(cq):
        return await cq.answer("Нет доступа", show_alert=True)

    support = get_setting("support_username", "@YaTochka_pan")
    hours = get_setting("working_hours", "09:00 - 23:00")
    min_s = get_setting("min_stars", "50")
    max_s = get_setting("max_stars", "20000")

    text = (
        f"⚙️ <b>Настройки магазина KAW Star</b>\n\n"
        f"💬 Поддержка: <b>{support}</b>\n"
        f"🕐 Рабочие часы: <b>{hours}</b>\n"
        f"🔻 Мин. Stars: <b>{min_s}</b>\n"
        f"🔺 Макс. Stars: <b>{max_s}</b>"
    )
    await cq.message.edit_text(text, reply_markup=admin_main_kb())
