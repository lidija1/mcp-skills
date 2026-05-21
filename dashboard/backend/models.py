from sqlalchemy import Column, Integer, String

from database import Base


class User(Base):
    __tablename__ = "users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Username mora biti unique
    username = Column(String, unique=True, nullable=False)

    # Ovde ide bcrypt hash
    password_hash = Column(String, nullable=False)

    # admin ili user
    role = Column(String, default="user")