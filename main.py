"""
main.py — Rewards Hub FastAPI Backend v3
يدعم: AdGem + BitLabs + CPX Research
"""

import hashlib
import json
import logging
import os
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

import database as db
from security import verify_signature, build_signature

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

# ── CPX Research ──────────────────────────────────────
CPX_APP_ID      = "33109"
CPX_SECURE_HASH = os.getenv("CPX_SECURE_HASH", "S5BVhx4aOGlnHQb06cvkhI09VN2K3ASY")
CPX_IPS         = {"188.40.3.73", "157.90.97.92", "2a01:4f8:d0a:30ff::2"}

def verify_cpx_hash(trans_id: str, received: str) -> bool:
    """CPX يستخدم: md5(trans_id-secure_hash)"""
    expected = hashlib.md5(f"{trans_id}-{CPX_SECURE_HASH}".encode()).hexdigest()
    return expected == received.lower()

# ─────────────────────────────────────────────────────
app = FastAPI(title="Rewards Hub API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DBConn = Annotated[object, Depends(db.get_db)]


@app.on_event("startup")
def startup():
    db.init_db()
    logger.info("✅  DB ready")


# ════════════════════════════════════════════════════
#  Health
# ════════════════════════════════════════════════════
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "Rewards Hub API v3"}


# ════════════════════════════════════════════════════
#  USERS
# ════════════════════════════════════════════════════
class UserCreate(BaseModel):
    username: Optional[str] = None
    email:    Optional[str] = None
    name:     Optional[str] = None
    balance:  float = 0.0


def _fmt(row) -> dict:
    if row is None:
        return None
    d = dict(row)
    if not d.get("username") and d.get("email"):
        d["username"] = d["email"]
    return d


@app.get("/users", tags=["Users"])
def list_users(conn: DBConn, username: Optional[str] = Query(None)):
    if username:
        row = db.get_user_by_username(conn, username)
        if row:
            return [_fmt(row)]
        row = db.get_user_by_email(conn, username)
        if row:
            return [_fmt(row)]
        return []
    return [_fmt(r) for r in db.get_all_users(conn)]


@app.post("/users", tags=["Users"], status_code=201)
def create_user(body: UserCreate, conn: DBConn):
    username = body.username or body.email or body.name
    email    = body.email if body.email and "@" in body.email else None
    if not username:
        raise HTTPException(400, "يجب إرسال username أو email")
    existing = db.get_user_by_username(conn, username)
    if not existing and email:
        existing = db.get_user_by_email(conn, email)
    if existing:
        raise HTTPException(409, "المستخدم موجود بالفعل")
    new_id = db.create_user(conn, username=username, email=email,
                            name=body.name, balance=body.balance)
    return _fmt(db.get_user_by_id(conn, new_id))


@app.get("/users/by_username/{username}", tags=["Users"])
def get_by_username(username: str, conn: DBConn):
    row = db.get_user_by_username(conn, username)
    if not row:
        raise HTTPException(404, "المستخدم غير موجود")
    return _fmt(row)


@app.get("/users/by_email/{email:path}", tags=["Users"])
def get_by_email(email: str, conn: DBConn):
    row = db.get_user_by_email(conn, email)
    if not row:
        raise HTTPException(404, "المستخدم غير موجود")
    return _fmt(row)


@app.get("/users/{user_id}", tags=["Users"])
def get_user(user_id: int, conn: DBConn):
    row = db.get_user_by_id(conn, user_id)
    if not row:
        raise HTTPException(404, "المستخدم غير موجود")
    return _fmt(row)


@app.get("/users/{user_id}/transactions", tags=["Users"])
def user_transactions(user_id: int, conn: DBConn):
    if not db.get_user_by_id(conn, user_id):
        raise HTTPException(404, "المستخدم غير موجود")
    return [dict(r) for r in db.get_user_transactions(conn, user_id)]


