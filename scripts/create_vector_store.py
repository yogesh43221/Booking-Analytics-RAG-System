# app/create_vector_store.py (Enhanced Aggregation)

import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import mysql.connector
import os
import pickle

# --- Config ---
MODEL_NAME = 'all-MiniLM-L6-v2'
FAISS_INDEX_PATH = 'vector_store/faiss_index.index'
DOCS_PATH = 'vector_store/text_data.pkl'

MYSQL_DB_CONFIG = {
    'user': 'root',
    'password': 'Your_password',
    'host': 'localhost',
    'port': 3306,
    'database': 'hotel_booking_db'
}
TABLE_NAME = 'bookings'

def fetch_aggregated_booking_data():
    print("Connecting to MySQL for grouped booking data...")
    conn = mysql.connector.connect(**MYSQL_DB_CONFIG)
    
    query = f"""
        SELECT
            hotel,
            country,
            arrival_date_year AS year,
            arrival_date_month AS month,
            COUNT(*) AS total_bookings,
            AVG(adr) AS avg_adr,
            AVG(lead_time) AS avg_lead_time,
            SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100 AS cancellation_rate
        FROM {TABLE_NAME}
        GROUP BY hotel, country, arrival_date_year, arrival_date_month
        ORDER BY year, month;
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f"✅ Fetched {len(df)} grouped booking records.")
    return df

def format_summary_texts(df):
    texts = []

    for _, row in df.iterrows():
        summary = (
            f"In {row['month']} {int(row['year'])}, there were {int(row['total_bookings'])} bookings "
            f"at {row['hotel']} in {row['country']}. "
            f"Average ADR: ${row['avg_adr']:.2f}, average lead time: {int(row['avg_lead_time'])} days, "
            f"cancellation rate: {row['cancellation_rate']:.2f}%."
        )
        texts.append(summary)

    print(f"✅ Formatted {len(texts)} summary texts for embedding.")
    return texts

def create_faiss_index(texts):
    print("🔍 Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    print("📐 Generating embeddings...")
    embeddings = model.encode(texts, show_progress_bar=True).astype('float32')

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    print(f"💾 Saving FAISS index to {FAISS_INDEX_PATH}...")
    faiss.write_index(index, FAISS_INDEX_PATH)

    with open(DOCS_PATH, 'wb') as f:
        pickle.dump(texts, f)

    print("✅ Enhanced FAISS index and summaries saved.")

if __name__ == '__main__':
    df = fetch_aggregated_booking_data()
    if not df.empty:
        texts = format_summary_texts(df)
        create_faiss_index(texts)
    else:
        print("❌ No data found to index.")
