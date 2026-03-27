import streamlit as st
import socket
import psycopg2
import time
import pandas as pd # Map के लिए ज़रूरी
from datetime import datetime
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

# --- CONFIG & SECRETS ---
try:
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets missing! Please check Streamlit Settings.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Amit GPS Pro - Map View", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'running' not in st.session_state: st.session_state.running = False

# --- LOGIN SYSTEM ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Login")
    with st.form("login_form"):
        u_email = st.text_input("Email").strip().lower()
        u_pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                auth = supabase.auth.sign_in_with_password({"email": u_email, "password": u_pwd})
                if auth.user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = u_email
                    st.rerun()
            except: st.error("Invalid Credentials")
    st.stop()

# --- SIDEBAR ---
st.sidebar.info(f"User: {st.session_state.user_email}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# --- MAIN LAYOUT (Two Columns) ---
st.title("🛰️ Amit GPS Live Tracking Center")
col_ctrl, col_map = st.columns([1, 1]) # स्क्रीन को दो हिस्सों में बाँटा

with col_ctrl:
    st.subheader("Controls")
    loc = get_geolocation()
    lat_now = loc['coords']['latitude'] if loc else 24.9194
    lon_now = loc['coords']['longitude'] if loc else 83.7905

    lat_input = st.number_input("Latitude", value=float(lat_now), format="%.7f")
    lon_input = st.number_input("Longitude", value=float(lon_now), format="%.7f")

    c1, c2 = st.columns(2)
    start = c1.button("🚀 START", type="primary", use_container_width=True)
    stop = c2.button("🛑 STOP", type="secondary", use_container_width=True)
    
    if start: st.session_state.running = True
    if stop: st.session_state.running = False

    status_box = st.empty()

with col_map:
    st.subheader("Live Map View")
    # Map डेटा तैयार करना
    map_data = pd.DataFrame({'lat': [lat_input], 'lon': [lon_input]})
    st.map(map_data, zoom=12) # यह स्क्रीन के दाईं तरफ मैप दिखाएगा

# --- DATA TRANSMISSION ---
if st.session_state.running:
    try:
        conn = psycopg2.connect(host="db.grdgexcjyrhkoffimsuw.supabase.co", database="postgres", user="postgres", password=DB_PASSWORD, port="5432", sslmode="require")
        cur = conn.cursor()
        
        while st.session_state.running:
            now = datetime.now()
            imei, v_no = "862567075041793", "BR04GA5974"
            payload = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{v_no},1,{now.strftime('%d%m%Y,%H%M%S')},{lat_input},N,{lon_input},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            
            cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_input, lon_input, payload, v_no))
            conn.commit()
            
            status_box.success(f"✅ Packet Sent: {now.strftime('%H:%M:%S')}")
            time.sleep(1) # 1 second interval
            if not st.session_state.running: break
    except Exception as e: st.error(e)