# ════════════════════════════════════════════════════
#  POSTBACK — AdGem / BitLabs
# ════════════════════════════════════════════════════
@app.get("/postback", response_class=PlainTextResponse, tags=["Postback"])
async def postback(
    request: Request, conn: DBConn,
    user_id:        int   = Query(...),
    offer_id:       str   = Query(...),
    transaction_id: str   = Query(...),
    amount:         float = Query(..., gt=0),
    currency:       str   = Query("USD"),
    sig:            str   = Query(...),
):
    client_ip  = request.client.host
    raw_params = json.dumps(dict(request.query_params))
    logger.info("📩 Postback AdGem | user=%s tx=%s amount=%s", user_id, transaction_id, amount)

    params = {"user_id": str(user_id), "offer_id": offer_id,
              "transaction_id": transaction_id,
              "amount": str(amount), "currency": currency}
    if not verify_signature(params, sig):
        logger.warning("🔴 Invalid sig | tx=%s", transaction_id)
        db._log(conn, transaction_id, user_id, offer_id, amount,
                currency, "invalid_sig", raw_params, client_ip)
        return PlainTextResponse("invalid_sig", status_code=200)

    if db.is_duplicate(conn, transaction_id):
        return PlainTextResponse("1", status_code=200)

    result = db.credit_offer_reward(
        conn=conn, user_id=user_id, amount=amount,
        offer_id=offer_id, external_tx_id=transaction_id,
        currency=currency, raw_params=raw_params, ip_address=client_ip,
    )
    if result["status"] == "user_not_found":
        return PlainTextResponse("user_not_found", status_code=200)

    logger.info("✅ Credited %.4f → user %s", amount, user_id)
    return PlainTextResponse("1", status_code=200)


# ════════════════════════════════════════════════════
#  POSTBACK — CPX Research
# ════════════════════════════════════════════════════
@app.get("/postback/cpx", response_class=PlainTextResponse, tags=["Postback"])
async def postback_cpx(
    request: Request, conn: DBConn,
    user_id:      int   = Query(...,  alias="user_id"),
    trans_id:     str   = Query(...),
    amount_usd:   float = Query(...,  gt=0),
    offer_id:     str   = Query("CPX", alias="offer_id"),
    status:       int   = Query(1),
    secure_hash:  str   = Query(""),
    amount_local: float = Query(0.0),
    currency:     str   = Query("USD"),
):
    """
    Postback خاص بـ CPX Research
    URL: /postback/cpx?user_id={user_id}&trans_id={trans_id}&amount_usd={amount_usd}&...&sig={secure_hash}
    التحقق: md5(trans_id-CPX_SECURE_HASH)
    """
    client_ip  = request.client.host
    raw_params = json.dumps(dict(request.query_params))

    logger.info("📩 CPX Postback | user=%s tx=%s amount=%.4f status=%s",
                user_id, trans_id, amount_usd, status)

    # ── 1. قبول فقط إذا status=1 (completed) ────────────
    if status != 1:
        logger.info("⏭ CPX status=%s — skipping (not completed)", status)
        return PlainTextResponse("1", status_code=200)

    # ── 2. التحقق من التوقيع ─────────────────────────────
    if secure_hash and not verify_cpx_hash(trans_id, secure_hash):
        logger.warning("🔴 CPX invalid hash | tx=%s", trans_id)
        db._log(conn, f"CPX_{trans_id}", user_id, offer_id, amount_usd,
                currency, "invalid_sig", raw_params, client_ip)
        return PlainTextResponse("1", status_code=200)

    # ── 3. فحص التكرار ───────────────────────────────────
    ext_id = f"CPX_{trans_id}"
    if db.is_duplicate(conn, ext_id):
        logger.info("🟡 CPX duplicate | tx=%s", trans_id)
        return PlainTextResponse("1", status_code=200)

    # ── 4. إضافة الرصيد ──────────────────────────────────
    result = db.credit_offer_reward(
        conn=conn, user_id=user_id, amount=amount_usd,
        offer_id=f"CPX_{offer_id}", external_tx_id=ext_id,
        currency="USD", raw_params=raw_params, ip_address=client_ip,
    )
    if result["status"] == "user_not_found":
        logger.warning("🔴 CPX user not found | user_id=%s", user_id)
        return PlainTextResponse("1", status_code=200)

    logger.info("✅ CPX Credited %.4f → user %s | bal=%.4f",
                amount_usd, user_id, result["new_balance"])
    return PlainTextResponse("1", status_code=200)


# ════════════════════════════════════════════════════
#  LOGS & TOOLS
# ════════════════════════════════════════════════════
@app.get("/postback/logs", tags=["Postback"])
def postback_logs(conn: DBConn, limit: int = Query(50, le=200)):
    return [dict(r) for r in db.get_postback_logs(conn, limit)]


@app.get("/postback/test-url", tags=["Postback"])
def test_url(
    request: Request,
    user_id: int = Query(1), offer_id: str = Query("OFFER_TEST_001"),
    transaction_id: str = Query("TX_DEMO_001"),
    amount: float = Query(5.0), currency: str = Query("USD"),
):
    params = {"user_id": str(user_id), "offer_id": offer_id,
              "transaction_id": transaction_id,
              "amount": str(amount), "currency": currency}
    sig  = build_signature(params)
    base = str(request.base_url).rstrip("/")
    qs   = "&".join(f"{k}={v}" for k, v in params.items())
    return {"test_url": f"{base}/postback?{qs}&sig={sig}",
            "params": {**params, "sig": sig}}
