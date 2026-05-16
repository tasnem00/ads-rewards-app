"""
app.py — Rewards Hub  v5 · Guest-First Edition
════════════════════════════════════════════════
• الزائر يرى كل شيء فوراً بدون تسجيل دخول
• تسجيل الدخول مطلوب فقط عند الضغط على أي عرض أو السحب
• AdGem Postback Key: hgda9gcjc891dljf0n9lha13
• AdGem App ID: 32570

pip install streamlit requests
streamlit run app.py
"""

import logging, time, random
import requests
import streamlit as st
import streamlit.components.v1 as components

# ── logging ───────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("rewards_hub")

# ── config ────────────────────────────────────────────
RAILWAY_URL       = "https://web-production-864fec.up.railway.app"   # ← تم التحديث
BITLABS_TOKEN     = "DCDEC791-3E5B-484D-B11C-3404631079D0"
ADGEM_APP_ID      = "32570"
ADGEM_POSTBACK    = "hgda9gcjc891dljf0n9lha13"

def bl_url(uid):
    return f"https://web.bitlabs.ai/?token={BITLABS_TOKEN}&uid={uid}"

def ag_url(uid):
    return f"https://adunits.adgem.com/wall?appid={ADGEM_APP_ID}&player_id={uid}"

HEADERS = {
    "Content-Type":  "application/json",
    "Accept":        "application/json",
    "User-Agent":    "RewardsHub/5.0",
    "X-App-Source": "streamlit-frontend",
}

def _get(path: str, **kw):
    return requests.get(f"{RAILWAY_URL}{path}", headers=HEADERS, timeout=10, **kw)

def _post(path: str, payload: dict):
    return requests.post(f"{RAILWAY_URL}{path}", headers=HEADERS,
                         json=payload, timeout=10)

def diagnose_server() -> str:
    lines = []
    tests = [
        ("GET /",              lambda: _get("/")),
        ("GET /users",         lambda: _get("/users")),
        ("GET /users/1",       lambda: _get("/users/1")),
        ("GET /docs",          lambda: _get("/docs")),
        ("GET /openapi.json",  lambda: _get("/openapi.json")),
    ]
    for name, fn in tests:
        try:
            r = fn()
            snippet = r.text[:80].replace("\n"," ")
            lines.append(f"[{r.status_code}] {name}  →  {snippet}")
        except Exception as e:
            lines.append(f"[ERR] {name}  →  {e}")
    return "\n".join(lines)

def fetch_or_create(username: str):
    username = username.strip()
    logger.info("🔑 auth attempt: %s", username)

    # ── المرحلة 1: by_username ──────────────────────
    try:
        r = _get(f"/users/by_username/{username}")
        logger.info("  /by_username → %s", r.status_code)
        if r.status_code == 200:
            d = r.json()
            logger.info("✅ found by_username | bal=%.4f", d.get("balance", 0))
            return d
    except Exception as e:
        logger.warning("  by_username err: %s", e)

    # ── المرحلة 2: by_email ─────────────────────────
    if "@" in username:
        try:
            r = _get(f"/users/by_email/{username}")
            logger.info("  /by_email → %s", r.status_code)
            if r.status_code == 200:
                d = r.json()
                logger.info("✅ found by_email | bal=%.4f", d.get("balance", 0))
                return d
        except Exception as e:
            logger.warning("  by_email err: %s", e)

    # ── المرحلة 3: query param ?username= ───────────
    try:
        r = _get(f"/users", params={"username": username})
        logger.info("  /users?username → %s", r.status_code)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                d = data[0]
                logger.info("✅ found by query | bal=%.4f", d.get("balance", 0))
                return d
            if isinstance(data, dict) and data.get("id"):
                logger.info("✅ found by query dict | bal=%.4f", data.get("balance", 0))
                return data
    except Exception as e:
        logger.warning("  query err: %s", e)

    # ── المرحلة 4: إنشاء حساب جديد ─────────────────
    payload = {"username": username}
    if "@" in username:
        payload["email"] = username

    try:
        r = _post("/users", payload)
        logger.info("  POST /users → %s | body: %s", r.status_code, r.text[:200])
        if r.status_code in (200, 201):
            d = r.json()
            logger.info("🆕 created | id=%s", d.get("id"))
            return d
        if r.status_code == 409:
            logger.info("  409 conflict — user exists, trying GET /users/by_username/")
            r2 = _get(f"/users/by_username/{username}")
            if r2.status_code == 200:
                return r2.json()
        logger.error("  POST failed %s: %s", r.status_code, r.text[:300])
    except Exception as e:
        logger.error("  POST err: %s", e)

    return None


def refresh_balance(uid):
    try:
        r = _get(f"/users/{uid}")
        if r.status_code == 200:
            d = r.json()
            logger.info("🔄 uid=%s bal=%.4f", uid, d.get("balance", 0))
            return d
        logger.warning("refresh_balance → %s", r.status_code)
    except Exception as e:
        logger.error("❌ refresh: %s", e)
    return None

# ── page setup ────────────────────────────────────────
st.set_page_config(page_title="Rewards Hub", page_icon="💎", layout="centered")

