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

# Session State Persistence (Initialize only once)
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'running' not in st.session_state: st.session_state.running = False
if 'manual_running' not in st.session_state: st.session_state.manual_running = False
if 'logs' not in st.session_state: st.session_state.logs = []
if 'extended_tags' not in st.session_state: 
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0
if 'manual_pkt_state' not in st.session_state: st.session_state.manual_pkt_state = ""

# --- 2. HELPERS ---
def get_checksum(body):
    cs = 0
    for c in body: cs ^= ord(c)
    return f"{cs:02X}"

def log_to_supabase(data):
    url = f"{SUPABASE_URL}/rest/v1/gps_logs"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    try: requests.post(url, json=data, headers=headers, timeout=2)
    except: pass

# --- 3. LOGIN ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🛰️ Amit GPS Master</h1>", unsafe_allow_html=True)
    with st.form("login"):
        u = st.text_input("Email", value="amit@admin.com")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            res = requests.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", 
                                json={"email": u, "password": p}, 
                                headers={"apikey": SUPABASE_KEY})
            if res.status_code == 200:
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("❌ Invalid Credentials")
    st.stop()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Config")
    imei_val = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    st.markdown("---")
    new_t = st.text_input("➕ Add New Tag").upper().strip()
    if st.button("Save Tag"):
        if new_t and new_t not in st.session_state.extended_tags:
            st.session_state.extended_tags.append(new_t)
            st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()

st.title("🛰️ Bihar VLTS Live Console")
tab1, tab2 = st.tabs(["🔄 Live Rotator", "📥 Static Bulk Mode"])

# --- TAB 1: LIVE ---
with tab1:
    col_l, col_r = st.columns([2, 1])
    with col_l:
        l_lat = st.number_input("Lat", value=25.650945, format="%.6f", key="llat")
        l_lon = st.number_input("Lon", value=84.784773, format="%.6f", key="llon")
        st.map(pd.DataFrame({'lat': [l_lat], 'lon': [l_lon]}), height=200)
    with col_r:
        l_gap = st.slider("Speed", 0.05, 5.0, 1.0, key="lgap")
        sel_tags = [t for t in st.session_state.extended_tags if st.checkbox(t, True, key=f"c_{t}")]
        if st.button("🚀 START LIVE"): st.session_state.running = True
        if st.button("⏹️ STOP LIVE"): st.session_state.running = False

# --- TAB 2: STATIC BULK ---
with tab2:
    col1, col2 = st.columns(2)
    m_count = col1.number_input("Count", 1, 1000, 10)
    m_gap = col2.number_input("Gap (Sec)", 0.1, 5.0, 1.0)
    bulk_mode = st.radio("Method", ["Auto", "Manual String Edit"], horizontal=True)
    
    if bulk_mode == "Auto":
        m_tag = st.selectbox("Tag", st.session_state.extended_tags)
        m_lat = st.number_input("Lat", value=25.650945, format="%.6f", key="mlat")
        m_lon = st.number_input("Lon", value=84.784773, format="%.6f", key="mlon")
        body = f"PVT,{m_tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{datetime.now().strftime('%d%m%Y,%H%M%S')},{m_lat:08.6f},N,{m_lon:09.6f},E,0.0,0.0,0,0,0,0,airtel,1,1,12.0,4.0,0,C,0,0,0,0"
        final_pkt = f"${body},{get_checksum(body)}*\r\n"
    else:
        raw_in = st.text_area("Custom Raw Packet (Body):", value=f"PVT,GRL,2.1.1,NR,01,L,{imei_val},{veh_no},1,{datetime.now().strftime('%d%m%Y,%H%M%S')},25.650945,N,84.784773,E,0.0,0.0,0,0,0,0,airtel,1,1,12.0,4.0,0,C,0,0,0,0")
        if st.button("🛠️ Fix Checksum"):
            st.session_state.manual_pkt_state = f"${raw_in},{get_checksum(raw_in)}*\r\n"
        final_pkt = st.session_state.manual_pkt_state if st.session_state.manual_pkt_state else f"${raw_in},{get_checksum(raw_in)}*\r\n"
    
    st.code(final_pkt.strip())
    if st.button("📤 SEND BULK"): st.session_state.manual_running = True

st.markdown("---")
log_area = st.empty()

# --- 5. ENGINES ---
if st.session_state.manual_running:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((srv_ip, srv_port))
            for i in range(int(m_count)):
                if not st.session_state.manual_running: break
                s.sendall(final_pkt.encode('ascii'))
                st.session_state.logs.insert(0, f"{datetime.now().strftime('%H:%M:%S')} | BULK {i+1} SENT")
                log_area.code("\n".join(st.session_state.logs[:10]))
                log_to_supabase({"imei": imei_val, "packet": final_pkt.strip(), "status": "BULK"})
                time.sleep(m_gap)
        st.success("Bulk Finished!")
    except Exception as e: st.error(e)
    st.session_state.manual_running = False
    st.rerun()

if st.session_state.running:
    if not sel_tags:
        st.warning("Select tags!"); st.session_state.running = False
    else:
        try:
            tag = sel_tags[st.session_state.current_idx % len(sel_tags)]
            now = datetime.now()
            body = f"PVT,{tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{now.strftime('%d%m%Y,%H%M%S')},{l_lat:08.6f},N,{l_lon:09.6f},E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83"
            pkt = f"${body},{get_checksum(body)}*\r\n"
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2); s.connect((srv_ip, srv_port))
                s.sendall(pkt.encode('ascii'))
            
            st.session_state.logs.insert(0, f"{now.strftime('%H:%M:%S')} | 🟢 {tag} Sent")
            log_area.code("\n".join(st.session_state.logs[:10]))
            log_to_supabase({"imei": imei_val, "tag": tag, "packet": pkt.strip(), "status": "LIVE"})
            
            st.session_state.current_idx += 1
            time.sleep(l_gap)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}"); st.session_state.running = False
