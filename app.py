"""
app.py — Rewards Hub  v4 · Premium Edition
════════════════════════════════════════════
pip install streamlit requests
streamlit run app.py
"""

import logging, time, random
import requests
import streamlit as st
import streamlit.components.v1 as components

# ── logging ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("rewards_hub")

# ── config ───────────────────────────────────────────────
RAILWAY_URL   = "https://ads-rewards-app-production.up.railway.app"
BITLABS_TOKEN = "DCDEC791-3E5B-484D-B11C-3404631079D0"
ADGEM_APP_ID  = "32570"

def bl_url(uid):  return f"https://web.bitlabs.ai/?token={BITLABS_TOKEN}&uid={uid}"
def ag_url(uid):  return f"https://adunits.adgem.com/wall?appid={ADGEM_APP_ID}&player_id={uid}"

def fetch_or_create(username: str):
    try:
        r = requests.get(f"{RAILWAY_URL}/users/by_username/{username}", timeout=8)
        if r.status_code == 200:
            d = r.json(); logger.info("✅ login %s bal=%.4f", username, d.get("balance",0)); return d
        if r.status_code == 404:
            c = requests.post(f"{RAILWAY_URL}/users", json={"username": username}, timeout=8)
            if c.status_code in (200,201):
                d = c.json(); logger.info("🆕 created %s", username); return d
    except Exception as e: logger.error("❌ %s", e)
    return None

def refresh_balance(uid):
    try:
        r = requests.get(f"{RAILWAY_URL}/users/{uid}", timeout=8)
        if r.status_code == 200:
            d = r.json(); logger.info("🔄 uid=%s bal=%.4f", uid, d.get("balance",0)); return d
    except Exception as e: logger.error("❌ %s", e)
    return None

# ── page setup ───────────────────────────────────────────
st.set_page_config(page_title="Rewards Hub", page_icon="💎", layout="centered")

# ── session defaults ─────────────────────────────────────
for k,v in {"logged_in":False,"user_data":None,"last_refresh":0,
            "login_err":"","tab":"offers"}.items():
    if k not in st.session_state: st.session_state[k] = v

# ════════════════════════════════════════════════════════
#  GLOBAL CSS  — Luxury Dark Finance
# ════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;500;600;700&display=swap');

:root{
  --ink:    #0a0a0e;
  --ink2:   #0f0f16;
  --glass:  rgba(255,255,255,.034);
  --glass2: rgba(255,255,255,.06);
  --rim:    rgba(255,255,255,.07);
  --rim2:   rgba(255,255,255,.13);
  --gold:   #c9a84c;
  --gold2:  #e8c96a;
  --gold3:  #f5dfa0;
  --gold-dim:#7a6128;
  --text:   #e8e8f0;
  --text2:  #9090b8;
  --text3:  #5a5a88;
  --green:  #3ecf8e;
  --blue:   #5b8ef0;
  --r:      20px;
  --rsm:    12px;
}

/* base */
html,body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="block-container"]{
  background:#0a0a0e !important;
  font-family:'Outfit',sans-serif;
  color:var(--text);
  max-width:680px;
}
[data-testid="stHeader"]{background:transparent !important;}
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important;}
[data-testid="block-container"]{padding-top:0!important;}

/* animated mesh background */
[data-testid="stAppViewContainer"]::before{
  content:'';position:fixed;inset:0;z-index:-2;
  background:
    radial-gradient(ellipse 900px 600px at 10% 20%, rgba(180,140,40,.12) 0%,transparent 55%),
    radial-gradient(ellipse 700px 500px at 90% 80%, rgba(60,100,200,.10) 0%,transparent 55%),
    radial-gradient(ellipse 500px 400px at 50% 50%, rgba(120,80,200,.06) 0%,transparent 60%),
    #0a0a0e;
  animation:meshMove 12s ease-in-out infinite alternate;
}
@keyframes meshMove{
  0%  {filter:hue-rotate(0deg) brightness(1);}
  50% {filter:hue-rotate(8deg)  brightness(1.05);}
  100%{filter:hue-rotate(-5deg) brightness(.97);}
}

/* noise overlay */
[data-testid="stAppViewContainer"]::after{
  content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
  background-size:200px 200px;
  opacity:.5;
}