# ── session defaults ──────────────────────────────────
for k, v in {
    "logged_in":     False,
    "user_data":     None,
    "last_refresh":  0,
    "login_err":     "",
    "show_login":    False,
    "login_reason":  "",
    "tab":           "offers",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ════════════════════════════════════════════════════
#  GLOBAL CSS
# ════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
  --ink:     #09090f;
  --glass:   rgba(255,255,255,.032);
  --glass2:  rgba(255,255,255,.055);
  --rim:     rgba(255,255,255,.07);
  --rim2:    rgba(255,255,255,.13);
  --gold:    #c9a84c;
  --gold2:   #e8c96a;
  --gold3:   #f5dfa0;
  --golddim: #7a6128;
  --text:    #e8e8f0;
  --text2:   #9090b8;
  --text3:   #5a5a88;
  --green:   #3ecf8e;
  --blue:    #5b8ef0;
  --r:       20px;
  --rsm:     12px;
}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"] {
  background: #09090f !important;
  font-family: 'Outfit', sans-serif;
  color: var(--text);
}
[data-testid="stHeader"]      { background: transparent !important; }
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"]  { display: none !important; }
[data-testid="block-container"] { padding-top: 0 !important; }

[data-testid="stAppViewContainer"]::before {
  content: ''; position: fixed; inset: 0; z-index: -2;
  background:
    radial-gradient(ellipse 900px 600px at 10% 20%, rgba(180,140,40,.11) 0%, transparent 55%),
    radial-gradient(ellipse 700px 500px at 90% 80%, rgba(60,100,200,.09) 0%, transparent 55%),
    radial-gradient(ellipse 500px 400px at 50% 50%, rgba(120,80,200,.05) 0%, transparent 60%),
    #09090f;
  animation: meshMove 14s ease-in-out infinite alternate;
}
@keyframes meshMove {
  0%   { filter: hue-rotate(0deg)  brightness(1);    }
  50%  { filter: hue-rotate(8deg)  brightness(1.04); }
  100% { filter: hue-rotate(-5deg) brightness(.97);  }
}
[data-testid="stAppViewContainer"]::after {
  content: ''; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");
  background-size: 180px 180px; opacity: .6;
}

[data-testid="stTextInput"] input {
  background: var(--glass2) !important;
  border: 1px solid var(--rim) !important;
  border-radius: var(--rsm) !important;
  color: var(--text) !important;
  font-family: 'Outfit', sans-serif !important;
  font-size: .95rem !important;
  padding: .7rem 1rem !important;
  transition: border-color .25s, box-shadow .25s !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: rgba(201,168,76,.45) !important;
  box-shadow: 0 0 0 3px rgba(201,168,76,.08) !important;
}
[data-testid="stTextInput"] label {
  color: var(--text3) !important; font-size: .7rem !important;
  letter-spacing: 2.5px !important; text-transform: uppercase !important;
  font-family: 'DM Mono', monospace !important;
}
[data-testid="stButton"] > button {
  background: var(--glass) !important;
  border: 1px solid var(--rim) !important;
  border-radius: var(--rsm) !important;
  color: var(--text2) !important;
  font-family: 'Outfit', sans-serif !important;
  font-weight: 500 !important; font-size: .88rem !important;
  padding: .6rem 1.2rem !important;
  transition: all .25s !important; letter-spacing: .3px !important;
}
[data-testid="stButton"] > button:hover {
  border-color: var(--gold) !important; color: var(--gold) !important;
  background: rgba(201,168,76,.06) !important;
  box-shadow: 0 0 18px rgba(201,168,76,.12) !important;
}

.div { border: none; border-top: 1px solid var(--rim); margin: 1.4rem 0; }

.alert { border-radius: var(--rsm); padding: .8rem 1rem; font-size: .83rem;
         margin: .5rem 0; display: flex; gap: .6rem; align-items: flex-start; }
.alert.err  { background:rgba(220,60,60,.07);  border:1px solid rgba(220,60,60,.2);  color:#f08080; }
.alert.warn { background:rgba(201,168,76,.07); border:1px solid rgba(201,168,76,.18);color:var(--gold); }
.alert.info { background:rgba(91,142,240,.07); border:1px solid rgba(91,142,240,.18);color:var(--blue); }
.alert.ok   { background:rgba(62,207,142,.07); border:1px solid rgba(62,207,142,.18);color:var(--green); }

.foot { text-align:center; padding:2rem 1rem; font-size:.75rem; color:var(--text3);
        border-top:1px solid var(--rim); margin-top:2rem; }
.foot a { color:var(--golddim); text-decoration:none; transition:color .2s; }
.foot a:hover { color:var(--gold); }

.modal { display:none; position:fixed; inset:0; z-index:9998;
         background:rgba(5,5,10,.92); backdrop-filter:blur(10px);
         align-items:flex-start; justify-content:center;
         padding:2rem 1rem; overflow-y:auto; }
.modal.on { display:flex; }
.mbox { background:rgba(16,16,26,.97); border:1px solid var(--rim2);
        border-radius:var(--r); padding:2.2rem; max-width:580px; width:100%;
        position:relative; animation:mIn .3s cubic-bezier(.22,1,.36,1); }
@keyframes mIn { from{opacity:0;transform:translateY(28px)} to{opacity:1;transform:translateY(0)} }
.mx { position:absolute; top:1rem; right:1rem; background:var(--glass2);
      border:1px solid var(--rim); color:var(--text3); width:30px; height:30px;
      border-radius:50%; cursor:pointer; display:flex; align-items:center;
      justify-content:center; font-size:.9rem; transition:all .2s; }
.mx:hover { background:var(--rim); color:var(--gold); }
.mh { font-family:'Cormorant Garamond',serif; font-size:1.6rem;
      font-weight:400; color:var(--gold); margin-bottom:1.4rem; }
.ms { margin-bottom:1.1rem; }
.ms h3 { font-family:'DM Mono',monospace; font-size:.66rem; letter-spacing:2px;
         text-transform:uppercase; color:var(--text3); margin-bottom:.4rem; }
.ms p  { font-size:.87rem; color:var(--text2); line-height:1.8; }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════
#  HELPER: LOGIN MODAL
# ════════════════════════════════════════════════════
def maybe_show_login_modal():
    if not st.session_state.show_login:
        return

    reason = st.session_state.login_reason or "تسجيل الدخول مطلوب لمتابعة."

    components.html(f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=DM+Mono:wght@400&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;margin:0;padding:0}}
