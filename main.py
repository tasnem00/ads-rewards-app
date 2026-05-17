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
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import create_token, decode_token, login_user, register_user
from config import LOG_LEVEL, PORT, PROVIDERS
from database import Transaction, User, get_db, init_db
from security import verify_request

# ─────────────────────────────────────────────
#  Logging  (ملف يومي + console)
# ─────────────────────────────────────────────

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

formatter = logging.Formatter(
    fmt     = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename    = os.path.join(LOG_DIR, "rewards.log"),
    when        = "midnight",
    backupCount = 30,
    encoding    = "utf-8",
)
file_handler.setFormatter(formatter)
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
    logger.info("🚀  تم تشغيل Rewards API | providers=%s", list(PROVIDERS.keys()))
    yield
    logger.info("🔒  تم إيقاف الخادم.")


app = FastAPI(
    title       = "Offers & Rewards API",
    description = "Backend لاستقبال Postbacks وإدارة حسابات المستخدمين.",
    version     = "2.0.0",
    lifespan    = lifespan,
)
from postback_routes import router as postback_router
app.include_router(postback_router)
# ─────────────────────────────────────────────
#  Idempotency Cache
# ─────────────────────────────────────────────

_processed: set[str] = set()


def already_processed(tx_id: str) -> bool:
    if tx_id in _processed:
        return True
    _processed.add(tx_id)
    return False


# ═════════════════════════════════════════════
#  Auth  —  Models + Dependency
# ═════════════════════════════════════════════

bearer = HTTPBearer(auto_error=False)


class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email:    str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)


class LoginBody(BaseModel):
    identifier: str
    password:   str


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db:    Session = Depends(get_db),
) -> User:
    if not creds:
        raise HTTPException(status_code=401, detail="يجب تسجيل الدخول.")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="الجلسة منتهية، سجّل دخولك مجدداً.")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="المستخدم غير موجود.")
    return user


# ─────────────────────────────────────────────
#  Auth Endpoints
# ─────────────────────────────────────────────

@app.post("/auth/register", summary="إنشاء حساب جديد", status_code=201, tags=["Auth"])
async def api_register(body: RegisterBody, db: Session = Depends(get_db)):
    logger.info("📝  طلب تسجيل | username=%s email=%s", body.username, body.email)
    user, err = register_user(db, body.username, body.email, body.password)
    if err:
        logger.warning("❌  فشل التسجيل | %s", err)
        raise HTTPException(status_code=400, detail=err)
    token = create_token(user.id, user.username)
    logger.info("🎉  تسجيل ناجح | user_id=%s", user.id)
    return {
        "token":    token,
        "user_id":  user.id,
        "username": user.username,
        "email":    user.email,
        "balance":  user.balance,
    }


@app.post("/auth/login", summary="تسجيل الدخول", tags=["Auth"])
async def api_login(body: LoginBody, db: Session = Depends(get_db)):
    logger.info("🔑  طلب دخول | identifier=%s", body.identifier)
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
async def api_me(current: User = Depends(get_current_user)):
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
    logger.info("📊  /auth/me | user_id=%s | balance=%.4f | txns=%d",
                current.id, current.balance, len(txns))
    return {
        "user_id":      current.id,
        "username":     current.username,
        "email":        current.email,
        "balance":      current.balance,
        "created_at":   current.created_at.isoformat(),
        "last_login":   current.last_login.isoformat() if current.last_login else None,
        "transactions": txns,
    }


# ═════════════════════════════════════════════
#  Postback Endpoint
# ═════════════════════════════════════════════

@app.get("/postback/{provider}", summary="استقبال مكافأة من شركة عروض",
         response_class=PlainTextResponse, tags=["Postback"])
async def postback(provider: str, request: Request, db: Session = Depends(get_db)):
    params    = dict(request.query_params)
    client_ip = request.client.host
    provider  = provider.lower().strip()

    logger.info("📥  Postback | provider=%s | IP=%s | params=%s",
                provider, client_ip, params)

    cfg = PROVIDERS.get(provider)
    if not cfg:
        logger.warning("⚠️   شركة غير معروفة: %s", provider)
        raise HTTPException(status_code=404, detail=f"المزود '{provider}' غير مدعوم.")

    user_id_raw = params.get(cfg.param_user)
    amount_raw  = params.get(cfg.param_amount)
    tx_id       = params.get(cfg.param_tx_id)
    offer_id    = params.get(cfg.param_offer, "")

    if not all([user_id_raw, amount_raw, tx_id]):
        missing = [k for k, v in {cfg.param_user: user_id_raw,
                                   cfg.param_amount: amount_raw,
                                   cfg.param_tx_id: tx_id}.items() if not v]
        logger.warning("❌  حقول مفقودة: %s", missing)
        raise HTTPException(status_code=400, detail=f"حقول مفقودة: {missing}")

    try:
        user_id = int(user_id_raw)
        amount  = round(float(amount_raw) / cfg.amount_divisor, 4)
    except ValueError:
        raise HTTPException(status_code=400, detail="قيم غير صالحة.")

    if not verify_request(provider, cfg, params):
        logger.warning("🚫  توقيع مرفوض | provider=%s tx_id=%s", provider, tx_id)
        raise HTTPException(status_code=403, detail="توقيع غير صالح.")

    full_tx_id = f"{provider}:{tx_id}"
    if already_processed(full_tx_id):
        return PlainTextResponse("1")

    existing = db.query(Transaction).filter(Transaction.tx_id == full_tx_id).first()
    if existing:
        return PlainTextResponse("1")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning("❌  مستخدم غير موجود | user_id=%s", user_id)
        raise HTTPException(status_code=404, detail=f"المستخدم {user_id} غير موجود.")

    old_balance  = user.balance
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

    logger.info("💰  مكافأة | user='%s'(id=%s) | شركة=%s | +%.4f %s | %.4f→%.4f | tx=%s",
                user.username, user_id, cfg.name,
                amount, cfg.currency, old_balance, user.balance, full_tx_id)

    return PlainTextResponse("1")


# ═════════════════════════════════════════════
#  Endpoints عامة
# ═════════════════════════════════════════════

@app.get("/users/{user_id}", summary="بيانات مستخدم", tags=["Users"])
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود.")
    return {"id": user.id, "username": user.username, "balance": user.balance,
            "created_at": user.created_at.isoformat()}


@app.get("/providers", summary="قائمة الشركات", tags=["Info"])
async def list_providers():
    return [{"key": k, "name": v.name, "currency": v.currency}
            for k, v in PROVIDERS.items()]


@app.get("/health", summary="فحص حالة الخادم", tags=["Info"])
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ─────────────────────────────────────────────
#  تشغيل محلي
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