/* streamlit widget overrides */
[data-testid="stTextInput"] input{
  background:var(--glass2)!important;
  border:1px solid var(--rim)!important;
  border-radius:var(--rsm)!important;
  color:var(--text)!important;
  font-family:'Outfit',sans-serif!important;
  font-size:.95rem!important;
  padding:.7rem 1rem!important;
  transition:border-color .25s,box-shadow .25s!important;
}
[data-testid="stTextInput"] input:focus{
  border-color:rgba(201,168,76,.45)!important;
  box-shadow:0 0 0 3px rgba(201,168,76,.09)!important;
}
[data-testid="stTextInput"] label{
  color:var(--text3)!important;
  font-size:.7rem!important;
  letter-spacing:2.5px!important;
  text-transform:uppercase!important;
  font-family:'DM Mono',monospace!important;
}
[data-testid="stButton"]>button{
  background:var(--glass)!important;
  border:1px solid var(--rim)!important;
  border-radius:var(--rsm)!important;
  color:var(--text2)!important;
  font-family:'Outfit',sans-serif!important;
  font-weight:500!important;
  font-size:.88rem!important;
  padding:.6rem 1.2rem!important;
  transition:all .25s!important;
  letter-spacing:.3px!important;
}
[data-testid="stButton"]>button:hover{
  border-color:var(--gold)!important;
  color:var(--gold)!important;
  background:rgba(201,168,76,.06)!important;
  box-shadow:0 0 18px rgba(201,168,76,.12)!important;
}

/* glass card */
.gc{
  background:var(--glass);
  border:1px solid var(--rim);
  border-radius:var(--r);
  backdrop-filter:blur(18px) saturate(150%);
  -webkit-backdrop-filter:blur(18px) saturate(150%);
  position:relative;overflow:hidden;
}
.gc::before{
  content:'';position:absolute;inset:0;border-radius:inherit;
  background:linear-gradient(135deg,rgba(255,255,255,.045) 0%,transparent 60%);
  pointer-events:none;
}

/* divider */
.div{border:none;border-top:1px solid var(--rim);margin:1.6rem 0;}

/* mono label */
.mono-label{
  font-family:'DM Mono',monospace;
  font-size:.65rem;letter-spacing:3px;
  text-transform:uppercase;color:var(--text3);
}

/* alert */
.alert{border-radius:var(--rsm);padding:.8rem 1rem;font-size:.83rem;margin:.5rem 0;
       display:flex;gap:.6rem;align-items:flex-start;}
