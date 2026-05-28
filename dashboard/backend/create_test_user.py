import dashboard_db


try:
    user = dashboard_db.create_user(
        username="ld",
        password="ld123",
        first_name="Lidija",
        last_name="Dubovac",
        role="admin",
    )
    print(f"Test user created: {user['username']} ({user['role']})")
except Exception as exc:
    if "UNIQUE constraint failed" in str(exc):
        print("Test user already exists")
    else:
        raise
