# from db_config import get_connection
# from datetime import datetime

# def add_expense(user_id, category, description, amount, date, method):
#     conn = get_connection()
#     if not conn:
#         return "Database connection failed."

#     if not category or amount <= 0 or not date:
#         return "Please provide valid expense details."

#     try:
#         if isinstance(date, datetime):
#             date = date.strftime("%Y-%m-%d")
#         elif isinstance(date, str):
#             date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")

#         cursor = conn.cursor()
#         cursor.execute("""
#             INSERT INTO expenses (user_id, category, description, amount, date, payment_method)
#             VALUES (?, ?, ?, ?, ?, ?)
#         """, (int(user_id), str(category), str(description), float(amount), str(date), str(method)))
#         conn.commit()
#         return "✅ Expense added successfully!"
#     except Exception as e:
#         conn.rollback()
#         return f"Error adding expense: {e}"
#     finally:
#         conn.close()


# def get_expenses(user_id):
#     conn = get_connection()
#     if not conn:
#         return []

#     try:
#         cursor = conn.cursor()
#         cursor.execute("""
#             SELECT category, description, amount, date, payment_method
#             FROM expenses
#             WHERE user_id = ?
#             ORDER BY date DESC
#         """, (int(user_id),))
#         return cursor.fetchall()
#     except Exception as e:
#         print(f"Error fetching expenses: {e}")
#         return []
#     finally:
#         conn.close()


# def delete_expense(record_id):
#     conn = get_connection()
#     if not conn:
#         return "Database connection failed."

#     try:
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM expenses WHERE expense_id = ?", (record_id,))
#         conn.commit()
#         return "✅ Expense record deleted!"
#     except Exception as e:
#         conn.rollback()
#         return f"Error deleting expense: {e}"
#     finally:
#         conn.close()

from db_config import get_connection
from datetime import datetime

def add_expense(user_id, category, description, amount, date, method):
    conn = get_connection()
    if not conn:
        return "Database connection failed."

    # Validate inputs
    if not category or amount is None or amount <= 0 or not date:
        return "Please provide valid expense details (Category, Amount > 0, and Date are required)."

    try:
        # Standardize date format for database insertion
        if isinstance(date, datetime):
            date_str = date.strftime("%Y-%m-%d")
        elif isinstance(date, str):
            # Attempt to re-format the string if it's already a string (Streamlit typically passes YYYY-MM-DD)
            date_str = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
        else:
            return "Invalid date format."

        # Ensure amount is treated as a float
        amount_float = float(amount)

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expenses (user_id, category, description, amount, date, payment_method)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (int(user_id), str(category), str(description), amount_float, date_str, str(method)))

        conn.commit()
        return "✅ Expense added successfully!"
    except Exception as e:
        conn.rollback()
        return f"Error adding expense: {e}"
    finally:
        if conn:
            conn.close()


def get_expenses(user_id):
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        # CRUCIAL FIX: Selecting all 6 required columns, starting with expense_id (for DataFrame 'ID').
        cursor.execute("""
            SELECT
                expense_id,      -- 1. Maps to ID for deletion
                category,        -- 2. Maps to Category
                description,     -- 3. Maps to Description
                amount,          -- 4. Maps to Amount
                date,            -- 5. Maps to Date
                payment_method   -- 6. Maps to Payment Method
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC
        """, (int(user_id),))

        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching expenses: {e}")
        return []
    finally:
        if conn:
            conn.close()


def delete_expense(record_id):
    conn = get_connection()
    if not conn:
        return "Database connection failed."

    try:
        cursor = conn.cursor()
        # Use expense_id column for deletion
        cursor.execute("DELETE FROM expenses WHERE expense_id = ?", (record_id,))
        conn.commit()
        return "✅ Expense record deleted!"
    except Exception as e:
        conn.rollback()
        return f"Error deleting expense: {e}"
    finally:
        if conn:
            conn.close()
