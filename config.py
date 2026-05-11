"""
config.py
─────────
إعدادات التطبيق والمفاتيح السرية لكل شركة عروض.

في الإنتاج: ضع هذه القيم في متغيرات البيئة على Railway:
    Settings → Variables → Add Variable
"""

import os
from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    """إعدادات شركة عروض واحدة."""
    name:         str
    secret_key:   str
    param_user:   str   # اسم الـ param الذي يحمل user_id
    param_amount: str   # اسم الـ param الذي يحمل قيمة المكافأة
    param_tx_id:  str   # اسم الـ param الذي يحمل معرّف العملية الفريد
    param_offer:  str = ""   # اسم الـ param الذي يحمل معرّف العرض (اختياري)
    currency:     str = "USD"
    # دالة تحويل القيمة: بعض الشركات ترسل النقاط وليس الدولارات
    # مثال: lambda v: v / 100  إذا كانت الشركة ترسل السنتات
    amount_divisor: float = 1.0


# ─────────────────────────────────────────────
#  تعريف الشركات  ← أضف شركة جديدة هنا فقط
# ─────────────────────────────────────────────

PROVIDERS: dict[str, ProviderConfig] = {

    "adgate": ProviderConfig(
        name          = "AdGate Media",
        secret_key    = os.getenv("ADGATE_SECRET", "adgate_secret_change_me"),
        param_user    = "user_id",
        param_amount  = "reward",
        param_tx_id   = "transaction_id",
        param_offer   = "offer_id",
        currency      = "USD",
        amount_divisor= 1.0,
    ),

    "bitlabs": ProviderConfig(
        name          = "BitLabs",
        secret_key    = os.getenv("BITLABS_SECRET", "bitlabs_secret_change_me"),
        param_user    = "uid",
        param_amount  = "reward",
        param_tx_id   = "transaction_id",
        param_offer   = "survey_id",
        currency      = "USD",
        amount_divisor= 1.0,
    ),

    "offertoro": ProviderConfig(
        name          = "OfferToro",
        secret_key    = os.getenv("OFFERTORO_SECRET", "offertoro_secret_change_me"),
        param_user    = "user_id",
        param_amount  = "amount",
        param_tx_id   = "oid",
        param_offer   = "offer_name",
        currency      = "USD",
        amount_divisor= 1.0,
    ),

    # ─── أضف شركة جديدة هنا ───────────────────
    # "myProvider": ProviderConfig(
    #     name         = "My New Provider",
    #     secret_key   = os.getenv("MYPROVIDER_SECRET", "change_me"),
    #     param_user   = "userId",
    #     param_amount = "coins",
    #     param_tx_id  = "txId",
    #     amount_divisor = 100.0,   # إذا كانت ترسل بالسنتات
    # ),
}


# ─────────────────────────────────────────────
#  إعدادات عامة
# ─────────────────────────────────────────────

APP_ENV   = os.getenv("APP_ENV", "development")   # development | production
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT      = int(os.getenv("PORT", 8000))           # Railway يضبط PORT تلقائياً
