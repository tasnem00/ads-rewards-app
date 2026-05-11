"""
security.py
───────────
التحقق من صحة الطلبات الواردة من شركات العروض.
كل شركة لها طريقة توقيع مختلفة — كلها موثّقة هنا.
"""

import hashlib
import hmac
import logging

from config import ProviderConfig

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  دوال التحقق لكل شركة
# ─────────────────────────────────────────────

def _verify_adgate(cfg: ProviderConfig, params: dict) -> bool:
    """
    AdGate: MD5(secret_key + user_id + reward + transaction_id)
    توثيق: https://adgatemedia.com/publishers/postback
    """
    payload = (
        cfg.secret_key
        + str(params.get(cfg.param_user, ""))
        + str(params.get(cfg.param_amount, ""))
        + str(params.get(cfg.param_tx_id, ""))
    )
    expected = hashlib.md5(payload.encode()).hexdigest()
    received = params.get("hash", "")
    return hmac.compare_digest(expected, received)


def _verify_bitlabs(cfg: ProviderConfig, params: dict) -> bool:
    """
    BitLabs: HMAC-SHA1(secret_key, uid:transaction_id)
    توثيق: https://support.bitlabs.io/postback
    """
    payload  = f"{params.get(cfg.param_user, '')}:{params.get(cfg.param_tx_id, '')}"
    expected = hmac.new(cfg.secret_key.encode(), payload.encode(), hashlib.sha1).hexdigest()
    received = params.get("signature", "")
    return hmac.compare_digest(expected, received)


def _verify_offertoro(cfg: ProviderConfig, params: dict) -> bool:
    """
    OfferToro: MD5(secret_key + user_id + oid)
    توثيق: https://www.offertoro.com/publishers/postback
    """
    payload = (
        cfg.secret_key
        + str(params.get(cfg.param_user, ""))
        + str(params.get(cfg.param_tx_id, ""))
    )
    expected = hashlib.md5(payload.encode()).hexdigest()
    received = params.get("hash", "")
    return hmac.compare_digest(expected, received)


def _verify_generic(cfg: ProviderConfig, params: dict) -> bool:
    """
    Fallback: HMAC-SHA256(secret_key, user_id:amount:tx_id)
    استخدمه لأي شركة جديدة حتى تعرف طريقة توقيعها الدقيقة.
    """
    payload = (
        f"{params.get(cfg.param_user, '')}:"
        f"{params.get(cfg.param_amount, '')}:"
        f"{params.get(cfg.param_tx_id, '')}"
    )
    expected = hmac.new(cfg.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    received = params.get("signature", params.get("hash", ""))
    return hmac.compare_digest(expected, received)


# ─────────────────────────────────────────────
#  Router: اختيار دالة التحقق المناسبة
# ─────────────────────────────────────────────

_VERIFIERS = {
    "adgate":    _verify_adgate,
    "bitlabs":   _verify_bitlabs,
    "offertoro": _verify_offertoro,
}


def verify_request(provider_key: str, cfg: ProviderConfig, params: dict) -> bool:
    """
    يختار دالة التحقق المناسبة للشركة ويُشغّلها.
    إذا لم تكن الشركة معرّفة يستخدم الـ generic verifier.
    """
    verifier = _VERIFIERS.get(provider_key, _verify_generic)
    result   = verifier(cfg, params)
    status   = "✅ صالح" if result else "❌ مرفوض"
    logger.info("🔐  تحقق التوقيع [%s]: %s", provider_key, status)
    return result