.alert.err {background:rgba(220,60,60,.07); border:1px solid rgba(220,60,60,.2); color:#f08080;}
.alert.warn{background:rgba(201,168,76,.07);border:1px solid rgba(201,168,76,.18);color:var(--gold);}
.alert.info{background:rgba(91,142,240,.07);border:1px solid rgba(91,142,240,.18);color:var(--blue);}

/* section title */
.sec{
  font-family:'Cormorant Garamond',serif;
  font-size:1.5rem;font-weight:300;font-style:italic;
  color:var(--text2);text-align:center;
  margin:1.8rem 0 1rem;letter-spacing:.5px;
}

/* footer */
.foot{
  text-align:center;padding:2rem 1rem;
  font-size:.75rem;color:var(--text3);
  border-top:1px solid var(--rim);margin-top:2rem;
}
.foot a{color:var(--gold-dim);text-decoration:none;transition:color .2s;}
.foot a:hover{color:var(--gold);}

/* modal */
.modal{display:none;position:fixed;inset:0;z-index:9999;
       background:rgba(5,5,10,.92);backdrop-filter:blur(10px);
       align-items:flex-start;justify-content:center;
       padding:2rem 1rem;overflow-y:auto;}
.modal.on{display:flex;}
.mbox{
  background:rgba(18,18,28,.97);
  border:1px solid var(--rim2);
  border-radius:var(--r);padding:2.2rem;
  max-width:580px;width:100%;position:relative;
  animation:mIn .3s cubic-bezier(.22,1,.36,1);
}
@keyframes mIn{from{opacity:0;transform:translateY(28px);}to{opacity:1;transform:translateY(0);}}
.mx{position:absolute;top:1rem;right:1rem;
    background:var(--glass2);border:1px solid var(--rim);color:var(--text3);
    width:30px;height:30px;border-radius:50%;cursor:pointer;
    display:flex;align-items:center;justify-content:center;
    font-size:.9rem;transition:all .2s;border:none;}
.mx:hover{background:var(--rim);color:var(--gold);}
.mh{font-family:'Cormorant Garamond',serif;font-size:1.6rem;
    font-weight:400;color:var(--gold);margin-bottom:1.4rem;}
.ms{margin-bottom:1.1rem;}
.ms h3{font-family:'DM Mono',monospace;font-size:.68rem;letter-spacing:2px;
       text-transform:uppercase;color:var(--text3);margin-bottom:.4rem;}
.ms p{font-size:.87rem;color:var(--text2);line-height:1.8;}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  LOGIN PAGE
# ════════════════════════════════════════════════════════
def page_login():
    components.html("""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300;1,400&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:transparent;padding:52px 16px 28px;text-align:center;font-family:'Cormorant Garamond',serif;}

.wordmark{
  font-size:3.6rem;font-weight:300;letter-spacing:-1px;
  color:#e8e8f0;margin-bottom:2px;
  text-shadow:0 0 60px rgba(201,168,76,.25);
}
.wordmark em{font-style:italic;color:#c9a84c;}

.gem{
  display:inline-block;
  font-size:2.8rem;margin-bottom:18px;
  filter:drop-shadow(0 0 24px rgba(201,168,76,.6));
  animation:float 4s ease-in-out infinite;
}
@keyframes float{0%,100%{transform:translateY(0) rotate(-3deg)}50%{transform:translateY(-10px) rotate(3deg)}}

.tagline{
  font-family:'DM Mono',monospace;
  font-size:.65rem;letter-spacing:4px;text-transform:uppercase;
  color:#5a5a88;margin-top:10px;
}

.rule{
  width:60px;height:1px;
  background:linear-gradient(90deg,transparent,rgba(201,168,76,.4),transparent);
  margin:22px auto 0;
}
</style>
</head>
<body>
  <div class="gem">💎</div>
  <div class="wordmark">Rewards <em>Hub</em></div>
  <div class="tagline">Complete Offers · Earn Real Rewards</div>
  <div class="rule"></div>
</body></html>
""", height=200)

    # glass login form
    components.html("""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:transparent;padding:6px 0 4px}
.card{
  background:rgba(255,255,255,.032);
  border:1px solid rgba(255,255,255,.07);
  border-radius:20px;padding:2rem 2.2rem 1.6rem;
  backdrop-filter:blur(20px);
  position:relative;overflow:hidden;
}
.card::before{
  content:'';position:absolute;
  top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent 0%,rgba(201,168,76,.35) 50%,transparent 100%);
}
.card::after{
  content:'';position:absolute;
  top:-80px;right:-80px;width:220px;height:220px;
  background:radial-gradient(circle,rgba(201,168,76,.08) 0%,transparent 65%);
  pointer-events:none;
}
.lbl{
  font-family:'DM Mono',monospace;
  font-size:.62rem;letter-spacing:3px;text-transform:uppercase;
  color:#5a5a88;margin-bottom:12px;
  display:flex;align-items:center;gap:8px;
}
.lbl::before{content:'';width:16px;height:1px;background:rgba(201,168,76,.4);}
</style>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400&display=swap" rel="stylesheet">
</head>
<body>
<div class="card">
  <div class="lbl">Secure Sign In</div>
</div>
</body></html>
""", height=82)

    username_val = st.text_input(
        "Username or Email Address",
        placeholder="your@email.com  or  username",
        key="login_field",
        label_visibility="collapsed",
    )

    # spacer
    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    if st.session_state.login_err:
        st.markdown(
            f'<div class="alert err">⚠ {st.session_state.login_err}</div>',
            unsafe_allow_html=True)

    # CTA button via components.html for full styling control
    btn_key = f"login_btn_{int(time.time()*10)%1000}"
    col1, col2 = st.columns([5, 1])
    with col1:
        login_clicked = st.button("Enter Rewards Hub →", use_container_width=True, key="login_btn")

    if login_clicked:
        val = (username_val or "").strip()
        if not val or len(val) < 3:
            st.session_state.login_err = "Please enter at least 3 characters."
            st.rerun()
        else:
            with st.spinner("Authenticating…"):
                data = fetch_or_create(val)
            if data:
                st.session_state.update(
                    logged_in=True, user_data=data,
                    last_refresh=time.time(), login_err="")
                st.rerun()
            else:
                st.session_state.login_err = "Server unreachable. Please try again."
                st.rerun()

    # trust badges
    components.html("""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:transparent;padding:16px 0 8px;}
.row{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:20px;}
.badge{
  display:flex;align-items:center;gap:6px;
  font-family:'DM Mono',monospace;font-size:.62rem;
  letter-spacing:1.5px;text-transform:uppercase;color:#3a3a60;
}
.dot{width:5px;height:5px;border-radius:50%;background:#c9a84c;opacity:.5;}
</style></head>
<body>
<div class="row">
  <div class="badge"><div class="dot"></div>SSL Encrypted</div>
  <div class="badge"><div class="dot"></div>GDPR Compliant</div>
  <div class="badge"><div class="dot"></div>Instant Payouts</div>
  <div class="badge"><div class="dot"></div>Global Access</div>
</div>
</body></html>
""", height=52)


# ════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════
def page_dashboard():
    user     = st.session_state.user_data
    uid      = user.get("id", 1)
    username = user.get("username", "—")
    balance  = user.get("balance", 0.0)

    if st.session_state.last_refresh:
        age = int(time.time() - st.session_state.last_refresh)
        age_s = f"{age}s ago" if age < 60 else f"{age//60}m ago"
    else:
        age_s = "—"

    # ── TOP NAV ─────────────────────────────────
    components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=DM+Mono:wght@400&family=Outfit:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:28px 0 16px;}}
