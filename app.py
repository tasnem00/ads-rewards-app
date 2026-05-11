"""
app.py  —  Rewards Hub  |  Streamlit Frontend (v2 – Enhanced)
══════════════════════════════════════════════════════════════
تشغيل:
    pip install streamlit requests
    streamlit run app.py
"""

import logging
import time
import requests
import streamlit as st
import streamlit.components.v1 as components

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
ADGEM_APP_ID  = "YOUR_ADGEM_APP_ID"      # ← ضع App ID من لوحة AdGem
ADGEM_API_KEY = "YOUR_ADGEM_API_KEY"     # ← ضع API Key من لوحة AdGem


def bitlabs_wall_url(uid: int) -> str:
    return f"https://web.bitlabs.ai/?token={BITLABS_TOKEN}&uid={uid}"


def adgem_wall_url(uid: int) -> str:
    """
    رابط جدار عروض AdGem.
    استبدل YOUR_ADGEM_APP_ID بالـ App ID الحقيقي من dashboard.adgem.com
    بعد الموافقة على حسابك.
    """
    return f"https://wall.adgem.com/?app_id={ADGEM_APP_ID}&user_id={uid}"


def fetch_balance(uid: int) -> dict | None:
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
#  CSS — تصميم فاخر مع خلفية متحركة
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap');

:root {
    --bg:        #07070e;
    --surface:   #0f0f1a;
    --card:      #141420;
    --card2:     #1a1a2e;
    --border:    #252540;
    --border2:   #353560;
    --gold:      #f2c84b;
    --gold2:     #e8a020;
    --gold3:     #ffd97a;
    --text:      #eaeaf8;
    --muted:     #6060a0;
    --muted2:    #9090c0;
    --green:     #2ecc8a;
    --blue:      #5090ff;
    --radius:    18px;
    --radius-sm: 10px;
}

/* ══ Reset & Base ══ */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="block-container"] {
    background: transparent !important;
    font-family: 'DM Sans', sans-serif;
    color: var(--text);
}

/* ══ خلفية متحركة ══ */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    z-index: -2;
    background: var(--bg);
}

[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed;
    inset: 0;
    z-index: -1;
    background:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(242,200,75,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(80,144,255,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 40% 30% at 50% 50%, rgba(242,200,75,0.03) 0%, transparent 70%);
    animation: bgPulse 8s ease-in-out infinite alternate;
    pointer-events: none;
}

@keyframes bgPulse {
    0%   { opacity: 0.6; transform: scale(1); }
    100% { opacity: 1;   transform: scale(1.04); }
}

/* ══ إخفاء عناصر Streamlit ══ */
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ══ نجوم الخلفية ══ */
.stars-layer {
    position: fixed;
    inset: 0;
    z-index: -1;
    overflow: hidden;
    pointer-events: none;
}
.star {
    position: absolute;
    border-radius: 50%;
    background: var(--gold3);
    opacity: 0;
    animation: twinkle var(--dur, 4s) ease-in-out infinite;
    animation-delay: var(--delay, 0s);
}
@keyframes twinkle {
    0%, 100% { opacity: 0; transform: scale(0.5); }
    50%       { opacity: var(--max-op, 0.6); transform: scale(1); }
}

/* ══ Header ══ */
.rh-header {
    text-align: center;
    padding: 3rem 1rem 1.5rem;
    position: relative;
}
.rh-logo {
    font-family: 'Syne', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -1.5px;
    background: linear-gradient(135deg, var(--gold3) 0%, var(--gold) 50%, var(--gold2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: .3rem;
    filter: drop-shadow(0 0 20px rgba(242,200,75,0.3));
}
.rh-sub {
    font-size: .9rem;
    color: var(--muted2);
    letter-spacing: .8px;
}
.rh-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(242,200,75,.08);
    border: 1px solid rgba(242,200,75,.2);
    color: var(--gold);
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: .3rem .9rem;
    border-radius: 99px;
    margin-bottom: 1.2rem;
}

/* ══ بطاقة الرصيد ══ */
.balance-card {
    background: linear-gradient(135deg, rgba(30,30,55,0.95) 0%, rgba(18,18,40,0.98) 100%);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 2rem 2.2rem;
    margin: 1rem 0;
    text-align: center;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(12px);
}
.balance-card::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(242,200,75,.1) 0%, transparent 65%);
    pointer-events: none;
}
.balance-card::after {
    content: '';
    position: absolute;
    bottom: -40px; left: -40px;
    width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(80,144,255,.07) 0%, transparent 65%);
    pointer-events: none;
}
.balance-label {
    font-size: .72rem;
    color: var(--muted);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: .5rem;
}
.balance-value {
    font-family: 'Syne', sans-serif;
    font-size: 3.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--gold3), var(--gold));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
    filter: drop-shadow(0 2px 12px rgba(242,200,75,0.35));
}
.balance-currency {
    font-size: .85rem;
    color: var(--muted2);
    margin-top: .5rem;
}
.username-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(242,200,75,.08);
    border: 1px solid rgba(242,200,75,.2);
    color: var(--gold);
    font-size: .78rem;
    letter-spacing: 1.5px;
    padding: .3rem .9rem;
    border-radius: 99px;
    margin-bottom: 1.2rem;
}

