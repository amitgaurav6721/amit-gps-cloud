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

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Amit GPS Admin Console", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- LOGIN ---
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

# --- ADMIN CHECK ---
is_admin = (st.session_state.user_email == "amit@admin.com")

if is_admin:
    st.title("🌟 Amit GPS Admin Dashboard")
    # YAHAN HAI OPTION: Humne 3 Tabs bana diye hain
    tab1, tab2, tab3 = st.tabs(["🚀 Tracking", "📊 Database", "👤 User Management"])
    
    with tab3:
        st.subheader("Add New User to System")
        with st.form("add_user_form"):
            new_email = st.text_input("New Email")
            new_pass = st.text_input("New Password", type="password")
            if st.form_submit_button("Create User"):
                try:
                    # Admin privileges to create user
                    supabase.auth.admin.create_user({
                        "email": new_email,
                        "password": new_pass,
                        "email_confirm": True
                    })
                    st.success(f"User {new_email} added successfully!")
                except Exception as e:
                    st.error(f"Error creating user: {e}")

    with tab2:
        st.subheader("Live Database Records")
        try:
            conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
            df = pd.read_sql("SELECT created_at, imei, vehicle_no, latitude, longitude FROM gps_data ORDER BY created_at DESC LIMIT 20", conn)
            st.dataframe(df, use_container_width=True)
            conn.close()
        except: st.warning("Database currently empty or connecting...")

    with tab1:
        col_l, col_r = st.columns([1.2, 1])
else:
    st.title("🛰️ Amit GPS User Terminal")
    col_l, col_r = st.columns([1.2, 1])

# --- TRACKING UI ---
with col_l:
    loc = get_geolocation()
    lat_val = st.number_input("Lat", value=float(loc['coords']['latitude'] if loc else 24.9194), format="%.7f", disabled=(loc_mode=="Automatic (GPS)"))
    lon_val = st.number_input("Lon", value=float(loc['coords']['longitude'] if loc else 83.7905), format="%.7f", disabled=(loc_mode=="Automatic (GPS)"))
    
    if st.button("🚀 START SENDING", type="primary", use_container_width=True): st.session_state.running = True
    if st.button("🛑 STOP ENGINE", type="secondary", use_container_width=True): st.session_state.running = False
    
    status_msg = st.empty()
    p_bar = st.progress(0)

with col_r:
    map_df = pd.DataFrame({'lat': [lat_val], 'lon': [lon_val]})
    st.map(map_df, zoom=14)

# --- SENDING LOGIC ---
if st.session_state.get('running', False):
    try:
        conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
        cur = conn.cursor()
        while st.session_state.running:
            for i in range(1, 101, 20): p_bar.progress(i); time.sleep(interval/5)
            now = datetime.now()
            payload = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{lat_val},N,{lon_val},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            packet = f"${payload}*BABA\r\n"
            try:
                with socket.create_connection((srv_ip, srv_port), timeout=1) as s: s.sendall(packet.encode('ascii'))
                server_res = "✅ SENT"
            except: server_res = "❌ FAIL"
            cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_val, lon_val, packet.strip(), veh_no))
            conn.commit()
            status_msg.info(f"Server: {server_res} | DB: ✅ LOGGED | Time: {now.strftime('%H:%M:%S')}")
            if not st.session_state.running: break
    except Exception as e: st.error(f"Error: {e}"); st.session_state.running = False
