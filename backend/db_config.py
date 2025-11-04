
# #Db_config.py
# import pyodbc

# # ================== UPDATE THESE ==================
# server = 'DESKTOP-3OQGQOV\\SQLEXPRESS'  # Your SQL Server instance
# database = 'personal_finance_tracker'    # Your database name
# username = 'sa'                          # SQL Server username (optional if using Trusted Connection)
# password = 'Nishant@12'                  # SQL Server password
# # ==================================================

# def get_connection():
#     """
#     Returns a connection object to the SQL Server database.
#     Tries SQL Server Authentication first, then Windows Authentication as fallback.
#     """
#     try:
#         # SQL Server Authentication
#         conn = pyodbc.connect(
#             f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
#         )
#         print(" Connected using SQL Server Authentication!")
#         return conn
#     except Exception as e_sql:
#         print(" SQL Server Authentication failed:", e_sql)
#         print("Trying Windows Authentication...")

#         try:
#             # Windows Authentication
#             conn = pyodbc.connect(
#                 f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
#             )
#             print("Connected using Windows Authentication!")
#             return conn
#         except Exception as e_win:
#             print("Windows Authentication also failed:", e_win)
#             return None


import pyodbc

# ================== UPDATE THESE ==================
# IMPORTANT: Use the most stable ODBC driver. 'ODBC Driver 17 for SQL Server' is recommended.
DRIVER = 'ODBC Driver 17 for SQL Server'
server = 'DESKTOP-3OQGQOV\\SQLEXPRESS'  # Your SQL Server instance
database = 'personal_finance_tracker'   # Your database name
username = 'sa'                         # SQL Server username
password = 'Nishant@12'                 # SQL Server password
# ==================================================

def get_connection():
    """
    Returns a connection object to the SQL Server database.
    Tries SQL Server Authentication first, then Windows Authentication as fallback.
    """
    # Connection string for SQL Server Authentication
    sql_auth_conn_str = (
        f'DRIVER={{{DRIVER}}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password}'
    )

    # Connection string for Windows Authentication
    win_auth_conn_str = (
        f'DRIVER={{{DRIVER}}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'Trusted_Connection=yes;'
    )

    try:
        # 1. SQL Server Authentication attempt (Primary attempt)
        conn = pyodbc.connect(sql_auth_conn_str)
        print("Connected using SQL Server Authentication!")
        return conn
    except Exception as e_sql:
        print("SQL Server Authentication failed:", e_sql)
        print("Trying Windows Authentication...")

        try:
            # 2. Windows Authentication attempt (Fallback)
            conn = pyodbc.connect(win_auth_conn_str)
            print("Connected using Windows Authentication!")
            return conn
        except Exception as e_win:
            print("Windows Authentication also failed:", e_win)
            return None
