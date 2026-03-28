import streamlit as st
import socket
import time
import requests
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(page_title="Amit GPS Master Pro", layout="wide")

# Maine aapki settings se sahi keys nikaal kar yahan daal di hain
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# --- SESSION INITIALIZATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "running" not in st.session_state:
    st.session_state.running = False
if "logs" not in st.session_state:
    st.session_state.logs = []
if "stats" not in st.session_state:
    st.session_state.stats = {"ok": 0, "fail": 0}

# --- 2. LOGIN LOGIC ---
if not st.session_state.authenticated:
    st.title("🔐 Login")
    with st.form("login_form"):
        email = st.text_input("Email", value="amit@admin.com")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            try:
                # Headers update kiye hain taaki Supabase error na de
                url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Content-Type": "application/json"
                }
                res = requests.post(url, json={"email": email, "password": password}, headers=headers)
                
                if res.status_code == 200:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error(f"❌ Login Failed: {res.json().get('error_description', 'Invalid Credentials')}")
            except Exception as e:
                st.error(f"⚠️ Error: {str(e)}")
    st.stop()

# --- 3. SIDEBAR & LOGOUT ---
with st.sidebar:
    st.header("⚙️ Settings")
    imei = st.text_input("IMEI", "862567075041793")
    vehicle = st.text_input("Vehicle", "BR04GA5974")
    host = st.text_input("Host", "vlts.bihar.gov.in")
    port = st.number_input("Port", value=9999)
    interval = st.slider("Interval (Sec)", 0.1, 5.0, 0.5)
    
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.running = False
        st.rerun()

# --- 4. MAIN DASHBOARD ---
st.title("🛰️ VLTS Simulator PRO")

col_a, col_b = st.columns(2)
lat = col_a.number_input("Latitude", value=25.650945, format="%.6f")
lon = col_b.number_input("Longitude", value=84.784773, format="%.6f")

tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT"]
st.write("### Select Tags")
selected_tags = [t for t in tags if st.checkbox(f"Tag: {t}", True, key=t)]

# Control Buttons
c1, c2 = st.columns(2)
if c1.button("🚀 START", use_container_width=True):
    if not selected_tags:
        st.error("Please select at least one tag")
    else:
        st.session_state.running = True

if c2.button("⏹️ STOP", use_container_width=True):
    st.session_state.running = False

# Display Areas
stat_placeholder = st.empty()
log_placeholder = st.empty()

# --- 5. TRANSMISSION LOGIC ---
def get_checksum(body):
    cs = 0
    for c in body: cs ^= ord(c)
    return f"{cs:04X}" # Bihar server requires 4-digit hex often

if st.session_state.running:
    try:
        idx = 0
        # Threading ki jagah direct loop Streamlit ke liye better hai
        while st.session_state.running:
            tag = selected_tags[idx % len(selected_tags)]
            ts = datetime.now()
            
            # Packet Body
            body = (f"PVT,{tag},2.1.1,NR,01,L,{imei},{vehicle},1,"
                    f"{ts.strftime('%d%m%Y')},{ts.strftime('%H%M%S')},"
                    f"{lat:.6f},N,{lon:.6f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,"
                    "26,404,73,0a83,e3c8,e3c7,0a83")
            
            pkt = f"${body},{get_checksum(body)}*\r\n"
            
            # Socket Send
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    s.connect((host, int(port)))
                    s.sendall(pkt.encode('ascii'))
                    st.session_state.stats["ok"] += 1
                    status_text = f"🟢 {tag} SENT"
            except:
                st.session_state.stats["fail"] += 1
                status_text = f"🔴 {tag} FAILED"

            # Update Logs
            st.session_state.logs.insert(0, f"{ts.strftime('%H:%M:%S')} | {status_text}")
            
            # Refresh UI
            stat_placeholder.markdown(f"### 📊 Stats: `OK: {st.session_state.stats['ok']}` | `FAIL: {st.session_state.stats['fail']}`")
            log_placeholder.code("\n".join(st.session_state.logs[:15]))
            
            idx += 1
            time.sleep(interval)
            
    except Exception as e:
        st.error(f"Loop Error: {e}")
        st.session_state.running = False
