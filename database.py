from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime

# SQLite database file
DATABASE_URL = "sqlite:///chat.db"

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create base class for models
Base = declarative_base()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Thread(Base):
    """Thread model representing a conversation thread."""
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to messages
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")


class Message(Base):
    """Message model representing a single message in a thread."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to thread
    thread = relationship("Thread", back_populates="messages")


def init_db():
    """Initialize the database by creating all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """
    Dependency function that yields a SQLAlchemy session.
    Used for FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
