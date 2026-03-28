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

def send_to_server(host, port, pkt):
    start = time.time()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((host, port))
            s.sendall(pkt.encode('ascii'))
            latency = int((time.time() - start) * 1000)
            return True, f"{latency}ms"
    except:
        return False, "TIMEOUT"

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
    st.markdown(
        "<h1 style='text-align: center;'>🛰️ Amit GPS Master Hybrid</h1>",
        unsafe_allow_html=True
    )

    _, col2, _ = st.columns([1, 2, 1])

    with col2:
        with st.form("login_form"):
            u_email = st.text_input("Email", value="amit@admin.com")
            u_pass = st.text_input("Password", type="password")

            if st.form_submit_button("🚪 Login", use_container_width=True):
                login_user(u_email, u_pass)

    st.stop()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    imei_val = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    
    st.markdown("---")
    st.subheader("➕ Custom Tag")
    c_tag = st.text_input("New Tag Name (e.g. ABCD)").upper().strip()
    if st.button("Add Tag", use_container_width=True):
        if c_tag and c_tag not in st.session_state.extended_tags:
            st.session_state.extended_tags.append(c_tag)
            st.success(f"Added {c_tag}")
            st.rerun()
        elif not c_tag:
            st.warning("Enter a tag name")
        else:
            st.info("Tag already exists")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# --- 5. MAIN UI ---
st.title("🛰️ Bihar VLTS Console")
tab1, tab2 = st.tabs(["🔄 Live Rotator", "📥 Static Bulk Mode"])

with tab1:
    col_l, col_r = st.columns([2, 1])
    with col_l:
        lat_val = st.number_input("Lat", value=25.650945, format="%.6f", key="lat_live")
        lon_val = st.number_input("Lon", value=84.784773, format="%.6f", key="lon_live")
        st.map(pd.DataFrame({'lat': [lat_val], 'lon': [lon_val]}), height=250)
    
    with col_r:
        st.subheader("Live Controls")
        gap = st.slider("Speed (Sec)", 0.05, 2.0, 0.50)
        selected_tags = [t for t in st.session_state.extended_tags if st.checkbox(f"{st.session_state.tag_status.get(t,'⚪')} {t}", value=True, key=f"t_{t}")]
        c1, c2 = st.columns(2)
        if c1.button("🚀 START LIVE"): st.session_state.running = True
        if c2.button("⏹️ STOP LIVE"): st.session_state.running = False

with tab2:
    st.subheader("Manual Bulk Sender")
    col_s1, col_s2, col_s3 = st.columns(3)
    # Custom tags ab dropdown mein bhi aayenge automatically
    m_tag = col_s1.selectbox("Select Tag", st.session_state.extended_tags, key="m_tag")
    m_count = col_s2.number_input("Packets Count", min_value=1, value=10)
    m_gap = col_s3.number_input("Interval (Sec)", min_value=0.1, value=1.0)
    
    m_lat = st.number_input("Manual Lat", value=25.650945, format="%.6f", key="m_lat")
    m_lon = st.number_input("Manual Lon", value=84.784773, format="%.6f", key="m_lon")
    
    mc1, mc2 = st.columns(2)
    if mc1.button("📤 START SENDING", use_container_width=True): st.session_state.manual_running = True
    if mc2.button("🛑 STOP SENDING", use_container_width=True): st.session_state.manual_running = False

# --- 6. DISPLAY PANELS ---
st.markdown("---")
col_log, col_raw = st.columns([3, 2])
with col_log:
    st.subheader("📡 Status & Logs")
    m_progress = st.empty() 
    log_area = st.empty()
with col_raw:
    st.subheader("📦 Last Raw Packet")
    raw_area = st.empty()

# --- 7. BULK MANUAL LOGIC ---
if st.session_state.manual_running:
    sent_count = 0
    while sent_count < m_count and st.session_state.manual_running:
        now = datetime.now()
        body = f"PVT,{m_tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{m_lat:08.6f},N,{m_lon:09.6f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83"
        pkt = f"${body},{get_checksum(body)}*\r\n"
        ok, res_ms = send_to_server(srv_ip, srv_port, pkt)
        sent_count += 1
        m_progress.info(f"📤 Manual Send: {sent_count}/{m_count} | Status: {res_ms}")
        st.session_state.logs.insert(0, f"{now.strftime('%H:%M:%S')} | 📥 MANUAL {m_tag} | {res_ms}")
        log_area.code("\n".join(st.session_state.logs[:15]))
        raw_area.code(pkt.strip())
        time.sleep(m_gap)
        if sent_count >= m_count: st.session_state.manual_running = False
    st.rerun()

# --- 8. LIVE ROTATOR LOGIC ---
if st.session_state.running:
    if not selected_tags:
        st.error("Select tags!"); st.session_state.running = False
    else:
        while st.session_state.running:
            tag = selected_tags[st.session_state.current_idx % len(selected_tags)]
            now = datetime.now()
            body = f"PVT,{tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{lat_val:08.6f},N,{lon_val:09.6f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83"
            pkt = f"${body},{get_checksum(body)}*\r\n"
            ok, res_ms = send_to_server(srv_ip, srv_port, pkt)
            if ok:
                st.session_state.tag_status[tag] = "✅"
                st.session_state.logs.insert(0, f"{now.strftime('%H:%M:%S')} | 🟢 {tag} | {res_ms}")
            else:
                st.session_state.tag_status[tag] = "❌"
                st.session_state.logs.insert(0, f"{now.strftime('%H:%M:%S')} | 🔴 {tag} | TIMEOUT")
            log_area.code("\n".join(st.session_state.logs[:15]))
            raw_area.code(pkt.strip())
            st.session_state.current_idx += 1
            time.sleep(gap)
            st.rerun()
