
from db_config import get_connection

def add_income(user_id, source, amount, date, category, notes):
    conn = get_connection()
    if not conn:
        return "Database connection failed."

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO income (user_id, source, amount, date, category, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, source, amount, date, category, notes))
        conn.commit()
        return "✅ Income added successfully!"
    except Exception as e:
        conn.rollback()
        return f"Error adding income: {e}"
    finally:
        if conn:
            conn.close()


def get_income(user_id):
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        # Removed: cursor.row_factory = None
        cursor.execute("""
            SELECT income_id, source, amount, date, category, notes
            FROM income
            WHERE user_id = ?
            ORDER BY date DESC
        """, (user_id,))

        rows = cursor.fetchall()
        return rows if rows else []
    except Exception as e:
        print(f"Error fetching income: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Assuming you also have a delete function:
def delete_income(income_id):
    conn = get_connection()
    if not conn:
        return "Database connection failed."
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM income WHERE income_id = ?", (income_id,))
        conn.commit()
        return "✅ Income record deleted successfully!"
    except Exception as e:
        conn.rollback()
        return f"Error deleting income record: {e}"
    finally:
        if conn:
            conn.close()
