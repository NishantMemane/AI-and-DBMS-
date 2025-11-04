
#users.py
from db_config import get_connection

def signup_user(name, email, password):
    conn = get_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE name=? OR email=?", (name, email))
        if cursor.fetchone():
            return " User with this name or email already exists!"
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )
        conn.commit()
        return " Signup successful!"
    except Exception as e:
        conn.rollback()
        return f" Error during signup: {e}"
    finally:
        conn.close()


def login_user(name, password):
    conn = get_connection()
    if not conn:
        return " Database connection failed."
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, name FROM users WHERE name=? AND password=?", (name, password))
        user = cursor.fetchone()
        if user:
            return {"user_id": user[0], "name": user[1]}
        return " Invalid name or password."
    except Exception as e:
        return f" Login error: {e}"
    finally:
        conn.close()
