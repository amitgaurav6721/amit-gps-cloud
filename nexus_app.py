import streamlit as st
import socket
import time
import random
from datetime import datetime
import threading
import requests

# --- CONFIG ---
st.set_page_config(page_title="Amit GPS Master Pro", layout="wide")

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "YOUR_KEY_HERE"

# --- SESSION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "running" not in st.session_state:
    st.session_state.running = False

if "logs" not in st.session_state:
    st.session_state.logs = []

if "stats" not in st.session_state:
    st.session_state.stats = {"ok": 0, "fail": 0, "nores": 0}

# --- LOGIN ---
if not st.session_state.authenticated:
    st.title("🔐 Login")

    with st.form("login"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.form_submit_button("Login"):
            try:
                url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
                res = requests.post(
                    url,
                    json={"email": email, "password": password},
                    headers={"apikey": SUPABASE_KEY}
                )

                if res.status_code == 200:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Login Failed")

            except Exception as e:
                st.error(e)

    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")

    imei = st.text_input("IMEI", "862567075041793")
    vehicle = st.text_input("Vehicle", "BR04GA5974")
    host = st.text_input("Host", "vlts.bihar.gov.in")
    port = st.number_input("Port", 0, 65535, 9999)
    interval = st.slider("Interval", 0.5, 5.0, 1.0)

    device_count = st.slider("Devices", 1, 5, 1)

    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

# --- MAIN ---
st.title("🛰️ VLTS Simulator PRO")

lat = st.number_input("Latitude", value=25.650945, format="%.6f")
lon = st.number_input("Longitude", value=84.784773, format="%.6f")

tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT"]
selected_tags = [t for t in tags if st.checkbox(t, True)]

col1, col2 = st.columns(2)

if col1.button("🚀 START"):
    if not selected_tags:
        st.error("Select at least one tag")
    else:
        st.session_state.running = True

if col2.button("⏹️ STOP"):
    st.session_state.running = False

log_box = st.empty()
stat_box = st.empty()

# --- CHECKSUM ---
def checksum(body):
    cs = 0
    for c in body:
        cs ^= ord(c)
    return f"{cs:02X}"

# --- SEND ---
def send_packet(body, device_id):
    try:
        pkt = f"${body},{checksum(body)}*\r\n"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, int(port)))

            s.sendall(pkt.encode())

            try:
                res = s.recv(1024)
                if res:
                    st.session_state.stats["ok"] += 1
                    return f"🟢 DEV{device_id} OK"
            except:
                st.session_state.stats["nores"] += 1
                return f"🟡 DEV{device_id} SENT"

    except Exception as e:
        st.session_state.stats["fail"] += 1
        return f"🔴 DEV{device_id} FAIL"

# --- DEVICE ---
def device_thread(device_id):
    idx = 0

    while st.session_state.running:
        tag = selected_tags[idx % len(selected_tags)]
        ts = datetime.now()

        body = (
            f"PVT,{tag},2.1.1,NR,01,L,{imei},{vehicle},1,"
            f"{ts.strftime('%d%m%Y')},{ts.strftime('%H%M%S')},"
            f"{lat:.6f},N,{lon:.6f},E,"
            "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,"
            "26,404,73,0a83,e3c8,e3c7,0a83"
        )

        status = send_packet(body, device_id)

        st.session_state.logs.insert(
            0, f"{datetime.now().strftime('%H:%M:%S')} | {status}"
        )

        idx += 1
        time.sleep(interval)

# --- START THREADS ---
if st.session_state.running:
    for i in range(device_count):
        threading.Thread(
            target=device_thread,
            args=(i+1,),
            daemon=True
        ).start()

    while st.session_state.running:
        log_box.text("\n".join(st.session_state.logs[:20]))
        stat_box.write(f"📊 {st.session_state.stats}")
        time.sleep(1)