/* ══ شبكة منصات العروض ══ */
.platforms-title {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: var(--muted2);
    letter-spacing: 2px;
    text-transform: uppercase;
    text-align: center;
    margin: 1.8rem 0 1rem;
}

/* ══ divider ══ */
.rh-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.8rem 0;
    position: relative;
}
.rh-divider-text {
    text-align: center;
    margin: 1.5rem 0;
    position: relative;
}
.rh-divider-text::before {
    content: '';
    position: absolute;
    top: 50%; left: 0;
    width: 100%; height: 1px;
    background: var(--border);
}
.rh-divider-text span {
    position: relative;
    background: var(--bg);
    padding: 0 1rem;
    font-size: .75rem;
    color: var(--muted);
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* ══ alerts ══ */
.rh-alert {
    border-radius: var(--radius-sm);
    padding: .85rem 1.1rem;
    font-size: .84rem;
    margin: .6rem 0;
    display: flex;
    align-items: flex-start;
    gap: .6rem;
}
.rh-alert.error   { background: rgba(255,80,80,.08);  border: 1px solid rgba(255,80,80,.2);  color:#ff9090; }
.rh-alert.success { background: rgba(46,204,138,.08); border: 1px solid rgba(46,204,138,.2); color:var(--green); }
.rh-alert.warn    { background: rgba(242,200,75,.07); border: 1px solid rgba(242,200,75,.18); color:var(--gold); }
.rh-alert.info    { background: rgba(80,144,255,.07); border: 1px solid rgba(80,144,255,.18); color:var(--blue); }

/* ══ Footer ══ */
.rh-footer {
    text-align: center;
    padding: 2rem 1rem;
    font-size: .78rem;
    color: var(--muted);
    border-top: 1px solid var(--border);
    margin-top: 2rem;
}
.rh-footer a {
    color: var(--gold);
    text-decoration: none;
    opacity: .7;
    transition: opacity .2s;
}
.rh-footer a:hover { opacity: 1; }

/* ══ Streamlit overrides ══ */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: .95rem !important;
}
[data-testid="stNumberInput"] label,
[data-testid="stTextInput"] label {
    color: var(--muted2) !important;
    font-size: .75rem !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
}
[data-testid="stButton"] button {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: .9rem !important;
    transition: all .25s !important;
}
[data-testid="stButton"] button:hover {
    border-color: var(--gold) !important;
    color: var(--gold) !important;
    background: rgba(242,200,75,.05) !important;
}

/* ══ modal overlay ══ */
.modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(0,0,5,0.88);
    backdrop-filter: blur(6px);
    align-items: flex-start;
    justify-content: center;
    padding: 2rem 1rem;
    overflow-y: auto;
}
.modal-overlay.active { display: flex; }
.modal-box {
    background: var(--card2);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 2rem;
    max-width: 600px;
    width: 100%;
    position: relative;
    animation: modalIn .25s ease;
}
@keyframes modalIn {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
.modal-close {
    position: absolute;
    top: 1rem; right: 1rem;
    background: var(--border);
    border: none;
    color: var(--muted2);
    width: 32px; height: 32px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1rem;
    display: flex; align-items: center; justify-content: center;
    transition: background .2s, color .2s;
}
.modal-close:hover { background: var(--border2); color: var(--gold); }
.modal-h1 {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    color: var(--gold);
    margin-bottom: 1.2rem;
}
.modal-section { margin-bottom: 1.2rem; }
.modal-section h3 {
    font-family: 'Syne', sans-serif;
    font-size: .85rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--muted2);
    margin-bottom: .4rem;
}
.modal-section p {
    font-size: .88rem;
    color: var(--text);
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Session State
# ─────────────────────────────────────────────
for k, v in {
    "user_data":    None,
    "last_refresh": 0,
    "fetch_error":  "",
    "page":         "home",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
#  خلفية النجوم المتحركة
# ─────────────────────────────────────────────
import random
stars_html = '<div class="stars-layer">'
for i in range(35):
    x   = random.randint(0, 100)
    y   = random.randint(0, 100)
    sz  = random.randint(1, 3)
    dur = round(random.uniform(3, 7), 1)
    delay = round(random.uniform(0, 6), 1)
    op  = round(random.uniform(0.3, 0.8), 2)
    stars_html += (
        f'<div class="star" style="left:{x}%;top:{y}%;'
        f'width:{sz}px;height:{sz}px;'
        f'--dur:{dur}s;--delay:{delay}s;--max-op:{op}"></div>'
    )
stars_html += '</div>'
st.markdown(stars_html, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="rh-header">
    <div class="rh-badge">✦ Earn Real Rewards</div>
    <div class="rh-logo">💎 Rewards Hub</div>
    <div class="rh-sub">أكمل العروض واربح مكافآت حقيقية من منصات متعددة</div>
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


# ─────────────────────────────────────────────
#  عنوان قسم المنصات
# ─────────────────────────────────────────────
st.markdown('<div class="platforms-title">اختر منصة العروض</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  بطاقة BitLabs
# ─────────────────────────────────────────────
wall_url_bl = bitlabs_wall_url(uid)
logger.info("🔗 BitLabs | uid=%s | url=%s", uid, wall_url_bl)

components.html(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:transparent; padding:6px 0; }}

.platform-card {{
    background: linear-gradient(135deg, rgba(20,20,40,0.97), rgba(14,14,30,0.98));
    border: 1px solid #2a2a4a;
    border-radius: 18px;
    padding: 20px 22px;
    margin-bottom: 2px;
    transition: border-color .3s, transform .2s;
    position: relative;
    overflow: hidden;
}}
.platform-card::before {{
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(242,200,75,.04) 0%, transparent 60%);
    pointer-events: none;
}}
.platform-card:hover {{ border-color: #f2c84b; transform: translateY(-2px); }}

.card-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}}
.provider-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: 'Syne', sans-serif;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #f2c84b;
    background: rgba(242,200,75,.08);
    border: 1px solid rgba(242,200,75,.2);
    padding: 4px 12px;
    border-radius: 99px;
}}
.status-dot {{
    width: 7px; height: 7px;
    background: #2ecc8a;
    border-radius: 50%;
    animation: pulse 2s ease infinite;
}}
@keyframes pulse {{
    0%,100% {{ opacity:1; box-shadow: 0 0 0 0 rgba(46,204,138,0.4); }}
    50%      {{ opacity:.8; box-shadow: 0 0 0 5px rgba(46,204,138,0); }}
}}
.card-title {{
    font-family: 'Syne', sans-serif;
    font-size: 1.05rem;
    font-weight: 800;
    color: #eaeaf8;
    margin-bottom: 4px;
}}
.card-sub {{
    font-size: .82rem;
    color: #6060a0;
    margin-bottom: 16px;
}}
.card-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 16px;
}}
.tag {{
    font-size: .7rem;
    font-weight: 600;
    letter-spacing: .8px;
    padding: 3px 10px;
    border-radius: 99px;
    background: rgba(242,200,75,.06);
    border: 1px solid rgba(242,200,75,.15);
    color: #c0a040;
}}

