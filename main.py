"""
main.py
───────
Offers & Rewards Backend — FastAPI + SQLite
رفع على Railway: يقرأ PORT من متغيرات البيئة تلقائياً.
"""

import json
import logging
import logging.handlers
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from config import PORT, PROVIDERS, LOG_LEVEL
from database import Transaction, User, get_db, init_db
from security import verify_request

# ─────────────────────────────────────────────
#  إعداد الـ Logging  (ملف + console)
# ─────────────────────────────────────────────

LOG_DIR  = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

formatter = logging.Formatter(
    fmt   = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)

# Handler 1: ملف يومي يحتفظ بآخر 30 يوم
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename    = os.path.join(LOG_DIR, "rewards.log"),
    when        = "midnight",
    backupCount = 30,
    encoding    = "utf-8",
)
file_handler.setFormatter(formatter)

# Handler 2: الطرفية (يظهر في Railway logs)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logging.basicConfig(
    level    = getattr(logging, LOG_LEVEL, logging.INFO),
    handlers = [file_handler, console_handler],
)

logger = logging.getLogger("rewards")


# ─────────────────────────────────────────────
#  دورة حياة التطبيق
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("🚀  تم تشغيل خادم Rewards API | providers=%s",
                list(PROVIDERS.keys()))
    yield
    logger.info("🔒  تم إيقاف الخادم.")


app = FastAPI(
    title       = "Offers & Rewards API",
    description = "Backend لاستقبال Postbacks من شركات العروض وتحديث أرصدة المستخدمين.",
    version     = "1.0.0",
    lifespan    = lifespan,
)


# ─────────────────────────────────────────────
#  مجموعة معرّفات العمليات المُعالَجة (Idempotency)
# ─────────────────────────────────────────────

_processed: set[str] = set()


def already_processed(tx_id: str) -> bool:
    if tx_id in _processed:
        return True
    _processed.add(tx_id)
    return False


# ─────────────────────────────────────────────
#  Postback Endpoint  GET /postback/{provider}
# ─────────────────────────────────────────────

@app.get(
    "/postback/{provider}",
    summary     = "استقبال مكافأة من شركة عروض",
    response_class = PlainTextResponse,   # معظم الشركات تتوقع "1" أو "OK"
)
async def postback(
    provider: str,
    request:  Request,
    db:       Session = Depends(get_db),
):
    params     = dict(request.query_params)
    client_ip  = request.client.host
    provider   = provider.lower().strip()

    logger.info(
        "📥  Postback وارد | provider=%s | IP=%s | params=%s",
        provider, client_ip, params,
    )

    # ── 1. التحقق من وجود الشركة في القائمة ──────────────
    cfg = PROVIDERS.get(provider)
    if not cfg:
        logger.warning("⚠️   شركة غير معروفة: %s", provider)
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"المزود '{provider}' غير مدعوم.",
        )

    # ── 2. استخراج الحقول الأساسية ───────────────────────
    user_id_raw = params.get(cfg.param_user)
    amount_raw  = params.get(cfg.param_amount)
    tx_id       = params.get(cfg.param_tx_id)
    offer_id    = params.get(cfg.param_offer, "")

    if not all([user_id_raw, amount_raw, tx_id]):
        missing = [k for k, v in {
            cfg.param_user: user_id_raw,
            cfg.param_amount: amount_raw,
            cfg.param_tx_id: tx_id,
        }.items() if not v]
        logger.warning("❌  حقول مفقودة من %s: %s", provider, missing)
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = f"حقول مفقودة: {missing}",
        )

    try:
        user_id = int(user_id_raw)
        amount  = round(float(amount_raw) / cfg.amount_divisor, 4)
    except ValueError:
        logger.warning("❌  قيم غير صالحة | user_id=%s amount=%s", user_id_raw, amount_raw)
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "user_id أو amount بقيمة غير صالحة.",
        )

    # ── 3. التحقق من التوقيع ─────────────────────────────
    if not verify_request(provider, cfg, params):
        logger.warning(
            "🚫  توقيع مرفوض | provider=%s | user_id=%s | tx_id=%s",
            provider, user_id, tx_id,
        )
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "توقيع غير صالح.",
        )

    # ── 4. منع المعالجة المزدوجة ─────────────────────────
    full_tx_id = f"{provider}:{tx_id}"

    if already_processed(full_tx_id):
        logger.info("🔁  عملية مكررة تجاهلناها | tx_id=%s", full_tx_id)
        return PlainTextResponse("1")  # نُعيد "1" حتى لا تُعيد الشركة الإرسال

    # تحقق مزدوج من قاعدة البيانات (ضمان بعد إعادة تشغيل الخادم)
    existing = db.query(Transaction).filter(Transaction.tx_id == full_tx_id).first()
    if existing:
        logger.info("🔁  tx_id موجود بالفعل في DB | tx_id=%s", full_tx_id)
        return PlainTextResponse("1")

    # ── 5. التحقق من وجود المستخدم ───────────────────────
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning("❌  مستخدم غير موجود | user_id=%s", user_id)
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"المستخدم {user_id} غير موجود.",
        )

    # ── 6. تحديث الرصيد وحفظ السجل ──────────────────────
    old_balance = user.balance
    user.balance = round(user.balance + amount, 4)

    txn = Transaction(
        user_id    = user_id,
        provider   = provider,
        offer_id   = offer_id,
        tx_id      = full_tx_id,
        amount     = amount,
        currency   = cfg.currency,
        ip_address = client_ip,
        raw_params = json.dumps(params, ensure_ascii=False),
    )
    db.add(txn)
    db.commit()
    db.refresh(user)

    logger.info(
        "💰  مكافأة مُضافة | المستخدم='%s' (id=%s) | الشركة=%s | "
        "المبلغ=+%.4f %s | الرصيد القديم=%.4f → الرصيد الجديد=%.4f | tx_id=%s",
        user.username, user_id, cfg.name,
        amount, cfg.currency,
        old_balance, user.balance,
        full_tx_id,
    )

    return PlainTextResponse("1")   # الاستجابة المطلوبة من معظم شركات العروض


