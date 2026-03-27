import streamlit as st
import socket
import psycopg2
import time
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

# --- SECRETS & CONFIG ---
try:
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets missing! Check Streamlit Settings.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Amit GPS Pro - Admin Console", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'running' not in st.session_state: st.session_state.running = False

# --- LOGIN SYSTEM ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Login")
    with st.form("login"):
        u = st.text_input("Email").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": u, "password": p})
                if res.user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = u
                    st.rerun()
            except: st.error("Invalid Credentials")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    imei = st.text_input("IMEI Number", "862567075041793")
    veh_no = st.text_input("Vehicle Number", "BR04GA5974")
    srv_ip = st.text_input("Server IP", "103.30.179.201")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Interval (sec)", 1.0, 10.0, 1.0)
    
    st.divider()
    loc_mode = st.radio("📍 Location Source", ["Automatic (GPS)", "Manual Input"], horizontal=True)
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- UI LOGIC: ADMIN vs USER ---
is_admin = (st.session_state.user_email == "amit@admin.com")

if is_admin:
    st.title("🌟 Amit GPS Admin Dashboard")
    tab1, tab2 = st.tabs(["🚀 Tracking Terminal", "📊 Database Records"])
    
    with tab2:
        st.subheader("Last 20 Packets in Database")
        try:
            conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
            df = pd.read_sql("SELECT created_at, imei, vehicle_no, latitude, longitude FROM gps_data ORDER BY created_at DESC LIMIT 20", conn)
            st.dataframe(df, use_container_width=True)
            conn.close()
        except Exception as e:
            st.error(f"DB Fetch Error: {e}")
    
    with tab1:
        # यहाँ एडमिन के लिए ट्रैकर UI खुलेगा
        col_l, col_r = st.columns([1.2, 1])
else:
    st.title("🛰️ Amit GPS User Terminal")
    col_l, col_r = st.columns([1.2, 1])

# --- TRACKING UI (Common for both but inside Tab for Admin) ---
with col_l:
    st.subheader("📍 Real-time Controls")
    loc = get_geolocation()
    curr_lat = loc['coords']['latitude'] if loc else 24.9194
    curr_lon = loc['coords']['longitude'] if loc else 83.7905
    
    c_lat, c_lon = st.columns(2)
    lat_val = c_lat.number_input("Lat", value=float(curr_lat), format="%.7f", disabled=(loc_mode=="Automatic (GPS)"))
    lon_val = c_lon.number_input("Lon", value=float(curr_lon), format="%.7f", disabled=(loc_mode=="Automatic (GPS)"))

    if st.button("🚀 START SENDING", type="primary", use_container_width=True): st.session_state.running = True
    if st.button("🛑 STOP ENGINE", type="secondary", use_container_width=True): st.session_state.running = False
    
    status_msg = st.empty()
    p_bar = st.progress(0)

with col_r:
    st.subheader("🗺️ Live Map")
    map_df = pd.DataFrame({'lat': [lat_val], 'lon': [lon_val]})
    st.map(map_df, zoom=14)

# --- TRANSMISSION LOGIC ---
if st.session_state.running:
    try:
        conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
        cur = conn.cursor()
        while st.session_state.running:
            for i in range(1, 101, 20):
                p_bar.progress(i)
                time.sleep(interval/5)
            
            now = datetime.now()
            payload = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{lat_val},N,{lon_val},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            packet = f"${payload}*BABA\r\n"

            try:
                with socket.create_connection((srv_ip, srv_port), timeout=1) as s:
                    s.sendall(packet.encode('ascii'))
                server_res = "✅ SENT"
            except: server_res = "❌ OFFLINE"

            cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_val, lon_val, packet.strip(), veh_no))
            conn.commit()
            status_msg.info(f"Server: {server_res} | DB: ✅ LOGGED | Time: {now.strftime('%H:%M:%S')}")
            if not st.session_state.running: break
    except Exception as e:
        st.error(f"Conn Error: {e}")
        st.session_state.running = False
