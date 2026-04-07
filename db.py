import sqlite3
from datetime import datetime, timezone
from config import DB_FILE, MAX_CHARGES

def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS commend_charges (
                discord_id   TEXT PRIMARY KEY,
                charges      INTEGER DEFAULT 3,
                last_accrual TEXT
            )
        """)

def get_current_charges(discord_id: str) -> int:
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT charges, last_accrual FROM commend_charges WHERE discord_id = ?",
            (discord_id,)
        ).fetchone()

        if not row:
            # First time user — initialise at max charges
            conn.execute(
                "INSERT INTO commend_charges (discord_id, charges, last_accrual) VALUES (?, ?, ?)",
                (discord_id, MAX_CHARGES, now.isoformat())
            )
            return MAX_CHARGES

        stored_charges, last_accrual_str = row
        last_accrual = datetime.fromisoformat(last_accrual_str)
        days_elapsed = (now - last_accrual).days
        new_charges  = min(MAX_CHARGES, stored_charges + days_elapsed)

        if days_elapsed > 0:
            conn.execute(
                "UPDATE commend_charges SET charges = ?, last_accrual = ? WHERE discord_id = ?",
                (new_charges, now.isoformat(), discord_id)
            )

        return new_charges

def deduct_charge(discord_id: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE commend_charges SET charges = charges - 1 WHERE discord_id = ?",
            (discord_id,)
        )

def next_charge_message(discord_id: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT last_accrual FROM commend_charges WHERE discord_id = ?",
            (discord_id,)
        ).fetchone()

    if not row:
        return "You'll get a charge tomorrow."

    last_accrual = datetime.fromisoformat(row[0])
    next_charge  = last_accrual.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Push forward to next day boundary
    from datetime import timedelta
    next_charge += timedelta(days=1)

    now  = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = next_charge - now
    total_seconds = int(diff.total_seconds())

    if total_seconds <= 0:
        return "You should have a charge available — try again."

    hours   = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"Next charge in **{hours}h {minutes}m**."