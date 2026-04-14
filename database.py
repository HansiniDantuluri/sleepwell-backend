from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite for local development — easy to swap to PostgreSQL later:
# DATABASE_URL = "postgresql://user:password@localhost/sleepwell"
DATABASE_URL = "sqlite:///./sleepwell.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite only
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency: provides a DB session per request, always closes after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
