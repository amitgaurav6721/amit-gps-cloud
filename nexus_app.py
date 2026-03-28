import streamlit as st
import socket
import psycopg2
import time
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

# --- 1. SECRETS & SUPABASE (Fixed for Single Login) ---
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

# --- 2. SESSION STATE MANAGEMENT ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'running' not in st.session_state: st.session_state.running = False
if 'custom_running' not in st.session_state: st.session_state.custom_running = False

# --- 3. LOGIN UI (One-Click Fix) ---
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
            except: st.error("Login Failed. Check Internet or User.")
    st.stop()

# --- 4. SIDEBAR (Location Switch and Config) ---
with st.sidebar:
    st.header("⚙️ Configuration")
    st.success(f"Logged in: {st.session_state.user_email}")
    imei = st.text_input("IMEI Number", "862567075041793")
    veh_no = st.text_input("Vehicle Number", "BR04GA5974")
    srv_ip = st.text_input("Server Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Interval (sec)", 0.5, 10.0, 1.0)
    
    st.divider()
    # ✅ Location Switch Wapas Aa Gya
    loc_mode = st.radio("📍 Location Source", ["Automatic (GPS)", "Manual Input"], horizontal=True)
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 5. ADMIN UI ---
is_admin = (st.session_state.user_email == "amit@admin.com")

if is_admin:
    st.title("🌟 Amit GPS Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["🚀 Tracking Terminal", "📊 Database Records", "💻 Custom Auto-Terminal"])
    
    with tab1: # TRACKING TERMINAL
        col_l, col_r = st.columns([1.2, 1])
        with col_l:
            st.subheader("📡 GPS Control")
            loc = get_geolocation()
            
            # Switch Logic for Lat/Lon
            default_lat = float(loc['coords']['latitude']) if (loc and loc_mode == "Automatic (GPS)") else 24.9194
            default_lon = float(loc['coords']['longitude']) if (loc and loc_mode == "Automatic (GPS)") else 83.7905
            
            lat_v = st.number_input("Lat", value=default_lat, format="%.7f", disabled=(loc_mode=="Automatic (GPS)"))
            lon_v = st.number_input("Lon", value=default_lon, format="%.7f", disabled=(loc_mode=="Automatic (GPS)"))
            
            if st.button("▶️ START AUTOMATIC", type="primary", use_container_width=True): st.session_state.running = True
            if st.button("⏹️ STOP ENGINE", type="secondary", use_container_width=True): st.session_state.running = False
            
            status_msg = st.empty()
            p_bar = st.progress(0)
        
        with col_r:
            st.subheader("🗺️ Live Map")
            st.map(pd.DataFrame({'lat': [lat_v], 'lon': [lon_v]}), zoom=14)

    with tab2: # DATABASE
        st.subheader("Live Database Logs")
        try:
            conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
            df = pd.read_sql("SELECT created_at, imei, vehicle_no, latitude, longitude, raw_packet FROM gps_data ORDER BY created_at DESC LIMIT 20", conn)
            st.dataframe(df, use_container_width=True)
            conn.close()
        except: st.warning("Connecting to database...")

    with tab3: # CUSTOM TERMINAL
        st.subheader("🤖 Auto-Custom Packet")
        c_msg = st.text_area("Packet to Loop", value=f"$PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{datetime.now().strftime('%d%m%Y,%H%M%S')},24.9194,N,83.7905,E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041*BABA\r\n", height=150)
        c1, c2 = st.columns(2)
        if c1.button("▶️ START CUSTOM", key="c_on"): st.session_state.custom_running = True
        if c2.button("⏹️ STOP CUSTOM", key="c_off"): st.session_state.custom_running = False
        c_stat = st.empty()

# --- 6. BACKGROUND LOOPS ---

# Loop 1: Standard Tracking
if st.session_state.running:
    try:
        conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
        cur = conn.cursor()
        while st.session_state.running:
            p_bar.progress(100)
            now = datetime.now()
            payload = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{lat_v},N,{lon_v},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            packet = f"${payload}*BABA\r\n"
            try:
                with socket.create_connection((srv_ip, srv_port), timeout=1) as s: s.sendall(packet.encode('ascii'))
                res = "✅ SENT"
            except: res = "❌ FAIL"
            cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_v, lon_v, packet.strip(), veh_no))
            conn.commit()
            status_msg.info(f"Server: {res} | Time: {now.strftime('%H:%M:%S')}")
            time.sleep(interval)
            if not st.session_state.running: break
    except: st.session_state.running = False

# Loop 2: Custom Terminal
if st.session_state.custom_running:
    try:
        while st.session_state.custom_running:
            with socket.create_connection((srv_ip, srv_port), timeout=2) as s:
                s.sendall(c_msg.encode('ascii'))
            c_stat.success(f"🚀 Custom Sent at {datetime.now().strftime('%H:%M:%S')}")
            time.sleep(interval)
            if not st.session_state.custom_running: break
    except: st.session_state.custom_running = False
