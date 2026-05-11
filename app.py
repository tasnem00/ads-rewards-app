"""
app.py  —  Rewards Hub  v3 (Professional)
══════════════════════════════════════════
تشغيل:
    pip install streamlit requests
    streamlit run app.py
"""

import logging
import time
import random
import requests
import streamlit as st
import streamlit.components.v1 as components

# ══════════════════════════════════════════════
#  Logging
# ══════════════════════════════════════════════
logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s | %(levelname)s | %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rewards_hub")

# ══════════════════════════════════════════════
#  Config
# ══════════════════════════════════════════════
RAILWAY_URL   = "https://ads-rewards-app-production.up.railway.app"
BITLABS_TOKEN = "DCDEC791-3E5B-484D-B11C-3404631079D0"
ADGEM_APP_ID  = "32570"


def bitlabs_wall_url(user_id) -> str:
    return f"https://web.bitlabs.ai/?token={BITLABS_TOKEN}&uid={user_id}"


def adgem_wall_url(user_id) -> str:
    return f"https://adunits.adgem.com/wall?appid={ADGEM_APP_ID}&player_id={user_id}"


def fetch_or_create_user(username: str) -> dict | None:
    """
    يحاول جلب المستخدم بالاسم.
    إذا لم يوجد (404) يُنشئه تلقائياً.
    يُعيد dict أو None عند الفشل.
    """
    try:
        resp = requests.get(
            f"{RAILWAY_URL}/users/by_username/{username}", timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            logger.info("✅ login | %s | balance=%.4f",
                        username, data.get("balance", 0))
            return data
        if resp.status_code == 404:
            create = requests.post(
                f"{RAILWAY_URL}/users",
                json={"username": username},
                timeout=8,
            )
            if create.status_code in (200, 201):
                data = create.json()
                logger.info("🆕 new user | %s", username)
                return data
        logger.warning("⚠️ server %s for %s", resp.status_code, username)
    except Exception as exc:
        logger.error("❌ connection error: %s", exc)
    return None


def fetch_balance(uid) -> dict | None:
    try:
        resp = requests.get(f"{RAILWAY_URL}/users/{uid}", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            logger.info("🔄 refresh uid=%s → %.4f", uid, data.get("balance", 0))
            return data
    except Exception as exc:
        logger.error("❌ balance fetch error: %s", exc)
    return None


# ══════════════════════════════════════════════
#  Page config
# ══════════════════════════════════════════════
st.set_page_config(
    page_title = "Rewards Hub",
    page_icon  = "💎",
    layout     = "centered",
)

# ══════════════════════════════════════════════
#  Global CSS
# ══════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --bg:       #08080f;
    --surface:  #0f0f1c;
    --card:     #141424;
    --card2:    #1b1b30;
    --border:   #242440;
    --border2:  #323260;
    --gold:     #D4AF37;
    --gold-lt:  #f0cc60;
    --gold-dk:  #a88520;
    --text:     #eaeaf5;
    --muted:    #5a5a90;
    --muted2:   #8888bb;
    --green:    #2ecc8a;
    --blue:     #4d8fff;
    --radius:   18px;
    --rsm:      10px;
}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"] {
    background: var(--bg) !important;
    font-family: 'DM Sans', sans-serif;
    color: var(--text);
}
[data-testid="stHeader"]      { background: transparent !important; }
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"]  { display: none !important; }

/* ambient glow */
[data-testid="stAppViewContainer"]::after {
    content: ''; position: fixed; inset: 0; z-index: -1; pointer-events: none;
    background:
        radial-gradient(ellipse 70% 45% at 15% 0%,  rgba(212,175,55,.09) 0%, transparent 65%),
        radial-gradient(ellipse 55% 40% at 85% 100%, rgba(77,143,255,.07) 0%, transparent 65%),
        radial-gradient(ellipse 40% 30% at 50%  50%, rgba(212,175,55,.03) 0%, transparent 70%);
    animation: amb 9s ease-in-out infinite alternate;
}
@keyframes amb {
    from { opacity:.6; transform:scale(1);    }
    to   { opacity:1;  transform:scale(1.05); }
}

