import streamlit as st
import socket
import time
from datetime import datetime
import pandas as pd
import requests

# --- 1. CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Amit GPS Master Hybrid", layout="wide", page_icon="🛰️")

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_token' not in st.session_state:
    st.session_state.user_token = None
if 'tag_status' not in st.session_state:
    st.session_state.tag_status = {}
if 'extended_tags' not in st.session_state:
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'running' not in st.session_state:
    st.session_state.running = False
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0

# --- 2. FUNCTIONS ---
def login_user(email, password):
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    try:
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            data = res.json()
            st.session_state.authenticated = True
            st.session_state.user_token = data['access_token']
            st.rerun()
        else:
            st.error("❌ Galat Email ya Password")
    except Exception as e:
        st.error(f"⚠️ Auth Error: {e}")

def get_bihar_checksum(payload):
    checksum = 0
    for char in payload: checksum ^= ord(char)
    return f"{checksum:04X}"

def log_to_supabase(imei, lat, lon, packet):
    if not st.session_state.user_token: return
    url = f"{SUPABASE_URL}/rest/v1/gps_data"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {st.session_state.user_token}",
        "Content-Type": "application/json"
    }
    payload = {"imei": str(imei), "latitude": float(lat), "longitude": float(lon), "raw_packet": str(packet)}
    try: requests.post(url, json=payload, headers=headers, timeout=0.4)
    except: pass

# --- 3. MAIN RENDER ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🛰️ Amit GPS Master Hybrid</h1>", unsafe_with_html=True)
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            u_email = st.text_input("Email", value="amit@admin.com")
            u_pass = st.text_input("Password", type="password")
            if st.form_submit_button("🚪 Login", use_container_width=True):
                login_user(u_email, u_pass)
else:
    # --- DASHBOARD ---
    with st.sidebar:
        st.header("⚙️ Settings")
        imei = st.text_input("IMEI", "862567075041793")
        veh_no = st.text_input("Vehicle", "BR04GA5974")
        srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
        srv_port = st.number_input("Port", value=9999)
        gap = st.slider("Speed (Sec)", 0.05, 2.0, 0.50)
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    st.title("🛰️ Bihar VLTS Console")
    lat = st.number_input("Lat", value=25.650945, format="%.6f")
    lon = st.number_input("Lon", value=84.784773, format="%.6f")
    
    selected_tags = [t for t in st.session_state.extended_tags if st.checkbox(f"{st.session_state.tag_status.get(t,'⚪')} {t}", value=True, key=f"t_{t}")]
    
    if st.button("🚀 START"): st.session_state.running = True
    if st.button("⏹️ STOP"): st.session_state.running = False

    if st.session_state.running:
        log_box = st.empty()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5); s.connect((srv_ip, srv_port))
                while st.session_state.running:
                    tag = selected_tags[st.session_state.current_idx % len(selected_tags)]
                    now = datetime.now()
                    body = f"PVT,{tag},2.1.1,NR,01,L,{imei},{veh_no},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{lat:08.6f},N,{lon:09.6f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                    pkt = f"${body},{get_bihar_checksum(body)}*\r\n"
                    try:
                        s.sendall(pkt.encode('ascii'))
                        log_to_supabase(imei, lat, lon, pkt.strip())
                        st.session_state.tag_status[tag] = "✅"
                        log_box.success(f"Sent {tag} | {now.strftime('%H:%M:%S')}")
                    except:
                        st.session_state.tag_status[tag] = "❌"
                        break
                    st.session_state.current_idx += 1
                    time.sleep(gap)
                    st.rerun()
        except:
            st.warning("🔄 Reconnecting..."); time.sleep(1); st.rerun()
