"""
app.py  —  Rewards Hub  |  Streamlit Frontend  v8
──────────────────────────────────────────────────
• حفظ الجلسة في Cookies → لا تنتهي عند الـ refresh
• إصلاح مشكلة st.form + st.rerun
"""

import hashlib
import logging
import logging.handlers
import os
import time

import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_cookies_manager import EncryptedCookieManager

# ─────────────────────────────────────────────
#  Logging
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
RAILWAY_URL   = "https://harmonious-recreation-production.up.railway.app"
BITLABS_TOKEN = "DCDEC791-3E5B-484D-B11C-3404631079D0"
ADGEM_APP_ID  = "32570"
CPX_APP_ID    = "33109"
CPX_SECURE    = "S5BVhx4aOGlnHQb06cvkhI09VN2K3ASY"
COOKIE_SECRET = "RewardsHub!CookieSecret2024XYZ!!"  # 32 حرف على الأقل

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def _auth_headers(token: str) -> dict:
    return {**HEADERS, "Authorization": f"Bearer {token}"}


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

def _safe_json(r) -> dict:
    try:
        if r.text.strip():
            return r.json()
    except Exception:
        pass
    return {}


def api_register(username: str, email: str, password: str) -> tuple:
    try:
        r = requests.post(f"{RAILWAY_URL}/auth/register",
                          json={"username": username, "email": email, "password": password},
                          headers=HEADERS, timeout=15)
        if r.status_code == 201:
            data = _safe_json(r)
            if data:
                return data, ""
            return None, "استجابة غير صالحة من الخادم."
        err = _safe_json(r).get("detail", f"خطأ {r.status_code}")
        return None, err
    except requests.exceptions.Timeout:
        return None, "انتهت مهلة الاتصال، حاول مجدداً."
    except Exception as e:
        logger.error("❌ API register error: %s", e)
        return None, "تعذّر الاتصال بالخادم."


