"""
app.py  —  Offers & Rewards  |  Streamlit Frontend
────────────────────────────────────────────────────
تشغيل:
    pip install streamlit requests
    streamlit run app.py
"""

import logging
import time
import requests
import streamlit as st

# ─────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s | %(levelname)s | %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("frontend")

# ─────────────────────────────────────────────
#  الإعدادات
# ─────────────────────────────────────────────
RAILWAY_URL   = "https://ads-rewards-app-production.up.railway.app"
BITLABS_TOKEN = "DCDEC791-3E5B-484D-B11C-3404631079D0"


def bitlabs_wall_url(uid: int) -> str:
    return f"https://web.bitlabs.ai?token={BITLABS_TOKEN}&uid={uid}"


def fetch_balance(uid: int) -> dict | None:
    """يجلب بيانات المستخدم من Railway."""
    try:
        resp = requests.get(f"{RAILWAY_URL}/users/{uid}", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            logger.info("✅ جُلب رصيد المستخدم %s = %.4f", uid, data.get("balance", 0))
            return data
        logger.warning("⚠️ الخادم أعاد %s للمستخدم %s", resp.status_code, uid)
    except Exception as e:
        logger.error("❌ خطأ في الاتصال بالخادم: %s", e)
    return None


# ─────────────────────────────────────────────
#  إعداد الصفحة
# ─────────────────────────────────────────────
st.set_page_config(
    page_title = "Rewards Hub",
    page_icon  = "💎",
    layout     = "centered",
)

# ─────────────────────────────────────────────
#  CSS  (تصميم داكن راقٍ)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── جذر ── */
:root {
    --bg:       #0a0a0f;
    --surface:  #13131a;
    --card:     #1a1a25;
    --border:   #2a2a3d;
    --gold:     #f0c040;
    --gold2:    #e8a020;
    --text:     #e8e8f0;
    --muted:    #7070a0;
    --green:    #30d080;
    --radius:   16px;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    font-family: 'DM Sans', sans-serif;
    color: var(--text);
}

[data-testid="stHeader"] { background: transparent !important; }

/* ── إخفاء عناصر Streamlit الافتراضية ── */
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }

