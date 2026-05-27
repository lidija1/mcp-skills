import dashboard_db


dashboard_db.init_db()
print(f"Dashboard tables are ready at {dashboard_db.DB_PATH}")
