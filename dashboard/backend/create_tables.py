# Import Base i engine
from database import Base, engine

# Import svih modela
# VEOMA VAŽNO:
# SQLAlchemy mora da "vidi" modele
from models import User


# Kreira sve tabele koje ne postoje
Base.metadata.create_all(bind=engine)

print("Tables created successfully")