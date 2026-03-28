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
if 'extended_tags' not in st.session_state: 
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0

# --- 2. HELPERS ---
def get_checksum(body):
    cs = 0
    for c in body: cs ^= ord(c)
    return f"{cs:02X}"

def log_to_supabase(data):
    url = f"{SUPABASE_URL}/rest/v1/gps_logs"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    try: requests.post(url, json=data, headers=headers, timeout=1)
    except: pass

def login_user(email, password):
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    try:
        res = requests.post(url, json={"email": email, "password": password}, headers={"apikey": SUPABASE_KEY})
        if res.status_code == 200:
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("❌ Login Failed")
    except: st.error("⚠️ Connection Error")

# --- 3. LOGIN ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🛰️ Amit GPS Master</h1>", unsafe_allow_html=True)
    with st.form("login"):
        u = st.text_input("Email", value="amit@admin.com")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"): login_user(u, p)
    st.stop()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Config")
    imei_val = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    st.markdown("---")
    c_tag = st.text_input("➕ Add Tag").upper().strip()
    if st.button("Add"):
        if c_tag and c_tag not in st.session_state.extended_tags:
            st.session_state.extended_tags.append(c_tag)
            st.rerun()
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

st.title("🛰️ Bihar VLTS Live Console")
tab1, tab2 = st.tabs(["🔄 Live Rotator", "📥 Static Bulk Mode"])

# --- TAB 1: LIVE ---
with tab1:
    col_l, col_r = st.columns([2, 1])
    with col_l:
        l_lat = st.number_input("Lat", value=25.650945, format="%.6f")
        l_lon = st.number_input("Lon", value=84.784773, format="%.6f")
        st.map(pd.DataFrame({'lat': [l_lat], 'lon': [l_lon]}), height=200)
    with col_r:
        gap = st.slider("Speed", 0.05, 2.0, 0.5)
        sel_tags = [t for t in st.session_state.extended_tags if st.checkbox(t, True, key=f"l_{t}")]
        if st.button("🚀 START"): st.session_state.running = True
        if st.button("⏹️ STOP"): st.session_state.running = False

# --- TAB 2: STATIC BULK ---
with tab2:
    col1, col2 = st.columns(2)
    m_count = col1.number_input("Packets Count", 1, 1000, 10)
    m_gap = col2.number_input("Gap (Sec)", 0.1, 5.0, 1.0)
    
    bulk_mode = st.radio("Bulk Method", ["Auto Generate", "Custom String Editor"], horizontal=True)
    
    if bulk_mode == "Auto Generate":
        m_tag = st.selectbox("Tag", st.session_state.extended_tags)
        m_lat = st.number_input("Manual Lat", value=25.650945, format="%.6f")
        m_lon = st.number_input("Manual Lon", value=84.784773, format="%.6f")
        now = datetime.now()
        body = f"PVT,{m_tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{m_lat:08.6f},N,{m_lon:09.6f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83"
        final_pkt = f"${body},{get_checksum(body)}*\r\n"
        st.code(final_pkt.strip())
    else:
        # ✅ MANUAL EDITOR WITH AUTO-CHECKSUM
        raw_input = st.text_area("Packet Body (without $ and *):", 
                                value=f"PVT,GRL,2.1.1,NR,01,L,{imei_val},{veh_no},1,{datetime.now().strftime('%d%m%Y,%H%M%S')},25.650945,N,84.784773,E,0.0,0.0,0,0,0,0,airtel,1,1,12.0,4.0,0,C,0,0,0,0")
        
        c1, c2 = st.columns([3, 1])
        if c2.button("🛠️ Fix Checksum"):
            st.session_state.manual_pkt = f"${raw_input},{get_checksum(raw_input)}*\r\n"
        
        final_pkt = st.session_state.get('manual_pkt', f"${raw_input},{get_checksum(raw_input)}*\r\n")
        st.success("Final Packet to be sent:")
        st.code(final_pkt.strip())

    if st.button("📤 SEND BULK"): st.session_state.manual_running = True
    if st.button("🛑 STOP BULK"): st.session_state.manual_running = False

st.markdown("---")
progress_info = st.empty()
log_box = st.empty()

# --- 5. EXECUTION ---
if st.session_state.manual_running:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((srv_ip, srv_port))
            for i in range(m_count):
                if not st.session_state.manual_running: break
                s.sendall(final_pkt.encode('ascii'))
                
                # ✅ SHOW PROGRESS
                progress_info.info(f"📤 Sending: {i+1} / {m_count} Packets...")
                st.session_state.logs.insert(0, f"{datetime.now().strftime('%H:%M:%S')} | BULK {i+1} SENT")
                log_box.code("\n".join(st.session_state.logs[:10]))
                
                log_to_supabase({"imei": imei_val, "packet": final_pkt.strip(), "status": "BULK"})
                time.sleep(m_gap)
        progress_info.success(f"✅ Finished sending {m_count} packets!")
    except Exception as e: st.error(e)
    st.session_state.manual_running = False
    st.rerun()

if st.session_state.running:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((srv_ip, srv_port))
            while st.session_state.running:
                tag = sel_tags[st.session_state.current_idx % len(sel_tags)]
                now = datetime.now()
                body = f"PVT,{tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{l_lat:08.6f},N,{l_lon:09.6f},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83"
                pkt = f"${body},{get_checksum(body)}*\r\n"
                s.sendall(pkt.encode('ascii'))
                st.session_state.logs.insert(0, f"{now.strftime('%H:%M:%S')} | 🟢 {tag} Sent")
                log_box.code("\n".join(st.session_state.logs[:10]))
                log_to_supabase({"imei": imei_val, "tag": tag, "packet": pkt.strip(), "status": "LIVE"})
                st.session_state.current_idx += 1
                time.sleep(gap)
                st.rerun()
    except: st.session_state.running = False; st.rerun()
