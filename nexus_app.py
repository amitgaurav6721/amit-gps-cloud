import streamlit as st
import socket
import time
from datetime import datetime
import pandas as pd
import requests

# --- 1. CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Amit GPS Master Hybrid", layout="wide", page_icon="🛰️")

# Supabase Credentials (Fixed)
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# Initialize Session States
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_token' not in st.session_state:
    st.session_state.user_token = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'tag_status' not in st.session_state:
    st.session_state.tag_status = {}
if 'extended_tags' not in st.session_state:
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'running' not in st.session_state:
    st.session_state.running = False
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0

# --- 2. AUTHENTICATION FUNCTIONS ---
def login_user(email, password):
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            st.session_state.authenticated = True
            st.session_state.user_token = data['access_token']
            st.session_state.user_email = data['user']['email']
            st.rerun()
        else:
            st.error("❌ Invalid Email or Password")
    except Exception as e:
        st.error(f"⚠️ Auth Error: {e}")

def logout_user():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- 3. CORE GPS LOGIC ---
def get_bihar_checksum(payload):
    checksum = 0
    for char in payload:
        checksum ^= ord(char)
    return f"{checksum:04X}"

def format_coord(val, is_lat=True):
    if is_lat: return f"{val:08.6f}"
    else: return f"{val:09.6f}"

# --- 4. DB LOGGER ---
def log_to_supabase(imei, lat, lon, packet):
    if not st.session_state.user_token: return
    url = f"{SUPABASE_URL}/rest/v1/gps_data"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {st.session_state.user_token}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {
        "imei": str(imei),
        "latitude": float(lat),
        "longitude": float(lon),
        "raw_packet": str(packet)
    }
    try:
        requests.post(url, json=payload, headers=headers, timeout=0.4)
    except:
        pass

# --- 5. MAIN RENDER LOGIC ---
def reset_running():
    st.session_state.running = False

if not st.session_state.authenticated:
    # LOGIN SCREEN (Indentation Checked)
    st.markdown("<h1 style='text-align: center;'>🛰️ Amit GPS Master Hybrid</h1>", unsafe_with_html=True)
    st.markdown("<h3 style='text-align: center;'>Secure Access Login</h3>", unsafe_with_html=True)
    
    _, col2, _ = st.columns
