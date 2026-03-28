import streamlit as st
import socket
import psycopg2
import time
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

# --- 1. SECRETS & SUPABASE ---
try:
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets missing! Please check Streamlit Cloud Settings.")
    st.stop()

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

st.set_page_config(page_title="Amit GPS Pro - Master Console", layout="wide")

# --- 2. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'running' not in st.session_state: st.session_state.running = False
if 'custom_running' not in st.session_state: st.session_state.custom_running = False

# --- 3. HELPER FUNCTIONS ---
def get_ais140_checksum(payload):
    checksum = 0
    for char in payload:
        checksum ^= ord(char)
    return f"{checksum:02X}"

# --- 4. LOGIN UI ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Login")
    with st.form("login_form"):
        u = st.text_input("Email").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": u, "password": p})
                if res.user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = u
                    st.rerun()
                else: st.error("Invalid Credentials")
            except: st.error("Login Failed.")
    st.stop()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    comp_name = st.text_input("GPS Company Tag", "WTEX") # Updated as per your screen
    imei = st.text_input("IMEI Number", "862491076910809")
    veh_no = st.text_input("Vehicle Number", "BR01GH9898")
    srv_ip = st.text_input("Server Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Interval (sec)", 0.5, 10.0, 1.0)
    loc_mode = st.radio("📍 Location Source", ["Automatic (GPS)", "Manual Input"], index=1)
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. ADMIN UI ---
if st.session_state.user_email == "amit@admin.com":
    st.title("🌟 Amit GPS Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["🚀 Tracking Terminal", "📊 Database Records", "💻 Custom Auto-Terminal"])
    
    with tab1:
        col_l, col_r = st.columns([1.2, 1])
        with col_l:
            st.subheader("📡 GPS Control")
            loc = get_geolocation()
            lat_v = st.number_input("Lat", value=25.6509450, format="%.7f")
            lon_v = st.number_input("Lon", value=84.7847730, format="%.7f")
            
            if st.button("▶️ START AUTOMATIC", type="primary"): st.session_state.running = True
            if st.button("⏹️ STOP ENGINE"): st.session_state.running = False
            
            status_msg = st.empty()
            p_bar = st.progress(0)
        
        with col_r:
            st.map(pd.DataFrame({'lat': [lat_v], 'lon': [lon_v]}), zoom=14)

# --- 7. BACKGROUND LOOP (FIXED PAYLOAD) ---
if st.session_state.running:
    try:
        conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
        cur = conn.cursor()
        while st.session_state.running:
            now = datetime.now()
            # As per your requirement: No comma before Checksum
            payload = f"PVT,{comp_name},2.1.1,NR,01,L,{imei},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{lat_v:.7f},N,{lon_v:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            cs = get_ais140_checksum(payload)
            final_packet = f"${payload},{cs}*\r\n" # Fixed format
            
            try:
                with socket.create_connection((srv_ip, srv_port), timeout=1) as s:
                    s.sendall(final_packet.encode('ascii'))
                res_text = f"✅ SENT TO SERVER"
            except: res_text = "❌ SERVER ERROR"
            
            cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_v, lon_v, final_packet.strip(), veh_no))
            conn.commit()
            status_msg.info(f"{res_text} | CS: {cs}")
            p_bar.progress(100)
            time.sleep(interval)
            p_bar.progress(0)
    except Exception as e:
        st.error(f"DB Error: {e}")
        st.session_state.running = False
