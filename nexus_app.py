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

st.set_page_config(page_title="Amit GPS Pro - VLTS Ready", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
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
            except: st.error("Invalid Credentials")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ VLTS Config")
    imei = st.text_input("IMEI Number", "862567075041793")
    veh_no = st.text_input("Vehicle Number", "BR04GA5974")
    # Yahan Bihar VLTS ka domain/IP daalein
    srv_ip = st.text_input("Server Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999) 
    interval = st.slider("Interval (sec)", 1.0, 10.0, 2.0)
    st.divider()
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- UI LAYOUT ---
st.title("🛰️ Amit GPS - VLTS Terminal")
col_l, col_r = st.columns([1.2, 1])

with col_l:
    loc = get_geolocation()
    lat_v = st.number_input("Lat", value=float(loc['coords']['latitude'] if loc else 24.9194), format="%.7f")
    lon_v = st.number_input("Lon", value=float(loc['coords']['longitude'] if loc else 83.7905), format="%.7f")
    
    if st.button("🚀 START SENDING", type="primary", use_container_width=True): st.session_state.running = True
    if st.button("🛑 STOP ENGINE", type="secondary", use_container_width=True): st.session_state.running = False
    
    status_msg = st.empty()
    p_bar = st.progress(0)

with col_r:
    st.map(pd.DataFrame({'lat': [lat_v], 'lon': [lon_v]}), zoom=14)

# --- TRANSMISSION LOGIC (Based on TCP Client App) ---
if st.session_state.running:
    try:
        # DB Connection
        conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
        cur = conn.cursor()
        
        while st.session_state.running:
            now = datetime.now()
            # String formatting exactly as Bihar Server expects
            payload = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{lat_v},N,{lon_v},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            full_packet = f"${payload}*BABA\r\n" # Adding \r\n is CRITICAL

            try:
                # TCP Connection simulating the mobile app
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    s.connect((srv_ip, srv_port))
                    s.sendall(full_packet.encode('ascii'))
                    # Check if server responds (Optional)
                server_res = "✅ SENT"
            except Exception as e:
                server_res = f"❌ {str(e)[:10]}"

            # Log to Supabase for Record
            cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_v, lon_v, full_packet.strip(), veh_no))
            conn.commit()
            
            status_msg.info(f"Target: {srv_ip} | Status: {server_res} | Time: {now.strftime('%H:%M:%S')}")
            p_bar.progress(100)
            time.sleep(interval)
            p_bar.progress(0)
            
            if not st.session_state.running: break
    except Exception as e:
        st.error(f"System Error: {e}")
        st.session_state.running = False
