import streamlit as st
import socket
import psycopg2
import time
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

# --- SECRETS ---
try:
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets missing!")
    st.stop()

if 'supabase' not in st.session_state:
    st.session_state.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Amit GPS Pro - Auto Terminal", layout="wide")

# --- SESSION STATES ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'running' not in st.session_state: st.session_state.running = False
if 'custom_running' not in st.session_state: st.session_state.custom_running = False

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Login")
    with st.form("login_form"):
        u = st.text_input("Email").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            try:
                res = st.session_state.supabase.auth.sign_in_with_password({"email": u, "password": p})
                if res.user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = u
                    st.rerun()
                else: st.error("Invalid Credentials")
            except: st.error("Login Failed")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    st.caption(f"User: {st.session_state.user_email}")
    imei = st.text_input("IMEI Number", "862567075041793")
    veh_no = st.text_input("Vehicle Number", "BR04GA5974")
    srv_ip = st.text_input("Server Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Interval (sec)", 0.5, 10.0, 1.0) # 1 sec default
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- ADMIN PANEL ---
is_admin = (st.session_state.user_email == "amit@admin.com")

if is_admin:
    st.title("🌟 Amit GPS Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["🚀 Tracking Terminal", "📊 Database Records", "💻 Custom Auto-Terminal"])
    
    with tab3:
        st.subheader("🤖 Automatic Custom Command")
        st.info("यहाँ लिखा मैसेज हर 1 सेकंड (या आपके सेट किए इंटरवल) पर लगातार भेजा जाएगा।")
        
        c_msg = st.text_area("Custom Packet to Loop", value=f"$PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{datetime.now().strftime('%d%m%Y,%H%M%S')},24.9194,N,83.7905,E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041*BABA\r\n", height=150)
        
        col1, col2 = st.columns(2)
        if col1.button("▶️ START AUTO SEND", type="primary", use_container_width=True):
            st.session_state.custom_running = True
        if col2.button("⏹️ STOP SENDING", type="secondary", use_container_width=True):
            st.session_state.custom_running = False

        c_status = st.empty()
        
        # --- CUSTOM LOOP LOGIC ---
        if st.session_state.custom_running:
            try:
                while st.session_state.custom_running:
                    with socket.create_connection((srv_ip, srv_port), timeout=2) as s:
                        s.sendall(c_msg.encode('ascii'))
                    c_status.success(f"🚀 Packet Sent at {datetime.now().strftime('%H:%M:%S')}")
                    time.sleep(interval)
                    if not st.session_state.custom_running: break
            except Exception as e:
                st.error(f"Connection Lost: {e}")
                st.session_state.custom_running = False

    with tab2:
        st.subheader("Live Database Logs")
        try:
            conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
            df = pd.read_sql("SELECT created_at, imei, vehicle_no, latitude, longitude, raw_packet FROM gps_data ORDER BY created_at DESC LIMIT 20", conn)
            st.dataframe(df, use_container_width=True)
            conn.close()
        except: st.warning("Connecting to database...")

    with tab1:
        # Standard Tracking UI
        col_l, col_r = st.columns([1.2, 1])
        # ... (बाकी पुराना ट्रैकिंग कोड यहाँ रहेगा) ...
