"""
database.py
───────────
النماذج + Auth (email / password_hash) + سجل العمليات + طلبات السحب.
"""
import logging
from datetime import datetime

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String, Text, create_engine)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

logger = logging.getLogger(__name__)

import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rewards.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
#  جدول المستخدمين
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(100), nullable=False, unique=True, index=True)
    email         = Column(String(200), nullable=False, unique=True, index=True)
    password_hash = Column(String(256), nullable=False)
    balance       = Column(Float, nullable=False, default=0.0)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_login    = Column(DateTime, nullable=True)

    transactions      = relationship("Transaction",     back_populates="user", cascade="all, delete-orphan")
    withdraw_requests = relationship("WithdrawRequest", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


# ─────────────────────────────────────────────
#  جدول العمليات (إيرادات من العروض)
# ─────────────────────────────────────────────
class Transaction(Base):
    __tablename__ = "transactions"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider    = Column(String(50),  nullable=False)
    offer_id    = Column(String(200), nullable=True)
    tx_id       = Column(String(200), nullable=False, unique=True, index=True)
    amount      = Column(Float,       nullable=False)
    currency    = Column(String(10),  default="USD")
    ip_address  = Column(String(50),  nullable=True)
    raw_params  = Column(Text,        nullable=True)
    created_at  = Column(DateTime,    default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")


# ─────────────────────────────────────────────
#  جدول طلبات السحب
# ─────────────────────────────────────────────
class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"

    id         = Column(Integer,  primary_key=True, index=True)
    user_id    = Column(Integer,  ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    method     = Column(String(50),  nullable=False)   # paypal / crypto_usdt / vodafone_cash / bank_transfer / gift_cards
    address    = Column(String(300), nullable=False)   # رقم الهاتف أو العنوان أو IBAN
    amount     = Column(Float,       nullable=False)   # بالـ USD
    status     = Column(String(20),  default="pending")  # pending / approved / rejected / paid
    admin_note = Column(Text,        nullable=True)    # ملاحظة منك كمسؤولة
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="withdraw_requests")

    def __repr__(self):
        return f"<WithdrawRequest id={self.id} user_id={self.user_id} method={self.method} amount={self.amount} status={self.status}>"


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("✅ تم تهيئة قاعدة البيانات (مع جداول Auth + WithdrawRequest).")
