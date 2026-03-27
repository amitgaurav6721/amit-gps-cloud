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
    st.error("Secrets missing in Streamlit!")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Amit GPS Pro - Fixed", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'running' not in st.session_state: st.session_state.running = False

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Login")
    with st.form("login"):
        u = st.text_input("Email").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                # Email confirm OFF hai, toh ab ye direct login hoga
                res = supabase.auth.sign_in_with_password({"email": u, "password": p})
                if res.user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = u
                    st.rerun()
            except Exception as e:
                st.error(f"Login Failed: {e}")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    imei = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Server IP", "103.30.179.201")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Interval (sec)", 1.0, 10.0, 1.0)
    loc_mode = st.radio("📍 Location", ["Automatic (GPS)", "Manual Input"], horizontal=True)
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- MAIN UI ---
st.title("🛰️ Amit GPS Cloud Terminal")
col_l, col_r = st.columns([1.2, 1])

with col_l:
    loc = get_geolocation()
    curr_lat = loc['coords']['latitude'] if loc else 24.9194
    curr_lon = loc['coords']['longitude'] if loc else 83.7905
    
    c1, c2 = st.columns(2)
    lat_val = c1.number_input("Lat", value=float(curr_lat), format="%.7f", disabled=(loc_mode=="Automatic (GPS)"))
    lon_val = c2.number_input("Lon", value=float(curr_lon), format="%.7f", disabled=(loc_mode=="Automatic (GPS)"))

    if st.button("🚀 START SENDING", type="primary", use_container_width=True): st.session_state.running = True
    if st.button("🛑 STOP ENGINE", type="secondary", use_container_width=True): st.session_state.running = False
    
    st.divider()
    status_msg = st.empty()
    p_bar = st.progress(0)

with col_r:
    map_df = pd.DataFrame({'lat': [lat_val], 'lon': [lon_val]})
    st.map(map_df, zoom=14)

# --- DATA SENDING LOGIC ---
if st.session_state.running:
    try:
        # Port 6543 (Pooler) use kar rahe hain connection error se bachne ke liye
        conn = psycopg2.connect(
            host="aws-0-ap-south-1.pooler.supabase.com", # <--- Apna naya Host yahan check karein
            database="postgres",
            user="postgres.grdgexcjyrhkoffimsuw", 
            password=DB_PASSWORD,
            port="6543",
            sslmode="require"
        )
        cur = conn.cursor()
        
        while st.session_state.running:
            for i in range(1, 101, 20):
                p_bar.progress(i)
                time.sleep(interval/5)
            
            now = datetime.now()
            payload = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{lat_val},N,{lon_val},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            packet = f"${payload}*BABA\r\n"

            # 1. Server Push
            try:
                with socket.create_connection((srv_ip, srv_port), timeout=1) as s:
                    s.sendall(packet.encode('ascii'))
                server_res = "✅ SENT"
            except: server_res = "❌ OFFLINE"

            # 2. Database Log
            cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_val, lon_val, packet.strip(), veh_no))
            conn.commit()
            
            status_msg.info(f"Server: {server_res} | DB: ✅ LOGGED | Time: {now.strftime('%H:%M:%S')}")
            if not st.session_state.running: break
    except Exception as e:
        st.error(f"Conn Error: {e}")
        st.session_state.running = False