.btn-wrap {{
    border-radius: 14px;
    padding: 2.5px;
    background: linear-gradient(135deg, #f2c84b, #e8a020, #f2c84b);
    background-size: 200%;
    animation: shimmer 2.5s ease infinite;
    box-shadow: 0 4px 24px rgba(242,200,75,.28);
}}
@keyframes shimmer {{
    0%   {{ background-position:0% 50%; }}
    50%  {{ background-position:100% 50%; }}
    100% {{ background-position:0% 50%; }}
}}
.btn-inner {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 14px 20px;
    background: linear-gradient(135deg, #f5ca45 0%, #df8f18 100%);
    border-radius: 12px;
    text-decoration: none;
    transition: filter .2s, transform .15s;
    cursor: pointer;
    border: none;
    width: 100%;
}}
.btn-inner:hover  {{ filter:brightness(1.08); transform:translateY(-1px); }}
.btn-inner:active {{ transform:translateY(0); filter:brightness(.96); }}
.btn-icon {{ font-size:1.4rem; animation: bounce 2s ease infinite; }}
@keyframes bounce {{
    0%,100% {{ transform:translateY(0); }}
    40%     {{ transform:translateY(-5px); }}
}}
.btn-text {{
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 800;
    color: #0a0a0f;
    letter-spacing: .3px;
}}
.btn-sub {{
    font-family: 'Syne', sans-serif;
    font-size: .65rem;
    font-weight: 700;
    color: rgba(10,10,15,.5);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 1px;
}}
</style>
</head>
<body>
<div class="platform-card">
    <div class="card-top">
        <div class="provider-badge">
            <div class="status-dot"></div>
            BitLabs
        </div>
    </div>
    <div class="card-title">الاستبيانات والعروض</div>
    <div class="card-sub">استبيانات مدفوعة عالية الجودة • uid: {uid}</div>
    <div class="card-tags">
        <span class="tag">📋 Surveys</span>
        <span class="tag">⚡ مدفوعات فورية</span>
        <span class="tag">🌍 متاح عالمياً</span>
    </div>
    <div class="btn-wrap">
        <a class="btn-inner" href="{wall_url_bl}" target="_blank" rel="noopener noreferrer"
           onclick="window.open('{wall_url_bl}','_blank','noopener,noreferrer');return false;">
            <span class="btn-icon">🎁</span>
            <div>
                <div class="btn-text">ابدأ مع BitLabs الآن</div>
                <div class="btn-sub">افتح جدار العروض</div>
            </div>
        </a>
    </div>
</div>
</body>
</html>
""", height=230)


# ─────────────────────────────────────────────
#  بطاقة AdGem
# ─────────────────────────────────────────────
wall_url_ag = adgem_wall_url(uid)
logger.info("🔗 AdGem | uid=%s | url=%s", uid, wall_url_ag)

components.html(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:transparent; padding:6px 0; }}

.platform-card {{
    background: linear-gradient(135deg, rgba(14,20,40,0.97), rgba(10,14,35,0.98));
    border: 1px solid #202245;
    border-radius: 18px;
    padding: 20px 22px;
    margin-bottom: 2px;
    transition: border-color .3s, transform .2s;
    position: relative;
    overflow: hidden;
}}
.platform-card::before {{
    content: '';
    position: absolute;
    top: -50px; right: -50px;
    width: 180px; height: 180px;
    background: radial-gradient(circle, rgba(80,144,255,.08) 0%, transparent 65%);
    pointer-events: none;
}}
.platform-card:hover {{ border-color: #5090ff; transform: translateY(-2px); }}

.card-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}}
.provider-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: 'Syne', sans-serif;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #5090ff;
    background: rgba(80,144,255,.08);
    border: 1px solid rgba(80,144,255,.2);
    padding: 4px 12px;
    border-radius: 99px;
}}
.status-dot {{
    width: 7px; height: 7px;
    background: #5090ff;
    border-radius: 50%;
    animation: pulse 2.5s ease infinite;
}}
@keyframes pulse {{
    0%,100% {{ opacity:1; box-shadow: 0 0 0 0 rgba(80,144,255,0.4); }}
    50%      {{ opacity:.8; box-shadow: 0 0 0 5px rgba(80,144,255,0); }}
}}
.card-title {{
    font-family: 'Syne', sans-serif;
    font-size: 1.05rem;
    font-weight: 800;
    color: #eaeaf8;
    margin-bottom: 4px;
}}
.card-sub {{
    font-size: .82rem;
    color: #5060a0;
    margin-bottom: 16px;
}}
.card-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 16px;
}}
.tag {{
    font-size: .7rem;
    font-weight: 600;
    letter-spacing: .8px;
    padding: 3px 10px;
    border-radius: 99px;
    background: rgba(80,144,255,.06);
    border: 1px solid rgba(80,144,255,.15);
    color: #7090d0;
}}
.pending-badge {{
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 3px 10px;
    border-radius: 99px;
    background: rgba(242,200,75,.08);
    border: 1px solid rgba(242,200,75,.2);
    color: #c0a040;
}}

.btn-wrap {{
    border-radius: 14px;
    padding: 2.5px;
    background: linear-gradient(135deg, #5090ff, #3060cc, #5090ff);
    background-size: 200%;
    animation: shimmer 2.5s ease infinite;
    box-shadow: 0 4px 24px rgba(80,144,255,.22);
}}
@keyframes shimmer {{
    0%   {{ background-position:0% 50%; }}
    50%  {{ background-position:100% 50%; }}
    100% {{ background-position:0% 50%; }}
}}
.btn-inner {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 14px 20px;
    background: linear-gradient(135deg, #5a9aff 0%, #3060cc 100%);
    border-radius: 12px;
    text-decoration: none;
    transition: filter .2s, transform .15s;
    cursor: pointer;
    border: none;
    width: 100%;
}}
.btn-inner:hover  {{ filter:brightness(1.08); transform:translateY(-1px); }}
.btn-inner:active {{ transform:translateY(0); filter:brightness(.96); }}
.btn-icon {{ font-size:1.4rem; }}
.btn-text {{
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: .3px;
}}
.btn-sub {{
    font-family: 'Syne', sans-serif;
    font-size: .65rem;
    font-weight: 700;
    color: rgba(255,255,255,.5);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 1px;
}}
.notice-box {{
    margin-top: 10px;
    background: rgba(242,200,75,.05);
    border: 1px solid rgba(242,200,75,.15);
    border-radius: 10px;
    padding: 10px 14px;
    font-size: .78rem;
    color: #a09050;
    line-height: 1.6;
}}
</style>
</head>
<body>
<div class="platform-card">
    <div class="card-top">
        <div class="provider-badge">
            <div class="status-dot"></div>
            AdGem
        </div>
        <span class="pending-badge">⏳ قيد الموافقة</span>
    </div>
    <div class="card-title">العروض والتطبيقات والمسابقات</div>
    <div class="card-sub">تنزيل تطبيقات • إكمال مهام • عروض خاصة • uid: {uid}</div>
    <div class="card-tags">
        <span class="tag">📱 Offerwall</span>
        <span class="tag">🎮 Tasks</span>
        <span class="tag">🏆 Contests</span>
    </div>
    <div class="btn-wrap">
        <a class="btn-inner" href="{wall_url_ag}" target="_blank" rel="noopener noreferrer"
           onclick="window.open('{wall_url_ag}','_blank','noopener,noreferrer');return false;">
            <span class="btn-icon">🚀</span>
            <div>
                <div class="btn-text">افتح AdGem</div>
                <div class="btn-sub">Explore Offers</div>
            </div>
        </a>
    </div>
    <div class="notice-box">
        ⚠️ هذه المنصة في انتظار الموافقة النهائية من AdGem. الزر جاهز تقنياً —
        فور حصولك على App ID الرسمي، ضعه في <code>ADGEM_APP_ID</code> بالكود وسيعمل فوراً.
    </div>
</div>
</body>
</html>
""", height=285)


