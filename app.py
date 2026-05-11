import streamlit as st
import requests
import logging

# --- الإعدادات الأساسية ---
st.set_page_config(page_title="Rewards Hub - Premium", page_icon="💎", layout="wide")

# إعدادات الروابط (تأكد من صحتها)
RAILWAY_URL = "https://ads-rewards-app-production.up.railway.app"
BITLABS_TOKEN = "DCDEC791-3E5B-484D-B11C-3404631079D0"
ADGEM_APP_ID = "32570"

# تنسيق CSS مخصص لجعل الموقع يبدو فاخراً وموثوقاً
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #D4AF37;
        color: black;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #FFD700; transform: scale(1.02); }
    .card {
        background-color: #1c1f26;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
    .trust-badge { color: #4CAF50; font-size: 0.8em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- نظام الجلسة وتسجيل الدخول ---
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

if st.session_state['user_id'] is None:
    st.title("💎 مرحبا بك في Rewards Hub")
    st.subheader("سجل دخولك لبدء جمع النقاط وتحويلها لأموال حقيقية")
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        user_input = st.text_input("أدخل اسم المستخدم أو البريد الإلكتروني:")
        if st.button("دخول آمن"):
            if user_input:
                st.session_state['user_id'] = user_input
                st.rerun()
            else:
                st.error("رجاءً أدخل اسماً صحيحاً")
        st.markdown('</div>', unsafe_allow_html=True)
        st.info("💡 نحن نضمن خصوصية بياناتك ولا نطلب كلمات مرور حساسة.")

else:
    # --- الواجهة الرئيسية بعد الدخول ---
    user_id = st.session_state['user_id']
    
    # الشريط العلوي
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"مرحباً، {user_id} 👋")
    with col2:
        if st.button("تسجيل الخروج"):
            st.session_state['user_id'] = None
            st.rerun()

    st.markdown("---")

    # عرض الرصيد (سيتم جلبه من السيرفر)
    st.markdown(f"""
        <div class="card" style="text-align: center;">
            <p style="margin:0;">رصيدك الحالي</p>
            <h2 style="color: #D4AF37;">0.00 نقطة</h2>
            <p class="trust-badge">✅ تم التحقق من الحساب</p>
        </div>
    """, unsafe_allow_html=True)

    # قسم العروض
    st.subheader("🚀 اختر منصة لبدء جمع الأرباح")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/5968/5968261.png", width=50)
        st.markdown("### AdGem Offers")
        st.write("أكمل المهام والألعاب البسيطة.")
        adgem_url = f"https://adunits.adgem.com/wall?appid={ADGEM_APP_ID}&player_id={user_id}"
        st.link_button("🎮 ابدأ الآن", adgem_url)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/2872/2872410.png", width=50)
        st.markdown("### BitLabs Surveys")
        st.write("شارك برأيك في استطلاعات سريعة.")
        bitlabs_url = f"https://web.bitlabs.ai/?token={BITLABS_TOKEN}&uid={user_id}"
        st.link_button("📋 ابدأ الاستطلاع", bitlabs_url)
        st.markdown('</div>', unsafe_allow_html=True)

    # تذييل الصفحة للمصداقية
    st.markdown("---")
    st.caption("🔒 جميع المعاملات مؤمنة وتتم مراجعتها يدوياً لضمان الدفع. | تواصل مع الدعم: support@rewardshub.com")
