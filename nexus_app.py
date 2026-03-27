import streamlit as st
import socket
import psycopg2
import time
from datetime import datetime
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

# --- SECRETS LOAD ---
try:
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets missing in Streamlit Settings!")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Amit GPS Pro", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'running' not in st.session_state: st.session_state.running = False

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Login")
    with st.form("login"):
        u = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                supabase.auth.sign_in_with_password({"email": u, "password": p})
                st.session_state.logged_in = True
                st.session_state.user_email = u
                st.rerun()
            except: st.error("Invalid Login")
    st.stop()

# --- APP UI ---
st.sidebar.write(f"Logged in: **{st.session_state.user_email}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# --- ADMIN SECTION ---
if st.session_state.user_email == "amit@admin.com":
    with st.sidebar.expander("⭐ Admin: Create User"):
        n_e = st.text_input("New Email")
        n_p = st.text_input("New Password")
        if st.button("Register User"):
            try:
                supabase.auth.admin.create_user({"email": n_e, "password": n_p, "email_confirm": True})
                st.success("Done!")
            except Exception as e: st.error(e)

# --- GPS TRACKER PANEL (यह हिस्सा गायब था) ---
st.title("🚀 Live GPS Tracker")

# 1. Location Logic
loc = get_geolocation()
lat_now = loc['coords']['latitude'] if loc else 25.6501
lon_now = loc['coords']['longitude'] if loc else 84.7851

col1, col2 = st.columns(2)
lat_val = col1.number_input("Latitude", value=float(lat_now), format="%.7f")
lon_val = col2.number_input("Longitude", value=float(lon_now), format="%.7f")

# 2. Controls
c1, c2 = st.columns(2)
if c1.button("🚀 START ENGINE", type="primary"): st.session_state.running = True
if c2.button("🛑 STOP ENGINE"): st.session_state.running = False

# 3. Transmission
if st.session_state.running:
    progress = st.progress(0)
    status = st.empty()
    try:
        conn = psycopg2.connect(host="db.grdgexcjyrhkoffimsuw.supabase.co", database="postgres", user="postgres", password=DB_PASSWORD, port="5432", sslmode="require")
        cur = conn.cursor()
        while st.session_state.running:
            for i in range(1, 101, 10):
                progress.progress(i)
                time.sleep(0.1)
            
            now = datetime.now()
            # Packet & DB Logic
            payload = f"PVT,EGAS,2.1.1,NR,01,L,862567075041793,BR04GA5974,1,{now.strftime('%d%m%Y,%H%M%S')},{lat_val},N,{lon_val},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", ("862567075041793", lat_val, lon_val, payload, "BR04GA5974"))
            conn.commit()
            status.success(f"Sent at {now.strftime('%H:%M:%S')}")
    except Exception as e: st.error(e)
