import json
import sqlite3

db = r"C:\data\dashboard.db"

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

for table in ["users", "jobs", "sessions"]:
    print(f"\n== {table} ==")
    rows = conn.execute(f"SELECT * FROM {table} LIMIT 10").fetchall()
    print(json.dumps([dict(row) for row in rows], indent=2, default=str))

conn.close()