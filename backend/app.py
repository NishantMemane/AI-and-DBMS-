
import streamlit as st
import pandas as pd
from datetime import date as dt_date
import matplotlib.pyplot as plt


from users import login_user, signup_user
from income import add_income, get_income, delete_income
from expenses import add_expense, get_expenses, delete_expense
from transactions import add_transaction, get_transactions
from ai_assistant import handle_ai_query, get_chat_history_for_user, reset_session_on_logout

# Page config
st.set_page_config(page_title="Personal Finance Tracker", page_icon="💰", layout="wide")

# --- Session state initialization ---
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "ai_chart_data" not in st.session_state:
    st.session_state.ai_chart_data = None
# ------------------------------------

# --- AUTH page ---
def show_auth_page():
    st.title("💰 Personal Finance Tracker")
    menu = ["Login", "Sign Up"]
    choice = st.radio("Select Option:", menu, horizontal=True, key="auth_radio")

    if choice == "Login":
        st.subheader("🔐 Login")
        name = st.text_input("Name", key="login_name")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", key="btn_login"):
            user = login_user(name, password)
            if isinstance(user, dict):
                st.session_state.user = user
                st.success(f"Welcome, {user['name']}!")
                st.session_state.chat_history = []
                st.session_state.ai_chart_data = None
                st.rerun()
            else:
                st.error(user)

    elif choice == "Sign Up":
        st.subheader("📝 Create New Account")
        name = st.text_input("Full Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Sign Up", key="btn_signup"):
            result = signup_user(name, email, password)
            if "✅" in result or "successful" in result.lower():
                st.success(result)
                st.info("You can now log in.")
            else:
                st.error(result)

# --- Helper Functions ---
def create_df_from_records(records, expected_cols_map):
    """
    Safely creates a DataFrame from database records, including a fix
    to flatten double-nested rows from pyodbc.
    """
    if not records:
        return pd.DataFrame()

    # --- FIX FOR VALUE ERROR: Flatten double-nested records ---
    if isinstance(records[0], tuple) and len(records[0]) == 1 and isinstance(records[0][0], (tuple, list)):
        records = [r[0] for r in records]
    # --------------------------------------------------------

    # Convert records to a list of lists/tuples for DataFrame creation
    try:
        data_list = [tuple(r) for r in records]
        df = pd.DataFrame(data_list)
    except Exception as e:
        print(f"Error creating DataFrame from records: {e}")
        return pd.DataFrame()


    cols = expected_cols_map.get(df.shape[1])

    if cols:
        df.columns = cols
    else:
        df.columns = [f"Col_{i}" for i in range(df.shape[1])]

    return df

# Helper for Income Deletion (Only deletes from the source table)
def delete_income_by_index(df, index_to_delete):
    """Deletes an income record using the DataFrame index to find the DB ID."""
    if df.empty or 'ID' not in df.columns:
        return "Cannot delete: Data not available or missing ID column."
    try:
        # Ensure the ID is correctly cast to an integer
        record_id = int(df.iloc[index_to_delete]['ID'])
        return delete_income(record_id)
    except IndexError:
        return f"Index {index_to_delete} out of bounds."
    except Exception as e:
        return f"Failed to retrieve ID for deletion: {e}"

# Helper for Expense Deletion (Only deletes from the source table)
def delete_expense_by_index(df, index_to_delete):
    """Deletes an expense record using the DataFrame index to find the DB ID."""
    if df.empty or 'ID' not in df.columns:
        return "Cannot delete: Data not available or missing ID column."
    try:
        # Ensure the ID is correctly cast to an integer
        record_id = int(df.iloc[index_to_delete]['ID'])
        return delete_expense(record_id)
    except IndexError:
        return f"Index {index_to_delete} out of bounds."
    except Exception as e:
        return f"Failed to retrieve ID for deletion: {e}"

# --- STYLING FUNCTION FOR TRANSACTIONS TABLE ---
def color_signed_amount(val):
    """
    Applies color to the 'Amount' column based on the sign of the value.
    Positive (Income) is Green, Negative (Expense) is Red.
    """
    try:
        val = float(val)
        if val > 0:
            return 'color: #00CC00'  # Bright Green
        elif val < 0:
            return 'color: #FF4B4B'  # Streamlit Red
        return ''
    except:
        return ''

# ---------------------------


