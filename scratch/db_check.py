import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", 5432),
        dbname=os.getenv("POSTGRES_DB", "ai_news"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    print("Successfully connected to the database.")
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print("Database is ready.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error connecting to database: {e}")
