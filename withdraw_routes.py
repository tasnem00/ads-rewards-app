"""
withdraw_routes.py
──────────────────
نظام السحب الكامل:
  POST /withdraw/request   — المستخدم يطلب سحب
  GET  /withdraw/my        — المستخدم يرى طلباته
  GET  /withdraw/admin/all — المسؤولة ترى كل الطلبات
  POST /withdraw/admin/{id}/approve — موافقة
  POST /withdraw/admin/{id}/reject  — رفض
  POST /withdraw/admin/{id}/paid    — تحديد كـ"تم الدفع"

أضيفي في main.py بعد app = FastAPI(...):
    from withdraw_routes import router as withdraw_router
    app.include_router(withdraw_router)
"""

import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import decode_token
from database import User, WithdrawRequest, get_db

logger  = logging.getLogger(__name__)
router  = APIRouter()
bearer  = HTTPBearer()

# ── كلمة سر لوحة الأدمن — غيّريها في Railway Variables ──
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "admin_super_secret_2024")

# ── إعدادات السحب ──
MIN_WITHDRAW = 1.0   # الحد الأدنى بالـ USD

VALID_METHODS = {
    "paypal":        "PayPal",
    "crypto_usdt":   "Crypto USDT",
    "vodafone_cash": "Vodafone Cash",
    "bank_transfer": "تحويل بنكي",
    "gift_cards":    "بطاقات هدايا",
}

ADDRESS_HINTS = {
    "paypal":        "البريد الإلكتروني لـ PayPal",
    "crypto_usdt":   "عنوان المحفظة TRC20/ERC20",
    "vodafone_cash": "رقم الهاتف",
    "bank_transfer": "رقم IBAN أو الحساب البنكي",
    "gift_cards":    "البريد الإلكتروني لاستلام الكود",
}


# ══════════════════════════════════════════════
#  Auth helpers
# ══════════════════════════════════════════════
def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(401, "توكن غير صالح أو منتهي.")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(401, "المستخدم غير موجود أو موقوف.")
    return user


def verify_admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    """تحقق بسيط للأدمن عبر كلمة سر ثابتة في الهيدر."""
    if creds.credentials != ADMIN_SECRET:
        raise HTTPException(403, "غير مصرح — كلمة سر الأدمن خاطئة.")


# ══════════════════════════════════════════════
#  Schemas
# ══════════════════════════════════════════════
class WithdrawRequestSchema(BaseModel):
    method:  str
    address: str
    amount:  float

class AdminNoteSchema(BaseModel):
    note: Optional[str] = ""


# ══════════════════════════════════════════════
#  دالة مساعدة — تحويل الطلب لـ dict
# ══════════════════════════════════════════════
def _wr_to_dict(wr: WithdrawRequest, include_user: bool = False) -> dict:
    d = {
        "id":         wr.id,
        "method":     wr.method,
        "method_ar":  VALID_METHODS.get(wr.method, wr.method),
        "address":    wr.address,
        "amount":     round(wr.amount, 4),
        "status":     wr.status,
        "admin_note": wr.admin_note or "",
        "created_at": wr.created_at.isoformat() if wr.created_at else "",
        "updated_at": wr.updated_at.isoformat() if wr.updated_at else "",
    }
    if include_user and wr.user:
        d["username"] = wr.user.username
        d["email"]    = wr.user.email
        d["user_id"]  = wr.user_id
    return d


