import streamlit as st
import socket
import psycopg2
import time
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

# --- SECRETS LOAD ---
try:
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets missing! Streamlit Settings > Secrets में जाकर Keys भरें।")
    st.stop()

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Amit GPS Pro Console", layout="wide")

# --- SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'running' not in st.session_state: st.session_state.running = False

# --- LOGIN SYSTEM ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Login")
    with st.form("login_form"):
        u = st.text_input("Email").strip().lower()
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                # Login using Supabase Auth
                res = supabase.auth.sign_in_with_password({"email": u, "password": p})
                if res.user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = u
                    st.rerun()
            except Exception as e:
                st.error(f"Login Failed: {e}")
    st.stop()

# --- SIDEBAR: ALL SETTINGS ---
with st.sidebar:
    st.header("⚙️ Device Configuration")
    imei = st.text_input("IMEI Number", "862567075041793")
    veh_no = st.text_input("Vehicle Number", "BR04GA5974")
    srv_ip = st.text_input("Server IP", "103.30.179.201")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Time Interval (sec)", 1.0, 10.0, 1.0)
    
    st.divider()
    loc_mode = st.radio("📍 Location Source", ["Automatic (GPS)", "Manual Input"], horizontal=True)
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- MAIN UI LAYOUT ---
st.title("🛰️ Amit GPS Cloud Terminal")
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("📍 Tracking Data")
    # Location Logic
    loc = get_geolocation()
    curr_lat = loc['coords']['latitude'] if loc else 24.9194
    curr_lon = loc['coords']['longitude'] if loc else 83.7905
    
    c1, c2 = st.columns(2)
    # Location switch logic
    if loc_mode == "Automatic (GPS)":
        lat_val = c1.number_input("Lat", value=float(curr_lat), format="%.7f", disabled=True)
        lon_val = c2.number_input("Lon", value=float(curr_lon), format="%.7f", disabled=True)
    else:
        lat_val = c1.number_input("Lat", value=float(curr_lat), format="%.7f")
        lon_val = c2.number_input("Lon", value=float(curr_lon), format="%.7f")

    st.divider()
    b1, b2 = st.columns(2)
    if b1.button("🚀 START SENDING", type="primary", use_container_width=True): st.session_state.running = True
    if b2.button("🛑 STOP ENGINE", type="secondary", use_container_width=True): st.session_state.running = False
    
    status_msg = st.empty()
    p_bar = st.progress(0)
    packet_box = st.empty()

with col_right:
    st.subheader("🗺️ Live Map View")
    map_df = pd.DataFrame({'lat': [lat_val], 'lon': [lon_val]})
    st.map(map_df, zoom=14)

# --- TRANSMISSION LOGIC (POOLER FIX) ---
if st.session_state.running:
    try:
        # यहाँ हमने Seoul Region का Pooler Host और Port 6543 सेट किया है
        conn = psycopg2.connect(
            host="aws-1-ap-northeast-2.pooler.supabase.com",
            database="postgres",
            user="postgres.grdgexcjyrhkoffimsuw",
            password=DB_PASSWORD,
            port="6543",
            sslmode="require"
        )
        cur = conn.cursor()
        
        while st.session_state.running:
            # Progress bar animation
            for i in range(1, 101, 20):
                p_bar.progress(i)
                time.sleep(interval/5)
            
            now = datetime.now()
            # Packet Generation
            payload = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{lat_val},N,{lon_val},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            packet = f"${payload}*BABA\r\n"

            # 1. External Server Send (Bihar Server)
            try:
                with socket.create_connection((srv_ip, srv_port), timeout=1) as s:
                    s.sendall(packet.encode('ascii'))
                server_res = "✅ SENT"
            except: server_res = "❌ OFFLINE"

            # 2. Supabase Database Log
            try:
                cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", 
                            (imei, lat_val, lon_val, packet.strip(), veh_no))
                conn.commit()
                db_res = "✅ LOGGED"
            except:
                db_res = "⚠️ RETRY"
                conn.rollback()
            
            status_msg.info(f"Server: {server_res} | DB: {db_res} | Time: {now.strftime('%H:%M:%S')}")
            packet_box.code(packet.strip())
            
            if not st.session_state.running: break
            
    except Exception as e:
        st.error(f"Critical Connection Error: {e}")
        st.session_state.running = False
    finally:
        if 'conn' in locals(): conn.close()
