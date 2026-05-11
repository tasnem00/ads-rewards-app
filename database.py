"""
database.py
───────────
إعداد قاعدة البيانات SQLite عبر SQLAlchemy.
"""

import logging
from datetime import datetime

from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String,
                        Text, create_engine)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///./rewards.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # مطلوب لـ SQLite مع FastAPI
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ─────────────────────────────────────────────
#  النماذج (Models)
# ─────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class User(Base):
    """جدول المستخدمين."""
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(100), nullable=False)
    balance    = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="user",
                                cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} username={self.username} balance={self.balance}>"


class Transaction(Base):
    """سجل جميع عمليات الإيداع الواردة من شركات العروض."""
    __tablename__ = "transactions"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    provider    = Column(String(50), nullable=False)   # adgate | bitlabs | offertoro
    offer_id    = Column(String(200), nullable=True)
    tx_id       = Column(String(200), nullable=False, unique=True, index=True)
    amount      = Column(Float, nullable=False)
    currency    = Column(String(10), default="USD")
    ip_address  = Column(String(50), nullable=True)
    raw_params  = Column(Text, nullable=True)          # كل params الطلب كـ JSON
    created_at  = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")


# ─────────────────────────────────────────────
#  Dependency: جلسة قاعدة البيانات
# ─────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """إنشاء جميع الجداول عند التشغيل الأول."""
    Base.metadata.create_all(bind=engine)
    logger.info("✅  تم تهيئة قاعدة البيانات.")