# ══════════════════════════════════════════════
#  [مستخدم] طلب سحب جديد
#  POST /withdraw/request
# ══════════════════════════════════════════════
@router.post("/withdraw/request")
def create_withdraw_request(
    req:  WithdrawRequestSchema,
    user: User    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    # ─ تحقق من الوسيلة ─
    if req.method not in VALID_METHODS:
        raise HTTPException(400, f"وسيلة سحب غير صالحة. الخيارات: {list(VALID_METHODS.keys())}")

    # ─ تحقق من المبلغ ─
    if req.amount < MIN_WITHDRAW:
        raise HTTPException(400, f"الحد الأدنى للسحب هو ${MIN_WITHDRAW:.2f}.")

    if req.amount > user.balance:
        raise HTTPException(400, f"الرصيد غير كافٍ. رصيدك: ${user.balance:.4f}")

    if not req.address.strip():
        raise HTTPException(400, f"يرجى إدخال {ADDRESS_HINTS.get(req.method, 'عنوان الاستلام')}.")

    # ─ التحقق من عدم وجود طلب معلق ─
    pending = db.query(WithdrawRequest).filter(
        WithdrawRequest.user_id == user.id,
        WithdrawRequest.status  == "pending"
    ).first()
    if pending:
        raise HTTPException(400, "لديك طلب سحب معلق بالفعل، انتظري معالجته أولاً.")

    # ─ خصم الرصيد وإنشاء الطلب ─
    user.balance -= req.amount
    wr = WithdrawRequest(
        user_id = user.id,
        method  = req.method,
        address = req.address.strip(),
        amount  = req.amount,
        status  = "pending",
    )
    db.add(wr)
    db.commit()
    db.refresh(wr)

    logger.info("💸 طلب سحب جديد | user=%s | method=%s | amount=%.4f USD | wr_id=%s",
                user.username, req.method, req.amount, wr.id)

    return {
        "status":  "ok",
        "message": "تم إرسال طلب السحب بنجاح! سيتم المعالجة خلال 24-48 ساعة.",
        "request": _wr_to_dict(wr),
        "new_balance": round(user.balance, 4),
    }


# ══════════════════════════════════════════════
#  [مستخدم] عرض طلباته
#  GET /withdraw/my
# ══════════════════════════════════════════════
@router.get("/withdraw/my")
def my_withdraw_requests(
    user: User    = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    requests = (
        db.query(WithdrawRequest)
        .filter(WithdrawRequest.user_id == user.id)
        .order_by(WithdrawRequest.created_at.desc())
        .all()
    )
    return {
        "balance":  round(user.balance, 4),
        "requests": [_wr_to_dict(r) for r in requests],
    }


# ══════════════════════════════════════════════
#  [أدمن] عرض كل الطلبات
#  GET /withdraw/admin/all?status=pending
# ══════════════════════════════════════════════
@router.get("/withdraw/admin/all")
def admin_all_requests(
    status: Optional[str] = None,   # pending / approved / rejected / paid
    _: HTTPAuthorizationCredentials = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    q = db.query(WithdrawRequest).order_by(WithdrawRequest.created_at.desc())
    if status:
        q = q.filter(WithdrawRequest.status == status)
    requests = q.all()

    # إحصائيات
    all_requests = db.query(WithdrawRequest).all()
    stats = {
        "total":    len(all_requests),
        "pending":  sum(1 for r in all_requests if r.status == "pending"),
        "approved": sum(1 for r in all_requests if r.status == "approved"),
        "paid":     sum(1 for r in all_requests if r.status == "paid"),
        "rejected": sum(1 for r in all_requests if r.status == "rejected"),
        "total_paid_usd": round(sum(r.amount for r in all_requests if r.status == "paid"), 4),
    }

    return {
        "stats":    stats,
        "requests": [_wr_to_dict(r, include_user=True) for r in requests],
    }


# ══════════════════════════════════════════════
#  [أدمن] موافقة على طلب
#  POST /withdraw/admin/{id}/approve
# ══════════════════════════════════════════════
@router.post("/withdraw/admin/{wr_id}/approve")
def admin_approve(
    wr_id: int,
    body:  AdminNoteSchema,
    _:     HTTPAuthorizationCredentials = Depends(verify_admin),
    db:    Session = Depends(get_db),
):
    wr = db.query(WithdrawRequest).filter(WithdrawRequest.id == wr_id).first()
    if not wr:
        raise HTTPException(404, "الطلب غير موجود.")
    if wr.status != "pending":
        raise HTTPException(400, f"الطلب ليس في حالة معلقة (الحالة الحالية: {wr.status}).")

    wr.status     = "approved"
    wr.admin_note = body.note or "تمت الموافقة"
    wr.updated_at = datetime.utcnow()
    db.commit()

    logger.info("✅ أدمن وافق على طلب #%s | user_id=%s | amount=%.4f", wr.id, wr.user_id, wr.amount)
    return {"status": "ok", "message": f"تمت الموافقة على الطلب #{wr_id}.", "request": _wr_to_dict(wr, True)}


# ══════════════════════════════════════════════
#  [أدمن] رفض طلب (إعادة الرصيد للمستخدم)
#  POST /withdraw/admin/{id}/reject
# ══════════════════════════════════════════════
@router.post("/withdraw/admin/{wr_id}/reject")
def admin_reject(
    wr_id: int,
    body:  AdminNoteSchema,
    _:     HTTPAuthorizationCredentials = Depends(verify_admin),
    db:    Session = Depends(get_db),
):
    wr = db.query(WithdrawRequest).filter(WithdrawRequest.id == wr_id).first()
    if not wr:
        raise HTTPException(404, "الطلب غير موجود.")
    if wr.status in ("paid", "rejected"):
        raise HTTPException(400, f"لا يمكن رفض طلب بحالة: {wr.status}.")

    # إعادة الرصيد للمستخدم
    user = db.query(User).filter(User.id == wr.user_id).first()
    if user:
        user.balance += wr.amount

    wr.status     = "rejected"
    wr.admin_note = body.note or "تم الرفض"
    wr.updated_at = datetime.utcnow()
    db.commit()

    logger.info("❌ أدمن رفض طلب #%s | user_id=%s | amount=%.4f أُعيد للرصيد", wr.id, wr.user_id, wr.amount)
    return {"status": "ok", "message": f"تم رفض الطلب #{wr_id} وإعادة الرصيد للمستخدم.", "request": _wr_to_dict(wr, True)}


# ══════════════════════════════════════════════
#  [أدمن] تحديد كـ"تم الدفع"
#  POST /withdraw/admin/{id}/paid
# ══════════════════════════════════════════════
@router.post("/withdraw/admin/{wr_id}/paid")
def admin_mark_paid(
    wr_id: int,
    body:  AdminNoteSchema,
    _:     HTTPAuthorizationCredentials = Depends(verify_admin),
    db:    Session = Depends(get_db),
):
    wr = db.query(WithdrawRequest).filter(WithdrawRequest.id == wr_id).first()
    if not wr:
        raise HTTPException(404, "الطلب غير موجود.")
    if wr.status == "rejected":
        raise HTTPException(400, "لا يمكن تحديد طلب مرفوض كمدفوع.")

    wr.status     = "paid"
    wr.admin_note = body.note or "تم الدفع"
    wr.updated_at = datetime.utcnow()
    db.commit()

    logger.info("💰 أدمن حدّد طلب #%s كمدفوع | user_id=%s | amount=%.4f", wr.id, wr.user_id, wr.amount)
    return {"status": "ok", "message": f"تم تحديد الطلب #{wr_id} كمدفوع.", "request": _wr_to_dict(wr, True)}
