

from db_config import get_connection

def add_transaction(user_id, t_type, category, description, amount, date):
    conn = get_connection()
    if not conn:
        return "Database connection failed."

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user_id, type, category, description, amount, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, t_type, category, description, amount, date))
        conn.commit()
        return "✅ Transaction added successfully!"
    except Exception as e:
        conn.rollback()
        return f"Error adding transaction: {e}"
    finally:
        if conn:
            conn.close()


def get_transactions(user_id):
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        # Removed: cursor.row_factory = None
        cursor.execute("""
            SELECT transaction_id, type, category, description, amount, date
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC
        """, (user_id,))

        rows = cursor.fetchall()
        return rows if rows else []
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []
    finally:
        if conn:
            conn.close()
