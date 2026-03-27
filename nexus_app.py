import streamlit as st
import socket
import psycopg2
import time
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

# --- 1. CONFIG & SECRETS ---
try:
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets missing in Streamlit Cloud!")
    st.stop()

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

st.set_page_config(page_title="Amit GPS Universal", layout="wide")

# --- 2. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'running' not in st.session_state: st.session_state.running = False

# --- 3. LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Login")
    u = st.text_input("Email").strip().lower()
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": u, "password": p})
            if res.user:
                st.session_state.logged_in = True
                st.session_state.user_email = u
                st.rerun()
        except: st.error("Login Failed")
    st.stop()

# --- 4. SIDEBAR & PROTOCOL SELECTOR ---
with st.sidebar:
    st.header("⚙️ Settings")
    # यूजर यहाँ से पेलोड चुन सकता है
    proto = st.selectbox("📜 Select Payload Type", ["$PVT (EGAS)", "$GPRMC (WTEX)", "$,100 (WTEX)"])
    
    imei = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle No", "BR04GA5974")
    srv_ip = st.text_input("Server", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Interval (sec)", 0.5, 10.0, 1.0)
    
    st.divider()
    loc_mode = st.radio("📍 Mode", ["Automatic", "Manual"])
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 5. MAIN UI ---
st.title(f"🛰️ Sending via: {proto}")
col1, col2 = st.columns([1, 1.5])

with col1:
    loc = get_geolocation()
    lat = st.number_input("Lat", value=float(loc['coords']['latitude'] if
