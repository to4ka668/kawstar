from config import ADMIN_ID

def status_text(s: str) -> str:
    mapping = {
        "new": "🆕 Новый",
        "pending_payment": "💳 Ожидает оплаты",
        "paid": "💰 Оплачен",
        "work": "⚙️ В работе",
        "in_work": "⚙️ В работе",
        "done": "✅ Выполнен",
        "completed": "✅ Выполнен",
        "cancelled": "❌ Отменён",
        "cancel": "❌ Отменён",
    }
    return mapping.get(str(s).lower(), str(s))

def format_currency(amount: int) -> str:
    try:
        return f"{int(amount):,}".replace(",", " ") + " сум"
    except (ValueError, TypeError):
        return f"{amount} сум"

def is_admin(user_id: int) -> bool:
    if not ADMIN_ID:
        return False
    return int(user_id) == ADMIN_ID
