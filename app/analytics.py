# app/analytics.py

import mysql.connector
import pandas as pd
from mysql.connector import errorcode

# --- Database Configuration ---
# NOTE: Ideally, import these from utils.py or a central config file
# to avoid repetition. For simplicity here, we redefine them.
DB_CONFIG = {
    'user': 'root',
    'password': 'Yogesh@666',  # Use your actual password
    'host': 'localhost',
    'port': 3306,
    'database': 'hotel_booking_db' # Connect directly to the database
}
TABLE_NAME = 'bookings'

# --- Helper Function to Execute Queries ---
def execute_query(query, fetch_option="all"):
    """Connects to DB, executes query, fetches results into DataFrame."""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if fetch_option == "dataframe":
             # Use pandas for easier handling, especially for trends/distributions
            df = pd.read_sql_query(query, conn)
            return df
        else:
            cursor = conn.cursor(dictionary=True) # Fetch as dictionaries
            cursor.execute(query)
            if fetch_option == "all":
                results = cursor.fetchall()
            elif fetch_option == "one":
                results = cursor.fetchone()
            else: # No fetch needed (e.g., for health check)
                results = None
            cursor.close()
            return results
    except mysql.connector.Error as err:
        print(f"❌ Database Error: {err}")
        # Depending on the error (e.g., connection refused), you might return specific health statuses
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Check your username or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"Database '{DB_CONFIG['database']}' does not exist")
        # Return None or empty structure on error
        return pd.DataFrame() if fetch_option == "dataframe" else None
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- Analytics Functions ---

def get_revenue_trends():
    """Calculates total revenue (sum of adr) grouped by year and month."""
    # Assuming 'adr' (Average Daily Rate) represents revenue contribution per booking
    query = f"""
        SELECT
            arrival_date_year,
            arrival_date_month,
            SUM(adr) AS total_revenue
        FROM {TABLE_NAME}
        WHERE is_canceled = 0  -- Only consider non-canceled bookings for revenue
        GROUP BY arrival_date_year, arrival_date_month
        ORDER BY arrival_date_year, MONTH(STR_TO_DATE(arrival_date_month,'%M'));
    """
    print("📊 Fetching revenue trends...")
    df = execute_query(query, fetch_option="dataframe")
    print(f"✅ Found revenue data for {len(df)} month(s).")
    return df

def get_cancellation_rate():
    """Calculates the overall cancellation rate."""
    query = f"""
        SELECT
            (SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*)) * 100 AS cancellation_rate_percent
        FROM {TABLE_NAME};
    """
    print("📊 Fetching cancellation rate...")
    result = execute_query(query, fetch_option="one")
    rate = result['cancellation_rate_percent'] if result else 0
    print(f"✅ Calculated cancellation rate: {rate:.2f}%")
    return {"cancellation_rate_percent": rate}

def get_geo_distribution():
    """Counts bookings grouped by country."""
    # Limit to top N countries for brevity, adjust N as needed
    top_n = 15
    query = f"""
        SELECT
            country,
            COUNT(*) AS booking_count
        FROM {TABLE_NAME}
        WHERE country IS NOT NULL AND country != '' AND country != 'NULL' -- Handle potential bad data
        GROUP BY country
        ORDER BY booking_count DESC
        LIMIT {top_n};
    """
    print(f"📊 Fetching geographical distribution (Top {top_n})...")
    df = execute_query(query, fetch_option="dataframe")
    print(f"✅ Found booking counts for {len(df)} countries.")
    return df

def get_lead_time_distribution():
    """Calculates average lead time and distribution percentiles."""
    query = f"""
        SELECT
            AVG(lead_time) AS average_lead_time,
            MIN(lead_time) AS min_lead_time,
            MAX(lead_time) AS max_lead_time,
            -- Calculate percentiles if supported and needed (syntax varies by MySQL version)
            -- Example for newer MySQL/MariaDB:
            -- PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY lead_time) AS percentile_25,
            -- PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY lead_time) AS median_lead_time,
            -- PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY lead_time) AS percentile_75
            -- For broader compatibility, we'll stick to AVG/MIN/MAX here
            COUNT(*) as total_bookings_analyzed
        FROM {TABLE_NAME};
        -- WHERE lead_time >= 0 -- Add constraints if needed
    """
    print("📊 Fetching lead time distribution stats...")
    result = execute_query(query, fetch_option="one")
    if result:
        print(f"✅ Calculated lead time stats: Avg={result.get('average_lead_time', 0):.2f}, Min={result.get('min_lead_time', 0)}, Max={result.get('max_lead_time', 0)}")
    # For a histogram-like distribution, you might query counts grouped by lead_time ranges
    # e.g., GROUP BY FLOOR(lead_time / 30) for monthly bins
    return result if result else {}


# --- (Optional) Health Check Function ---
def check_db_connection():
    """Checks if a connection to the database can be established."""
    print("🩺 Checking database connection...")
    conn = None
    try:
        # Try connecting with a short timeout
        conn = mysql.connector.connect(**DB_CONFIG, connection_timeout=5)
        if conn.is_connected():
            print("✅ Database connection successful.")
            return {"status": "ok", "message": "Database connection successful"}
        else:
            print("❌ Database connection failed (unknown reason).")
            return {"status": "error", "message": "Database connection failed"}
    except mysql.connector.Error as err:
        print(f"❌ Database connection error: {err}")
        return {"status": "error", "message": str(err)}
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    # Example usage when running this file directly
    print("\n--- Running Analytics Examples ---")
    revenue = get_revenue_trends()
    print("Revenue Trends:\n", revenue.head())

    rate = get_cancellation_rate()
    print("\nCancellation Rate:", rate)

    geo = get_geo_distribution()
    print("\nGeo Distribution:\n", geo.head())

    lead_time = get_lead_time_distribution()
    print("\nLead Time Stats:", lead_time)

    health = check_db_connection()
    print("\nDB Health Check:", health)
    print("\n--- Analytics Examples Complete ---")