# Dashboard page
def show_dashboard():
    user = st.session_state.user
    user_id = user["user_id"]

    st.sidebar.success(f"👤 Logged in as: {user['name']}")
    if st.sidebar.button("Logout", key="sidebar_logout"):
        reset_session_on_logout(user_id)
        st.session_state.user = None
        st.session_state.chat_history = []
        st.session_state.ai_chart_data = None
        st.rerun()
        return

    st.title(f"📊 Welcome, {user['name']}!")

    # Fetch data
    income_data = get_income(user_id)
    expenses = get_expenses(user_id)

    # --- Income DataFrame ---
    # Expected columns: ["ID", "Source", "Amount", "Date", "Category", "Notes"] (6 columns)
    df_income = create_df_from_records(income_data, {
        6: ["ID", "Source", "Amount", "Date", "Category", "Notes"],
    })
    if "Amount" in df_income.columns:
        df_income["Amount"] = pd.to_numeric(df_income["Amount"], errors="coerce")
        total_income = df_income["Amount"].sum()
    else:
        total_income = 0.0

    # --- Expense DataFrame ---
    # Expected columns: ["ID", "Category", "Description", "Amount", "Date", "Payment Method"] (6 columns)
    df_exp = create_df_from_records(expenses, {
        6: ["ID", "Category", "Description", "Amount", "Date", "Payment Method"],
    })

    if "Amount" in df_exp.columns:
        df_exp["Amount"] = pd.to_numeric(df_exp["Amount"], errors="coerce")
        df_exp = df_exp.dropna(subset=["Amount"])
        total_expenses = df_exp["Amount"].sum()
    else:
        total_expenses = 0.0

    remaining_balance = total_income - total_expenses

    # --- Simple Summary metrics ---
    col1, col2, col3 = st.columns(3)
    col1.metric("💵 Total Income", f"₹ {total_income:,.2f}")
    col2.metric("💸 Total Expenses", f"₹ {total_expenses:,.2f}")
    col3.metric("💰 Remaining Balance", f"₹ {remaining_balance:,.2f}")

    st.markdown("---")

    # Tabs
    tabs = st.tabs(["💵 Income", "💸 Expenses", "🔁 Transactions", "📊 Summary", "🤖 AI Assistant"])

    # 1. Income tab
    with tabs[0]:
        st.subheader("Add Income")
        col_add_inc_1, col_add_inc_2 = st.columns(2)
        with col_add_inc_1:
            src = st.selectbox("Source", options=["Salary", "Freelance", "Investments", "Gift", "Other"], key="inc_src")
            cat = st.selectbox("Category", options=["Work", "Freelance", "Service", "Other"], key="inc_cat")
        with col_add_inc_2:
            amt = st.number_input("Amount", min_value=0.0, key="inc_amt")
            date_input = st.date_input("Date", key="inc_date", value=dt_date.today())

        notes = st.text_area("Notes", key="inc_notes")

        if st.button("Add Income", key="btn_add_income"):
            date_str = date_input.strftime("%Y-%m-%d")
            msg = add_income(user_id, src, amt, date_str, cat, notes)
            if "✅" in msg:
                # Add a record to the transactions table
                add_transaction(user_id, "income", cat, notes or src, amt, date_str)
            st.success(msg)
            st.rerun()

        st.divider()
        st.subheader("Your Income Records")

        # Column configuration helper to define index column properties (if supported)
        try:
            col_config = {"Index": st.column_config.NumberColumn("Index", help="Use this number to delete", width="small", format="%d")}
        except AttributeError:
            col_config = None

        if not df_income.empty and 'ID' in df_income.columns:
            df_display_income = df_income.drop(columns=['ID']).reset_index(names=['Index'])

            st.dataframe(
                df_display_income,
                width='stretch', # FIXED: Replaced use_container_width=True
                column_config=col_config
            )

            st.markdown("#### 🗑️ Delete Income Record by Index")
            available_indices = df_display_income['Index'].tolist()
            if available_indices:
                income_index_to_delete = st.selectbox("Select **Index** to Delete:", available_indices, key="delete_inc_select")
                if st.button("Delete Income", key="btn_delete_income"):
                    if income_index_to_delete is not None and income_index_to_delete >= 0:
                        msg = delete_income_by_index(df_income, income_index_to_delete)
                        st.success(msg)
                        if "deleted" in msg:
                            st.rerun()
                    else:
                        st.warning("Please select a valid Index.")
            else:
                st.info("No indices available to select for deletion.")
        else:
            st.info("No income records found.")

    # 2. Expense tab
    with tabs[1]:
        st.subheader("Add Expense")
        col_add_exp_1, col_add_exp_2 = st.columns(2)
        with col_add_exp_1:
            cat2 = st.selectbox("Category", options=["Food", "Bills", "Transport", "Entertainment", "Shopping", "Other"], key="exp_cat")
            method = st.text_input("Payment Method", key="exp_method", value="Debit Card")
        with col_add_exp_2:
            amt2 = st.number_input("Amount", min_value=0.0, key="exp_amt")
            date_input2 = st.date_input("Date", key="exp_date", value=dt_date.today())

        desc = st.text_input("Description", key="exp_desc")

        if st.button("Add Expense", key="btn_add_expense"):
            date_str2 = date_input2.strftime("%Y-%m-%d")

            try:
                amount_value = float(amt2)
            except ValueError:
                st.error("Invalid amount entered. Please use a number.")
                amount_value = 0.0

            msg = add_expense(user_id, cat2, desc, amount_value, date_str2, method)
            if "✅" in msg:
                # Add a record to the transactions table
                add_transaction(user_id, "expense", cat2, desc or method, amount_value, date_str2)
            st.success(msg)
            st.rerun()

        st.divider()
        st.subheader("Your Expense Records")

        if not df_exp.empty and 'ID' in df_exp.columns:
            # Ensure ID column is numeric for indexing/deletion logic
            df_exp['ID'] = pd.to_numeric(df_exp['ID'], errors='coerce').astype('Int64')
            df_exp_cleaned = df_exp.dropna(subset=['ID'])

            df_display_exp = df_exp_cleaned.drop(columns=['ID']).reset_index(names=['Index'])

            st.dataframe(
                df_display_exp,
                width='stretch', # FIXED: Replaced use_container_width=True
                column_config=col_config
            )

            st.markdown("#### 🗑️ Delete Expense Record by Index")
            available_indices_exp = df_display_exp['Index'].tolist()
            if available_indices_exp:
                expense_index_to_delete = st.selectbox("Select **Index** to Delete:", available_indices_exp, key="delete_exp_select")

                if st.button("Delete Expense", key="btn_delete_expense"):
                    if expense_index_to_delete is not None and expense_index_to_delete >= 0:
                        msg = delete_expense_by_index(df_exp_cleaned, expense_index_to_delete)
                        st.success(msg)
                        if "deleted" in msg:
                            st.rerun()
                    else:
                        st.warning("Please select a valid Index.")
            else:
                st.info("No indices available to select for deletion.")

        else:
            st.info("No expense records found.")


    # 3. Transactions tab
    with tabs[2]:
        st.subheader("All Transactions")

        # --- LOGIC: Combine Income and Expenses on the fly for real-time updates ---

        # 1. Prepare Income for merge
        if not df_income.empty:
            df_inc_temp = df_income.rename(columns={'Source': 'Category_Trans', 'Category': 'Description_Trans', 'Notes': 'Notes_Trans'}).copy()

            df_inc_temp['Description_Trans'] = df_inc_temp.apply(
                lambda row: f"{row['Notes_Trans']} ({row['Description_Trans']})" if row['Notes_Trans'] else row['Description_Trans'],
                axis=1
            )

            df_inc_temp = df_inc_temp[['Date', 'Category_Trans', 'Description_Trans', 'Amount']].copy()
            df_inc_temp.columns = ['Date', 'Category', 'Description', 'Amount']

            df_inc_temp['Type'] = 'income'
        else:
            df_inc_temp = pd.DataFrame()

        # 2. Prepare Expenses for merge
        if not df_exp.empty:
            df_exp_temp = df_exp[['Date', 'Category', 'Description', 'Amount']].copy()
            df_exp_temp['Type'] = 'expense'
        else:
            df_exp_temp = pd.DataFrame()

        # 3. Combine them
        df_all = pd.concat([df_inc_temp, df_exp_temp], ignore_index=True)
        # -----------------------------------------------------------------------------

        if not df_all.empty and "Amount" in df_all.columns:
            # Data cleaning and sorting
            df_all["Date"] = pd.to_datetime(df_all["Date"], errors='coerce')
            df_all["Amount"] = pd.to_numeric(df_all["Amount"], errors="coerce")
            df_all = df_all.dropna(subset=["Amount", "Date"])
            # Ensure transactions are sorted descending by date
            df_all = df_all.sort_values(by="Date", ascending=False)

            # 1. Calculate Signed Amount column for color formatting
            # Note: The expense amount is already positive in df_exp_temp, so we negate it here
            df_all['Amount'] = df_all.apply(
                lambda row: row['Amount'] if row['Type'] == 'income' else -row['Amount'],
                axis=1
            )

            # Get unique dates in descending order
            unique_dates = df_all["Date"].dt.date.unique()

            display_cols = ["Date", "Type", "Category", "Description", "Amount"]

            # Iterate through each unique date to render the summary and table
            for date_val in unique_dates:
                # Filter the main DataFrame to get the group for this date
                group = df_all[df_all["Date"].dt.date == date_val].copy()

                # Calculate Daily Summary (using the already signed 'Amount' column)
                daily_net = group['Amount'].sum()
                daily_income = group[group['Amount'] > 0]['Amount'].sum()
                daily_expense = abs(group[group['Amount'] < 0]['Amount'].sum())

                # Print Daily Summary Box
                st.markdown(f"### 🗓️ {date_val.strftime('%A, %B %d, %Y')}")
                # HTML block to display summary metrics
                st.markdown(f"""
                <div style="padding: 10px; background-color: #333333; border-radius: 5px; margin-bottom: 15px; color: white;">
                    💰 **Daily Net:** ₹{daily_net:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; 💵 Income: ₹{daily_income:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; 💸 Expense: ₹{daily_expense:,.2f}
                </div>
                """, unsafe_allow_html=True)

                # Prepare data for the table for this specific day
                group_display = group[display_cols].copy()
                group_display['Date'] = group_display['Date'].dt.strftime('%Y-%m-%d')

                st.markdown("#### Transactions:")

                # Apply styling function to the 'Amount' column and format it
                # FIXED: Using Styler.map for elementwise styling
                styled_df = group_display.style.map(
                    color_signed_amount,
                    subset=['Amount']
                ).format(
                    {'Amount': '₹ {:,.2f}'}
                )

                # RENDER THE DATAFRAME FOR THIS DAY
                st.dataframe(
                    styled_df,
                    width='stretch', # FIXED: Replaced use_container_width=True
                    hide_index=True
                )

                st.markdown("---") # Separator between days

        else:
            st.info("No transactions found yet.")

    # 4. Summary & charts
    with tabs[3]:
        st.subheader("Summary & Charts")
        if not df_exp.empty and "Amount" in df_exp.columns and "Category" in df_exp.columns:
            summary = df_exp.groupby("Category")["Amount"].sum()
            summary = summary[summary > 0]
            st.write("Total Spending by Category:")
            st.dataframe(summary, width='stretch')

            col_pie, col_bar = st.columns(2)

            with col_pie:
                fig1, ax1 = plt.subplots()
                summary.plot.pie(autopct="%1.1f%%", ax=ax1)
                ax1.set_ylabel("")
                ax1.set_title("Expense Category Breakdown")
                st.pyplot(fig1)

            with col_bar:
                fig2, ax2 = plt.subplots()
                data = pd.Series([total_income, total_expenses], index=["Income", "Expenses"])
                data.plot.bar(ax=ax2, color=['#00CC00', '#FF4B4B'])
                ax2.set_title("Total Income vs Total Expenses")
                ax2.set_ylabel("Amount (₹)")
                plt.xticks(rotation=0)
                st.pyplot(fig2)
        else:
            st.info("No expense data to plot.")

    # 5. AI Assistant tab
    with tabs[4]:
        st.subheader("🤖 Smart Finance Assistant")
        st.write("Ask about your finances or add new entries.")

        # Display chat history (including the latest user query)
        chat_hist = get_chat_history_for_user(user_id)

        for msg in chat_hist:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['text']}")
            else:
                st.markdown(f"💬 **AI:** {msg['text']}")

        # Display chart if provided by AI
        if st.session_state.ai_chart_data and len(st.session_state.ai_chart_data) > 0:
            chart_df = pd.DataFrame(
                list(st.session_state.ai_chart_data.items()),
                columns=['Category', 'Amount']
            )
            chart_df["Amount"] = pd.to_numeric(chart_df["Amount"], errors="coerce")
            chart_df = chart_df[chart_df["Amount"] > 0]

            if not chart_df.empty:
                st.markdown("### 📈 Expense Breakdown Visualization")
                # Use st.bar_chart for a quick display
                st.bar_chart(chart_df.set_index('Category'))
                # IMPORTANT: Chart data is consumed once to avoid infinite display
                st.session_state.ai_chart_data = None

        st.markdown("---")
        user_input = st.text_input("💭 Ask something:", key="ai_input")

        if st.button("Send", key="ai_send"):
            if user_input.strip():
                # handle_ai_query now returns a dictionary
                response_dict = handle_ai_query(user_id, user_input)

                # Safely retrieve chart data
                st.session_state.ai_chart_data = response_dict.get("chart_data")

                # Rerun to update the display (chat history, charts)
                st.rerun()
            else:
                st.warning("Please enter a query.")

# Main entry
if st.session_state.user:
    show_dashboard()
else:
    show_auth_page()