.overlay{{
  position:fixed;inset:0;z-index:9999;
  background:rgba(5,5,12,.93);backdrop-filter:blur(12px);
  display:flex;align-items:center;justify-content:center;padding:1rem;
}}
.box{{
  background:rgba(14,14,24,.98);
  border:1px solid rgba(255,255,255,.1);
  border-radius:22px;padding:2.4rem 2.6rem;
  max-width:440px;width:100%;position:relative;
  animation:up .35s cubic-bezier(.22,1,.36,1);
  box-shadow:0 32px 80px rgba(0,0,0,.6);
}}
@keyframes up{{from{{opacity:0;transform:translateY(30px)}}to{{opacity:1;transform:translateY(0)}}}}
.box::before{{
  content:'';position:absolute;top:0;left:15%;right:15%;height:1px;
  background:linear-gradient(90deg,transparent,rgba(201,168,76,.45),transparent);
}}
.icon{{font-size:2.4rem;text-align:center;margin-bottom:14px;
       filter:drop-shadow(0 0 16px rgba(201,168,76,.4));}}
.title{{font-family:'Cormorant Garamond',serif;font-size:1.7rem;font-weight:300;
        color:#e8e8f0;text-align:center;margin-bottom:6px;letter-spacing:.3px;}}
.sub{{font-family:'Outfit',sans-serif;font-size:.82rem;color:#5a5a88;
      text-align:center;margin-bottom:22px;line-height:1.6;}}
.reason{{
  background:rgba(201,168,76,.07);border:1px solid rgba(201,168,76,.15);
  border-radius:10px;padding:10px 14px;
  font-family:'DM Mono',monospace;font-size:.68rem;
  letter-spacing:1.5px;text-transform:uppercase;
  color:#c9a84c;text-align:center;margin-bottom:20px;
}}
</style></head>
<body>
<div class="overlay" id="ov">
  <div class="box">
    <div class="icon">🔐</div>
    <div class="title">Create Free Account</div>
    <div class="sub">Sign in to track your earnings, complete offers, and withdraw your rewards.</div>
    <div class="reason">{reason}</div>
  </div>
</div>
</body></html>
""", height=320)

    st.markdown('<div style="max-width:440px;margin:0 auto;margin-top:-12px">', unsafe_allow_html=True)

    col_x, col_main = st.columns([1, 8])
    with col_x:
        if st.button("✕", key="close_login_modal"):
            st.session_state.show_login   = False
            st.session_state.login_reason = ""
            st.rerun()

    uval = st.text_input("Username or Email", placeholder="your@email.com",
                         key="modal_username", label_visibility="collapsed")

    if st.session_state.login_err:
        st.markdown(f'<div class="alert err">⚠ {st.session_state.login_err}</div>',
                    unsafe_allow_html=True)

    if st.button("Enter Rewards Hub →", use_container_width=True, key="modal_login_btn"):
        val = (uval or "").strip()
        if not val or len(val) < 3:
            st.session_state.login_err = "Please enter at least 3 characters."
            st.rerun()
        else:
            with st.spinner("Authenticating…"):
                data = fetch_or_create(val)
            if data:
                st.session_state.update(
                    logged_in=True, user_data=data,
                    last_refresh=time.time(),
                    login_err="", show_login=False, login_reason="")
                st.rerun()
            else:
                st.session_state.login_err = (
                    "⚠ Could not connect to server. "
                    "Make sure the Railway backend is running — "
                    "check Railway → View Logs for details."
                )
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════
#  NAVBAR
# ════════════════════════════════════════════════════
def render_navbar():
    user = st.session_state.user_data
    logged = st.session_state.logged_in

    if logged and user:
        uname   = user.get("username", "—")
        balance = user.get("balance",  0.0)
        right_html = f"""
        <div class="nav-right">
          <div class="bal-chip">
            <span class="bal-icon">◈</span>
            <span class="bal-val">${balance:,.3f}</span>
          </div>
          <div class="user-chip">
            <div class="avatar">{uname[0].upper()}</div>
            <span class="uname">{uname}</span>
          </div>
        </div>"""
    else:
        right_html = """
        <div class="nav-right">
          <div class="guest-pill">👤 Guest Mode</div>
        </div>"""

    components.html(f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=DM+Mono:wght@400&family=Outfit:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:24px 0 14px;}}
nav{{
  display:flex;align-items:center;justify-content:space-between;
  border-bottom:1px solid rgba(255,255,255,.06);padding-bottom:14px;
}}
.brand{{font-family:'Cormorant Garamond',serif;font-size:1.55rem;
        font-weight:300;color:#e8e8f0;letter-spacing:.5px;}}
.brand em{{font-style:italic;color:#c9a84c;}}
.nav-right{{display:flex;align-items:center;gap:10px;}}
.bal-chip{{
  display:flex;align-items:center;gap:6px;
  background:rgba(201,168,76,.08);border:1px solid rgba(201,168,76,.18);
  border-radius:99px;padding:5px 13px;
}}
.bal-icon{{color:#c9a84c;font-size:.9rem;}}
.bal-val{{font-family:'DM Mono',monospace;font-size:.82rem;color:#c9a84c;letter-spacing:.5px;}}
.user-chip{{
  display:flex;align-items:center;gap:7px;
  background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);
  border-radius:99px;padding:5px 13px 5px 7px;
}}
.avatar{{width:24px;height:24px;border-radius:50%;
         background:linear-gradient(135deg,#c9a84c,#7a6128);
         display:flex;align-items:center;justify-content:center;
         font-size:.75rem;font-weight:600;color:#0a0a0e;
         font-family:'Outfit',sans-serif;}}
.uname{{font-family:'Outfit',sans-serif;font-size:.8rem;color:#9090b8;}}
.guest-pill{{
  font-family:'DM Mono',monospace;font-size:.64rem;letter-spacing:2px;
  text-transform:uppercase;color:#3a3a60;
  background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);
  border-radius:99px;padding:5px 14px;
}}
</style></head>
<body>
<nav>
  <div class="brand">Rewards <em>Hub</em></div>
  {right_html}
</nav>
</body></html>
""", height=80)


# ════════════════════════════════════════════════════
#  HERO SECTION
# ════════════════════════════════════════════════════
def render_hero():
    components.html("""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,600;1,400&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:transparent;padding:36px 0 28px;text-align:center;}
.gem{
  display:inline-block;font-size:3rem;margin-bottom:16px;
  filter:drop-shadow(0 0 28px rgba(201,168,76,.55));
  animation:float 4s ease-in-out infinite;
}
@keyframes float{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-10px) rotate(2deg)}}
.headline{
  font-family:'Cormorant Garamond',serif;
  font-size:2.8rem;font-weight:300;
  color:#e8e8f0;letter-spacing:-1px;margin-bottom:6px;
  line-height:1.1;
}
.headline em{font-style:italic;color:#c9a84c;}
.sub{
  font-family:'DM Mono',monospace;font-size:.65rem;
  letter-spacing:4px;text-transform:uppercase;
  color:#4a4a78;margin-bottom:28px;
}
.stats{display:flex;align-items:center;justify-content:center;gap:32px;flex-wrap:wrap;}
.stat .n{
  font-family:'Cormorant Garamond',serif;font-size:2rem;
  font-weight:300;color:#c9a84c;display:block;line-height:1;
}
.stat .l{
  font-family:'DM Mono',monospace;font-size:.58rem;
  letter-spacing:2px;text-transform:uppercase;color:#3a3a60;
  margin-top:4px;display:block;
}
.sep{width:1px;height:40px;background:rgba(255,255,255,.07);}
</style></head>
<body>
  <div class="gem">💎</div>
  <div class="headline">Complete Offers,<br>Earn <em>Real Money</em></div>
  <div class="sub">Surveys · Apps · Tasks · Contests</div>
  <div class="stats">
    <div class="stat"><span class="n">2M+</span><span class="l">Active Users</span></div>
    <div class="sep"></div>
    <div class="stat"><span class="n">$8M+</span><span class="l">Paid Out</span></div>
    <div class="sep"></div>
    <div class="stat"><span class="n">150+</span><span class="l">Offer Types</span></div>
    <div class="sep"></div>
    <div class="stat"><span class="n">4.8★</span><span class="l">User Rating</span></div>
  </div>
</body></html>
""", height=240)


# ════════════════════════════════════════════════════
#  OFFER CARDS
# ════════════════════════════════════════════════════
def render_offer_cards():
    logged = st.session_state.logged_in
    uid    = st.session_state.user_data.get("id", 0) if logged else 0

    _bl = bl_url(uid) if logged else "#"
    _ag = ag_url(uid) if logged else "#"

    onclick_bl = f"window.open('{_bl}','_blank')" if logged else \
        "window.__triggerLogin('Sign in to start earning with BitLabs')"
    onclick_ag = f"window.open('{_ag}','_blank')" if logged else \
        "window.__triggerLogin('Sign in to start earning with AdGem')"

    lock_overlay = "" if logged else """
    <div style="position:absolute;inset:0;border-radius:20px;z-index:2;
                display:flex;align-items:center;justify-content:center;
                background:rgba(9,9,15,.65);backdrop-filter:blur(3px)">
      <div style="text-align:center;">
        <div style="font-size:1.8rem;margin-bottom:8px">🔒</div>
        <div style="font-family:'DM Mono',monospace;font-size:.62rem;
                    letter-spacing:2px;text-transform:uppercase;color:#5a5a88">
          Sign in to unlock
        </div>
      </div>
    </div>"""

    components.html(f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=DM+Mono:wght@400&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:4px 0;}}
