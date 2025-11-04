
# ai_assitant.py
import os
import re
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
import dateparser

# Optional Gemini SDK
try:
    import google.generativeai as genai
except Exception:
    genai = None

# Project DB helpers (your existing modules)
from db_config import get_connection
from income import add_income, get_income
from expenses import add_expense, get_expenses
from transactions import add_transaction, get_transactions

load_dotenv()
GENIE_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if GENIE_KEY and genai:
    try:
        genai.configure(api_key=GENIE_KEY)
    except Exception:
        # continue even if configure fails
        pass

# In-memory session state
pending_actions: Dict[str, Dict[str, Any]] = {}
chat_memory: Dict[str, List[Dict[str, Any]]] = {}

# Regex patterns (UNCHANGED)
AMOUNT_RE = re.compile(r"₹?\s?([0-9]{1,3}(?:[,0-9]{0,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)")
ON_CAT_RE = re.compile(r"(?:on|for|in)\s+([a-zA-Z ]+)")
FROM_SRC_RE = re.compile(r"from\s+([a-zA-Z ]+)")
DATE_KEYWORDS = ["today", "yesterday", "tomorrow", "last", "this", "on", "week", "month"]

# ---------------- parsing helpers (UNCHANGED) ----------------
def parse_amount(text: str) -> Optional[float]:
    if not text:
        return None
    m = AMOUNT_RE.search(text.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

def parse_category(text: str) -> Optional[str]:
    if not text:
        return None
    m = ON_CAT_RE.search(text.lower())
    if m:
        return m.group(1).strip().title()
    for w in ["food", "bills", "bill", "transport", "rent", "shopping",
              "entertainment", "groceries", "salary", "freelance", "investments"]:
        if w in text.lower():
            return (w[:-1].title() if w.endswith("s") else w.title())
    return None

def parse_source(text: str) -> Optional[str]:
    if not text:
        return None
    m = FROM_SRC_RE.search(text.lower())
    if m:
        return m.group(1).strip().title()
    for w in ["salary", "freelance", "gift", "investments"]:
        if w in text.lower():
            return w.title()
    return None

def parse_date(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    tl = text.lower()
    if "today" in tl:
        return date.today().strftime("%Y-%m-%d")
    if "yesterday" in tl:
        return (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    # dateparser for flexible parsing
    try:
        dt = dateparser.parse(text, settings={"PREFER_DATES_FROM": "past"})
        if dt:
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text or "")
    if m:
        return m.group(1)
    return None

# ---------------- authoritative DB helpers (UNCHANGED) ----------------
def _sql_sum_income(user_id: str, date_from: Optional[str] = None, date_to: Optional[str] = None) -> float:
    conn = get_connection()
    if not conn:
        return 0.0
    try:
        cur = conn.cursor()
        q = "SELECT SUM(amount) FROM income WHERE user_id = ?"
        params = [int(user_id)]
        if date_from:
            q += " AND date >= ?"; params.append(date_from)
        if date_to:
            q += " AND date <= ?"; params.append(date_to)
        cur.execute(q, params)
        row = cur.fetchone()
        return float(row[0]) if row and row[0] is not None else 0.0
    except Exception:
        return 0.0
    finally:
        conn.close()

def _sql_sum_expenses_by_category(user_id: str, category: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None) -> float:
    conn = get_connection()
    if not conn:
        return 0.0
    try:
        cur = conn.cursor()
        q = "SELECT SUM(amount) FROM expenses WHERE user_id = ?"
        params = [int(user_id)]
        if category:
            q += " AND LOWER(category) = LOWER(?)"; params.append(category)
        if date_from:
            q += " AND date >= ?"; params.append(date_from)
        if date_to:
            q += " AND date <= ?"; params.append(date_to)
        cur.execute(q, params)
        r = cur.fetchone()
        return float(r[0]) if r and r[0] is not None else 0.0
    except Exception:
        return 0.0
    finally:
        conn.close()

def _sql_expense_breakdown(user_id: str, limit: int = 50) -> Dict[str, float]:
    conn = get_connection()
    if not conn:
        return {}
    try:
        cur = conn.cursor()
        cur.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC", (int(user_id),))
        rows = cur.fetchmany(limit)
        return {r[0]: float(r[1]) for r in rows} if rows else {}
    except Exception:
        return {}
    finally:
        conn.close()

def _sql_recent_transactions(user_id: str, n: int = 5) -> List[Dict[str, Any]]:
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        # Some pyodbc drivers don't allow parameterized TOP; try safe approach
        cur.execute(f"""
            SELECT date, type, category, description, amount
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT {n}
        """, (int(user_id),))
        rows = cur.fetchall()
        out = []
        for r in rows:
            out.append({
                "date": str(r[0]),
                "type": r[1],
                "category": r[2],
                "description": r[3],
                "amount": float(r[4])
            })
        return out
    except Exception:
        return []
    finally:
        conn.close()

# ---------------- business helpers (UNCHANGED) ----------------
def compute_summary(user_id: str) -> Dict[str, float]:
    sql_income = _sql_sum_income(user_id)
    breakdown = _sql_expense_breakdown(user_id)
    total_expense = sum(breakdown.values()) if breakdown else 0.0
    return {"total_income": sql_income, "total_expense": total_expense, "balance": sql_income - total_expense}

# ---------------- pending & chat memory ----------------
def begin_pending_action(user_id: str, action: Dict[str, Any]) -> None:
    pending_actions[str(user_id)] = action

def peek_pending_action(user_id: str) -> Optional[Dict[str, Any]]:
    return pending_actions.get(str(user_id))

def pop_pending_action(user_id: str) -> Optional[Dict[str, Any]]:
    return pending_actions.pop(str(user_id), None)

def append_chat(user_id: str, role: str, text: str) -> None:
    user = str(user_id)
    if user not in chat_memory:
        chat_memory[user] = []
    # Avoid appending duplicate user messages if the front-end has already added it
    if not chat_memory[user] or not (chat_memory[user][-1]['role'] == role and chat_memory[user][-1]['text'] == text):
        chat_memory[user].append({"role": role, "text": text, "ts": datetime.now().isoformat()})

def get_chat_history(user_id: str) -> List[Dict[str, Any]]:
    return chat_memory.get(str(user_id), [])

# --- Session Reset Functionality ---
def reset_session_for_user(user_id: str) -> None:
    uid = str(user_id)
    if uid in chat_memory:
        del chat_memory[uid]
    if uid in pending_actions:
        del pending_actions[uid]

def reset_session_on_logout(user_id: str) -> None:
    """Public function for external calls (e.g., from a logout route)."""
    reset_session_for_user(user_id)
    print(f"Session for user {user_id} reset on logout.")

# ---------------- create record helpers (UNCHANGED) ----------------
def create_expense(user_id: str, amount: float, category: str, description: str, date_str: str, method: str = "Unknown") -> str:
    msg = add_expense(user_id, category, description, amount, date_str, method)
    try:
        add_transaction(user_id, "expense", category, description or method, amount, date_str)
    except Exception:
        pass
    return msg

def create_income(user_id: str, amount: float, source: str, category: str, date_str: str, notes: str = "") -> str:
    msg = add_income(user_id, source, amount, date_str, category, notes)
    try:
        add_transaction(user_id, "income", category, notes or source, amount, date_str)
    except Exception:
        pass
    return msg

# ---------------- follow-up handler (UNCHANGED) ----------------
def handle_followup_for_pending(user_id: str, user_text: str) -> Optional[str]:
    pa = peek_pending_action(user_id)
    if not pa:
        return None

    amt = parse_amount(user_text)
    cat = parse_category(user_text)
    src = parse_source(user_text)
    dt = parse_date(user_text)

    # Update pending action details
    if amt:
        pa["amount"] = amt
    if cat and pa.get("type") == "expense":
        pa["category"] = cat
    if src and pa.get("type") == "income":
        pa["source"] = src
    if dt:
        pa["date"] = dt

    # Finalize expense
    if pa["type"] == "expense":
        if "amount" in pa and "category" in pa:
            action = pop_pending_action(user_id)
            try:
                date_used = action.get("date", date.today().strftime("%Y-%m-%d"))
                create_expense(user_id, float(action["amount"]), action["category"], action.get("description", ""), date_used, action.get("method", "Unknown"))
                reply = f"✅ Added expense: ₹{action['amount']:.2f} under '{action['category']}' on {date_used}."
                append_chat(user_id, "assistant", reply) # Append here to ensure consistency
                return reply
            except Exception as e:
                reply = f"Error adding expense: {e}"
                append_chat(user_id, "assistant", reply)
                return reply
        else:
            missing = []
            if "amount" not in pa: missing.append("amount")
            if "category" not in pa: missing.append("category")
            reply = f"I still need {', '.join(missing)} to add this expense. Please tell me."
            return reply # Do not append to chat memory here, as it will be returned to the main handler which appends.

    # Finalize income
    if pa["type"] == "income":
        if "amount" in pa and ("source" in pa or "category" in pa):
            action = pop_pending_action(user_id)
            src_val = action.get("source") or action.get("category") or "Other"
            try:
                date_used = action.get("date", date.today().strftime("%Y-%m-%d"))
                create_income(user_id, float(action["amount"]), src_val, action.get("category", "Work"), date_used, action.get("notes", ""))
                reply = f"✅ Added income: ₹{action['amount']:.2f} from '{src_val}' on {date_used}."
                append_chat(user_id, "assistant", reply) # Append here to ensure consistency
                return reply
            except Exception as e:
                reply = f"Error adding income: {e}"
                append_chat(user_id, "assistant", reply)
                return reply
        else:
            missing = []
            if "amount" not in pa: missing.append("amount")
            if "source" not in pa and "category" not in pa: missing.append("source/category")
            reply = f"I still need {', '.join(missing)} to add this income. Please tell me."
            return reply # Do not append to chat memory here.

    return None

# ---------------- Gemini / LLM wrapper (safe usage) (UNCHANGED) ----------------
def _gemini_rewrite(user_id: str, user_query: str, context_text: str) -> str:
    """
    If Gemini is available, ask it to rewrite/explain the provided context_text
    in a friendly short human tone. Only sanitized context_text is sent.
    """
    if not GENIE_KEY or not genai:
        return context_text + ("\n\n(Set GEMINI_API_KEY in .env to get a friendlier rewrite.)")

    try:
        # Use gemini-2.5-flash if available, or fall back to 2.0-flash
        model_name = "gemini-2.5-flash" if "2.5-flash" in genai.list_models() else "gemini-2.0-flash"
        model = genai.GenerativeModel(model_name)
        prompt = f"""You are a concise personal finance assistant.
The user asked:
"{user_query}"

Here is the verified data (from the user's database). Use this exact data to answer, do NOT invent numbers or facts:
{context_text}

Produce 1-3 short sentences referencing the verified numbers.
"""
        response = model.generate_content(prompt)
        text = response.text.strip() if response and getattr(response, "text", None) else context_text
        return text
    except Exception as e:
        return f"{context_text}\n\n(LLM rewrite failed: {e})"

# ---------------- command detection & execution ----------------
def detect_and_execute_command(user_id: str, text: str) -> Optional[Dict[str, Any]]:
    # 1. Handle pending follow-ups first (Highest Priority)
    followup_text = handle_followup_for_pending(user_id, text)
    if followup_text:
        return {"text": followup_text, "chart_data": None}

    t = (text or "").lower()
    uid = str(user_id)
    chart_data = None

    # --- Reset Chat Command ---
    if any(k in t for k in ["reset", "clear chat", "delete history", "start over"]):
        reset_session_for_user(user_id)
        reply = "✅ Chat history and any pending actions have been reset."
        append_chat(uid, "assistant", reply)
        return {"text": reply, "chart_data": None}

    # 2. Summary and totals (Data Query Intent - Higher Priority)
    # ADDED KEYWORDS: "expence", "expences", "compare"
    if any(k in t for k in ["summary", "balance", "total", "how much", "spent on", "how much i spent", "top spending", "top expense", "breakdown", "expense total", "income total", "explain my incomes", "explain my income", "received total", "expence", "expences", "compare"]):

        # Check for specific category query (e.g., "spent on Food")
        cat = parse_category(text)
        if ("spent on" in t or ("how much" in t and cat and ("expense" in t or "spent" in t or "expence" in t))):
            if not cat:
                ask = "Which category would you like to check? (e.g., Food, Bills, Transport)"
                append_chat(user_id, "assistant", ask)
                return {"text": ask, "chart_data": None}

            total = _sql_sum_expenses_by_category(user_id, cat)
            context = f"Total spent on {cat}: ₹{total:,.2f} (verified from your database)."
            reply = context if not (GENIE_KEY and genai) else _gemini_rewrite(user_id, text, context)
            append_chat(user_id, "assistant", reply)
            return {"text": reply, "chart_data": None}

        # Handle specific income query (e.g., "explain my incomes")
        if any(k in t for k in ["income", "earned", "received", "explain my incomes", "explain my income"]):
            s = compute_summary(user_id)
            context_text = f"Total Income: ₹{s['total_income']:,.2f} (verified from your database)."
            reply = context_text if not (GENIE_KEY and genai) else _gemini_rewrite(user_id, text, context_text)
            append_chat(user_id, "assistant", reply)
            return {"text": reply, "chart_data": None}

        # General summary (Fall through for queries like "summary", "balance", "compare", or general "expences" queries)
        s = compute_summary(user_id)
        breakdown = _sql_expense_breakdown(user_id)

        # Populate chart_data for app.py consumption
        chart_data = breakdown

        top_lines = []
        for i, (c, amt) in enumerate(breakdown.items()):
            if i >= 5: break
            top_lines.append(f"{c}: ₹{amt:,.2f}")
        recent = _sql_recent_transactions(user_id, n=5)
        recent_lines = [f"{r['date']} - {r['type']} - {r['category']} - ₹{r['amount']:.2f}" for r in recent]

        context_parts = [
            f"Total Income: ₹{s['total_income']:,.2f}",
            f"Total Expenses: ₹{s['total_expense']:,.2f}",
            f"Balance: ₹{s['balance']:,.2f}",
            "",
            "Top expense categories (top 5):",
            ("\n".join(top_lines) if top_lines else "None"),
            "",
            "Recent transactions (latest 5):",
            ("\n".join(recent_lines) if recent_lines else "None"),
        ]
        context_text = "\n".join(context_parts)
        reply = context_text if not (GENIE_KEY and genai) else _gemini_rewrite(user_id, text, context_text)
        append_chat(user_id, "assistant", reply)
        return {"text": reply, "chart_data": chart_data}

    # 3. Add Expense intent (Data Entry Intent)
    # ADDED KEYWORD: "expence"
    if any(k in t for k in ["spent", "bought", "paid", "expense", "purchase", "paid for", "expence"]):
        amt = parse_amount(text)
        cat = parse_category(text)
        dt = parse_date(text) or date.today().strftime("%Y-%m-%d")
        desc = text
        if amt and cat:
            try:
                create_expense(user_id, amt, cat, desc, dt, "Unknown")
                res = f"✅ Added expense: ₹{amt:,.2f} under '{cat}' on {dt}."
                append_chat(user_id, "assistant", res)
                return {"text": res, "chart_data": None}
            except Exception as e:
                res = f"Error adding expense: {e}"
                append_chat(user_id, "assistant", res)
                return {"text": res, "chart_data": None}
        else:
            pa = {"type": "expense", "description": desc, "date": dt}
            if amt: pa["amount"] = amt
            if cat: pa["category"] = cat
            begin_pending_action(user_id, pa)
            missing = []
            if "amount" not in pa: missing.append("amount")
            if "category" not in pa: missing.append("category")
            ask = f"I can add this expense. I still need {', '.join(missing)}. Please reply with the missing info (e.g., '₹500 on Food today')."
            append_chat(user_id, "assistant", ask)
            return {"text": ask, "chart_data": None}

    # 4. Add Income intent (Data Entry Intent)
    if any(k in t for k in ["earned", "got", "received", "income", "salary", "i got", "paid me"]):
        amt = parse_amount(text)
        src = parse_source(text) or parse_category(text)
        dt = parse_date(text) or date.today().strftime("%Y-%m-%d")
        notes = text
        if amt and src:
            try:
                create_income(user_id, amt, src, "Work", dt, notes)
                res = f"✅ Added income: ₹{amt:,.2f} from '{src}' on {dt}."
                append_chat(user_id, "assistant", res)
                return {"text": res, "chart_data": None}
            except Exception as e:
                res = f"Error adding income: {e}"
                append_chat(user_id, "assistant", res)
                return {"text": res, "chart_data": None}
        else:
            pa = {"type": "income", "date": dt}
            if amt: pa["amount"] = amt
            if src: pa["source"] = src
            begin_pending_action(user_id, pa)
            missing = []
            if "amount" not in pa: missing.append("amount")
            if "source" not in pa: missing.append("source/category")
            ask = f"I can add this income. I still need {', '.join(missing)} to add this income. Please reply with the missing info (e.g., 'from Salary')."
            append_chat(user_id, "assistant", ask)
            return {"text": ask, "chart_data": None}

    # 5. Recent transactions explicit (Lowest Priority)
    if any(k in t for k in ["recent", "last transactions", "show transactions", "recent tx", "last 5"]):
        recent = _sql_recent_transactions(user_id, n=5)
        if not recent:
            no = "No recent transactions found."
            append_chat(user_id, "assistant", no)
            return {"text": no, "chart_data": None}
        lines = [f"{r['date']} - {r['type']} - {r['category']} - ₹{r['amount']:.2f} ({r['description']})" for r in recent]
        out = "Recent transactions:\n" + "\n".join(lines)
        append_chat(user_id, "assistant", out)
        return {"text": out, "chart_data": None}

    return None

# ---------------- public handler ----------------
def handle_ai_query(user_id: str, query: str) -> Dict[str, Any]:
    uid = str(user_id)

    # Define a default structured response, including the expected 'chart_data'
    structured_response = {
        "text": "",
        "chart_data": None,
        "status": "ok"
    }

    # Check if user message is already in history (prevents duplicates on rerun)
    if not get_chat_history(uid) or get_chat_history(uid)[-1].get("text") != query:
        append_chat(uid, "user", query)

    try:
        # detect_and_execute_command now returns a Dict or None
        result_dict = detect_and_execute_command(uid, query)

        if result_dict:
            return result_dict
    except Exception as e:
        err_msg = f"Internal error during command execution: {e}"
        append_chat(uid, "assistant", err_msg)
        structured_response["text"] = err_msg
        structured_response["status"] = "error"
        return structured_response

    # Fallback: If no specific command was detected, provide a strict domain-specific guidance.
    # --- Strict Domain Fallback ---
    fallback_message = (
        "I'm a personal finance assistant. I can help you with:\n"
        "1. **Adding Data**: Say 'I spent ₹500 on Food' or 'Received salary of ₹50,000'.\n"
        "2. **Checking Data**: Ask 'What is my balance?' or 'How much did I spend on Transport?' or 'Compare income and expenses'.\n" # UPDATED guidance
        "3. **Viewing History**: Say 'Show recent transactions.'\n"
        "4. **Resetting**: Say 'Reset chat'."
    )

    structured_response["text"] = fallback_message
    append_chat(uid, "assistant", fallback_message) # Append to memory

    return structured_response

def get_chat_history_for_user(user_id: str) -> List[Dict[str, Any]]:
    return get_chat_history(str(user_id))

# ---------- local test (UNCHANGED) ----------
if __name__ == "__main__":
    print("AI Assistant (safe) - local test. Type 'exit' to quit.")
    uid = "1"
    while True:
        q = input("You: ").strip()
        if q.lower() in ("exit", "quit"):
            break
        result = handle_ai_query(uid, q)
        print("AI Text:", result.get("text"))
        if result.get("chart_data"):
            print("AI Chart Data:", result.get("chart_data"))
