import streamlit as st
import socket
import time
import requests
import pandas as pd
from datetime import datetime

# --- 1. CONFIG & SESSION ---
st.set_page_config(page_title="Amit GPS Master Hybrid", layout="wide", page_icon="🛰️")

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'running' not in st.session_state: st.session_state.running = False
if 'logs' not in st.session_state: st.session_state.logs = []
if 'extended_tags' not in st.session_state: 
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0

# --- 2. HELPERS ---
def get_checksum(body):
    cs = 0
    for c in body: cs ^= ord(c)
    return f"{cs:02X}" # ✅ FIXED: Strict Hex (No spaces)

def log_to_supabase(data):
    url = f"{SUPABASE_URL}/rest/v1/gps_logs"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"}
    try: requests.post(url, json=data, headers=headers, timeout=1)
    except: pass

# --- 3. LOGIN ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🛰️ Amit GPS Master</h1>", unsafe_allow_html=True)
    with st.form("login"):
        u = st.text_input("Email", value="amit@admin.com")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                res = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", json={"email": u, "password": p}, headers={"apikey": SUPABASE_KEY})
                if res.status_code == 200:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("❌ Invalid Login")
            except: st.error("Connection Error")
    st.stop()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Config")
    imei_val = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    st.markdown("---")
    new_t = st.text_input("➕ New Tag").upper().strip()
    if st.button("Save Tag"):
        if new_t and new_t not in st.session_state.extended_tags:
            st.session_state.extended_tags.append(new_t)
            st.rerun()
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

st.title("🛰️ Bihar VLTS Live Console")

# --- 5. TRANSMISSION ENGINE (Live Rotator) ---
@st.fragment(run_every=1.0 if st.session_state.running else None)
def transmission_engine(sel_tags, l_lat, l_lon):
    if st.session_state.running and sel_tags:
        tag = sel_tags[st.session_state.current_idx % len(sel_tags)]
        now = datetime.now()
        # ✅ Strict format: No spaces
        body = f"PVT,{tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{l_lat:.6f},N,{l_lon:.6f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83"
        pkt = f"${body},{get_checksum(body)}*\r\n"
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2); s.connect((srv_ip, srv_port)); s.sendall(pkt.encode('ascii'))
            st.session_state.logs.insert(0, f"{now.strftime('%H:%M:%S')} | 🟢 {tag} Sent")
            log_to_supabase({"imei": imei_val, "tag": tag, "lat": l_lat, "lon": l_lon, "packet": pkt.strip(), "status": "LIVE"})
        except:
            st.session_state.logs.insert(0, f"{now.strftime('%H:%M:%S')} | 🔴 Server Error")
        
        st.session_state.current_idx += 1
    
    st.subheader("📡 Status")
    st.code("\n".join(st.session_state.logs[:12]))

# --- 6. UI TABS ---
t1, t2 = st.tabs(["🔄 Live Rotator", "📥 Static Bulk Mode"])

with t1:
    col_l, col_r = st.columns([2, 1])
    with col_l:
        l_lat = st.number_input("Lat", value=25.650945, format="%.6f", key="llat")
        l_lon = st.number_input("Lon", value=84.784773, format="%.6f", key="llon")
        st.map(pd.DataFrame({'lat': [l_lat], 'lon': [l_lon]}), height=200)
    with col_r:
        st.write("Select Tags:")
        sel_tags = [t for t in st.session_state.extended_tags if st.checkbox(t, True, key=f"c_{t}")]
        if st.button("🚀 START"): st.session_state.running = True; st.rerun()
        if st.button("⏹️ STOP"): st.session_state.running = False; st.rerun()
    transmission_engine(sel_tags, l_lat, l_lon)

with t2:
    m_count = st.number_input("Count", 1, 1000, 10)
    m_gap = st.number_input("Interval", 0.1, 5.0, 1.0)
    b_mode = st.radio("Method", ["Auto", "Manual (Paste Full Packet)"], horizontal=True)
    
    if b_mode == "Auto":
        m_tag = st.selectbox("Tag", st.session_state.extended_tags)
        m_lat = st.number_input("Lat", value=25.650945, format="%.6f", key="mlat")
        m_lon = st.number_input("Lon", value=84.784773, format="%.6f", key="mlon")
        body = f"PVT,{m_tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{datetime.now().strftime('%d%m%Y')},{datetime.now().strftime('%H%M%S')},{m_lat:.6f},N,{m_lon:.6f},E,0.00,0.0,0,0,0,0,airtel,1,1,12.0,4.0,0,C,0,0,0,0"
        final_pkt = f"${body},{get_checksum(body)}*\r\n"
    else:
        # ✅ MANUAL: No changes to your packet or checksum
        raw_in = st.text_area("Paste Full Packet (including $ and *):", value="")
        final_pkt = raw_in.strip() + "\r\n" if raw_in else ""

    st.code(final_pkt.strip())
    if st.button("📤 SEND BULK"):
        if not final_pkt: st.error("Please enter a packet"); st.stop()
        p_bar = st.progress(0); s_text = st.empty()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5); s.connect((srv_ip, srv_port))
                for i in range(int(m_count)):
                    s.sendall(final_pkt.encode('ascii'))
                    log_to_supabase({"imei": imei_val, "packet": final_pkt.strip(), "status": "BULK"})
                    p_bar.progress((i + 1) / m_count)
                    s_text.text(f"Sending {i+1}/{m_count}...")
                    time.sleep(m_gap)
            st.success("Sent Successfully!")
        except Exception as e: st.error(e)
