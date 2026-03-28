import streamlit as st
import socket
import time
from datetime import datetime
import requests
import os

# --- CONFIG ---
st.set_page_config(page_title="Amit GPS Master", layout="wide")

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --- SESSION STATE ---
defaults = {
    "authenticated": False,
    "tag_status": {},
    "running": False,
    "current_idx": 0
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- LOGIN ---
if not st.session_state.authenticated:
    st.title("🛰️ Amit GPS Login")

    with st.form("login_form"):
        u = st.text_input("Email", value="amit@admin.com")
        p = st.text_input("Password", type="password")

        if st.form_submit_button("Login"):
            try:
                url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
                headers = {
                    "apikey": SUPABASE_KEY,
                    "Content-Type": "application/json"
                }

                res = requests.post(
                    url,
                    json={"email": u, "password": p},
                    headers=headers
                )

                if res.status_code == 200:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Login Failed")

            except Exception as e:
                st.error(f"Error: {e}")

    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")

    imei = st.text_input("IMEI", "862567075041793")
    veh = st.text_input("Vehicle", "BR04GA5974")
    host = st.text_input("Host", "vlts.bihar.gov.in")
    port = st.number_input("Port", value=9999)
    gap = st.slider("Interval", 0.1, 2.0, 0.5)

    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.running = False
        st.rerun()

# --- MAIN UI ---
st.header("🛰️ Bihar VLTS Live Console")

lat = st.number_input("Lat", value=25.650945, format="%.6f")
lon = st.number_input("Lon", value=84.784773, format="%.6f")

tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]

sel = []
for t in tags:
    checked = st.checkbox(
        f"{st.session_state.tag_status.get(t, '⚪')} {t}",
        value=True,
        key=t
    )
    if checked:
        sel.append(t)

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 START"):
        if len(sel) == 0:
            st.error("❌ At least 1 tag select karo")
        else:
            st.session_state.running = True

with col2:
    if st.button("⏹️ STOP"):
        st.session_state.running = False

# --- SOCKET LOOP ---
box = st.empty()

if st.session_state.running:
    try:
        while st.session_state.running:

            if len(sel) == 0:
                st.warning("No tags selected")
                break

            tag = sel[st.session_state.current_idx % len(sel)]
            ts = datetime.now()

            body = (
                f"PVT,{tag},2.1.1,NR,01,L,{imei},{veh},1,"
                f"{ts.strftime('%d%m%Y')},{ts.strftime('%H%M%S')},"
                f"{lat:08.6f},N,{lon:09.6f},E,"
                "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,"
                "26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,"
                "c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            )

            # checksum
            cs = 0
            for char in body:
                cs ^= ord(char)

            pkt = f"${body},{cs:04X}*\r\n"

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    s.connect((host, int(port)))
                    s.sendall(pkt.encode("ascii"))

                st.session_state.tag_status[tag] = "✅"
                box.success(f"Sent: {tag} | {ts.strftime('%H:%M:%S')}")

            except Exception as e:
                box.error(f"Socket Error: {e}")

            st.session_state.current_idx += 1
            time.sleep(gap)

    except Exception as e:
        st.error(f"Critical Error: {e}")