st.markdown('<hr class="rh-divider">', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  جلب الرصيد
# ─────────────────────────────────────────────
col_fetch, col_refresh = st.columns([3, 1])

with col_fetch:
    fetch_clicked = st.button("🔍  جلب رصيدي", use_container_width=True)

with col_refresh:
    refresh_clicked = st.button("↻", use_container_width=True, help="تحديث الرصيد")

if fetch_clicked or refresh_clicked:
    logger.info("🖱️ جلب الرصيد | uid=%s", uid)
    with st.spinner("جارٍ الاتصال بالخادم…"):
        data = fetch_balance(uid)
    if data:
        st.session_state.user_data    = data
        st.session_state.last_refresh = time.time()
        st.session_state.fetch_error  = ""
        logger.info("💾 تم تخزين بيانات %s", uid)
    else:
        st.session_state.fetch_error = f"تعذّر الاتصال أو المستخدم {uid} غير موجود."
        logger.warning("❌ فشل جلب uid=%s", uid)

if st.session_state.fetch_error:
    st.markdown(
        f'<div class="rh-alert error">⚠️ {st.session_state.fetch_error}</div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
#  بطاقة الرصيد
# ─────────────────────────────────────────────
user = st.session_state.user_data
if user:
    username = user.get("username", "—")
    balance  = user.get("balance", 0.0)
    age_str  = "—"
    if st.session_state.last_refresh:
        age = int(time.time() - st.session_state.last_refresh)
        age_str = f"منذ {age} ث" if age < 60 else f"منذ {age//60} د"

    st.markdown(f"""
    <div class="balance-card">
        <div class="username-tag">👤 {username}</div>
        <div class="balance-label">رصيدك الحالي</div>
        <div class="balance-value">{balance:,.4f}</div>
        <div class="balance-currency">USD · آخر تحديث: {age_str}</div>
    </div>
    """, unsafe_allow_html=True)
    logger.info("🖥️ عرض الرصيد | uid=%s | %.4f", uid, balance)
    st.markdown(
        '<div class="rh-alert warn">💡 أكمل عرضاً ثم اضغط ↻ لترى رصيدك المُحدَّث فوراً.</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="rh-alert info" style="justify-content:center">💡 اضغط <strong>جلب رصيدي</strong> لعرض رصيدك بعد إتمام العروض.</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
#  Footer مع زر الشروط
# ─────────────────────────────────────────────
st.markdown("""
<div class="rh-footer">
    <div style="margin-bottom:.5rem">
        © 2024 Rewards Hub · جميع الحقوق محفوظة
    </div>
    <a href="#" onclick="document.getElementById('terms-modal').classList.add('active');return false;">
        📄 الشروط والأحكام
    </a>
    &nbsp;·&nbsp;
    <a href="mailto:support@rewardshub.com">✉️ الدعم</a>
</div>

<!-- ══ مودال الشروط ══ -->
<div id="terms-modal" class="modal-overlay" onclick="if(event.target===this)this.classList.remove('active')">
    <div class="modal-box">
        <button class="modal-close" onclick="document.getElementById('terms-modal').classList.remove('active')">✕</button>
        <div class="modal-h1">📄 الشروط والأحكام</div>

        <div class="modal-section">
            <h3>١. قبول الشروط</h3>
            <p>باستخدامك لمنصة Rewards Hub فإنك توافق على الالتزام بهذه الشروط والأحكام بالكامل. إذا كنت لا توافق على أي جزء منها، يُرجى عدم استخدام المنصة.</p>
        </div>

        <div class="modal-section">
            <h3>٢. أهلية الاستخدام</h3>
            <p>يجب أن يكون عمرك 18 عاماً أو أكثر لاستخدام هذه المنصة. بتسجيلك أنت تقرّ بأنك تستوفي هذا الشرط. المنصة غير متاحة في المناطق التي يحظر فيها القانون المحلي مثل هذه الخدمات.</p>
        </div>

        <div class="modal-section">
            <h3>٣. كسب المكافآت</h3>
            <p>يتم احتساب المكافآت تلقائياً عبر شركاء العروض (BitLabs، AdGem وغيرها). نحتفظ بالحق في مراجعة أي معاملة مشبوهة وإلغائها دون إشعار مسبق. المكافآت غير قابلة للتحويل بين الحسابات.</p>
        </div>

        <div class="modal-section">
            <h3>٤. قواعد الاستخدام المقبول</h3>
            <p>يُحظر استخدام أدوات الأتمتة (bots)، أو إنشاء حسابات وهمية، أو تكرار إتمام العروض بطرق احتيالية. يؤدي انتهاك هذه القواعد إلى إيقاف الحساب فوراً ومصادرة الرصيد.</p>
        </div>

        <div class="modal-section">
            <h3>٥. الخصوصية والبيانات</h3>
            <p>نحن نجمع ونحفظ الحد الأدنى من البيانات اللازمة لتشغيل الخدمة (User ID، الرصيد). لا نبيع بياناتك لأي طرف ثالث. بيانات العروض تُعالَج مباشرة من قِبل شركاء العروض وتخضع لسياسات الخصوصية الخاصة بكل منهم.</p>
        </div>

        <div class="modal-section">
            <h3>٦. إخلاء المسؤولية</h3>
            <p>Rewards Hub وسيط بين المستخدمين وشركاء العروض. لا نتحمل مسؤولية أي تأخر في الإضافة، أو مشاكل تقنية لدى الشركاء. في حال وجود نزاع حول مكافأة، يُرجى التواصل مع الدعم خلال 30 يوماً.</p>
        </div>

        <div class="modal-section">
            <h3>٧. التعديلات</h3>
            <p>نحتفظ بالحق في تعديل هذه الشروط في أي وقت. سيتم إشعار المستخدمين النشطين بأي تغييرات جوهرية. الاستمرار في استخدام المنصة بعد التعديل يُعدّ موافقةً ضمنية.</p>
        </div>

        <div style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid #252540; font-size:.78rem; color:#5050a0; text-align:center;">
            آخر تحديث: يناير 2025 · Rewards Hub · جميع الحقوق محفوظة
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
