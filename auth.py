"""
auth.py
───────
تشفير كلمات المرور + توليد/التحقق من JWT tokens.
"""

import logging
import os
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import User

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  الإعدادات — غيّرها في Railway → Variables
# ─────────────────────────────────────────────
SECRET_KEY      = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET_IN_PRODUCTION_32CHARS")
ALGORITHM       = "HS256"
TOKEN_EXPIRE_DAYS = 30          # الجلسة تبقى 30 يوم بدون إعادة تسجيل

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────────────────────
#  كلمات المرور
# ─────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ─────────────────────────────────────────────
#  JWT
# ─────────────────────────────────────────────

def create_token(user_id: int, username: str) -> str:
    """يُنشئ JWT يصلح لمدة TOKEN_EXPIRE_DAYS."""
    payload = {
        "sub":      str(user_id),
        "username": username,
        "exp":      datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS),
        "iat":      datetime.utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    logger.info("🔑  تم إنشاء Token | user_id=%s | expires_in=%dd",
                user_id, TOKEN_EXPIRE_DAYS)
    return token


def decode_token(token: str) -> dict | None:
    """يُحلل JWT ويُعيد الـ payload، أو None عند الفشل."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.warning("⚠️  Token غير صالح: %s", e)
        return None


# ─────────────────────────────────────────────
#  منطق التسجيل وتسجيل الدخول
# ─────────────────────────────────────────────

def register_user(db: Session, username: str,
                  email: str, password: str) -> tuple[User | None, str]:
    """
    يُنشئ مستخدماً جديداً.
    يُعيد (user, "") عند النجاح أو (None, "رسالة الخطأ") عند الفشل.
    """
    username = username.strip()
    email    = email.strip().lower()

    if db.query(User).filter(User.username == username).first():
        return None, "اسم المستخدم مأخوذ، جرّب اسماً آخر."
    if db.query(User).filter(User.email == email).first():
        return None, "البريد الإلكتروني مسجّل مسبقاً."
    if len(password) < 6:
        return None, "كلمة المرور يجب أن تكون 6 أحرف على الأقل."

    user = User(
        username      = username,
        email         = email,
        password_hash = hash_password(password),
        balance       = 0.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("👤  حساب جديد | id=%s | username=%s | email=%s",
                user.id, user.username, user.email)
    return user, ""


def login_user(db: Session, identifier: str,
               password: str) -> tuple[User | None, str]:
    """
    تسجيل الدخول بالبريد أو اسم المستخدم.
    يُعيد (user, token) أو (None, "رسالة الخطأ").
    """
    identifier = identifier.strip()
    user = (
        db.query(User).filter(User.email == identifier.lower()).first()
        or db.query(User).filter(User.username == identifier).first()
    )

    if not user:
        logger.warning("🚫  محاولة دخول بمعرّف غير موجود: %s", identifier)
        return None, "البريد أو اسم المستخدم غير موجود."

    if not verify_password(password, user.password_hash):
        logger.warning("🚫  كلمة مرور خاطئة | user_id=%s", user.id)
        return None, "كلمة المرور غير صحيحة."

    if not user.is_active:
        return None, "الحساب موقوف، تواصل مع الدعم."

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_token(user.id, user.username)
    logger.info("✅  تسجيل دخول ناجح | user_id=%s | username=%s",
                user.id, user.username)
    return user, token