# ─────────────────────────────────────────────
#  Endpoints الإدارية
# ─────────────────────────────────────────────

@app.post("/users", summary="إنشاء مستخدم جديد", status_code=201)
async def create_user(username: str, db: Session = Depends(get_db)):
    user = User(username=username, balance=0.0)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("👤  مستخدم جديد | id=%s username=%s", user.id, user.username)
    return {"id": user.id, "username": user.username, "balance": user.balance}


@app.get("/users/{user_id}", summary="بيانات مستخدم")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود.")
    return {
        "id":           user.id,
        "username":     user.username,
        "balance":      user.balance,
        "created_at":   user.created_at.isoformat(),
    }


@app.get("/users/{user_id}/transactions", summary="سجل عمليات مستخدم")
async def get_transactions(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود.")
    return [
        {
            "id":         t.id,
            "provider":   t.provider,
            "offer_id":   t.offer_id,
            "amount":     t.amount,
            "currency":   t.currency,
            "created_at": t.created_at.isoformat(),
        }
        for t in user.transactions
    ]


@app.get("/providers", summary="قائمة الشركات المدعومة")
async def list_providers():
    return [
        {"key": k, "name": v.name, "currency": v.currency}
        for k, v in PROVIDERS.items()
    ]


@app.get("/health", summary="فحص حالة الخادم")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ─────────────────────────────────────────────
#  تشغيل محلي
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)


# ═════════════════════════════════════════════
#  Auth Endpoints  (تسجيل / دخول / بيانات)
# ═════════════════════════════════════════════

from pydantic import BaseModel, EmailStr, Field
from auth import register_user, login_user, decode_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer(auto_error=False)


class RegisterBody(BaseModel):
    username: str  = Field(..., min_length=3, max_length=50)
    email:    str  = Field(..., min_length=5)
    password: str  = Field(..., min_length=6)


class LoginBody(BaseModel):
    identifier: str   # email أو username
    password:   str


def _current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db:    Session = Depends(get_db),
) -> "User":
    """Dependency: يُعيد المستخدم الحالي من الـ JWT أو يرفع 401."""
    from database import User as UserModel
    if not creds:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول.")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="الجلسة منتهية، سجّل دخولك مجدداً.")
    user = db.query(UserModel).filter(UserModel.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="المستخدم غير موجود.")
    return user


@app.post("/auth/register", summary="إنشاء حساب جديد", status_code=201,
          tags=["Auth"])
async def api_register(body: RegisterBody, db: Session = Depends(get_db)):
    user, err = register_user(db, body.username, body.email, body.password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    from auth import create_token
    token = create_token(user.id, user.username)
    logger.info("🎉  تسجيل ناجح عبر API | user_id=%s", user.id)
    return {
        "token":    token,
        "user_id":  user.id,
        "username": user.username,
        "email":    user.email,
        "balance":  user.balance,
    }


@app.post("/auth/login", summary="تسجيل الدخول", tags=["Auth"])
async def api_login(body: LoginBody, db: Session = Depends(get_db)):
    user, token_or_err = login_user(db, body.identifier, body.password)
    if not user:
        raise HTTPException(status_code=401, detail=token_or_err)
    return {
        "token":      token_or_err,
        "user_id":    user.id,
        "username":   user.username,
        "email":      user.email,
        "balance":    user.balance,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


@app.get("/auth/me", summary="بيانات المستخدم الحالي", tags=["Auth"])
async def api_me(
    current = Depends(_current_user),
    db: Session = Depends(get_db),
):
    txns = [
        {
            "id":         t.id,
            "provider":   t.provider,
            "offer_id":   t.offer_id,
            "amount":     t.amount,
            "currency":   t.currency,
            "created_at": t.created_at.isoformat(),
        }
        for t in current.transactions
    ]
    logger.info("📊  /auth/me | user_id=%s | txns=%d", current.id, len(txns))
    return {
        "user_id":      current.id,
        "username":     current.username,
        "email":        current.email,
        "balance":      current.balance,
        "created_at":   current.created_at.isoformat(),
        "last_login":   current.last_login.isoformat() if current.last_login else None,
        "transactions": txns,
    }