/* Streamlit overrides */
[data-testid="stTextInput"]   input,
[data-testid="stNumberInput"] input {
    background: var(--card)   !important;
    border:     1px solid var(--border) !important;
    border-radius: var(--rsm) !important;
    color:      var(--text)   !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size:  .95rem !important;
}
[data-testid="stTextInput"]   label,
[data-testid="stNumberInput"] label {
    color: var(--muted2) !important;
    font-size: .74rem   !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
}
[data-testid="stButton"] button {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--rsm) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: all .25s !important;
}
[data-testid="stButton"] button:hover {
    border-color: var(--gold)          !important;
    color: var(--gold)                 !important;
    background: rgba(212,175,55,.05)   !important;
}

/* divider */
.rh-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.6rem 0;
}

/* alerts */
.rh-alert {
    border-radius: var(--rsm);
    padding: .85rem 1.1rem;
    font-size: .84rem;
    margin: .6rem 0;
    display: flex; align-items: flex-start; gap: .6rem;
}
.rh-alert.error   { background:rgba(255,85,85,.08);  border:1px solid rgba(255,85,85,.2);  color:#ff9090; }
.rh-alert.warn    { background:rgba(212,175,55,.07); border:1px solid rgba(212,175,55,.18); color:var(--gold); }
.rh-alert.info    { background:rgba(77,143,255,.07); border:1px solid rgba(77,143,255,.18); color:var(--blue); }

/* section label */
.sec-title {
    font-family: 'Syne', sans-serif;
    font-size: .75rem; font-weight: 700;
    letter-spacing: 3px; text-transform: uppercase;
    color: var(--muted); text-align: center;
    margin: 2rem 0 1rem;
}

/* footer */
.rh-footer {
    text-align: center; padding: 2rem 1rem;
    font-size: .78rem; color: var(--muted);
    border-top: 1px solid var(--border); margin-top: 2.5rem;
}
.rh-footer a { color:var(--gold); text-decoration:none; opacity:.7; transition:opacity .2s; }
.rh-footer a:hover { opacity:1; }

/* modal */
.modal-overlay {
    display: none; position: fixed; inset: 0; z-index: 9999;
    background: rgba(0,0,8,.9); backdrop-filter: blur(7px);
    align-items: flex-start; justify-content: center;
    padding: 2rem 1rem; overflow-y: auto;
}
.modal-overlay.active { display: flex; }
.modal-box {
    background: var(--card2); border: 1px solid var(--border2);
    border-radius: var(--radius); padding: 2rem;
    max-width: 600px; width: 100%; position: relative;
    animation: mIn .25s ease;
}
@keyframes mIn {
    from { opacity:0; transform:translateY(24px); }
    to   { opacity:1; transform:translateY(0); }
}
.modal-close {
    position:absolute; top:1rem; right:1rem;
    background:var(--border); border:none; color:var(--muted2);
    width:32px; height:32px; border-radius:50%; cursor:pointer;
    font-size:1rem; display:flex; align-items:center; justify-content:center;
    transition: all .2s;
}
.modal-close:hover { background:var(--border2); color:var(--gold); }
.modal-h1 { font-family:'Syne',sans-serif; font-size:1.4rem; font-weight:800; color:var(--gold); margin-bottom:1.2rem; }
.modal-section { margin-bottom:1.2rem; }
.modal-section h3 {
    font-family:'Syne',sans-serif; font-size:.8rem; font-weight:700;
    letter-spacing:1.5px; text-transform:uppercase; color:var(--muted2); margin-bottom:.4rem;
}
.modal-section p { font-size:.88rem; color:var(--text); line-height:1.75; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  Session State
# ══════════════════════════════════════════════
DEFAULTS: dict = {
    "logged_in":    False,
    "user_data":    None,
    "last_refresh": 0,
    "login_error":  "",
    "active_tab":   "offers",
}
for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ══════════════════════════════════════════════
#  Helper: animated stars background
# ══════════════════════════════════════════════
def _stars() -> None:
    bits = ['<div style="position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden">']
    for _ in range(40):
        x, y  = random.randint(0, 100), random.randint(0, 100)
        sz    = random.randint(1, 3)
        dur   = round(random.uniform(3, 8), 1)
        delay = round(random.uniform(0, 7), 1)
        op    = round(random.uniform(.2, .65), 2)
        bits.append(
            f'<div style="position:absolute;left:{x}%;top:{y}%;'
            f'width:{sz}px;height:{sz}px;border-radius:50%;background:#D4AF37;'
            f'animation:twk {dur}s {delay}s ease-in-out infinite;opacity:0"></div>'
        )
    bits.append('</div>')
    bits.append('<style>@keyframes twk{0%,100%{opacity:0;transform:scale(.5)}'
                '50%{opacity:1;transform:scale(1)}}</style>')
    st.markdown("".join(bits), unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  PAGE: LOGIN
# ══════════════════════════════════════════════
def page_login() -> None:
    _stars()

    # hero
    components.html("""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:transparent;padding:36px 0 22px;text-align:center}
.gem{font-size:3.4rem;line-height:1;margin-bottom:14px;
     filter:drop-shadow(0 0 20px rgba(212,175,55,.55));
     animation:fl 3.5s ease-in-out infinite}
@keyframes fl{0%,100%{transform:translateY(0)}50%{transform:translateY(-9px)}}
.logo{font-family:'Syne',sans-serif;font-size:2.5rem;font-weight:800;letter-spacing:-1px;
      background:linear-gradient(135deg,#f0cc60,#D4AF37,#a88520);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
      filter:drop-shadow(0 0 16px rgba(212,175,55,.28));margin-bottom:6px}
.tag{font-size:.88rem;color:#6868a8;letter-spacing:.8px}
</style></head>
<body>
  <div class="gem">💎</div>
  <div class="logo">Rewards Hub</div>
  <div class="tag">أكمل العروض · اربح مكافآت حقيقية</div>
</body></html>
""", height=180)

    # login card
    st.markdown("""
<div style="background:linear-gradient(135deg,rgba(27,27,48,.97),rgba(16,16,32,.98));
            border:1px solid #2a2a48;border-radius:18px;
            padding:2rem 2.2rem 1.4rem;margin:.4rem 0 .8rem;
            position:relative;overflow:hidden">
  <div style="position:absolute;top:-50px;right:-50px;width:180px;height:180px;
              background:radial-gradient(circle,rgba(212,175,55,.07) 0%,transparent 65%);
              pointer-events:none"></div>
  <div style="font-size:.7rem;color:#5a5a90;letter-spacing:3px;
              text-transform:uppercase;margin-bottom:1rem">🔐 تسجيل الدخول</div>
""", unsafe_allow_html=True)

    username_val = st.text_input(
        "اسم المستخدم أو البريد الإلكتروني",
        placeholder="ahmed123  أو  user@email.com",
        key="login_field",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.login_error:
        st.markdown(
            f'<div class="rh-alert error">⚠️ {st.session_state.login_error}</div>',
            unsafe_allow_html=True,
        )

    col_btn, _ = st.columns([3, 1])
    with col_btn:
        clicked = st.button("🚀  دخول إلى Rewards Hub", use_container_width=True)

    if clicked:
        val = (username_val or "").strip()
        if not val:
            st.session_state.login_error = "الرجاء إدخال اسم المستخدم أو البريد الإلكتروني."
            st.rerun()
        elif len(val) < 3:
            st.session_state.login_error = "يجب أن يكون الاسم 3 أحرف على الأقل."
            st.rerun()
        else:
            with st.spinner("جارٍ التحقق من حسابك…"):
                data = fetch_or_create_user(val)
            if data:
                st.session_state.logged_in    = True
                st.session_state.user_data    = data
                st.session_state.last_refresh = time.time()
                st.session_state.login_error  = ""
                logger.info("🔓 login success | %s | id=%s", val, data.get("id"))
                st.rerun()
            else:
                st.session_state.login_error = "تعذّر الاتصال بالخادم. حاول مجدداً."
                st.rerun()

    # trust strip
    st.markdown("""
<div style="display:flex;align-items:center;justify-content:center;flex-wrap:wrap;
            gap:12px;margin-top:.9rem;font-size:.75rem;color:#4a4a80">
    <span>🔒 اتصال مشفر</span>
    <span style="opacity:.35">·</span>
    <span>✅ حماية البيانات</span>
    <span style="opacity:.35">·</span>
    <span>🌍 متاح عالمياً</span>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  PAGE: DASHBOARD
# ══════════════════════════════════════════════
def page_dashboard() -> None:
    user     = st.session_state.user_data
    uid      = user.get("id",       1)
    username = user.get("username", "—")
    balance  = user.get("balance",  0.0)

    age_str = "—"
    if st.session_state.last_refresh:
        age = int(time.time() - st.session_state.last_refresh)
        age_str = f"منذ {age} ث" if age < 60 else f"منذ {age // 60} د"

    _stars()

    # ── header ──────────────────────────────────
    components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:26px 0 10px;text-align:center}}
.logo{{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;letter-spacing:-1px;
       background:linear-gradient(135deg,#f0cc60,#D4AF37,#a88520);
       -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
       filter:drop-shadow(0 0 12px rgba(212,175,55,.28));margin-bottom:4px}}
.sub{{font-size:.82rem;color:#6868a8;letter-spacing:.6px}}
</style></head>
<body>
  <div class="logo">💎 Rewards Hub</div>
  <div class="sub">مرحباً — {username}</div>
</body></html>
""", height=96)

    # ── balance card ─────────────────────────────
    components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:4px 0 8px}}
.card{{
    background:linear-gradient(135deg,rgba(26,26,48,.97),rgba(16,16,34,.98));
    border:1px solid #323260;border-radius:20px;padding:24px 28px;
    position:relative;overflow:hidden;text-align:center
}}
.glow-tr{{position:absolute;top:-60px;right:-60px;width:220px;height:220px;
          background:radial-gradient(circle,rgba(212,175,55,.11) 0%,transparent 65%);pointer-events:none}}
.glow-bl{{position:absolute;bottom:-50px;left:-50px;width:180px;height:180px;
          background:radial-gradient(circle,rgba(77,143,255,.07) 0%,transparent 65%);pointer-events:none}}
.user-pill{{
    display:inline-flex;align-items:center;gap:6px;
    background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.22);
    color:#D4AF37;font-size:.73rem;font-weight:600;letter-spacing:1.5px;
    padding:.28rem .85rem;border-radius:99px;margin-bottom:14px
}}
.lbl{{font-size:.68rem;color:#5a5a90;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px}}
.val{{
    font-family:'Syne',sans-serif;font-size:3.4rem;font-weight:800;
    background:linear-gradient(135deg,#f0cc60,#D4AF37);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
    line-height:1;filter:drop-shadow(0 2px 14px rgba(212,175,55,.38))
}}
.sub{{font-size:.82rem;color:#6868a8;margin-top:6px}}
.badges{{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:8px;margin-top:18px}}
.badge{{display:inline-flex;align-items:center;gap:5px;
        padding:.3rem .85rem;border-radius:99px;font-size:.7rem;font-weight:600;letter-spacing:.8px}}
.green{{background:rgba(46,204,138,.1);border:1px solid rgba(46,204,138,.25);color:#2ecc8a}}
.gold {{background:rgba(212,175,55,.1); border:1px solid rgba(212,175,55,.25); color:#D4AF37}}
.blue {{background:rgba(77,143,255,.1); border:1px solid rgba(77,143,255,.25); color:#4d8fff}}
</style></head>
<body>
<div class="card">
  <div class="glow-tr"></div><div class="glow-bl"></div>
  <div class="user-pill">👤 {username} · ID: {uid}</div>
  <div class="lbl">رصيدك الحالي</div>
  <div class="val">${balance:,.4f}</div>
  <div class="sub">USD · آخر تحديث: {age_str}</div>
  <div class="badges">
    <span class="badge green">✅ Verified Account</span>
    <span class="badge gold" >🔒 Secure Payments</span>
    <span class="badge blue" >🌐 Global Access</span>
  </div>
</div>
</body></html>
""", height=228)

    # refresh
    col_r, _ = st.columns([1, 3])
    with col_r:
        if st.button("↻  تحديث الرصيد", use_container_width=True):
            with st.spinner("جارٍ التحديث…"):
                fresh = fetch_balance(uid)
            if fresh:
                st.session_state.user_data    = fresh
                st.session_state.last_refresh = time.time()
                st.rerun()
            else:
                st.markdown(
                    '<div class="rh-alert error">⚠️ تعذّر الاتصال بالخادم.</div>',
                    unsafe_allow_html=True,
                )

    # ── tab bar ──────────────────────────────────
    cur = st.session_state.active_tab
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎁  العروض والمكافآت", use_container_width=True,
                     type="primary" if cur == "offers" else "secondary"):
            st.session_state.active_tab = "offers"
            st.rerun()
    with c2:
        if st.button("💸  السحب والتحويل", use_container_width=True,
                     type="primary" if cur == "withdraw" else "secondary"):
            st.session_state.active_tab = "withdraw"
            st.rerun()

    st.markdown('<hr class="rh-divider">', unsafe_allow_html=True)

    # ════════════════════════════════════════════
    #  TAB — OFFERS
    # ════════════════════════════════════════════
    if st.session_state.active_tab == "offers":

        st.markdown('<div class="sec-title">اختر منصة العروض</div>', unsafe_allow_html=True)

        # BitLabs
        bl = bitlabs_wall_url(uid)
        logger.info("🔗 BitLabs | uid=%s", uid)
        components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:6px 0}}
.card{{background:linear-gradient(135deg,rgba(22,22,42,.97),rgba(14,14,28,.98));
       border:1px solid #2a2a48;border-radius:18px;padding:20px 22px;
       transition:border-color .3s,transform .2s;position:relative;overflow:hidden}}
.card::before{{content:'';position:absolute;top:-40px;right:-40px;width:160px;height:160px;
               background:radial-gradient(circle,rgba(212,175,55,.08) 0%,transparent 65%);pointer-events:none}}
.card:hover{{border-color:#D4AF37;transform:translateY(-2px)}}
.prov{{display:inline-flex;align-items:center;gap:7px;
       font-family:'Syne',sans-serif;font-size:.73rem;font-weight:700;
       letter-spacing:2px;text-transform:uppercase;color:#D4AF37;
       background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.2);
       padding:4px 12px;border-radius:99px;margin-bottom:14px}}
.dot{{width:7px;height:7px;background:#2ecc8a;border-radius:50%;
      animation:p 2s ease infinite}}
@keyframes p{{0%,100%{{box-shadow:0 0 0 0 rgba(46,204,138,.45)}}
              50%{{box-shadow:0 0 0 5px transparent}}}}
.title{{font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:800;color:#eaeaf5;margin-bottom:4px}}
.sub{{font-size:.82rem;color:#5a5a90;margin-bottom:14px}}
.tags{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}}
.tag{{font-size:.7rem;font-weight:600;letter-spacing:.8px;padding:3px 10px;border-radius:99px;
      background:rgba(212,175,55,.06);border:1px solid rgba(212,175,55,.14);color:#b09030}}
.btn-o{{border-radius:13px;padding:2.5px;
        background:linear-gradient(135deg,#f0cc60,#D4AF37,#f0cc60);
        background-size:200%;animation:sh 2.5s ease infinite;
        box-shadow:0 4px 22px rgba(212,175,55,.28)}}
@keyframes sh{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
.btn{{display:flex;align-items:center;justify-content:center;gap:10px;
      padding:14px 20px;background:linear-gradient(135deg,#f2ca48 0%,#d09018 100%);
      border-radius:11px;border:none;cursor:pointer;width:100%;
      transition:filter .2s,transform .15s}}
.btn:hover{{filter:brightness(1.08);transform:translateY(-1px)}}
.btn:active{{transform:translateY(0);filter:brightness(.96)}}
.ico{{font-size:1.4rem;animation:b 2s ease infinite}}
@keyframes b{{0%,100%{{transform:translateY(0)}}40%{{transform:translateY(-5px)}}}}
.bt{{font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;color:#0a0a0f;letter-spacing:.3px}}
.bs{{font-family:'Syne',sans-serif;font-size:.62rem;font-weight:700;
     color:rgba(10,10,15,.5);letter-spacing:1.5px;text-transform:uppercase;margin-top:1px}}
</style></head>
<body>
<div class="card">
  <div class="prov"><div class="dot"></div>BitLabs</div>
  <div class="title">الاستبيانات المدفوعة</div>
  <div class="sub">استبيانات عالية الجودة · مدفوعات فورية · uid: {uid}</div>
  <div class="tags">
    <span class="tag">📋 Surveys</span>
    <span class="tag">⚡ فوري</span>
    <span class="tag">🌍 عالمي</span>
  </div>
  <div class="btn-o">
    <button class="btn" onclick="window.open('{bl}','_blank')">
      <span class="ico">🎁</span>
      <div><div class="bt">ابدأ مع BitLabs الآن</div><div class="bs">Open Offer Wall</div></div>
    </button>
  </div>
</div>
</body></html>
""", height=232)

        # AdGem
        ag = adgem_wall_url(uid)
        logger.info("🔗 AdGem | uid=%s | url=%s", uid, ag)
        components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:6px 0}}
.card{{background:linear-gradient(135deg,rgba(14,18,38,.97),rgba(10,12,28,.98));
       border:1px solid #202244;border-radius:18px;padding:20px 22px;
       transition:border-color .3s,transform .2s;position:relative;overflow:hidden}}
.card::before{{content:'';position:absolute;top:-40px;right:-40px;width:160px;height:160px;
               background:radial-gradient(circle,rgba(77,143,255,.09) 0%,transparent 65%);pointer-events:none}}
.card:hover{{border-color:#4d8fff;transform:translateY(-2px)}}
.prov{{display:inline-flex;align-items:center;gap:7px;
       font-family:'Syne',sans-serif;font-size:.73rem;font-weight:700;
       letter-spacing:2px;text-transform:uppercase;color:#4d8fff;
       background:rgba(77,143,255,.08);border:1px solid rgba(77,143,255,.2);
       padding:4px 12px;border-radius:99px;margin-bottom:14px}}
.dot{{width:7px;height:7px;background:#4d8fff;border-radius:50%;
      animation:p 2.5s ease infinite}}
@keyframes p{{0%,100%{{box-shadow:0 0 0 0 rgba(77,143,255,.45)}}
              50%{{box-shadow:0 0 0 5px transparent}}}}
.title{{font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:800;color:#eaeaf5;margin-bottom:4px}}
.sub{{font-size:.82rem;color:#4a5080;margin-bottom:14px}}
.tags{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}}
.tag{{font-size:.7rem;font-weight:600;letter-spacing:.8px;padding:3px 10px;border-radius:99px;
      background:rgba(77,143,255,.06);border:1px solid rgba(77,143,255,.14);color:#5068a0}}
.btn-o{{border-radius:13px;padding:2.5px;
        background:linear-gradient(135deg,#6aabff,#4d8fff,#6aabff);
        background-size:200%;animation:sh 2.5s ease infinite;
        box-shadow:0 4px 22px rgba(77,143,255,.22)}}
@keyframes sh{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
.btn{{display:flex;align-items:center;justify-content:center;gap:10px;
      padding:14px 20px;background:linear-gradient(135deg,#5a9aff 0%,#2c5fcc 100%);
      border-radius:11px;border:none;cursor:pointer;width:100%;
      transition:filter .2s,transform .15s}}
.btn:hover{{filter:brightness(1.08);transform:translateY(-1px)}}
.btn:active{{transform:translateY(0);filter:brightness(.96)}}
.bt{{font-family:'Syne',sans-serif;font-size:1rem;font-weight:800;color:#fff;letter-spacing:.3px}}
.bs{{font-family:'Syne',sans-serif;font-size:.62rem;font-weight:700;
     color:rgba(255,255,255,.5);letter-spacing:1.5px;text-transform:uppercase;margin-top:1px}}
</style></head>
<body>
<div class="card">
  <div class="prov"><div class="dot"></div>AdGem</div>
  <div class="title">العروض والتطبيقات والمهام</div>
  <div class="sub">تنزيل تطبيقات · مهام مدفوعة · player_id: {uid}</div>
  <div class="tags">
    <span class="tag">📱 Offerwall</span>
    <span class="tag">🎮 Tasks</span>
    <span class="tag">🏆 Contests</span>
  </div>
  <div class="btn-o">
    <button class="btn" onclick="window.open('{ag}','_blank')">
      <span style="font-size:1.4rem">🚀</span>
      <div><div class="bt">افتح AdGem الآن</div><div class="bs">Explore Offers</div></div>
    </button>
  </div>
</div>
</body></html>
""", height=228)

        st.markdown(
            '<div class="rh-alert warn" style="margin-top:.4rem">'
            '💡 بعد إتمام أي عرض اضغط <strong>↻ تحديث الرصيد</strong> لرؤية أرباحك فوراً.'
            '</div>',
            unsafe_allow_html=True,
        )

    # ════════════════════════════════════════════
    #  TAB — WITHDRAW
    # ════════════════════════════════════════════
    else:
        st.markdown('<div class="sec-title">طرق السحب المتاحة</div>', unsafe_allow_html=True)

        components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:4px 0 8px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}}
.m{{background:linear-gradient(135deg,rgba(20,20,36,.97),rgba(13,13,25,.98));
    border:1px solid #242440;border-radius:14px;padding:18px 16px;
    text-align:center;transition:border-color .3s,transform .2s;position:relative;overflow:hidden}}
.m:hover{{border-color:#D4AF37;transform:translateY(-2px)}}
.icon{{font-size:2rem;margin-bottom:8px}}
.name{{font-family:'Syne',sans-serif;font-size:.9rem;font-weight:800;color:#eaeaf5;margin-bottom:3px}}
.msub{{font-size:.72rem;color:#5a5a90;letter-spacing:.5px}}
.pill{{display:inline-block;margin-top:8px;font-size:.65rem;font-weight:700;
       letter-spacing:1px;padding:2px 10px;border-radius:99px}}
.soon{{background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.2);color:#a08828}}
.min{{background:rgba(212,175,55,.05);border:1px solid rgba(212,175,55,.14);
      border-radius:10px;padding:12px 16px;font-size:.8rem;color:#7a6020;
      display:flex;align-items:center;gap:8px}}
.min strong{{color:#D4AF37}}
</style></head>
<body>
<div class="grid">
  <div class="m"><div class="icon">💙</div>
    <div class="name">PayPal</div><div class="msub">دولي · سريع</div>
    <div class="pill soon">قريباً</div></div>
  <div class="m"><div class="icon">📱</div>
    <div class="name">Vodafone Cash</div><div class="msub">مصر · فوري</div>
    <div class="pill soon">قريباً</div></div>
  <div class="m"><div class="icon">₿</div>
    <div class="name">Crypto (USDT)</div><div class="msub">TRC-20 · BEP-20</div>
    <div class="pill soon">قريباً</div></div>
  <div class="m"><div class="icon">🎮</div>
    <div class="name">Gift Cards</div><div class="msub">Amazon · Google Play</div>
    <div class="pill soon">قريباً</div></div>
</div>
<div class="min">
  💡 الحد الأدنى للسحب: <strong>$5.00</strong> ·
  رصيدك الحالي: <strong>${balance:,.4f}</strong>
</div>
</body></html>
""", height=295)

        st.markdown(
            '<div class="rh-alert info">'
            '🔔 سيتم تفعيل السحب قريباً. ستصلك إشعار فور الإتاحة.'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── footer ───────────────────────────────────
    st.markdown("""
<div class="rh-footer">
  <div style="margin-bottom:.5rem">© 2025 Rewards Hub · All rights reserved</div>
  <a href="#" onclick="document.getElementById('tm').classList.add('active');return false;">
      📄 الشروط والأحكام
  </a>
  &nbsp;·&nbsp;
  <a href="mailto:support@rewardshub.com">✉️ الدعم</a>
</div>

<div id="tm" class="modal-overlay"
     onclick="if(event.target===this)this.classList.remove('active')">
  <div class="modal-box">
    <button class="modal-close"
            onclick="document.getElementById('tm').classList.remove('active')">✕</button>
    <div class="modal-h1">📄 الشروط والأحكام</div>
    <div class="modal-section"><h3>١. قبول الشروط</h3>
      <p>باستخدامك Rewards Hub توافق على الالتزام بهذه الشروط بالكامل.</p></div>
    <div class="modal-section"><h3>٢. أهلية الاستخدام</h3>
      <p>يجب أن يكون عمرك 18 عاماً أو أكثر. المنصة غير متاحة حيث يحظر القانون ذلك.</p></div>
    <div class="modal-section"><h3>٣. كسب المكافآت</h3>
      <p>تُحتسب المكافآت تلقائياً عبر شركاء العروض. نحتفظ بالحق في مراجعة أي معاملة مشبوهة.</p></div>
    <div class="modal-section"><h3>٤. قواعد الاستخدام</h3>
      <p>يُحظر استخدام أدوات الأتمتة أو الحسابات الوهمية. المخالفة تؤدي لإيقاف الحساب فوراً.</p></div>
    <div class="modal-section"><h3>٥. الخصوصية</h3>
      <p>نجمع الحد الأدنى من البيانات اللازمة للخدمة. لا نبيع بياناتك لأي طرف ثالث.</p></div>
    <div class="modal-section"><h3>٦. إخلاء المسؤولية</h3>
      <p>Rewards Hub وسيط بين المستخدمين وشركاء العروض. لا نتحمل مسؤولية تأخر الشركاء.</p></div>
    <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid #242440;
                font-size:.74rem;color:#404070;text-align:center">
        آخر تحديث: يناير 2025 · Rewards Hub
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # invisible logout
    if st.button("خروج", key="__logout__"):
        for _k, _v in DEFAULTS.items():
            st.session_state[_k] = _v
        st.rerun()


# ══════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════
if st.session_state.logged_in and st.session_state.user_data:
    page_dashboard()
else:
    page_login()
