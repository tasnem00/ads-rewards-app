"""
admin_panel.py  —  Rewards Hub | لوحة تحكم المسؤولة
═════════════════════════════════════════════════════
شغّليه محلياً أو على Streamlit Cloud:
    streamlit run admin_panel.py

يتصل بنفس Railway Backend.
كلمة سر الأدمن = قيمة ADMIN_SECRET في Railway Variables.
"""

import os
import requests
import streamlit as st

RAILWAY_URL  = "https://harmonious-recreation-production.up.railway.app"
ADMIN_SECRET = st.secrets.get("ADMIN_SECRET", os.getenv("ADMIN_SECRET", ""))

st.set_page_config(page_title="لوحة التحكم | Rewards Hub", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');
:root{--bg:#0a0a0f;--card:#1a1a25;--border:#2a2a3d;--gold:#f0c040;
      --text:#e8e8f0;--muted:#7070a0;--green:#30d080;--red:#ff6060;--radius:12px;}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important;font-family:'DM Sans',sans-serif;color:var(--text);}
[data-testid="stHeader"]{background:transparent!important;}
#MainMenu,footer{display:none!important;}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  padding:1rem 1.2rem;text-align:center;}
.stat-val{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;color:var(--gold);}
.stat-lbl{font-size:.7rem;color:var(--muted);letter-spacing:1px;text-transform:uppercase;}
.badge{display:inline-block;padding:.15rem .6rem;border-radius:99px;font-size:.7rem;font-weight:700;}
.badge-pending{background:rgba(240,192,64,.15);color:var(--gold);border:1px solid rgba(240,192,64,.3);}
.badge-approved{background:rgba(80,130,255,.15);color:#8ab4ff;border:1px solid rgba(80,130,255,.3);}
.badge-paid{background:rgba(48,208,128,.15);color:var(--green);border:1px solid rgba(48,208,128,.3);}
.badge-rejected{background:rgba(255,96,96,.15);color:var(--red);border:1px solid rgba(255,96,96,.3);}
</style>
""", unsafe_allow_html=True)

st.markdown("# 🛡️ لوحة تحكم Rewards Hub")

# ─── تسجيل الدخول كأدمن ────────────────────────
if "admin_token" not in st.session_state:
    st.session_state.admin_token = ""

if not st.session_state.admin_token:
    with st.form("admin_login"):
        secret = st.text_input("كلمة سر الأدمن", type="password")
        if st.form_submit_button("دخول", type="primary"):
            # تحقق بسيط — الكلمة تُستخدم مباشرة كـ Bearer token
            if secret:
                st.session_state.admin_token = secret
                st.rerun()
            else:
                st.error("أدخلي كلمة السر")
    st.stop()

TOKEN = st.session_state.admin_token
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def admin_get(path, params=None):
    try:
        r = requests.get(f"{RAILWAY_URL}{path}", headers=HEADERS, params=params, timeout=15)
        if r.status_code == 403:
            st.error("كلمة سر الأدمن خاطئة!")
            st.session_state.admin_token = ""
            st.rerun()
        return r.json() if r.ok else {}
    except Exception as e:
        st.error(f"خطأ في الاتصال: {e}")
        return {}

def admin_post(path, note=""):
    try:
        r = requests.post(f"{RAILWAY_URL}{path}", headers=HEADERS, json={"note": note}, timeout=15)
        return r.json() if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}

# ─── خروج ──────────────────────────────────────
col_title, col_out = st.columns([5, 1])
with col_out:
    if st.button("خروج"):
        st.session_state.admin_token = ""
        st.rerun()

# ─── جلب البيانات ──────────────────────────────
filter_status = st.selectbox(
    "تصفية حسب الحالة",
    ["الكل", "pending", "approved", "paid", "rejected"],
    index=0
)
params = {} if filter_status == "الكل" else {"status": filter_status}

if st.button("↻ تحديث", type="primary"):
    st.rerun()

data = admin_get("/withdraw/admin/all", params=params)
stats    = data.get("stats", {})
requests_list = data.get("requests", [])

# ─── إحصائيات ──────────────────────────────────
st.markdown("---")
c1, c2, c3, c4, c5 = st.columns(5)
for col, label, val in [
    (c1, "إجمالي الطلبات",    stats.get("total", 0)),
    (c2, "معلّق ⏳",           stats.get("pending", 0)),
    (c3, "موافق عليه ✅",      stats.get("approved", 0)),
    (c4, "تم الدفع 💰",        stats.get("paid", 0)),
    (c5, "مدفوع (USD) 💵",     f"${stats.get('total_paid_usd', 0):.2f}"),
]:
    with col:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val">{val}</div>
            <div class="stat-lbl">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ─── قائمة الطلبات ─────────────────────────────
STATUS_BADGE = {
    "pending":  "badge-pending",
    "approved": "badge-approved",
    "paid":     "badge-paid",
    "rejected": "badge-rejected",
}
STATUS_AR = {
    "pending": "معلّق", "approved": "موافق عليه",
    "paid": "مدفوع", "rejected": "مرفوض"
}
METHOD_ICON = {
    "paypal": "💳", "crypto_usdt": "₿",
    "vodafone_cash": "📱", "bank_transfer": "🏦", "gift_cards": "🎁"
}

if not requests_list:
    st.info("لا توجد طلبات بهذه الحالة.")
else:
    for req in requests_list:
        badge_class = STATUS_BADGE.get(req["status"], "")
        icon        = METHOD_ICON.get(req["method"], "💸")
        date        = req["created_at"][:10]

        with st.expander(
            f"{icon} #{req['id']} | {req.get('username','?')} | "
            f"${req['amount']:.4f} | {req['method_ar']} | {date}"
        ):
            col_info, col_actions = st.columns([3, 2])

            with col_info:
                st.markdown(f"""
                **المستخدم:** `{req.get('username','?')}` ({req.get('email','')})  
                **الوسيلة:** {icon} {req['method_ar']}  
                **العنوان:** `{req['address']}`  
                **المبلغ:** `${req['amount']:.4f} USD`  
                **الحالة:** <span class="badge {badge_class}">{STATUS_AR.get(req['status'], req['status'])}</span>  
                **ملاحظة:** {req['admin_note'] or '—'}  
                **التاريخ:** {req['created_at'][:16].replace('T',' ')}
                """, unsafe_allow_html=True)

            with col_actions:
                note_key = f"note_{req['id']}"
                note = st.text_input("ملاحظة (اختياري)", key=note_key, placeholder="مثال: تم الإرسال عبر PayPal")

                if req["status"] == "pending":
                    col_a, col_r = st.columns(2)
                    with col_a:
                        if st.button("✅ موافقة", key=f"approve_{req['id']}", use_container_width=True):
                            res = admin_post(f"/withdraw/admin/{req['id']}/approve", note)
                            if "error" not in res:
                                st.success("تمت الموافقة!")
                                st.rerun()
                            else:
                                st.error(res.get("error"))
                    with col_r:
                        if st.button("❌ رفض", key=f"reject_{req['id']}", use_container_width=True):
                            res = admin_post(f"/withdraw/admin/{req['id']}/reject", note)
                            if "error" not in res:
                                st.success("تم الرفض وإعادة الرصيد!")
                                st.rerun()
                            else:
                                st.error(res.get("error"))

                if req["status"] == "approved":
                    if st.button("💰 تم الدفع", key=f"paid_{req['id']}", use_container_width=True, type="primary"):
                        res = admin_post(f"/withdraw/admin/{req['id']}/paid", note)
                        if "error" not in res:
                            st.success("تم التحديث كمدفوع!")
                            st.rerun()
                        else:
                            st.error(res.get("error"))

                if req["status"] in ("paid", "rejected"):
                    st.markdown(f"✔ لا يوجد إجراء متاح لهذا الطلب.")
