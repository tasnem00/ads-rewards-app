"""
app.py  —  Rewards Hub  |  Streamlit Frontend  v6
──────────────────────────────────────────────────
• تسجيل دخول / إنشاء حساب
• الجلسة تُحفظ في st.session_state  →  لا تختفي عند الـ refresh
• Token يُرسَل مع كل طلب للـ Backend
• الزر الذهبي يظهر دائماً بعد تسجيل الدخول
"""

import hashlib
import logging
import logging.handlers
import os
import time

import requests
import streamlit as st
import streamlit.components.v1 as components

# ─────────────────────────────────────────────
#  Logging  (ملف يومي + console)
# ─────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
_fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s",
                         datefmt="%Y-%m-%d %H:%M:%S")
_fh  = logging.handlers.TimedRotatingFileHandler(
    "logs/frontend.log", when="midnight", backupCount=30, encoding="utf-8")
_fh.setFormatter(_fmt)
_ch  = logging.StreamHandler()
_ch.setFormatter(_fmt)
logging.basicConfig(level=logging.INFO, handlers=[_fh, _ch])
logger = logging.getLogger("frontend")

# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────
RAILWAY_URL   = "https://web-production-864fec.up.railway.app"
BITLABS_TOKEN = "DCDEC791-3E5B-484D-B11C-3404631079D0"
ADGEM_APP_ID  = "32570"
CPX_APP_ID    = "33109"
CPX_SECURE    = "S5BVhx4aOGlnHQb06cvkhI09VN2K3ASY"

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def _auth_headers(token: str) -> dict:
    return {**HEADERS, "Authorization": f"Bearer {token}"}


# ── رابط جدران العروض ──────────────────────

def bl_url(uid):
    return f"https://web.bitlabs.ai/?token={BITLABS_TOKEN}&uid={uid}"

def ag_url(uid):
    return f"https://adunits.adgem.com/wall?appid={ADGEM_APP_ID}&player_id={uid}"

def cpx_url(uid):
    h = hashlib.md5(f"{uid}-{CPX_SECURE}".encode()).hexdigest()
    return (f"https://offers.cpx-research.com/index.php"
            f"?app_id={CPX_APP_ID}&ext_user_id={uid}&secure_hash={h}")


# ─────────────────────────────────────────────
#  API helpers
# ─────────────────────────────────────────────

def api_register(username: str, email: str, password: str) -> tuple[dict | None, str]:
    try:
        r = requests.post(f"{RAILWAY_URL}/auth/register",
                          json={"username": username, "email": email, "password": password},
                          headers=HEADERS, timeout=10)
        if r.status_code == 201:
            logger.info("✅ تسجيل ناجح | username=%s", username)
            return r.json(), ""
        err = r.json().get("detail", "خطأ غير معروف")
        logger.warning("❌ فشل التسجيل | %s", err)
        return None, err
    except Exception as e:
        logger.error("❌ API register error: %s", e)
        return None, "تعذّر الاتصال بالخادم."


def api_login(identifier: str, password: str) -> tuple[dict | None, str]:
    try:
        r = requests.post(f"{RAILWAY_URL}/auth/login",
                          json={"identifier": identifier, "password": password},
                          headers=HEADERS, timeout=10)
        if r.status_code == 200:
            logger.info("✅ دخول ناجح | identifier=%s", identifier)
            return r.json(), ""
        err = r.json().get("detail", "خطأ غير معروف")
        logger.warning("❌ فشل الدخول | %s", err)
        return None, err
    except Exception as e:
        logger.error("❌ API login error: %s", e)
        return None, "تعذّر الاتصال بالخادم."


def api_me(token: str) -> dict | None:
    try:
        r = requests.get(f"{RAILWAY_URL}/auth/me",
                         headers=_auth_headers(token), timeout=10)
        if r.status_code == 200:
            data = r.json()
            logger.info("📊 /me | user_id=%s | balance=%.4f",
                        data.get("user_id"), data.get("balance", 0))
            return data
        logger.warning("⚠️ /me أعاد %s", r.status_code)
    except Exception as e:
        logger.error("❌ API me error: %s", e)
    return None