nav{{
  display:flex;align-items:center;justify-content:space-between;
  border-bottom:1px solid rgba(255,255,255,.06);padding-bottom:16px;
}}
.brand{{
  font-family:'Cormorant Garamond',serif;
  font-size:1.5rem;font-weight:300;color:#e8e8f0;letter-spacing:.5px;
}}
.brand em{{font-style:italic;color:#c9a84c;}}
.user-chip{{
  display:flex;align-items:center;gap:8px;
  background:rgba(255,255,255,.04);
  border:1px solid rgba(255,255,255,.07);
  border-radius:99px;padding:6px 14px 6px 8px;
}}
.avatar{{
  width:28px;height:28px;border-radius:50%;
  background:linear-gradient(135deg,#c9a84c,#7a6128);
  display:flex;align-items:center;justify-content:center;
  font-size:.8rem;font-weight:600;color:#0a0a0e;
  font-family:'Outfit',sans-serif;
}}
.uname{{
  font-family:'Outfit',sans-serif;font-size:.82rem;
  color:#9090b8;letter-spacing:.3px;
}}
</style></head>
<body>
<nav>
  <div class="brand">Rewards <em>Hub</em></div>
  <div class="user-chip">
    <div class="avatar">{username[0].upper()}</div>
    <span class="uname">{username}</span>
  </div>
</nav>
</body></html>
""", height=84)

    # ── BALANCE CARD ─────────────────────────────
    components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&family=DM+Mono:wght@300;400&family=Outfit:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:4px 0 10px;}}

.card{{
  background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.08);
  border-radius:22px;
  padding:32px 36px 28px;
  position:relative;overflow:hidden;
  backdrop-filter:blur(20px);
}}
/* top shine line */
.card::before{{
  content:'';position:absolute;top:0;left:10%;right:10%;height:1px;
  background:linear-gradient(90deg,transparent,rgba(201,168,76,.5),transparent);
}}
/* ambient glow */
.card::after{{
  content:'';position:absolute;
  top:-100px;right:-100px;width:300px;height:300px;
  background:radial-gradient(circle,rgba(201,168,76,.09) 0%,transparent 65%);
  pointer-events:none;
}}
.bl-glow{{
  position:absolute;bottom:-80px;left:-80px;width:250px;height:250px;
  background:radial-gradient(circle,rgba(91,142,240,.07) 0%,transparent 65%);
  pointer-events:none;
}}

/* grid layout */
.top-row{{
  display:flex;align-items:flex-start;justify-content:space-between;
  margin-bottom:28px;
}}
.left .label{{
  font-family:'DM Mono',monospace;font-size:.6rem;
  letter-spacing:3px;text-transform:uppercase;color:#5a5a88;
  margin-bottom:12px;
}}
.amount{{
  font-family:'Cormorant Garamond',serif;
  font-size:3.8rem;font-weight:300;line-height:1;
  color:#e8e8f0;letter-spacing:-1px;
}}
.amount .dollar{{
  font-size:2rem;vertical-align:super;
  color:#c9a84c;font-weight:300;
}}
.amount .cents{{
  font-size:2rem;color:#9090b8;
}}
.currency{{
  font-family:'DM Mono',monospace;font-size:.7rem;
  letter-spacing:2px;color:#5a5a88;margin-top:8px;
}}

.right .id-badge{{
  background:rgba(201,168,76,.07);
  border:1px solid rgba(201,168,76,.15);
  border-radius:8px;padding:8px 14px;text-align:right;
}}
.right .id-label{{
  font-family:'DM Mono',monospace;font-size:.55rem;
  letter-spacing:2.5px;text-transform:uppercase;color:#7a6128;
  margin-bottom:4px;
}}
.right .id-value{{
  font-family:'DM Mono',monospace;font-size:.9rem;
  color:#c9a84c;letter-spacing:1px;
}}

/* trust badges row */
.badges{{
  display:flex;flex-wrap:wrap;gap:8px;
  padding-top:22px;
  border-top:1px solid rgba(255,255,255,.05);
}}
.badge{{
  display:inline-flex;align-items:center;gap:6px;
  padding:5px 12px;border-radius:99px;
  font-family:'DM Mono',monospace;
  font-size:.6rem;letter-spacing:1.5px;text-transform:uppercase;
}}
.badge.g{{background:rgba(62,207,142,.07);border:1px solid rgba(62,207,142,.18);color:#3ecf8e;}}
.badge.a{{background:rgba(201,168,76,.07);border:1px solid rgba(201,168,76,.18);color:#c9a84c;}}
.badge.b{{background:rgba(91,142,240,.07);border:1px solid rgba(91,142,240,.18);color:#5b8ef0;}}

.refresh-note{{
  font-family:'DM Mono',monospace;font-size:.58rem;
  letter-spacing:1.5px;color:#3a3a60;
  text-align:right;margin-top:4px;
}}
</style></head>
<body>
<div class="card">
  <div class="bl-glow"></div>
  <div class="top-row">
    <div class="left">
      <div class="label">Current Balance</div>
      <div class="amount">
        <span class="dollar">$</span>{int(balance):,}<span class="cents">.{f"{balance:.4f}".split('.')[1]}</span>
      </div>
      <div class="currency">United States Dollar · {age_s}</div>
    </div>
    <div class="right">
      <div class="id-badge">
        <div class="id-label">Account ID</div>
        <div class="id-value">#{uid:06d}</div>
      </div>
    </div>
  </div>
  <div class="badges">
    <span class="badge g">✓ Verified Account</span>
    <span class="badge a">⬡ Secure Payments</span>
    <span class="badge b">◎ Global Access</span>
  </div>
</div>
<div class="refresh-note">Last updated: {age_s}</div>
</body></html>
""", height=248)

    # refresh + logout row
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
            for k in ["logged_in","user_data","last_refresh","login_err","tab"]:
                st.session_state[k] = {"logged_in":False,"user_data":None,
                    "last_refresh":0,"login_err":"","tab":"offers"}[k]
            st.rerun()

    st.markdown('<hr class="div">', unsafe_allow_html=True)

    # ── TAB SWITCHER ─────────────────────────────
    t1, t2 = st.columns(2)
    with t1:
        a1 = st.session_state.tab == "offers"
        if st.button("◈  Earn Rewards", use_container_width=True,
                     type="primary" if a1 else "secondary"):
            st.session_state.tab = "offers"; st.rerun()
    with t2:
        a2 = st.session_state.tab == "withdraw"
        if st.button("◇  Withdraw Funds", use_container_width=True,
                     type="primary" if a2 else "secondary"):
            st.session_state.tab = "withdraw"; st.rerun()

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    # ════════════════════════════════════════════
    #  TAB: OFFERS
    # ════════════════════════════════════════════
    if st.session_state.tab == "offers":
        st.markdown('<div class="sec">Choose your offer platform</div>', unsafe_allow_html=True)

        # ── BitLabs ──────────────────────────────
        _bl = bl_url(uid)
        logger.info("🔗 BitLabs uid=%s", uid)
        components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&family=DM+Mono:wght@400&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:5px 0;}}