/* ── Header ── */
.rh-header {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
}
.rh-logo {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -1px;
    background: linear-gradient(135deg, var(--gold) 0%, var(--gold2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: .25rem;
}
.rh-sub {
    font-size: .9rem;
    color: var(--muted);
    letter-spacing: .5px;
}

/* ── بطاقة المستخدم ── */
.balance-card {
    background: linear-gradient(135deg, #1e1e30 0%, #16162a 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.8rem 2rem;
    margin: 1rem 0;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.balance-card::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 150px; height: 150px;
    background: radial-gradient(circle, rgba(240,192,64,.12) 0%, transparent 70%);
    pointer-events: none;
}
.balance-label {
    font-size: .75rem;
    color: var(--muted);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: .4rem;
}
.balance-value {
    font-family: 'Syne', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    color: var(--gold);
    line-height: 1;
}
.balance-currency { font-size: 1.1rem; color: var(--muted); margin-top: .3rem; }
.username-tag {
    display: inline-block;
    background: rgba(240,192,64,.1);
    border: 1px solid rgba(240,192,64,.25);
    color: var(--gold);
    font-size: .78rem;
    letter-spacing: 1px;
    padding: .25rem .75rem;
    border-radius: 99px;
    margin-bottom: 1rem;
}

/* ── زر BitLabs ── */
.bl-btn-wrap { margin: 1.5rem 0 1rem; }
.bl-btn {
    display: block;
    width: 100%;
    padding: 1rem;
    background: linear-gradient(135deg, var(--gold) 0%, var(--gold2) 100%);
    color: #0a0a0f !important;
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: .5px;
    text-align: center;
    text-decoration: none !important;
    border-radius: var(--radius);
    border: none;
    cursor: pointer;
    transition: filter .2s, transform .15s;
    box-shadow: 0 4px 24px rgba(240,192,64,.25);
}
.bl-btn:hover { filter: brightness(1.1); transform: translateY(-1px); }
.bl-btn span { margin-right: .5rem; }

/* ── divider ── */
.rh-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}

/* ── info pill ── */
.info-pill {
    display: flex;
    align-items: center;
    gap: .6rem;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: .75rem 1rem;
    font-size: .82rem;
    color: var(--muted);
    margin-bottom: .6rem;
}
.info-pill .icon { font-size: 1rem; }
.info-pill strong { color: var(--text); }

/* ── خطأ / نجاح ── */
.rh-alert {
    border-radius: 10px;
    padding: .8rem 1rem;
    font-size: .85rem;
    margin: .5rem 0;
}
.rh-alert.error   { background: rgba(255,80,80,.1);  border:1px solid rgba(255,80,80,.25); color:#ff8080; }
.rh-alert.success { background: rgba(48,208,128,.1); border:1px solid rgba(48,208,128,.25); color:var(--green); }
.rh-alert.warn    { background: rgba(240,192,64,.08); border:1px solid rgba(240,192,64,.2); color:var(--gold); }

/* ── Streamlit input override ── */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stNumberInput"] label,
[data-testid="stTextInput"] label {
    color: var(--muted) !important;
    font-size: .8rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}

/* ── Streamlit button override ── */
[data-testid="stButton"] button {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: border-color .2s !important;
}
[data-testid="stButton"] button:hover {
    border-color: var(--gold) !important;
    color: var(--gold) !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  الحالة  (Session State)
# ─────────────────────────────────────────────
if "user_data"     not in st.session_state: st.session_state.user_data     = None
if "last_refresh"  not in st.session_state: st.session_state.last_refresh  = 0
if "fetch_error"   not in st.session_state: st.session_state.fetch_error   = ""


# ─────────────────────────────────────────────
#  Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="rh-header">
    <div class="rh-logo">💎 Rewards Hub</div>
    <div class="rh-sub">أكمل العروض واربح مكافآت حقيقية</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  إدخال User ID
# ─────────────────────────────────────────────
uid = st.number_input(
    "رقم المستخدم (User ID)",
    min_value = 1,
    step      = 1,
    value     = 1,
    help      = "أدخل الـ ID الخاص بك على المنصة",
)

col_fetch, col_refresh = st.columns([3, 1])

with col_fetch:
    fetch_clicked = st.button("🔍  جلب بياناتي", use_container_width=True)

with col_refresh:
    refresh_clicked = st.button("↻", use_container_width=True, help="تحديث الرصيد")

# ─────────────────────────────────────────────
#  جلب البيانات
# ─────────────────────────────────────────────
should_fetch = fetch_clicked or refresh_clicked or (
    st.session_state.user_data and
    st.session_state.user_data.get("id") != uid
)

if fetch_clicked or refresh_clicked:
    logger.info("🖱️  المستخدم طلب جلب البيانات | uid=%s", uid)
    with st.spinner("جارٍ الاتصال بالخادم…"):
        data = fetch_balance(uid)
    if data:
        st.session_state.user_data    = data
        st.session_state.last_refresh = time.time()
        st.session_state.fetch_error  = ""
        logger.info("💾  تم تخزين بيانات المستخدم %s في الجلسة", uid)
    else:
        st.session_state.fetch_error = f"تعذّر الاتصال بالخادم أو المستخدم {uid} غير موجود."
        logger.warning("❌  فشل جلب بيانات uid=%s", uid)

# ─────────────────────────────────────────────
#  عرض الخطأ
# ─────────────────────────────────────────────
if st.session_state.fetch_error:
    st.markdown(
        f'<div class="rh-alert error">⚠️ {st.session_state.fetch_error}</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
#  بطاقة الرصيد + زر BitLabs
# ─────────────────────────────────────────────
user = st.session_state.user_data

if user:
    username    = user.get("username", "—")
    balance     = user.get("balance", 0.0)
    wall_url    = bitlabs_wall_url(uid)

    # وقت آخر تحديث
    if st.session_state.last_refresh:
        age = int(time.time() - st.session_state.last_refresh)
        age_str = f"منذ {age} ث" if age < 60 else f"منذ {age//60} د"
    else:
        age_str = "—"

    # ── بطاقة الرصيد ──
    st.markdown(f"""
    <div class="balance-card">
        <div class="username-tag">👤 {username}</div>
        <div class="balance-label">رصيدك الحالي</div>
        <div class="balance-value">{balance:,.4f}</div>
        <div class="balance-currency">USD · آخر تحديث: {age_str}</div>
    </div>
    """, unsafe_allow_html=True)

    logger.info("🖥️  عرض بطاقة الرصيد | uid=%s | balance=%.4f", uid, balance)

    # ── معلومات ──
    st.markdown('<hr class="rh-divider">', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="info-pill">
        <span class="icon">🔗</span>
        <span>الخادم: <strong>{RAILWAY_URL}</strong></span>
    </div>
    <div class="info-pill">
        <span class="icon">🎯</span>
        <span>مزود العروض: <strong>BitLabs</strong></span>
    </div>
    <div class="info-pill">
        <span class="icon">🆔</span>
        <span>User ID المُرسَل: <strong>{uid}</strong></span>
    </div>
    """, unsafe_allow_html=True)

    # ── زر BitLabs ──
    st.markdown('<hr class="rh-divider">', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="bl-btn-wrap">
        <a class="bl-btn" href="{wall_url}" target="_blank">
            <span>🎮</span> افتح جدار العروض — BitLabs
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div class="rh-alert warn">💡 أكمل عرضاً ثم اضغط ↻ أعلاه لترى رصيدك المُحدَّث.</div>',
        unsafe_allow_html=True,
    )

    logger.info("🔗  تم توليد رابط BitLabs لـ uid=%s", uid)

else:
    # حالة فارغة — قبل أي بحث
    st.markdown("""
    <div class="rh-alert warn" style="text-align:center; padding:1.5rem;">
        🔍 أدخل رقم مستخدمك ثم اضغط <strong>جلب بياناتي</strong>
    </div>
    """, unsafe_allow_html=True)
