import sqlite3
from datetime import datetime
from config import (
    DB_NAME,
    DEFAULT_PRICE,
    DEFAULT_STAR_COST_PRICE,
    DEFAULT_MIN_STARS,
    DEFAULT_MAX_STARS,
)

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Settings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # 2. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 0,
            total_topups INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            total_stars INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    # Migration check for users table
    user_cols = [row["name"] for row in cursor.execute("PRAGMA table_info(users)").fetchall()]
    user_additions = {
        "balance": "INTEGER DEFAULT 0",
        "total_topups": "INTEGER DEFAULT 0",
        "total_spent": "INTEGER DEFAULT 0",
        "total_stars": "INTEGER DEFAULT 0",
    }
    for col_name, col_def in user_additions.items():
        if col_name not in user_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")

    # 3. Top-Up Requests Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            payment_method TEXT NOT NULL,
            entered_amount INTEGER NOT NULL,
            fee_amount INTEGER DEFAULT 0,
            net_amount INTEGER NOT NULL,
            bonus_amount INTEGER DEFAULT 0,
            final_credit_amount INTEGER NOT NULL,
            promo_code TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            admin_id INTEGER
        )
    """)

    # 4. Orders Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            stars INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            cost_price INTEGER DEFAULT 0,
            payment_method TEXT DEFAULT 'balance',
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            promo_code TEXT,
            discount_amount INTEGER DEFAULT 0,
            order_type TEXT DEFAULT 'stars',
            item_id INTEGER,
            recipient_type TEXT DEFAULT 'self',
            recipient_username TEXT,
            is_anonymous INTEGER DEFAULT 0,
            gift_signature TEXT,
            signature_fee INTEGER DEFAULT 0
        )
    """)
    order_cols = [row["name"] for row in cursor.execute("PRAGMA table_info(orders)").fetchall()]
    order_additions = {
        "cost_price": "INTEGER DEFAULT 0",
        "payment_method": "TEXT DEFAULT 'balance'",
        "updated_at": "TEXT",
        "promo_code": "TEXT",
        "discount_amount": "INTEGER DEFAULT 0",
        "order_type": "TEXT DEFAULT 'stars'",
        "item_id": "INTEGER",
        "recipient_type": "TEXT DEFAULT 'self'",
        "recipient_username": "TEXT",
        "is_anonymous": "INTEGER DEFAULT 0",
        "gift_signature": "TEXT",
        "signature_fee": "INTEGER DEFAULT 0",
    }
    for col_name, col_def in order_additions.items():
        if col_name not in order_cols:
            cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_def}")

    # 5. Products Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'gift',
            price INTEGER NOT NULL,
            cost_price INTEGER DEFAULT 0,
            is_available INTEGER DEFAULT 1,
            description TEXT,
            image_id TEXT
        )
    """)

    # 6. Promocodes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL DEFAULT 'discount',
            value INTEGER NOT NULL,
            uses_count INTEGER DEFAULT 0,
            max_uses INTEGER DEFAULT 100,
            max_uses_per_user INTEGER DEFAULT 1,
            expires_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    promo_cols = [row["name"] for row in cursor.execute("PRAGMA table_info(promocodes)").fetchall()]
    promo_additions = {
        "type": "TEXT NOT NULL DEFAULT 'discount'",
        "value": "INTEGER NOT NULL DEFAULT 10",
        "max_uses_per_user": "INTEGER DEFAULT 1",
    }
    for col_name, col_def in promo_additions.items():
        if col_name not in promo_cols:
            cursor.execute(f"ALTER TABLE promocodes ADD COLUMN {col_name} {col_def}")

    # 7. Promocode Uses Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promocode_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promo_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            used_at TEXT NOT NULL
        )
    """)

    # 8. Operations (Transaction History) Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'completed',
            created_at TEXT NOT NULL,
            admin_id INTEGER
        )
    """)

    # Default Settings
    default_settings = {
        "price": str(DEFAULT_PRICE),
        "star_cost_price": str(DEFAULT_STAR_COST_PRICE),
        "min_stars": str(DEFAULT_MIN_STARS),
        "max_stars": str(DEFAULT_MAX_STARS),
        "card_requisites": "5614 6835 1296 6896",
        "paynet_requisites": "+998881400008",
        "paynet_manager": "@YaTochka_pan",
        "nft_manager": "@YaTochka_pan",
        "crypto_address": "UQAfQ6LWkNS7_p7QlTIWgJJd3cvWLrJr8Hl6gqyZ73Zw8j8w",
        "crypto_network": "Gramm (ex. TON)",
        "crypto_instruction": "⚠️ ВАЖНО!\n\nСтрого пополняйте в сети Gramm (ex. TON).\nЕсли будет отправлена другая монета или фейк-токен, ваши средства могут быть утрачены навсегда.\nАдминистрация не возмещает потери, возникшие из-за отправки средств в неправильной сети, неправильной монеты или фейк-токена.",
        "support_username": "@YaTochka_pan",
        "welcome_text": "⭐ <b>Добро пожаловать в KAW Star!</b>\n\nЗдесь вы можете приобрести Telegram Stars и подарки быстро и выгодно.",
        "working_hours": "09:00 - 23:00",
        "reviews_url": "https://t.me/kaw_star_reviews",
    }
    for k, v in default_settings.items():
        if cursor.execute("SELECT 1 FROM settings WHERE key=?", (k,)).fetchone() is None:
            cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Seed Initial Products if empty
    if cursor.execute("SELECT COUNT(*) x FROM products").fetchone()["x"] == 0:
        seed_products = [
            ("🎁 15 Stars", "gift", 6000, 15 * DEFAULT_STAR_COST_PRICE, 1, "🎁 Подарок 15 Telegram Stars"),
            ("🎁 25 Stars", "gift", 9000, 25 * DEFAULT_STAR_COST_PRICE, 1, "🎁 Подарок 25 Telegram Stars"),
            ("🎁 50 Stars", "gift", 18000, 50 * DEFAULT_STAR_COST_PRICE, 1, "🎁 Подарок 50 Telegram Stars"),
            ("🎁 100 Stars", "gift", 36000, 100 * DEFAULT_STAR_COST_PRICE, 1, "🎁 Подарок 100 Telegram Stars"),
        ]
        for title, ptype, pr, cpr, avail, desc in seed_products:
            cursor.execute(
                "INSERT INTO products (title, type, price, cost_price, is_available, description) VALUES (?, ?, ?, ?, ?, ?)",
                (title, ptype, pr, cpr, avail, desc),
            )

    conn.commit()
    conn.close()

# ----------------- Settings API -----------------
def get_setting(key: str, default: str = "") -> str:
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

# ----------------- Users & Balance API -----------------
def add_or_update_user(user_id: int, username: str, first_name: str):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO users (user_id, username, first_name, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
    """, (user_id, username, first_name, now))
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row