# ─────────────────────────────────────────────
#  إعداد الصفحة
# ─────────────────────────────────────────────
st.set_page_config(page_title="Rewards Hub", page_icon="💎", layout="centered")

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --bg:#0a0a0f; --surface:#13131a; --card:#1a1a25; --border:#2a2a3d;
    --gold:#f0c040; --gold2:#e8a020; --text:#e8e8f0; --muted:#7070a0;
    --green:#30d080; --red:#ff6060; --radius:16px;
}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important;font-family:'DM Sans',sans-serif;color:var(--text);}
[data-testid="stHeader"]{background:transparent!important;}
#MainMenu,footer,[data-testid="stToolbar"]{display:none!important;}

/* header */
.rh-logo{font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;
    background:linear-gradient(135deg,var(--gold),var(--gold2));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;text-align:center;margin-bottom:.2rem;}
.rh-sub{text-align:center;font-size:.85rem;color:var(--muted);margin-bottom:1.5rem;}

/* بطاقة */
.balance-card{background:linear-gradient(135deg,#1e1e30,#16162a);
    border:1px solid var(--border);border-radius:var(--radius);
    padding:1.6rem 2rem;margin:.8rem 0;text-align:center;position:relative;overflow:hidden;}
.balance-card::before{content:'';position:absolute;top:-40px;right:-40px;
    width:150px;height:150px;
    background:radial-gradient(circle,rgba(240,192,64,.12),transparent 70%);pointer-events:none;}
.balance-label{font-size:.7rem;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-bottom:.3rem;}
.balance-value{font-family:'Syne',sans-serif;font-size:2.8rem;font-weight:800;color:var(--gold);line-height:1;}
.balance-currency{font-size:.95rem;color:var(--muted);margin-top:.25rem;}
.username-tag{display:inline-block;background:rgba(240,192,64,.1);
    border:1px solid rgba(240,192,64,.25);color:var(--gold);
    font-size:.75rem;letter-spacing:1px;padding:.2rem .7rem;border-radius:99px;margin-bottom:.8rem;}

/* تبويبات Auth */
.auth-box{background:var(--card);border:1px solid var(--border);
    border-radius:var(--radius);padding:1.8rem;margin-top:.5rem;}
.auth-title{font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:700;
    color:var(--text);margin-bottom:1.2rem;text-align:center;}

/* alerts */
.rh-alert{border-radius:10px;padding:.75rem 1rem;font-size:.83rem;margin:.4rem 0;}
.rh-alert.error  {background:rgba(255,96,96,.1);border:1px solid rgba(255,96,96,.25);color:var(--red);}
.rh-alert.success{background:rgba(48,208,128,.1);border:1px solid rgba(48,208,128,.25);color:var(--green);}
.rh-alert.warn   {background:rgba(240,192,64,.08);border:1px solid rgba(240,192,64,.2);color:var(--gold);}

/* divider */
.rh-divider{border:none;border-top:1px solid var(--border);margin:1.2rem 0;}

/* سجل العمليات */
.tx-row{display:flex;justify-content:space-between;align-items:center;
    background:var(--card);border:1px solid var(--border);border-radius:10px;
    padding:.6rem 1rem;margin-bottom:.4rem;font-size:.82rem;}
.tx-provider{color:var(--muted);font-size:.75rem;}
.tx-amount{font-family:'Syne',sans-serif;font-weight:700;color:var(--green);}

/* input override */
[data-testid="stTextInput"] input{
    background:var(--card)!important;border:1px solid var(--border)!important;
    border-radius:10px!important;color:var(--text)!important;}
[data-testid="stTextInput"] label{color:var(--muted)!important;font-size:.78rem!important;
    letter-spacing:1px!important;text-transform:uppercase!important;}

/* button override */
[data-testid="stButton"] button{
    background:var(--card)!important;border:1px solid var(--border)!important;
    border-radius:10px!important;color:var(--text)!important;transition:border-color .2s!important;}
[data-testid="stButton"] button:hover{border-color:var(--gold)!important;color:var(--gold)!important;}
[data-testid="stButton"] button[kind="primary"]{
    background:linear-gradient(135deg,var(--gold),var(--gold2))!important;
    color:#0a0a0f!important;border:none!important;font-weight:700!important;}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Session State  (يبقى بعد الـ refresh)
# ─────────────────────────────────────────────
for k, v in {
    "token":       None,
    "user":        None,
    "auth_tab":    "login",    # login | register
    "auth_error":  "",
    "auth_ok":     "",
    "last_refresh": 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
#  Header
# ─────────────────────────────────────────────
st.markdown('<div class="rh-logo">💎 Rewards Hub</div>', unsafe_allow_html=True)
st.markdown('<div class="rh-sub">أكمل العروض واربح مكافآت حقيقية</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  صفحة Auth  (لم يسجّل دخول بعد)
# ══════════════════════════════════════════════
if not st.session_state.token:

    tab_login, tab_reg = st.tabs(["🔑  تسجيل الدخول", "✨  حساب جديد"])

    # ── تسجيل الدخول ──────────────────────────
    with tab_login:
        st.markdown('<div class="auth-title">أهلاً بعودتك 👋</div>',
                    unsafe_allow_html=True)

        identifier = st.text_input("البريد الإلكتروني أو اسم المستخدم",
                                   placeholder="you@example.com",
                                   key="li_id")
        password   = st.text_input("كلمة المرور", type="password",
                                   placeholder="••••••••", key="li_pw")

        if st.session_state.auth_error:
            st.markdown(f'<div class="rh-alert error">⚠️ {st.session_state.auth_error}</div>',
                        unsafe_allow_html=True)
        if st.session_state.auth_ok:
            st.markdown(f'<div class="rh-alert success">✅ {st.session_state.auth_ok}</div>',
                        unsafe_allow_html=True)

        if st.button("تسجيل الدخول", use_container_width=True,
                     type="primary", key="btn_login"):
            if not identifier or not password:
                st.session_state.auth_error = "يرجى ملء جميع الحقول."
            else:
                logger.info("🖱️ محاولة دخول | identifier=%s", identifier)
                with st.spinner("جارٍ التحقق…"):
                    data, err = api_login(identifier, password)
                if data:
                    st.session_state.token      = data["token"]
                    st.session_state.user       = data
                    st.session_state.auth_error = ""
                    st.session_state.auth_ok    = ""
                    logger.info("✅ دخول ناجح في الواجهة | user_id=%s", data["user_id"])
                    st.rerun()
                else:
                    st.session_state.auth_error = err
                    st.rerun()

    # ── إنشاء حساب جديد ───────────────────────
    with tab_reg:
        st.markdown('<div class="auth-title">إنشاء حساب جديد 🚀</div>',
                    unsafe_allow_html=True)

        r_username = st.text_input("اسم المستخدم", placeholder="ahmed_123", key="rg_user")
        r_email    = st.text_input("البريد الإلكتروني", placeholder="you@example.com", key="rg_email")
        r_pw       = st.text_input("كلمة المرور (6 أحرف على الأقل)",
                                   type="password", placeholder="••••••••", key="rg_pw")
        r_pw2      = st.text_input("تأكيد كلمة المرور",
                                   type="password", placeholder="••••••••", key="rg_pw2")

        if st.session_state.auth_error:
            st.markdown(f'<div class="rh-alert error">⚠️ {st.session_state.auth_error}</div>',
                        unsafe_allow_html=True)
        if st.session_state.auth_ok:
            st.markdown(f'<div class="rh-alert success">✅ {st.session_state.auth_ok}</div>',
                        unsafe_allow_html=True)

        if st.button("إنشاء الحساب", use_container_width=True,
                     type="primary", key="btn_reg"):
            if not all([r_username, r_email, r_pw, r_pw2]):
                st.session_state.auth_error = "يرجى ملء جميع الحقول."
            elif r_pw != r_pw2:
                st.session_state.auth_error = "كلمتا المرور غير متطابقتين."
            else:
                logger.info("🖱️ محاولة تسجيل | username=%s email=%s", r_username, r_email)
                with st.spinner("جارٍ إنشاء حسابك…"):
                    data, err = api_register(r_username, r_email, r_pw)
                if data:
                    st.session_state.token      = data["token"]
                    st.session_state.user       = data
                    st.session_state.auth_error = ""
                    st.session_state.auth_ok    = ""
                    logger.info("🎉 حساب جديد في الواجهة | user_id=%s", data["user_id"])
                    st.rerun()
                else:
                    st.session_state.auth_error = err
                    st.rerun()

    st.stop()   # لا تُكمل تحميل بقية الصفحة


# ══════════════════════════════════════════════
#  الصفحة الرئيسية  (بعد تسجيل الدخول)
# ══════════════════════════════════════════════

user = st.session_state.user or {}
uid  = user.get("user_id", 1)

# ── شريط علوي: اسم المستخدم + زر خروج ────────
col_name, col_out = st.columns([4, 1])
with col_name:
    st.markdown(f'<div class="username-tag">👤 {user.get("username","")}</div>',
                unsafe_allow_html=True)
with col_out:
    if st.button("خروج", key="btn_logout"):
        logger.info("🚪 خروج | user_id=%s", uid)
        for k in ["token", "user", "auth_error", "auth_ok", "last_refresh"]:
            st.session_state[k] = None if k in ("token","user") else ""
        st.session_state.last_refresh = 0
        st.rerun()

# ── بطاقة الرصيد ──────────────────────────────
balance = user.get("balance", 0.0)
st.markdown(f"""
<div class="balance-card">
    <div class="balance-label">رصيدك الحالي</div>
    <div class="balance-value">{balance:,.4f}</div>
    <div class="balance-currency">USD</div>
</div>
""", unsafe_allow_html=True)

# ── زر تحديث الرصيد ───────────────────────────
if st.button("↻  تحديث الرصيد", use_container_width=True):
    with st.spinner("جارٍ جلب البيانات…"):
        fresh = api_me(st.session_state.token)
    if fresh:
        st.session_state.user         = {**user, **fresh, "user_id": fresh["user_id"]}
        st.session_state.last_refresh = time.time()
        logger.info("🔄 رصيد محدَّث | user_id=%s | balance=%.4f",
                    uid, fresh.get("balance", 0))
        st.rerun()
    else:
        st.markdown('<div class="rh-alert error">⚠️ تعذّر تحديث الرصيد.</div>',
                    unsafe_allow_html=True)

st.markdown('<hr class="rh-divider">', unsafe_allow_html=True)

# ── جدران العروض ──────────────────────────────
st.markdown("#### 🎯 جدران العروض", unsafe_allow_html=False)

WALLS = [
    ("BitLabs",  bl_url(uid),  "#4a6cf7", "استبيانات بمكافآت عالية"),
    ("AdGem",    ag_url(uid),  "#f7a94a", "عروض متنوعة وسريعة"),
    ("CPX",      cpx_url(uid), "#4af7a9", "استبيانات CPX Research"),
]

for name, url, color, desc in WALLS:
    logger.info("🔗 توليد رابط %s | uid=%s", name, uid)
    components.html(f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap" rel="stylesheet">
    <style>
    *{{margin:0;padding:0;box-sizing:border-box;}}
    body{{background:transparent;padding:0 0 8px;}}
    .btn{{display:flex;align-items:center;gap:12px;padding:14px 20px;
        background:linear-gradient(135deg,{color}22,{color}11);
        border:1.5px solid {color}55;border-radius:14px;
        text-decoration:none;cursor:pointer;transition:all .2s;}}
    .btn:hover{{background:linear-gradient(135deg,{color}44,{color}22);
        border-color:{color};transform:translateY(-1px);
        box-shadow:0 4px 20px {color}33;}}
    .dot{{width:10px;height:10px;border-radius:50%;background:{color};
        box-shadow:0 0 8px {color};flex-shrink:0;}}
    .name{{font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;color:#e8e8f0;}}
    .desc{{font-size:.75rem;color:#7070a0;margin-top:2px;}}
    .arrow{{margin-left:auto;color:{color};font-size:1.1rem;}}
    </style></head><body>
    <a class="btn" href="{url}" target="_blank" rel="noopener noreferrer"
       onclick="window.open('{url}','_blank','noopener,noreferrer');return false;">
        <div class="dot"></div>
        <div><div class="name">{name}</div><div class="desc">{desc}</div></div>
        <div class="arrow">↗</div>
    </a>
    </body></html>
    """, height=68)

st.markdown('<hr class="rh-divider">', unsafe_allow_html=True)

# ── سجل العمليات ──────────────────────────────
txns = user.get("transactions", [])
st.markdown(f"#### 📋 سجل العمليات  <span style='color:var(--muted);font-size:.8rem'>({len(txns)} عملية)</span>",
            unsafe_allow_html=True)

if not txns:
    st.markdown('<div class="rh-alert warn">لا توجد عمليات بعد — أكمل عرضاً لترى مكافأتك هنا!</div>',
                unsafe_allow_html=True)
else:
    for t in sorted(txns, key=lambda x: x["created_at"], reverse=True)[:20]:
        date = t["created_at"][:10]
        st.markdown(f"""
        <div class="tx-row">
            <div>
                <div style="color:var(--text);font-weight:500">{t.get("offer_id") or "—"}</div>
                <div class="tx-provider">{t["provider"].upper()} · {date}</div>
            </div>
            <div class="tx-amount">+{t["amount"]:.4f} {t["currency"]}</div>
        </div>
        """, unsafe_allow_html=True)
