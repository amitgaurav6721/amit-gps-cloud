import streamlit as st
import socket
import time
import requests
import pandas as pd
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(page_title="Amit GPS Master Hybrid", layout="wide", page_icon="🛰️")

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# Session State Initialization
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'running' not in st.session_state: st.session_state.running = False
if 'manual_running' not in st.session_state: st.session_state.manual_running = False
if 'logs' not in st.session_state: st.session_state.logs = []
if 'tag_status' not in st.session_state: st.session_state.tag_status = {}
if 'extended_tags' not in st.session_state: 
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0

# --- 2. HELPERS ---
def get_checksum(body):
    cs = 0
    for c in body: cs ^= ord(c)
    return f"{cs:02X}"

def log_to_supabase(data):
    """Saves to public.gps_logs table"""
    url = f"{SUPABASE_URL}/rest/v1/gps_logs"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try: requests.post(url, json=data, headers=headers, timeout=1)
    except: pass

def login_user(email, password):
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    try:
        res = requests.post(url, json={"email": email, "password": password}, headers=headers)
        if res.status_code == 200:
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("❌ Login Failed")
    except: st.error("⚠️ Connection Error")

# --- 3. LOGIN SCREEN ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🛰️ Amit GPS Master</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            u_email = st.text_input("Email", value="amit@admin.com")
            u_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                login_user(u_email, u_pass)
    st.stop()

# --- 4. DASHBOARD UI ---
with st.sidebar:
    st.header("⚙️ Configuration")
    imei_val = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.title("🛰️ Bihar VLTS Live Console")
tab1, tab2 = st.tabs(["🔄 Live Rotator", "📥 Static Bulk Mode"])

with tab1:
    col_l, col_r = st.columns([2, 1])
    with col_l:
        lat_live = st.number_input("Lat", value=25.650945, format="%.6f", key="l_lat")
        lon_live = st.number_input("Lon", value=84.784773, format="%.6f", key="l_lon")
        st.map(pd.DataFrame({'lat': [lat_live], 'lon': [lon_live]}), height=250)
    with col_r:
        gap = st.slider("Speed (Sec)", 0.05, 2.0, 0.50)
        sel_tags = [t for t in st.session_state.extended_tags if st.checkbox(f"{t}", value=True, key=f"t_{t}")]
        if st.button("🚀 START LIVE"): st.session_state.running = True
        if st.button("⏹️ STOP LIVE"): st.session_state.running = False

with tab2:
    st.subheader("Manual Bulk Sender")
    col_s1, col_s2, col_s3 = st.columns(3)
    m_tag = col_s1.selectbox("Tag", st.session_state.extended_tags)
    m_count = col_s2.number_input("Count", min_value=1, value=10)
    m_gap = col_s3.number_input("Interval", min_value=0.1, value=1.0)
    m_lat = st.number_input("Manual Lat", value=25.650945, format="%.6f")
    m_lon = st.number_input("Manual Lon", value=84.784773, format="%.6f")
    if st.button("📤 START BULK"): st.session_state.manual_running = True
    if st.button("🛑 STOP BULK"): st.session_state.manual_running = False

st.markdown("---")
log_area = st.empty()
raw_area = st.empty()

# --- 5. EXECUTION ENGINE ---

# Persistent Socket Logic
def run_transmission(target_tag, target_lat, target_lon, is_manual=False):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((srv_ip, srv_port))
            
            # Loop handler
            count_limit = int(m_count) if is_manual else 999999
            current_count = 0
            
            while (st.session_state.running or st.session_state.manual_running) and current_count < count_limit:
                # Determine tag for rotator vs manual
                tag = target_tag if is_manual else sel_tags[st.session_state.current_idx % len(sel_tags)]
                now = datetime.now()
                
                body = f"PVT,{tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{target_lat:08.6f},N,{target_lon:09.6f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83"
                pkt = f"${body},{get_checksum(body)}*\r\n"
                
                start_t = time.time()
                s.sendall(pkt.encode('ascii'))
                lat_ms = int((time.time() - start_t) * 1000)
                
                # UI & DB Logging
                st.session_state.logs.insert(0, f"{now.strftime('%H:%M:%S')} | {'📥' if is_manual else '🟢'} {tag} | {lat_ms}ms")
                log_area.code("\n".join(st.session_state.logs[:15]))
                raw_area.code(pkt.strip())
                
                log_to_supabase({
                    "imei": imei_val, "tag": tag, "lat": target_lat, "lon": target_lon,
                    "packet": pkt.strip(), "status": "SENT", "latency": f"{lat_ms}ms"
                })
                
                current_count += 1
                st.session_state.current_idx += 1
                time.sleep(m_gap if is_manual else gap)
                st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
        st.session_state.running = False
        st.session_state.manual_running = False

if st.session_state.manual_running:
    run_transmission(m_tag, m_lat, m_lon, is_manual=True)
    st.session_state.manual_running = False
    st.rerun()

if st.session_state.running:
    run_transmission(None, lat_live, lon_live, is_manual=False)