.card{{
  background:rgba(255,255,255,.028);
  border:1px solid rgba(255,255,255,.07);
  border-radius:20px;padding:24px 26px;
  position:relative;overflow:hidden;
  backdrop-filter:blur(16px);
  cursor:pointer;
  transition:border-color .3s,transform .25s,box-shadow .3s;
}}
.card::before{{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(201,168,76,.3),transparent);
}}
.card::after{{
  content:'';position:absolute;top:-60px;right:-60px;
  width:180px;height:180px;
  background:radial-gradient(circle,rgba(201,168,76,.07) 0%,transparent 65%);
  pointer-events:none;
}}
.card:hover{{
  border-color:rgba(201,168,76,.4);
  transform:translateY(-3px);
  box-shadow:0 16px 48px rgba(0,0,0,.35),0 0 0 1px rgba(201,168,76,.08);
}}
.row{{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;}}
.provider{{
  display:inline-flex;align-items:center;gap:8px;
  font-family:'DM Mono',monospace;font-size:.65rem;
  letter-spacing:2.5px;text-transform:uppercase;
  color:#c9a84c;
  background:rgba(201,168,76,.07);
  border:1px solid rgba(201,168,76,.18);
  padding:5px 14px;border-radius:99px;
}}
.live{{width:6px;height:6px;border-radius:50%;background:#3ecf8e;
       animation:pulse 2s ease infinite;}}
