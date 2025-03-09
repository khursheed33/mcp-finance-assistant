import sqlite3
from datetime import datetime

import sqlite3
from datetime import datetime
from pathlib import Path

# Get the absolute path to the project root and db directory
BASE_DIR = Path(__file__).resolve().parent.parent  # Moves up from /src to project root
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "transactions.db"

def init_db():
    # Create db directory if it doesn’t exist
    DB_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            amount REAL,
            category TEXT,
            description TEXT
        )
    """)
    # Insert mock data if table is empty
    cursor.execute("SELECT COUNT(*) FROM transactions")
    if cursor.fetchone()[0] == 0:
        mock_data = [
            ("2025-03-01", 50.0, "Food", "Groceries"),
            ("2025-03-02", 20.0, "Transport", "Bus fare"),
            ("2025-03-03", 100.0, "Entertainment", "Movie tickets"),
        ]
        cursor.executemany("INSERT INTO transactions (date, amount, category, description) VALUES (?, ?, ?, ?)", mock_data)
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect("db/transactions.db")
    cursor = conn.cursor()
    cursor.execute("SELECT date, amount, category, description FROM transactions")
    rows = cursor.fetchall()
    conn.close()
    return [{"date": r[0], "amount": r[1], "category": r[2], "description": r[3]} for r in rows]

def add_transaction(amount: float, category: str, description: str):
    conn = sqlite3.connect("db/transactions.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transactions (date, amount, category, description) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d"), amount, category, description)
    )
    conn.commit()
    conn.close()