.wrap{{display:flex;flex-direction:column;gap:12px;}}
.card{{
  background:rgba(255,255,255,.028);
  border:1px solid rgba(255,255,255,.07);
  border-radius:20px;padding:24px 26px;
  position:relative;overflow:hidden;
  backdrop-filter:blur(16px);
  transition:border-color .3s,transform .25s,box-shadow .3s;
  cursor:{'pointer' if logged else 'default'};
}}
.card::before{{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(201,168,76,.25),transparent);
}}
.card.gold:hover{{border-color:rgba(201,168,76,{'0.4' if logged else '0.1'});
  transform:translateY({'-3px' if logged else '0'});
  box-shadow:{'0 16px 48px rgba(0,0,0,.35)' if logged else 'none'};}}
.card.blue:hover{{border-color:rgba(91,142,240,{'0.4' if logged else '0.1'});
  transform:translateY({'-3px' if logged else '0'});}}
.glow-gold{{position:absolute;top:-60px;right:-60px;width:200px;height:200px;
            background:radial-gradient(circle,rgba(201,168,76,.08) 0%,transparent 65%);pointer-events:none;}}
.glow-blue{{position:absolute;top:-60px;right:-60px;width:200px;height:200px;
            background:radial-gradient(circle,rgba(91,142,240,.08) 0%,transparent 65%);pointer-events:none;}}