@keyframes pulse{{
  0%,100%{{box-shadow:0 0 0 0 rgba(62,207,142,.5);}}
  50%{{box-shadow:0 0 0 6px rgba(62,207,142,0);}}
}}
.title{{
  font-family:'Cormorant Garamond',serif;
  font-size:1.4rem;font-weight:300;color:#e8e8f0;
  margin-bottom:5px;letter-spacing:.3px;
}}
.sub{{
  font-family:'Outfit',sans-serif;
  font-size:.8rem;color:#5a5a88;margin-bottom:18px;letter-spacing:.2px;
}}
.tags{{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:20px;}}
.tag{{
  font-family:'DM Mono',monospace;font-size:.6rem;
  letter-spacing:1.5px;text-transform:uppercase;
  padding:4px 11px;border-radius:6px;
  background:rgba(255,255,255,.04);
  border:1px solid rgba(255,255,255,.07);
  color:#6a6a98;
}}
.cta{{
  display:flex;align-items:center;justify-content:space-between;
  background:linear-gradient(135deg,rgba(201,168,76,.12) 0%,rgba(201,168,76,.06) 100%);
  border:1px solid rgba(201,168,76,.22);
  border-radius:14px;padding:16px 20px;
  cursor:pointer;transition:all .25s;
  text-decoration:none;
}}
.cta:hover{{
  background:linear-gradient(135deg,rgba(201,168,76,.2) 0%,rgba(201,168,76,.1) 100%);
  border-color:rgba(201,168,76,.4);
}}
.cta-left{{display:flex;align-items:center;gap:12px;}}
.cta-icon{{font-size:1.5rem;}}
.cta-text{{
  font-family:'Outfit',sans-serif;font-size:.95rem;
  font-weight:600;color:#c9a84c;letter-spacing:.3px;
}}
.cta-sub{{
  font-family:'DM Mono',monospace;font-size:.58rem;
  letter-spacing:2px;text-transform:uppercase;
  color:#7a6128;margin-top:2px;
}}
.cta-arrow{{font-size:1.2rem;color:rgba(201,168,76,.5);transition:transform .25s;}}
.cta:hover .cta-arrow{{transform:translateX(4px);}}
</style></head>
<body>
<div class="card">
  <div class="row">
    <div class="provider"><div class="live"></div>BitLabs</div>
  </div>
  <div class="title">Paid Surveys & Research</div>
  <div class="sub">High-quality market research surveys · Instant credit · uid: {uid}</div>
  <div class="tags">
    <span class="tag">Surveys</span>
    <span class="tag">Instant Payout</span>
    <span class="tag">Global</span>
    <span class="tag">Daily Offers</span>
  </div>
  <button class="cta" onclick="window.open('{_bl}','_blank')">
    <div class="cta-left">
      <span class="cta-icon">🎯</span>
      <div>
        <div class="cta-text">Start Earning with BitLabs</div>
        <div class="cta-sub">Open Offer Wall</div>
      </div>
    </div>
    <div class="cta-arrow">→</div>
  </button>
