# 🎁 Offers & Rewards API

Backend لاستقبال Postbacks من شركات العروض وتحديث أرصدة المستخدمين.

---

## هيكل المشروع

```
rewards_app/
├── main.py          # FastAPI — نقطة الدخول الرئيسية
├── database.py      # النماذج وإعداد SQLAlchemy
├── config.py        # إعدادات الشركات والمفاتيح السرية
├── security.py      # التحقق من التوقيعات
├── requirements.txt
└── logs/
    └── rewards.log  # يُنشأ تلقائياً
```

---

## الـ Endpoints

| الطريقة | الرابط | الوصف |
|---------|--------|-------|
| `GET` | `/postback/{provider}` | استقبال مكافأة من شركة عروض |
| `POST` | `/users?username=...` | إنشاء مستخدم جديد |
| `GET` | `/users/{id}` | بيانات ورصيد مستخدم |
| `GET` | `/users/{id}/transactions` | سجل عمليات مستخدم |
| `GET` | `/providers` | قائمة الشركات المدعومة |
| `GET` | `/health` | فحص حالة الخادم |

---

## روابط الـ Postback لكل شركة

بعد الرفع على Railway ستكون روابطك:

```
# AdGate
https://your-app.railway.app/postback/adgate?user_id={user_id}&reward={reward}&transaction_id={transaction_id}&offer_id={offer_id}&hash={hash}

# BitLabs
https://your-app.railway.app/postback/bitlabs?uid={uid}&reward={reward}&transaction_id={transaction_id}&survey_id={survey_id}&signature={signature}

# OfferToro
https://your-app.railway.app/postback/offertoro?user_id={user_id}&amount={amount}&oid={oid}&offer_name={offer_name}&hash={hash}
```

---

## الرفع على Railway

### 1. رفع الكود على GitHub
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/username/rewards-app.git
git push -u origin main
```

### 2. إنشاء مشروع على Railway
- اذهب إلى railway.com
- New Project → Deploy from GitHub → اختر المستودع

### 3. إضافة متغيرات البيئة
في Railway: **Settings → Variables** أضف:

```
ADGATE_SECRET      = المفتاح_الذي_أعطاك_إياه_AdGate
BITLABS_SECRET     = المفتاح_الذي_أعطاك_إياه_BitLabs
OFFERTORO_SECRET   = المفتاح_الذي_أعطاك_إياه_OfferToro
APP_ENV            = production
LOG_LEVEL          = INFO
```

> Railway يُعيّن PORT تلقائياً — لا تضيفه يدوياً.

---

## إضافة شركة جديدة

افتح `config.py` وأضف:

```python
"myprovider": ProviderConfig(
    name          = "My New Provider",
    secret_key    = os.getenv("MYPROVIDER_SECRET", "change_me"),
    param_user    = "userId",      # اسم الـ param في الرابط
    param_amount  = "coins",
    param_tx_id   = "txId",
    amount_divisor= 100.0,         # إذا كانت ترسل بالسنتات
),
```

ثم في `security.py` أضف دالة `_verify_myprovider` وسجّلها في `_VERIFIERS`.

---

## التشغيل المحلي

```bash
pip install -r requirements.txt
python main.py
# أو
uvicorn main:app --reload
```

ثم افتح: http://localhost:8000/docs
