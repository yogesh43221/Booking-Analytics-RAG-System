# app/utils.py (Corrected)

import pandas as pd
import numpy as np # Keep numpy import
import mysql.connector
from mysql.connector import errorcode

# MySQL connection details
DB_CONFIG = {
    'user': 'root',
    'password': 'Yogesh@666', # Use your actual password
    'host': 'localhost',
    'port': 3306
    # Database name is added separately where needed
}

DB_NAME = 'hotel_booking_db'
TABLE_NAME = 'bookings'

# Create connection to MySQL server (without selecting DB)
def connect_to_server():
    # Consider adding error handling
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"❌ Error connecting to MySQL Server: {err}")
        return None

# Connect to DB directly
def connect_to_db():
    # Add database to config for direct connection
    db_conn_config = DB_CONFIG.copy()
    db_conn_config['database'] = DB_NAME
    # Consider adding error handling
    try:
        return mysql.connector.connect(**db_conn_config)
    except mysql.connector.Error as err:
        print(f"❌ Error connecting to database '{DB_NAME}': {err}")
        return None

# Create the database if it doesn't exist
def create_database():
    conn = connect_to_server()
    if not conn: return # Exit if server connection failed

    cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print(f"✅ Database `{DB_NAME}` created or already exists.")
    except mysql.connector.Error as err:
        print(f"❌ Failed creating database: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Create table based on selected columns
def create_table():
    conn = connect_to_db()
    if not conn: return # Exit if DB connection failed

    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel VARCHAR(100),
                is_canceled BOOLEAN,
                lead_time INT,
                arrival_date_year INT,
                arrival_date_month VARCHAR(20),
                country VARCHAR(10),
                adr FLOAT,
                booking_date DATE
            )
        """)
        print(f"✅ Table `{TABLE_NAME}` created or already exists.")
    except mysql.connector.Error as err:
         print(f"❌ Failed creating table '{TABLE_NAME}': {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Insert data from CSV
def load_data_to_mysql():
    try:
        df = pd.read_csv('data/hotel_bookings.csv')
    except FileNotFoundError:
        print("❌ Error: data/hotel_bookings.csv not found. Make sure the path is correct.")
        return

    # Preprocess: select columns
    df = df[[
        'hotel', 'is_canceled', 'lead_time', 'arrival_date_year',
        'arrival_date_month', 'country', 'adr'
    ]].copy()

    # Create booking_date column from year and month
    # Explicitly define format to handle month names correctly
    try:
        df['booking_date'] = pd.to_datetime(
             df['arrival_date_year'].astype(str) + '-' + df['arrival_date_month'] + '-01',
             errors='coerce',
             format='%Y-%B-%d' # Match month names like 'July', 'August'
        )
    except ValueError as e:
        print(f"❌ Error converting dates, likely month name mismatch: {e}")
        print("Make sure month names in CSV match full names (e.g., 'July').")
        # Optionally list unique month names found: print(df['arrival_date_month'].unique())
        return

    # Drop rows where date conversion failed
    initial_rows = len(df)
    df.dropna(subset=['booking_date'], inplace=True)
    if len(df) < initial_rows:
         print(f"⚠️ Dropped {initial_rows - len(df)} rows due to invalid date conversion.")


    conn = connect_to_db()
    if not conn: return # Exit if DB connection failed

    cursor = conn.cursor()

    insert_query = f"""
        INSERT INTO {TABLE_NAME}
        (hotel, is_canceled, lead_time, arrival_date_year, arrival_date_month, country, adr, booking_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    # Prepare data tuples, converting pandas dtypes to Python native types where needed
    # Replace potential NaN/NaT with None for SQL compatibility
    data_tuples = []
    for _, row in df.iterrows():
         # Convert row to list, replacing NaN/NaT with None
         values = [None if pd.isna(v) else v for v in row.tolist()]
         data_tuples.append(tuple(values))

    try:
        cursor.executemany(insert_query, data_tuples) # Use executemany
        conn.commit()
        print(f"✅ Inserted {len(data_tuples)} rows into `{TABLE_NAME}`.")
    except mysql.connector.Error as err:
        print(f"❌ Error inserting data: {err}")
        conn.rollback() # Rollback on error
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# --- CORRECTED FUNCTION ---
def fetch_booking_data():
    """Fetches booking data and formats it into descriptive sentences for RAG."""
    print("(Inside utils.py) Fetching data from MySQL for RAG...")
    # Use the DB_CONFIG defined above
    db_conn_config = DB_CONFIG.copy()
    db_conn_config['database'] = DB_NAME # Add database name for connection

    conn = None
    try:
        # Connect using the combined config
        conn = mysql.connector.connect(**db_conn_config) # <<< Use corrected config here
    except mysql.connector.Error as err:
         print(f"❌ Error connecting to database '{DB_NAME}': {err}")
         return [] # Return empty list if connection fails

    # Select necessary columns including 'id' if needed for mapping later
    query = f"SELECT id, hotel, is_canceled, lead_time, arrival_date_year, arrival_date_month, country, adr FROM {TABLE_NAME}"

    df = None
    try:
        # Use pandas UserWarning suppression context if desired, or ignore the warning
        df = pd.read_sql_query(query, conn)
    except Exception as e:
         print(f"❌ Error fetching data with pandas: {e}")
         # Ensure connection is closed even if pandas fails
         if conn and conn.is_connected():
              conn.close()
         return [] # Return empty list on error
    finally:
        # Close connection if pandas was successful or failed after opening
        if conn and conn.is_connected():
             conn.close()

    texts = []
    if df is None or df.empty:
         print("⚠️ No data fetched from database.")
         return texts

    for _, row in df.iterrows():
        # Create the descriptive sentence, handling potential None/NaN values from DB
        try:
            # Check for None before int conversion for is_canceled
            canceled_val = row.get('is_canceled')
            canceled_text = "Yes" if canceled_val is not None and int(canceled_val) == 1 else "No"

            # Use .get with defaults and ensure type conversions handle None
            adr_val = row.get('adr', 0)
            lead_time_val = row.get('lead_time', 0)

            text = (
                 f"Booking at {row.get('hotel', 'N/A')} in {row.get('country', 'N/A')}. "
                 f"Arrival: {row.get('arrival_date_month', 'N/A')} {row.get('arrival_date_year', 'N/A')}. "
                 f"Canceled: {canceled_text}. ADR: {float(adr_val if adr_val is not None else 0):.2f}. "
                 f"Lead time: {int(lead_time_val if lead_time_val is not None else 0)} days."
            )
            texts.append(text)
        except Exception as e:
             print(f"⚠️ Error formatting row {row.get('id', 'N/A')}: {e}")
             # Optionally append a placeholder or skip the row

    print(f"(Inside utils.py) Fetched and formatted {len(texts)} text records for RAG.")
    return texts
# --- END OF CORRECTION ---


# Keep the original main execution block if you still use it for setup
if __name__ == "__main__":
    create_database()
    create_table()
    load_data_to_mysql()