from database import SessionLocal
from models import User
from security import hash_password

# Open DB session
session = SessionLocal()

# Create test user
user = User(
    username="lidija",
    password_hash=hash_password("test123"),
    role="admin"
)

# Save user
session.add(user)
session.commit()

print("Test user created")