.hrow{{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;}}
.provider{{display:inline-flex;align-items:center;gap:7px;
           font-family:'DM Mono',monospace;font-size:.64rem;
           letter-spacing:2.5px;text-transform:uppercase;
           padding:5px 13px;border-radius:99px;}}
.provider.gold{{color:#c9a84c;background:rgba(201,168,76,.07);border:1px solid rgba(201,168,76,.18);}}
.provider.blue{{color:#5b8ef0;background:rgba(91,142,240,.07);border:1px solid rgba(91,142,240,.2);}}
.dot{{width:6px;height:6px;border-radius:50%;}}
.dot.g{{background:#3ecf8e;animation:pg 2s ease infinite;}}
.dot.b{{background:#5b8ef0;animation:pb 2.5s ease infinite;}}
@keyframes pg{{0%,100%{{box-shadow:0 0 0 0 rgba(62,207,142,.5)}}50%{{box-shadow:0 0 0 6px rgba(62,207,142,0)}}}}
@keyframes pb{{0%,100%{{box-shadow:0 0 0 0 rgba(91,142,240,.5)}}50%{{box-shadow:0 0 0 6px rgba(91,142,240,0)}}}}
.title{{font-family:'Cormorant Garamond',serif;font-size:1.35rem;font-weight:300;
        color:#e8e8f0;margin-bottom:5px;letter-spacing:.3px;}}
.desc{{font-family:'Outfit',sans-serif;font-size:.8rem;color:#5a5a88;margin-bottom:16px;}}
.tags{{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:18px;}}
.tag{{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:1.5px;
      text-transform:uppercase;padding:4px 11px;border-radius:6px;
      background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);color:#5a5a88;}}
.cta{{display:flex;align-items:center;justify-content:space-between;
      border-radius:13px;padding:15px 20px;cursor:pointer;
      transition:all .25s;border:none;width:100%;}}
.cta.gold{{background:linear-gradient(135deg,rgba(201,168,76,.1),rgba(201,168,76,.05));
           border:1px solid rgba(201,168,76,.2);}}
.cta.gold:hover{{background:linear-gradient(135deg,rgba(201,168,76,.18),rgba(201,168,76,.09));
                 border-color:rgba(201,168,76,.38);}}
.cta.blue{{background:linear-gradient(135deg,rgba(91,142,240,.1),rgba(91,142,240,.05));
           border:1px solid rgba(91,142,240,.2);}}
.cta.blue:hover{{background:linear-gradient(135deg,rgba(91,142,240,.18),rgba(91,142,240,.09));
                 border-color:rgba(91,142,240,.38);}}
.cta-l{{display:flex;align-items:center;gap:12px;}}
.cta-ico{{font-size:1.4rem;}}
.ct{{font-family:'Outfit',sans-serif;font-size:.93rem;font-weight:600;letter-spacing:.3px;}}
.ct.gold{{color:#c9a84c;}} .ct.blue{{color:#5b8ef0;}}
.cs{{font-family:'DM Mono',monospace;font-size:.57rem;letter-spacing:2px;
     text-transform:uppercase;margin-top:2px;}}
.cs.gold{{color:#7a6128;}} .cs.blue{{color:#2a4888;}}
.arr{{font-size:1.1rem;transition:transform .25s;}}
.arr.gold{{color:rgba(201,168,76,.45);}} .arr.blue{{color:rgba(91,142,240,.45);}}
.cta:hover .arr{{transform:translateX(4px);}}
</style>
<script>
window.__triggerLogin = function(reason){{
  window.parent.postMessage({{type:'login_request',reason:reason}},'*');
}};
</script>
</head>
<body>
<div class="wrap">
  <div class="card gold">
    <div class="glow-gold"></div>
    {lock_overlay}
    <div class="hrow">
      <div class="provider gold"><div class="dot g"></div>BitLabs</div>
    </div>
    <div class="title">Paid Surveys & Research</div>
    <div class="desc">High-paying market research surveys · Results credited within minutes</div>
    <div class="tags">
      <span class="tag">📋 Surveys</span>
      <span class="tag">⚡ Instant</span>
      <span class="tag">🌍 Worldwide</span>
      <span class="tag">💰 High CPL</span>
    </div>
    <button class="cta gold" onclick="{onclick_bl}">
      <div class="cta-l">
        <span class="cta-ico">🎯</span>
        <div>
          <div class="ct gold">{'Start Earning — BitLabs' if logged else 'Sign In to Unlock'}</div>
          <div class="cs gold">{'Open Offer Wall · uid ' + str(uid) if logged else 'Free Account Required'}</div>
        </div>
      </div>
      <div class="arr gold">→</div>
    </button>
  </div>

  <div class="card blue">
    <div class="glow-blue"></div>
    {lock_overlay}
    <div class="hrow">
      <div class="provider blue"><div class="dot b"></div>AdGem</div>
    </div>
    <div class="title">Apps, Tasks & Contests</div>
    <div class="desc">Install apps · Complete missions · Daily contests · Prize draws</div>
    <div class="tags">
      <span class="tag">📱 App Installs</span>
      <span class="tag">🎮 Missions</span>
      <span class="tag">🏆 Contests</span>
      <span class="tag">🎁 Daily Offers</span>
    </div>
    <button class="cta blue" onclick="{onclick_ag}">
      <div class="cta-l">
        <span class="cta-ico">🚀</span>
        <div>
          <div class="ct blue">{'Start Earning — AdGem' if logged else 'Sign In to Unlock'}</div>
          <div class="cs blue">{'App ID {ADGEM_APP_ID} · player ' + str(uid) if logged else 'Free Account Required'}</div>
        </div>
      </div>
      <div class="arr blue">→</div>
    </button>
  </div>
</div>
</body></html>
""", height=560)


# ════════════════════════════════════════════════════
#  BALANCE SECTION
# ════════════════════════════════════════════════════
def render_balance_section():
    user    = st.session_state.user_data
    uid     = user.get("id",       1)
    uname   = user.get("username", "—")
    balance = user.get("balance",  0.0)

    if st.session_state.last_refresh:
        age = int(time.time() - st.session_state.last_refresh)
        age_s = f"{age}s ago" if age < 60 else f"{age//60}m ago"
    else:
        age_s = "—"

    components.html(f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&family=DM+Mono:wght@300;400&family=Outfit:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:4px 0 8px;}}
.card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);
       border-radius:22px;padding:28px 32px 24px;position:relative;overflow:hidden;backdrop-filter:blur(20px);}}
.card::before{{content:'';position:absolute;top:0;left:10%;right:10%;height:1px;
  background:linear-gradient(90deg,transparent,rgba(201,168,76,.5),transparent);}}
.gtr{{position:absolute;top:-90px;right:-90px;width:260px;height:260px;
      background:radial-gradient(circle,rgba(201,168,76,.09) 0%,transparent 65%);pointer-events:none;}}
.gbl{{position:absolute;bottom:-70px;left:-70px;width:220px;height:220px;
      background:radial-gradient(circle,rgba(91,142,240,.06) 0%,transparent 65%);pointer-events:none;}}
.row{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:24px;}}
.lbl{{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:3px;
      text-transform:uppercase;color:#5a5a88;margin-bottom:10px;}}
.amount{{font-family:'Cormorant Garamond',serif;font-size:3.6rem;font-weight:300;
         line-height:1;color:#e8e8f0;letter-spacing:-1px;}}
.dollar{{font-size:2rem;vertical-align:super;color:#c9a84c;}}
.cents{{font-size:2rem;color:#9090b8;}}
.currency{{font-family:'DM Mono',monospace;font-size:.68rem;letter-spacing:2px;
           color:#5a5a88;margin-top:8px;}}
.id-box{{background:rgba(201,168,76,.06);border:1px solid rgba(201,168,76,.14);
         border-radius:10px;padding:10px 16px;text-align:right;}}
.id-lbl{{font-family:'DM Mono',monospace;font-size:.55rem;letter-spacing:2.5px;
         text-transform:uppercase;color:#7a6128;margin-bottom:4px;}}
.id-val{{font-family:'DM Mono',monospace;font-size:.88rem;color:#c9a84c;letter-spacing:1px;}}
.badges{{display:flex;flex-wrap:wrap;gap:8px;
         padding-top:20px;border-top:1px solid rgba(255,255,255,.05);}}
.badge{{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:99px;
        font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:1.5px;text-transform:uppercase;}}
.bg{{background:rgba(62,207,142,.07);border:1px solid rgba(62,207,142,.18);color:#3ecf8e;}}
.ba{{background:rgba(201,168,76,.07);border:1px solid rgba(201,168,76,.18);color:#c9a84c;}}
.bb{{background:rgba(91,142,240,.07);border:1px solid rgba(91,142,240,.18);color:#5b8ef0;}}
</style></head>
<body>
<div class="card">
  <div class="gtr"></div><div class="gbl"></div>
  <div class="row">
    <div>
      <div class="lbl">Current Balance</div>
      <div class="amount">
        <span class="dollar">$</span>{int(balance):,}<span class="cents">.{f"{balance:.4f}".split('.')[1]}</span>
      </div>
      <div class="currency">USD · {age_s}</div>
    </div>
    <div class="id-box">
      <div class="id-lbl">Account</div>
      <div class="id-val">#{uid:06d}</div>
    </div>
  </div>
  <div class="badges">
    <span class="badge bg">✓ Verified</span>
    <span class="badge ba">⬡ Secure</span>
    <span class="badge bb">◎ Global</span>
  </div>
</div>
</body></html>
""", height=228)

    rc1, rc2, rc3 = st.columns([2, 1, 1])
    with rc1:
        if st.button("↺  Refresh Balance", use_container_width=True):
            with st.spinner("Syncing…"):
                fresh = refresh_balance(uid)
            if fresh:
                st.session_state.user_data    = fresh
                st.session_state.last_refresh = time.time()
                st.rerun()
            else:
                st.markdown('<div class="alert err">⚠ Server unreachable.</div>',
                            unsafe_allow_html=True)
    with rc3:
        if st.button("Sign Out", use_container_width=True):
            for k, v in {"logged_in":False,"user_data":None,
                         "last_refresh":0,"login_err":"","tab":"offers"}.items():
                st.session_state[k] = v
            st.rerun()


# ════════════════════════════════════════════════════
#  WITHDRAW SECTION
# ════════════════════════════════════════════════════
def render_withdraw():
    balance = st.session_state.user_data.get("balance", 0.0) \
              if st.session_state.logged_in and st.session_state.user_data else 0.0

    components.html(f"""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=DM+Mono:wght@400&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:4px 0 8px;}}
.notice{{background:rgba(201,168,76,.05);border:1px solid rgba(201,168,76,.12);
         border-radius:14px;padding:16px 22px;
         display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;}}
.n-lbl{{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:2.5px;
        text-transform:uppercase;color:#5a5a88;margin-bottom:4px;}}
.n-val{{font-family:'Cormorant Garamond',serif;font-size:1.9rem;font-weight:300;color:#c9a84c;}}
.n-val.dim{{color:#5a5a88;font-size:1.3rem;}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;}}
.m{{background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.065);
    border-radius:16px;padding:20px 18px;text-align:center;
    position:relative;overflow:hidden;transition:border-color .3s,transform .2s;}}
.m::before{{content:'';position:absolute;top:0;left:20%;right:20%;height:1px;
            background:linear-gradient(90deg,transparent,rgba(255,255,255,.07),transparent);}}
.m:hover{{border-color:rgba(255,255,255,.11);transform:translateY(-2px);}}
.m-icon{{font-size:1.9rem;margin-bottom:9px;}}
.m-name{{font-family:'Outfit',sans-serif;font-size:.88rem;font-weight:600;
         color:#e8e8f0;margin-bottom:3px;}}
.m-sub{{font-family:'DM Mono',monospace;font-size:.57rem;letter-spacing:1.5px;
        text-transform:uppercase;color:#404068;}}
.pill{{display:inline-block;margin-top:9px;font-family:'DM Mono',monospace;
       font-size:.57rem;letter-spacing:1.5px;text-transform:uppercase;
       padding:3px 10px;border-radius:99px;
       background:rgba(201,168,76,.06);border:1px solid rgba(201,168,76,.14);color:#7a6128;}}
</style></head>
<body>
<div class="notice">
  <div><div class="n-lbl">Your Balance</div><div class="n-val">${balance:,.4f}</div></div>
  <div style="text-align:right"><div class="n-lbl">Minimum</div><div class="n-val dim">$2.00</div></div>
</div>
<div class="grid">
  <div class="m"><div class="m-icon">💙</div>
    <div class="m-name">PayPal</div><div class="m-sub">International · Fast</div>
    <div class="pill">Coming Soon</div></div>
  <div class="m"><div class="m-icon">📱</div>
    <div class="m-name">Vodafone Cash</div><div class="m-sub">Egypt · Instant</div>
    <div class="pill">Coming Soon</div></div>
  <div class="m"><div class="m-icon">₿</div>
    <div class="m-name">Crypto USDT</div><div class="m-sub">TRC-20 · BEP-20</div>
    <div class="pill">Coming Soon</div></div>
  <div class="m"><div class="m-icon">🎁</div>
    <div class="m-name">Gift Cards</div><div class="m-sub">Amazon · Google Play</div>
    <div class="pill">Coming Soon</div></div>
</div>
</body></html>
""", height=335)
    st.markdown(
        '<div class="alert info">🔔 Withdrawal methods activate soon. You\'ll be notified when they go live.</div>',
        unsafe_allow_html=True)


# ════════════════════════════════════════════════════
#  SIGN-IN TEASER
# ════════════════════════════════════════════════════
def render_signin_teaser():
    components.html("""
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=DM+Mono:wght@400&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:transparent;padding:6px 0;}
.teaser{background:rgba(201,168,76,.04);border:1px solid rgba(201,168,76,.14);
        border-radius:18px;padding:24px 28px;position:relative;overflow:hidden;text-align:center;}
.teaser::before{content:'';position:absolute;top:0;left:10%;right:10%;height:1px;
  background:linear-gradient(90deg,transparent,rgba(201,168,76,.3),transparent);}
.t-icon{font-size:1.8rem;margin-bottom:10px;}
.t-title{font-family:'Cormorant Garamond',serif;font-size:1.35rem;font-weight:300;
          color:#e8e8f0;margin-bottom:6px;letter-spacing:.3px;}
.t-sub{font-family:'Outfit',sans-serif;font-size:.82rem;color:#5a5a88;
       margin-bottom:20px;line-height:1.6;}
.perks{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;}
.perk{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:1.5px;text-transform:uppercase;
      padding:5px 12px;border-radius:99px;
      background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);color:#6060a0;}
</style></head>
<body>
<div class="teaser">
  <div class="t-icon">✦</div>
  <div class="t-title">Track Your Earnings</div>
  <div class="t-sub">
    Create a free account to save your progress, track completed offers,<br>
    and withdraw your earnings to PayPal, Crypto, or Gift Cards.
  </div>
  <div class="perks">
    <span class="perk">💰 Balance Tracking</span>
    <span class="perk">📊 Offer History</span>
    <span class="perk">💸 Withdrawals</span>
    <span class="perk">🔔 Notifications</span>
  </div>
</div>
</body></html>
""", height=220)

    if st.button("✦  Create Free Account  →", use_container_width=True, key="teaser_signup"):
        st.session_state.show_login   = True
        st.session_state.login_reason = "Create your free account to start earning."
        st.rerun()


# ════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════
def render_footer():
    st.markdown("""
<div class="foot">
  <div style="font-family:'DM Mono',monospace;font-size:.57rem;letter-spacing:2px;
              text-transform:uppercase;color:#222238;margin-bottom:.6rem">
    © 2025 Rewards Hub · All Rights Reserved
  </div>
  <a href="#" onclick="document.getElementById('tm').classList.add('on');return false;">Terms & Conditions</a>
  &ensp;·&ensp;
  <a href="mailto:support@rewardshub.com">Support</a>
  &ensp;·&ensp;
  <a href="#" style="color:#2a2a48" onclick="return false;">Privacy Policy</a>
</div>

<div id="tm" class="modal" onclick="if(event.target===this)this.classList.remove('on')">
  <div class="mbox">
    <button class="mx" onclick="document.getElementById('tm').classList.remove('on')">✕</button>
    <div class="mh">Terms & Conditions</div>
    <div class="ms"><h3>1. Acceptance</h3>
      <p>By using Rewards Hub you agree to these terms. Guests may browse freely; account required to earn.</p></div>
    <div class="ms"><h3>2. Eligibility</h3>
      <p>You must be 18 or older. The platform is unavailable where local law prohibits such services.</p></div>
    <div class="ms"><h3>3. Earning Rewards</h3>
      <p>Rewards are tracked via AdGem (Postback Key active) and BitLabs. Suspicious activity may be reviewed and voided.</p></div>
    <div class="ms"><h3>4. Prohibited Conduct</h3>
      <p>Bots, fake accounts, and fraudulent completions result in immediate termination and forfeiture of balance.</p></div>
    <div class="ms"><h3>5. Privacy</h3>
      <p>We collect only minimum data to operate the service. Your data is never sold to third parties.</p></div>
    <div class="ms"><h3>6. Disclaimer</h3>
      <p>Rewards Hub is an intermediary. We are not liable for offer partner delays or technical issues.</p></div>
    <div style="margin-top:1.4rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,.05);
                font-family:'DM Mono',monospace;font-size:.57rem;letter-spacing:2px;
                text-transform:uppercase;color:#222238;text-align:center">
      Last updated: January 2025
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════
#  MAIN RENDER
# ════════════════════════════════════════════════════
maybe_show_login_modal()
render_navbar()
render_hero()

st.markdown('<hr class="div">', unsafe_allow_html=True)

if st.session_state.logged_in and st.session_state.user_data:
    render_balance_section()
    st.markdown('<hr class="div">', unsafe_allow_html=True)

    t1, t2 = st.columns(2)
    with t1:
        if st.button("◈  Earn Rewards", use_container_width=True,
                     type="primary" if st.session_state.tab == "offers" else "secondary"):
            st.session_state.tab = "offers"; st.rerun()
    with t2:
        if st.button("◇  Withdraw", use_container_width=True,
                     type="primary" if st.session_state.tab == "withdraw" else "secondary"):
            st.session_state.tab = "withdraw"; st.rerun()

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

    if st.session_state.tab == "offers":
        render_offer_cards()
        st.markdown(
            '<div class="alert warn">💡 After completing any offer, click <strong>↺ Refresh Balance</strong>.</div>',
            unsafe_allow_html=True)
    else:
        render_withdraw()

else:
    render_offer_cards()
    st.markdown('<hr class="div">', unsafe_allow_html=True)
    render_signin_teaser()

render_footer()
