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
    st.error("Secrets missing! Check Streamlit Settings.")
    st.stop()

if 'supabase' not in st.session_state:
    st.session_state.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Amit GPS Pro - Terminal Edition", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'running' not in st.session_state: st.session_state.running = False

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
    st.caption(f"Connected: {st.session_state.user_email}")
    imei = st.text_input("IMEI Number", "862567075041793")
    veh_no = st.text_input("Vehicle Number", "BR04GA5974")
    srv_ip = st.text_input("Server Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Interval (sec)", 1.0, 10.0, 2.0)
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- ADMIN DASHBOARD ---
is_admin = (st.session_state.user_email == "amit@admin.com")

if is_admin:
    st.title("🌟 Amit GPS Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["🚀 Tracking Terminal", "📊 Database Records", "💻 Custom Command"])
    
    with tab3:
        st.subheader("Direct TCP Terminal (Like PlayStore App)")
        st.info("यहाँ आप कोई भी Custom Packet टाइप करके सीधे सर्वर को भेज सकते हैं।")
        custom_packet = st.text_area("Type your message here", value=f"$PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{datetime.now().strftime('%d%m%Y,%H%M%S')},24.9194,N,83.7905,E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041*BABA\r\n")
        
        if st.button("📤 SEND CUSTOM PACKET", type="primary"):
            try:
                with socket.create_connection((srv_ip, srv_port), timeout=2) as s:
                    s.sendall(custom_packet.encode('ascii'))
                st.success(f"Sent to {srv_ip}:{srv_port} successfully!")
            except Exception as e:
                st.error(f"Failed to send: {e}")

    with tab2:
        st.subheader("Live Database Logs")
        try:
            conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
            df = pd.read_sql("SELECT created_at, imei, vehicle_no, latitude, longitude, raw_packet FROM gps_data ORDER BY created_at DESC LIMIT 20", conn)
            st.dataframe(df, use_container_width=True)
            conn.close()
        except: st.warning("Connecting to database...")

    with tab1:
        col_l, col_r = st.columns([1.2, 1])
else:
    st.title("🛰️ Amit GPS User Terminal")
    col_l, col_r = st.columns([1.2, 1])

# --- COMMON TRACKING UI ---
with col_l:
    loc = get_geolocation()
    lat_v = st.number_input("Lat", value=float(loc['coords']['latitude'] if loc else 24.9194), format="%.7f")
    lon_v = st.number_input("Lon", value=float(loc['coords']['longitude'] if loc else 83.7905), format="%.7f")
    
    if st.button("🚀 START AUTOMATIC SENDING", type="primary", use_container_width=True): st.session_state.running = True
    if st.button("🛑 STOP ENGINE", type="secondary", use_container_width=True): st.session_state.running = False
    
    status_msg = st.empty()
    p_bar = st.progress(0)

with col_r:
    st.map(pd.DataFrame({'lat': [lat_v], 'lon': [lon_v]}), zoom=14)

# --- LOOP LOGIC ---
if st.session_state.running:
    try:
        conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
        cur = conn.cursor()
        while st.session_state.running:
            for i in range(1, 101, 20): p_bar.progress(i); time.sleep(interval/5)
            now = datetime.now()
            payload = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{lat_v},N,{lon_v},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            packet = f"${payload}*BABA\r\n"
            try:
                with socket.create_connection((srv_ip, srv_port), timeout=1) as s: s.sendall(packet.encode('ascii'))
                server_res = "✅ SENT"
            except: server_res = "❌ FAIL"
            cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_v, lon_v, packet.strip(), veh_no))
            conn.commit()
            status_msg.info(f"Server: {server_res} | DB: ✅ LOGGED | {now.strftime('%H:%M:%S')}")
            if not st.session_state.running: break
    except Exception as e: 
        st.error(f"Error: {e}")
        st.session_state.running = False
