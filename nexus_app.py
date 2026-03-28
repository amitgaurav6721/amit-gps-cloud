import streamlit as st
import socket
import time
import random
from datetime import datetime
import threading

# --- CONFIG ---
st.set_page_config(page_title="VLTS PRO MAX", layout="wide")

# --- SESSION STATE ---
if "running" not in st.session_state:
    st.session_state.running = False

if "logs" not in st.session_state:
    st.session_state.logs = []

if "stats" not in st.session_state:
    st.session_state.stats = {
        "accepted": 0,
        "rejected": 0,
        "no_response": 0
    }

# --- UI ---
st.title("🛰️ VLTS Multi Device Pro Simulator")

with st.sidebar:
    st.header("⚙️ Settings")

    host = st.text_input("Host", "vlts.bihar.gov.in")
    port = st.number_input("Port", value=9999)

    interval = st.slider("Interval", 0.5, 5.0, 1.0)
    device_count = st.slider("Devices", 1, 10, 2)

base_lat = st.number_input("Latitude", value=25.650945, format="%.6f")
base_lon = st.number_input("Longitude", value=84.784773, format="%.6f")

tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT"]
selected_tags = [t for t in tags if st.checkbox(t, True)]

col1, col2 = st.columns(2)

if col1.button("🚀 START"):
    if len(selected_tags) == 0:
        st.error("Select at least 1 tag")
    else:
        st.session_state.running = True

if col2.button("⏹️ STOP"):
    st.session_state.running = False

log_box = st.empty()
stat_box = st.empty()

# --- CHECKSUM ---
def calculate_checksum(body):
    cs = 0
    for c in body:
        cs ^= ord(c)
    return f"{cs:02X}"

# --- SEND FUNCTION ---
def send_packet(host, port, body, device_id):
    try:
        checksum = calculate_checksum(body)
        packet = f"${body},{checksum}*\r\n"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, int(port)))

            start = time.time()
            s.sendall(packet.encode("ascii"))

            try:
                response = s.recv(1024)
                latency = int((time.time() - start) * 1000)

                if response:
                    st.session_state.stats["accepted"] += 1
                    return f"🟢 DEV{device_id} ACCEPTED ({latency} ms)"

                else:
                    st.session_state.stats["no_response"] += 1
                    return f"🟡 DEV{device_id} NO RESPONSE"

            except socket.timeout:
                st.session_state.stats["no_response"] += 1
                return f"🟡 DEV{device_id} TIMEOUT"

    except Exception as e:
        st.session_state.stats["rejected"] += 1
        return f"🔴 DEV{device_id} ERROR: {e}"

# --- DEVICE THREAD ---
def simulate_device(device_id):
    imei = f"86256707504{100+device_id}"

    idx = 0

    while st.session_state.running:

        tag = selected_tags[idx % len(selected_tags)]
        ts = datetime.now()

        # STATIC VEHICLE (NO MOVEMENT)
        lat = base_lat
        lon = base_lon

        body = (
            f"PVT,{tag},2.1.1,NR,01,L,{imei},VEH{device_id},1,"
            f"{ts.strftime('%d%m%Y')},{ts.strftime('%H%M%S')},"
            f"{lat:.6f},N,{lon:.6f},E,"
            "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,"
            "26,404,73,0a83,e3c8,e3c7,0a83"
        )

        status = send_packet(host, port, body, device_id)

        log = f"{datetime.now().strftime('%H:%M:%S')} | {status}"
        st.session_state.logs.insert(0, log)

        idx += 1

        time.sleep(interval + random.uniform(-0.1, 0.1))

# --- START THREADS ---
if st.session_state.running:
    threads = []

    for i in range(device_count):
        t = threading.Thread(target=simulate_device, args=(i+1,), daemon=True)
        threads.append(t)
        t.start()

    while st.session_state.running:
        log_box.text("\n".join(st.session_state.logs[:20]))
        stat_box.write(f"📊 Stats: {st.session_state.stats}")
        time.sleep(1)
