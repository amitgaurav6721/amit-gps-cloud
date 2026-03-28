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
except Exception as e:
    st.error(f"Secrets missing or corrupted: {e}")
    st.stop()

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

st.set_page_config(page_title="Amit GPS Hybrid Console", layout="wide")

# --- 2. SESSION STATE MANAGEMENT ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'running' not in st.session_state:
    st.session_state.running = False

# --- 3. AIS-140 CHECKSUM ENGINE ---
def get_ais140_checksum(payload):
    checksum = 0
    for char in payload:
        checksum ^= ord(char)
    return f"{checksum:02X}"

# --- 4. LOGIN LOGIC ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Hybrid Login")
    with st.form("login_gate"):
        u_input = st.text_input("Email").strip().lower()
        p_input = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login", use_container_width=True)
        if submit_button:
            if u_input and p_input:
                try:
                    res = supabase.auth.sign_in_with_password({"email": u_input, "password": p_input})
                    if res.user:
                        st.session_state.logged_in = True
                        st.session_state.user_email = u_input
                        st.rerun()
                    else:
                        st.error("Authentication failed: User not found.")
                except Exception as e:
                    st.error(f"🚨 Login Error Detail: {e}")
            else:
                st.warning("Please enter both email and password.")
    st.stop()

# --- 5. SIDEBAR CONFIG ---
with st.sidebar:
    st.header("⚙️ Configuration")
    st.success(f"User: {st.session_state.user_email}")
    comp_name = st.text_input("Company Tag", "WTEX") 
    imei = st.text_input("IMEI Number", "862491076910809")
    veh_no = st.text_input("Vehicle Number", "BR01GH9898")
    srv_ip = st.text_input("Server Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Interval (sec)", 0.5, 10.0, 1.0)
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.running = False
        st.rerun()

# --- 6. ADMIN DASHBOARD UI ---
if st.session_state.user_email == "amit@admin.com":
    st.title("🌟 Dual-Engine Tracking Console")
    col_l, col_r = st.columns([1.2, 1])
    with col_l:
        st.subheader("📡 GPS Control")
        lat_v = st.number_input("Lat", value=25.6509450, format="%.7f")
        lon_v = st.number_input("Lon", value=84.7847730, format="%.7f")
        c1, c2 = st.columns(2)
        if c1.button("▶️ START ENGINE", type="primary", use_container_width=True):
            st.session_state.running = True
        if c2.button("⏹️ STOP ENGINE", use_container_width=True):
            st.session_state.running = False
            st.rerun()
        status_msg = st.empty()
        p_bar = st.progress(0)
    with col_r:
        st.map(pd.DataFrame({'lat': [lat_v], 'lon': [lon_v]}), zoom=14)

# --- 7. HYBRID DUAL LOOP (Optimized) ---
if st.session_state.running:
    try:
        conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
        cur = conn.cursor()
        packet_count = 0 # Counter shuru
        
        while st.session_state.running:
            start_time = time.time()
            now = datetime.now()
            d, t = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
            packet_count += 1
            
            p1 = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{d},{t},{lat_v},N,{lon_v},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            cs1 = get_ais140_checksum(p1)
            packet_a = f"${p1},{cs1}*\r\n"
            
            p2 = f"PVT,{comp_name},2.1.1,NR,01,L,{imei},{veh_no},1,{d}{t},{lat_v:.7f},N,{lon_v:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            cs2 = get_ais140_checksum(p2)
            packet_b = f"${p2}{cs2}*\r\n"
            
            # 1. Server ko data hamesha bhejenge
            for p in [packet_a, packet_b]:
                try:
                    with socket.create_connection((srv_ip, srv_port), timeout=1) as s:
                        s.sendall(p.encode('ascii'))
                except: pass
            
            # 2. Database mein sirf har 10th packet save karenge
            db_status = "Skipped"
            if packet_count % 10 == 0:
                try:
                    cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_v, lon_v, packet_b.strip(), veh_no))
                    conn.commit()
                    db_status = "Saved ✅"
                except: db_status = "DB Error ❌"
            
            end_time = time.time()
            latency = int((end_time - start_time) * 1000)
            
            status_msg.info(f"⚡ Packets: {packet_count} | Latency: {latency}ms | DB: {db_status}")
            p_bar.progress(100)
            time.sleep(max(0, interval - (end_time - start_time)))
            p_bar.progress(0)
            if not st.session_state.running: break
            
    except Exception as e:
        st.error(f"Error: {e}")
        st.session_state.running = False
