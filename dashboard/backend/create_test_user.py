from database import SessionLocal
from models import User
from security import hash_password

# Open DB session
session = SessionLocal()

# Create test user
user = User(
    username="ld",
    password_hash=hash_password("ld123"),
    role="user"
)

# Save user
session.add(user)
session.commit()

print("Test user created")