def get_user_by_username(username: str):
    conn = get_db()
    clean_name = username.replace("@", "").strip()
    row = conn.execute("SELECT * FROM users WHERE LOWER(username)=LOWER(?)", (clean_name,)).fetchone()
    conn.close()
    return row

def get_all_users(limit: int = 100):
    conn = get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows

def get_all_user_ids() -> list:
    conn = get_db()
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

def update_user_balance_atomic(user_id: int, delta: int, op_type: str, description: str, admin_id: int = None) -> bool:
    """
    Atomically updates user balance and logs the operation.
    If delta < 0, ensures user balance does not drop below 0.
    """
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    user = cursor.execute("SELECT balance, total_topups, total_spent FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return False

    current_bal = user["balance"]
    new_bal = current_bal + delta
    if new_bal < 0:
        conn.close()
        return False

    if delta > 0:
        cursor.execute(
            "UPDATE users SET balance = balance + ?, total_topups = total_topups + ? WHERE user_id=?",
            (delta, delta if op_type == "topup" else 0, user_id),
        )
    else:
        spent = abs(delta)
        cursor.execute(
            "UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id=?",
            (spent, spent if op_type in ("buy_stars", "buy_gift") else 0, user_id),
        )

    cursor.execute(
        "INSERT INTO operations (user_id, type, amount, description, status, created_at, admin_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, op_type, delta, description, "completed", now, admin_id),
    )

    conn.commit()
    conn.close()
    return True

# ----------------- Topups API -----------------
def create_topup_request(
    user_id: int,
    username: str,
    payment_method: str,
    entered_amount: int,
    fee_amount: int,
    net_amount: int,
    bonus_amount: int,
    final_credit_amount: int,
    promo_code: str = None,
) -> int:
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO topups (
            user_id, username, payment_method, entered_amount, fee_amount,
            net_amount, bonus_amount, final_credit_amount, promo_code, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
    """,
        (
            user_id,
            username,
            payment_method,
            entered_amount,
            fee_amount,
            net_amount,
            bonus_amount,
            final_credit_amount,
            promo_code,
            now,
            now,
        ),
    )
    tid = cur.lastrowid
    conn.commit()
    conn.close()
    return tid

def get_topup_request(topup_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM topups WHERE id=?", (topup_id,)).fetchone()
    conn.close()
    return row

def get_pending_topups(limit: int = 30):
    conn = get_db()
    rows = conn.execute("SELECT * FROM topups WHERE status='pending' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows

def approve_topup_request(topup_id: int, custom_credit_amount: int = None, admin_id: int = None) -> bool:
    conn = get_db()
    cursor = conn.cursor()

    req = cursor.execute("SELECT * FROM topups WHERE id=?", (topup_id,)).fetchone()
    if not req or req["status"] != "pending":
        conn.close()
        return False

    credit_amt = custom_credit_amount if custom_credit_amount is not None else req["final_credit_amount"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update topup record
    cursor.execute(
        "UPDATE topups SET status='approved', final_credit_amount=?, updated_at=?, admin_id=? WHERE id=?",
        (credit_amt, now, admin_id, topup_id),
    )

    # Credit user balance & update statistics
    cursor.execute(
        "UPDATE users SET balance = balance + ?, total_topups = total_topups + ? WHERE user_id=?",
        (credit_amt, credit_amt, req["user_id"]),
    )

    # Log operation
    method_name = {"card": "Карта", "cash": "Paynet / Наличные", "crypto": "Криптовалюта"}.get(req["payment_method"], req["payment_method"])
    desc = f"Пополнение #{topup_id} ({method_name})"
    if req["promo_code"]:
        desc += f" [Промокод: {req['promo_code']}]"

    cursor.execute(
        "INSERT INTO operations (user_id, type, amount, description, status, created_at, admin_id) VALUES (?, 'topup', ?, ?, 'completed', ?, ?)",
        (req["user_id"], credit_amt, desc, now, admin_id),
    )

    conn.commit()
    conn.close()
    return True

def reject_topup_request(topup_id: int, admin_id: int = None) -> bool:
    conn = get_db()
    req = conn.execute("SELECT * FROM topups WHERE id=?", (topup_id,)).fetchone()
    if not req or req["status"] != "pending":
        conn.close()
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE topups SET status='rejected', updated_at=?, admin_id=? WHERE id=?", (now, admin_id, topup_id))
    conn.commit()
    conn.close()
    return True

# ----------------- Orders API -----------------
def create_order(
    user_id: int,
    username: str,
    stars: int,
    amount: int,
    cost_price: int = 0,
    payment_method: str = "balance",
    status: str = "new",
    promo_code: str = None,
    discount_amount: int = 0,
    order_type: str = "stars",
    item_id: int = None,
    recipient_type: str = "self",
    recipient_username: str = None,
    is_anonymous: int = 0,
    gift_signature: str = None,
    signature_fee: int = 0,
) -> int:
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO orders (
            user_id, username, stars, amount, cost_price, payment_method, status,
            created_at, updated_at, promo_code, discount_amount, order_type, item_id,
            recipient_type, recipient_username, is_anonymous, gift_signature, signature_fee
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            user_id,
            username,
            stars,
            amount,
            cost_price,
            payment_method,
            status,
            now,
            now,
            promo_code,
            discount_amount,
            order_type,
            item_id,
            recipient_type,
            recipient_username,
            is_anonymous,
            gift_signature,
            signature_fee,
        ),
    )
    oid = cur.lastrowid
    conn.commit()
    conn.close()
    return oid

def get_order(order_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    return row

def get_user_orders(user_id: int, limit: int = 20):
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    conn.close()
    return rows

def get_orders_by_status(status_filter: str = None, limit: int = 30):
    conn = get_db()
    if status_filter:
        rows = conn.execute("SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT ?", (status_filter, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows

def update_order_status(order_id: int, status: str):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (status, now, order_id))
    conn.commit()
    conn.close()

# ----------------- Operations & History API -----------------
def get_user_operations(user_id: int, limit: int = 20):
    conn = get_db()
    rows = conn.execute("SELECT * FROM operations WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
    conn.close()
    return rows

def log_operation(user_id: int, op_type: str, amount: int, description: str, admin_id: int = None):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO operations (user_id, type, amount, description, status, created_at, admin_id) VALUES (?, ?, ?, ?, 'completed', ?, ?)",
        (user_id, op_type, amount, description, now, admin_id),
    )
    conn.commit()
    conn.close()

# ----------------- Products API -----------------
def get_all_products(available_only: bool = False):
    conn = get_db()
    if available_only:
        rows = conn.execute("SELECT * FROM products WHERE is_available=1 ORDER BY price ASC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM products ORDER BY id ASC").fetchall()
    conn.close()
    return rows

def get_product(product_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()
    return row

def add_product(title: str, price: int, cost_price: int, description: str = "", image_id: str = None, is_available: int = 1):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (title, price, cost_price, is_available, description, image_id) VALUES (?, ?, ?, ?, ?, ?)",
        (title, price, cost_price, is_available, description, image_id),
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid

def update_product_availability(product_id: int, is_available: int):
    conn = get_db()
    conn.execute("UPDATE products SET is_available=? WHERE id=?", (is_available, product_id))
    conn.commit()
    conn.close()

def update_product_price(product_id: int, price: int, cost_price: int = None):
    conn = get_db()
    if cost_price is not None:
        conn.execute("UPDATE products SET price=?, cost_price=? WHERE id=?", (price, cost_price, product_id))
    else:
        conn.execute("UPDATE products SET price=? WHERE id=?", (price, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id: int):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

# ----------------- Promocodes API -----------------
def get_promocode(code: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM promocodes WHERE UPPER(code)=UPPER(?)", (code.strip(),)).fetchone()
    conn.close()
    return row

def get_all_promocodes():
    conn = get_db()
    rows = conn.execute("SELECT * FROM promocodes ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def add_promocode(
    code: str,
    promo_type: str,
    value: int,
    max_uses: int = 100,
    max_uses_per_user: int = 1,
    expires_at: str = None,
):
    conn = get_db()
    promo_cols = [row["name"] for row in conn.execute("PRAGMA table_info(promocodes)").fetchall()]
    if "discount_percent" in promo_cols:
        cur = conn.execute(
            "INSERT INTO promocodes (code, type, value, discount_percent, max_uses, max_uses_per_user, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code.upper().strip(), promo_type, value, value, max_uses, max_uses_per_user, expires_at),
        )
    else:
        cur = conn.execute(
            "INSERT INTO promocodes (code, type, value, max_uses, max_uses_per_user, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (code.upper().strip(), promo_type, value, max_uses, max_uses_per_user, expires_at),
        )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid

def can_user_use_promo(promo_id: int, user_id: int) -> bool:
    conn = get_db()
    promo = conn.execute("SELECT * FROM promocodes WHERE id=?", (promo_id,)).fetchone()
    if not promo or promo["is_active"] != 1:
        conn.close()
        return False
    if promo["uses_count"] >= promo["max_uses"]:
        conn.close()
        return False

    user_uses = conn.execute(
        "SELECT COUNT(*) x FROM promocode_uses WHERE promo_id=? AND user_id=?", (promo_id, user_id)
    ).fetchone()["x"]
    conn.close()
    return user_uses < promo["max_uses_per_user"]

def record_promo_use(promo_id: int, code: str, user_id: int):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE promocodes SET uses_count = uses_count + 1 WHERE id=?", (promo_id,))
    conn.execute("INSERT INTO promocode_uses (promo_id, code, user_id, used_at) VALUES (?, ?, ?, ?)", (promo_id, code.upper(), user_id, now))
    conn.commit()
    conn.close()

def toggle_promocode(promo_id: int):
    conn = get_db()
    row = conn.execute("SELECT is_active FROM promocodes WHERE id=?", (promo_id,)).fetchone()
    if row:
        new_val = 0 if row["is_active"] == 1 else 1
        conn.execute("UPDATE promocodes SET is_active=? WHERE id=?", (new_val, promo_id))
        conn.commit()
    conn.close()

def delete_promocode(promo_id: int):
    conn = get_db()
    conn.execute("DELETE FROM promocodes WHERE id=?", (promo_id,))
    conn.execute("DELETE FROM promocode_uses WHERE promo_id=?", (promo_id,))
    conn.commit()
    conn.close()

# ----------------- Statistics API -----------------
def get_statistics():
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) x FROM users").fetchone()["x"]
    total_orders = conn.execute("SELECT COUNT(*) x FROM orders").fetchone()["x"]
    completed_orders = conn.execute("SELECT COUNT(*) x FROM orders WHERE status IN ('completed', 'done')").fetchone()["x"]
    cancelled_orders = conn.execute("SELECT COUNT(*) x FROM orders WHERE status IN ('cancelled', 'cancel')").fetchone()["x"]

    total_stars = conn.execute(
        "SELECT COALESCE(SUM(stars), 0) x FROM orders WHERE status IN ('completed', 'done')"
    ).fetchone()["x"]

    revenue = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) x FROM orders WHERE status IN ('completed', 'done')"
    ).fetchone()["x"]

    cost = conn.execute(
        "SELECT COALESCE(SUM(cost_price), 0) x FROM orders WHERE status IN ('completed', 'done')"
    ).fetchone()["x"]

    total_topups = conn.execute(
        "SELECT COALESCE(SUM(final_credit_amount), 0) x FROM topups WHERE status='approved'"
    ).fetchone()["x"]

    gifts_count = conn.execute(
        "SELECT COUNT(*) x FROM orders WHERE status IN ('completed', 'done') AND order_type='gift'"
    ).fetchone()["x"]

    conn.close()

    profit = revenue - cost
    return {
        "total_users": total_users,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "total_stars": total_stars,
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "total_topups": total_topups,
        "gifts_count": gifts_count,
    }