</div>
</body></html>
""", height=252)

        # ── AdGem ─────────────────────────────────
        _ag = ag_url(uid)
        logger.info("🔗 AdGem uid=%s url=%s", uid, _ag)
        components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=DM+Mono:wght@400&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:5px 0 8px;}}
.card{{
  background:rgba(255,255,255,.025);
  border:1px solid rgba(255,255,255,.065);
  border-radius:20px;padding:24px 26px;
  position:relative;overflow:hidden;
  backdrop-filter:blur(16px);
  transition:border-color .3s,transform .25s,box-shadow .3s;
}}
.card::before{{
  content:'';position:absolute;top:0;left:0;right:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(91,142,240,.3),transparent);
}}
.card::after{{
  content:'';position:absolute;top:-60px;right:-60px;
  width:180px;height:180px;
  background:radial-gradient(circle,rgba(91,142,240,.07) 0%,transparent 65%);
  pointer-events:none;
}}
.card:hover{{
  border-color:rgba(91,142,240,.4);
  transform:translateY(-3px);
  box-shadow:0 16px 48px rgba(0,0,0,.35),0 0 0 1px rgba(91,142,240,.08);
}}
.row{{display:flex;align-items:center;margin-bottom:18px;}}
.provider{{
  display:inline-flex;align-items:center;gap:8px;
  font-family:'DM Mono',monospace;font-size:.65rem;
  letter-spacing:2.5px;text-transform:uppercase;
  color:#5b8ef0;
  background:rgba(91,142,240,.07);
  border:1px solid rgba(91,142,240,.2);
  padding:5px 14px;border-radius:99px;
}}
.live{{width:6px;height:6px;border-radius:50%;background:#5b8ef0;
       animation:pulse 2.5s ease infinite;}}
@keyframes pulse{{
  0%,100%{{box-shadow:0 0 0 0 rgba(91,142,240,.5);}}
  50%{{box-shadow:0 0 0 6px rgba(91,142,240,0);}}
}}
.title{{font-family:'Cormorant Garamond',serif;
        font-size:1.4rem;font-weight:300;color:#e8e8f0;margin-bottom:5px;letter-spacing:.3px;}}
.sub{{font-family:'Outfit',sans-serif;font-size:.8rem;color:#5a5a88;margin-bottom:18px;}}
.tags{{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:20px;}}
.tag{{font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:1.5px;
      text-transform:uppercase;padding:4px 11px;border-radius:6px;
      background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);color:#6a6a98;}}
.cta{{
  display:flex;align-items:center;justify-content:space-between;
  background:linear-gradient(135deg,rgba(91,142,240,.1) 0%,rgba(91,142,240,.05) 100%);
  border:1px solid rgba(91,142,240,.22);
  border-radius:14px;padding:16px 20px;cursor:pointer;transition:all .25s;
}}
.cta:hover{{
  background:linear-gradient(135deg,rgba(91,142,240,.18),rgba(91,142,240,.09));
  border-color:rgba(91,142,240,.4);
}}
.cta-left{{display:flex;align-items:center;gap:12px;}}
.cta-icon{{font-size:1.5rem;}}
.cta-text{{font-family:'Outfit',sans-serif;font-size:.95rem;font-weight:600;color:#5b8ef0;letter-spacing:.3px;}}
.cta-sub{{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:2px;
          text-transform:uppercase;color:#2a4888;margin-top:2px;}}
.cta-arrow{{font-size:1.2rem;color:rgba(91,142,240,.5);transition:transform .25s;}}
.cta:hover .cta-arrow{{transform:translateX(4px);}}
</style></head>
<body>
<div class="card">
  <div class="row">
    <div class="provider"><div class="live"></div>AdGem</div>
  </div>
  <div class="title">Apps, Tasks & Contests</div>
  <div class="sub">Install apps · Complete missions · Win prizes · player_id: {uid}</div>
  <div class="tags">
    <span class="tag">Offerwall</span>
    <span class="tag">Mobile Tasks</span>
    <span class="tag">Contests</span>
    <span class="tag">App Installs</span>
  </div>
  <button class="cta" onclick="window.open('{_ag}','_blank')">
    <div class="cta-left">
      <span class="cta-icon">🚀</span>
      <div>
        <div class="cta-text">Start Earning with AdGem</div>
        <div class="cta-sub">Explore Offers · App ID {ADGEM_APP_ID}</div>
      </div>
    </div>
    <div class="cta-arrow">→</div>
  </button>
</div>
</body></html>
""", height=248)

        st.markdown(
            '<div class="alert warn" style="margin-top:.3rem">'
            '💡 After completing any offer, click <strong>↺ Refresh Balance</strong> to see your earnings.'
            '</div>',
            unsafe_allow_html=True)

    # ════════════════════════════════════════════
    #  TAB: WITHDRAW
    # ════════════════════════════════════════════
    else:
        st.markdown('<div class="sec">Withdrawal Methods</div>', unsafe_allow_html=True)

        components.html(f"""
<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=DM+Mono:wght@400&family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;padding:4px 0 8px;}}

.balance-notice{{
  background:rgba(201,168,76,.05);
  border:1px solid rgba(201,168,76,.12);
  border-radius:14px;padding:16px 20px;
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:20px;
}}
.bn-label{{font-family:'DM Mono',monospace;font-size:.6rem;
           letter-spacing:2.5px;text-transform:uppercase;color:#5a5a88;margin-bottom:4px;}}
.bn-val{{font-family:'Cormorant Garamond',serif;font-size:1.8rem;
         font-weight:300;color:#c9a84c;letter-spacing:-.5px;}}
.bn-min{{text-align:right;}}
.bn-min .bn-label{{text-align:right;}}
.bn-min .bn-val{{font-size:1.2rem;color:#5a5a88;}}

.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
.method{{
  background:rgba(255,255,255,.025);
  border:1px solid rgba(255,255,255,.065);
  border-radius:16px;padding:20px 18px;text-align:center;
  position:relative;overflow:hidden;
  transition:border-color .3s,transform .2s;cursor:default;
}}
.method:hover{{border-color:rgba(255,255,255,.12);transform:translateY(-2px);}}
.method::before{{
  content:'';position:absolute;top:0;left:20%;right:20%;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);
}}
.m-icon{{font-size:2rem;margin-bottom:10px;}}
.m-name{{font-family:'Outfit',sans-serif;font-size:.9rem;font-weight:600;
         color:#e8e8f0;margin-bottom:3px;}}
.m-sub{{font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:1.5px;
        text-transform:uppercase;color:#4a4a78;}}
.pill{{
  display:inline-block;margin-top:10px;
  font-family:'DM Mono',monospace;font-size:.58rem;
  letter-spacing:1.5px;text-transform:uppercase;
  padding:3px 10px;border-radius:99px;
  background:rgba(201,168,76,.06);
  border:1px solid rgba(201,168,76,.15);
  color:#7a6128;
}}
</style></head>
<body>
<div class="balance-notice">
  <div>
    <div class="bn-label">Available Balance</div>
    <div class="bn-val">${balance:,.4f}</div>
  </div>
  <div class="bn-min">
    <div class="bn-label">Minimum Withdrawal</div>
    <div class="bn-val">$5.00</div>
  </div>
</div>
<div class="grid">
  <div class="method">
    <div class="m-icon">💙</div>
    <div class="m-name">PayPal</div>
    <div class="m-sub">International · Fast</div>
    <div class="pill">Coming Soon</div>
  </div>
  <div class="method">
    <div class="m-icon">📱</div>
    <div class="m-name">Vodafone Cash</div>
    <div class="m-sub">Egypt · Instant</div>
    <div class="pill">Coming Soon</div>
  </div>
  <div class="method">
    <div class="m-icon">₿</div>
    <div class="m-name">Crypto USDT</div>
    <div class="m-sub">TRC-20 · BEP-20</div>
    <div class="pill">Coming Soon</div>
  </div>
  <div class="method">
    <div class="m-icon">🎁</div>
    <div class="m-name">Gift Cards</div>
    <div class="m-sub">Amazon · Google Play</div>
    <div class="pill">Coming Soon</div>
  </div>
</div>
</body></html>
""", height=340)

        st.markdown(
            '<div class="alert info">'
            '🔔 Withdrawal methods activate automatically. You\'ll be notified when they go live.'
            '</div>',
            unsafe_allow_html=True)

    # ── FOOTER ───────────────────────────────────
    st.markdown("""
<div class="foot">
  <div style="margin-bottom:.6rem;font-family:'DM Mono',monospace;font-size:.58rem;
              letter-spacing:2px;text-transform:uppercase;color:#2a2a48">
    © 2025 Rewards Hub · All Rights Reserved
  </div>
  <a href="#" onclick="document.getElementById('tm').classList.add('on');return false;">Terms & Conditions</a>
  &ensp;·&ensp;
  <a href="mailto:support@rewardshub.com">Support</a>
  &ensp;·&ensp;
  <a href="#" style="color:#3a3a58" onclick="return false;">Privacy Policy</a>
</div>

<div id="tm" class="modal" onclick="if(event.target===this)this.classList.remove('on')">
  <div class="mbox">
    <button class="mx" onclick="document.getElementById('tm').classList.remove('on')">✕</button>
    <div class="mh">Terms & Conditions</div>
    <div class="ms"><h3>1. Acceptance</h3>
      <p>By using Rewards Hub you agree to these terms in full. If you disagree with any part, please discontinue use.</p></div>
    <div class="ms"><h3>2. Eligibility</h3>
      <p>You must be 18 or older. The platform is unavailable where local law prohibits such services.</p></div>
    <div class="ms"><h3>3. Earning Rewards</h3>
      <p>Rewards are calculated automatically via offer partners. We reserve the right to review and void suspicious transactions.</p></div>
    <div class="ms"><h3>4. Prohibited Conduct</h3>
      <p>Automation tools, fake accounts, and fraudulent completions are strictly prohibited and result in immediate account termination.</p></div>
    <div class="ms"><h3>5. Privacy</h3>
      <p>We collect only the minimum data needed to operate the service. Your data is never sold to third parties.</p></div>
    <div class="ms"><h3>6. Disclaimer</h3>
      <p>Rewards Hub acts as an intermediary between users and offer partners. We are not liable for partner delays or technical issues.</p></div>
    <div style="margin-top:1.4rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,.06);
                font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:2px;
                text-transform:uppercase;color:#2a2a48;text-align:center">
      Last updated: January 2025
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  ROUTER
# ════════════════════════════════════════════════════════
if st.session_state.logged_in and st.session_state.user_data:
    page_dashboard()
else:
    page_login()