def api_login(identifier: str, password: str) -> tuple:
    try:
        r = requests.post(f"{RAILWAY_URL}/auth/login",
                          json={"identifier": identifier, "password": password},
                          headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = _safe_json(r)
            if data:
                return data, ""
            return None, "استجابة غير صالحة من الخادم."
        err = _safe_json(r).get("detail", f"خطأ {r.status_code}")
        return None, err
    except requests.exceptions.Timeout:
        return None, "انتهت مهلة الاتصال، حاول مجدداً."
    except Exception as e:
        logger.error("❌ API login error: %s", e)
        return None, "تعذّر الاتصال بالخادم."


def api_me(token: str) -> dict:
    try:
        r = requests.get(f"{RAILWAY_URL}/auth/me",
                         headers=_auth_headers(token), timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error("❌ API me error: %s", e)
    return None


# ─────────────────────────────────────────────
#  إعداد الصفحة
# ─────────────────────────────────────────────
st.set_page_config(page_title="Rewards Hub", page_icon="💎", layout="centered")

# ─────────────────────────────────────────────
#  Cookies Manager  ← يحفظ الجلسة بعد الـ refresh
# ─────────────────────────────────────────────
cookies = EncryptedCookieManager(prefix="rh_", password=COOKIE_SECRET)
if not cookies.ready():
    st.stop()

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

.rh-logo{font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;
    background:linear-gradient(135deg,var(--gold),var(--gold2));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;text-align:center;margin-bottom:.2rem;}
.rh-sub{text-align:center;font-size:.85rem;color:var(--muted);margin-bottom:1.5rem;}

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

.auth-title{font-family:'Syne',sans-serif;font-size:1.15rem;font-weight:700;
    color:var(--text);margin-bottom:1.2rem;text-align:center;}

.rh-alert{border-radius:10px;padding:.75rem 1rem;font-size:.83rem;margin:.4rem 0;}
.rh-alert.error  {background:rgba(255,96,96,.1);border:1px solid rgba(255,96,96,.25);color:var(--red);}
.rh-alert.success{background:rgba(48,208,128,.1);border:1px solid rgba(48,208,128,.25);color:var(--green);}
.rh-alert.warn   {background:rgba(240,192,64,.08);border:1px solid rgba(240,192,64,.2);color:var(--gold);}

.rh-divider{border:none;border-top:1px solid var(--border);margin:1.2rem 0;}

.tx-row{display:flex;justify-content:space-between;align-items:center;
    background:var(--card);border:1px solid var(--border);border-radius:10px;
    padding:.6rem 1rem;margin-bottom:.4rem;font-size:.82rem;}
.tx-provider{color:var(--muted);font-size:.75rem;}
.tx-amount{font-family:'Syne',sans-serif;font-weight:700;color:var(--green);}

[data-testid="stTextInput"] input{
    background:var(--card)!important;border:1px solid var(--border)!important;
    border-radius:10px!important;color:var(--text)!important;}
[data-testid="stTextInput"] label{color:var(--muted)!important;font-size:.78rem!important;
    letter-spacing:1px!important;text-transform:uppercase!important;}

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
#  Session State
# ─────────────────────────────────────────────
for k, v in {
    "token":        None,
    "user":         None,
    "auth_tab":     "login",
    "auth_error":   "",
    "last_refresh": 0,
    "_login_id":    "",
    "_login_pw":    "",
    "_reg_user":    "",
    "_reg_email":   "",
    "_reg_pw":      "",
    "_reg_pw2":     "",
    "_login_submitted": False,
    "_reg_submitted":   False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── استعادة الجلسة من Cookies عند الـ refresh ──
if not st.session_state.token:
    saved_token = cookies.get("token", "")
    saved_user  = cookies.get("user_json", "")
    if saved_token and saved_user:
        import json
        try:
            st.session_state.token = saved_token
            st.session_state.user  = json.loads(saved_user)
            logger.info("🍪 جلسة مستعادة من Cookies")
        except Exception:
            cookies["token"]     = ""
            cookies["user_json"] = ""
            cookies.save()


# ─────────────────────────────────────────────
#  Header
# ─────────────────────────────────────────────
st.markdown('<div class="rh-logo">💎 Rewards Hub</div>', unsafe_allow_html=True)
st.markdown('<div class="rh-sub">أكمل العروض واربح مكافآت حقيقية</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  صفحة Auth
# ══════════════════════════════════════════════
if not st.session_state.token:

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔑  تسجيل الدخول", use_container_width=True,
                     type="primary" if st.session_state.auth_tab == "login" else "secondary",
                     key="switch_login"):
            st.session_state.auth_tab   = "login"
            st.session_state.auth_error = ""
            st.rerun()
    with col_b:
        if st.button("✨  حساب جديد", use_container_width=True,
                     type="primary" if st.session_state.auth_tab == "register" else "secondary",
                     key="switch_reg"):
            st.session_state.auth_tab   = "register"
            st.session_state.auth_error = ""
            st.rerun()

    st.markdown('<hr class="rh-divider">', unsafe_allow_html=True)

    if st.session_state.auth_error:
        st.markdown(
            f'<div class="rh-alert error">⚠️ {st.session_state.auth_error}</div>',
            unsafe_allow_html=True)

    # ══ نموذج تسجيل الدخول ══════════════════════
    if st.session_state.auth_tab == "login":
        st.markdown('<div class="auth-title">أهلاً بعودتك 👋</div>', unsafe_allow_html=True)

        with st.form("form_login"):
            identifier = st.text_input("البريد الإلكتروني أو اسم المستخدم",
                                        placeholder="you@example.com")
            password   = st.text_input("كلمة المرور", type="password",
                                        placeholder="••••••••")
            submitted  = st.form_submit_button("تسجيل الدخول",
                                                use_container_width=True, type="primary")
            if submitted:
                st.session_state._login_id        = identifier
                st.session_state._login_pw        = password
                st.session_state._login_submitted = True

        if st.session_state._login_submitted:
            st.session_state._login_submitted = False
            _id = st.session_state._login_id.strip()
            _pw = st.session_state._login_pw

            if not _id or not _pw:
                st.session_state.auth_error = "يرجى ملء جميع الحقول."
            else:
                st.session_state.auth_error = ""
                with st.spinner("جارٍ التحقق…"):
                    data, err = api_login(_id, _pw)
                if data:
                    import json
                    st.session_state.token = data["token"]
                    st.session_state.user  = data
                    # ← حفظ في Cookies
                    cookies["token"]     = data["token"]
                    cookies["user_json"] = json.dumps(data)
                    cookies.save()
                    logger.info("✅ دخول | user_id=%s", data.get("user_id"))
                else:
                    st.session_state.auth_error = err
            st.rerun()

    # ══ نموذج إنشاء الحساب ══════════════════════
    else:
        st.markdown('<div class="auth-title">إنشاء حساب جديد 🚀</div>', unsafe_allow_html=True)

        with st.form("form_register"):
            r_username = st.text_input("اسم المستخدم",    placeholder="ahmed_123")
            r_email    = st.text_input("البريد الإلكتروني", placeholder="you@example.com")
            r_pw       = st.text_input("كلمة المرور (6 أحرف على الأقل)",
                                       type="password", placeholder="••••••••")
            r_pw2      = st.text_input("تأكيد كلمة المرور",
                                       type="password", placeholder="••••••••")
            submitted  = st.form_submit_button("إنشاء الحساب",
                                               use_container_width=True, type="primary")
            if submitted:
                st.session_state._reg_user      = r_username
                st.session_state._reg_email     = r_email
                st.session_state._reg_pw        = r_pw
                st.session_state._reg_pw2       = r_pw2
                st.session_state._reg_submitted = True

        if st.session_state._reg_submitted:
            st.session_state._reg_submitted = False
            _user  = st.session_state._reg_user.strip()
            _email = st.session_state._reg_email.strip()
            _pw    = st.session_state._reg_pw
            _pw2   = st.session_state._reg_pw2

            if not _user or not _email or not _pw or not _pw2:
                st.session_state.auth_error = "يرجى ملء جميع الحقول."
            elif _pw != _pw2:
                st.session_state.auth_error = "كلمتا المرور غير متطابقتين."
            else:
                st.session_state.auth_error = ""
                with st.spinner("جارٍ إنشاء حسابك…"):
                    data, err = api_register(_user, _email, _pw)
                if data:
                    import json
                    st.session_state.token = data["token"]
                    st.session_state.user  = data
                    # ← حفظ في Cookies
                    cookies["token"]     = data["token"]
                    cookies["user_json"] = json.dumps(data)
                    cookies.save()
                    logger.info("🎉 حساب جديد | user_id=%s", data.get("user_id"))
                else:
                    st.session_state.auth_error = err
            st.rerun()

    st.stop()


# ══════════════════════════════════════════════
#  الصفحة الرئيسية
# ══════════════════════════════════════════════

user = st.session_state.user or {}
uid  = user.get("user_id", 1)

col_name, col_out = st.columns([4, 1])
with col_name:
    st.markdown(f'<div class="username-tag">👤 {user.get("username","")}</div>',
                unsafe_allow_html=True)
with col_out:
    if st.button("خروج", key="btn_logout"):
        # ← مسح الـ Cookies عند الخروج
        cookies["token"]     = ""
        cookies["user_json"] = ""
        cookies.save()
        for k in ["token", "user", "auth_error", "last_refresh",
                  "_login_id", "_login_pw", "_reg_user", "_reg_email",
                  "_reg_pw", "_reg_pw2", "_login_submitted", "_reg_submitted"]:
            st.session_state[k] = None if k in ("token", "user") else (
                False if k.endswith("_submitted") else "")
        st.session_state.last_refresh = 0
        st.rerun()

balance = user.get("balance", 0.0)
st.markdown(f"""
<div class="balance-card">
    <div class="balance-label">رصيدك الحالي</div>
    <div class="balance-value">{balance:,.4f}</div>
    <div class="balance-currency">USD</div>
</div>
""", unsafe_allow_html=True)

if st.button("↻  تحديث الرصيد", use_container_width=True):
    with st.spinner("جارٍ جلب البيانات…"):
        fresh = api_me(st.session_state.token)
    if fresh:
        import json
        updated = {**user, **fresh, "user_id": fresh["user_id"]}
        st.session_state.user         = updated
        st.session_state.last_refresh = time.time()
        # ← تحديث الـ Cookie بالبيانات الجديدة
        cookies["user_json"] = json.dumps(updated)
        cookies.save()
        st.rerun()
    else:
        st.markdown('<div class="rh-alert error">⚠️ تعذّر تحديث الرصيد.</div>',
                    unsafe_allow_html=True)

st.markdown('<hr class="rh-divider">', unsafe_allow_html=True)

st.markdown("#### 🎯 جدران العروض")

WALLS = [
    ("BitLabs",  bl_url(uid),  "#4a6cf7", "استبيانات بمكافآت عالية"),
    ("AdGem",    ag_url(uid),  "#f7a94a", "عروض متنوعة وسريعة"),
    ("CPX",      cpx_url(uid), "#4af7a9", "استبيانات CPX Research"),
]

for name, url, color, desc in WALLS:
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
