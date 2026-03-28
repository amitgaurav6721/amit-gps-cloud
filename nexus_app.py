import streamlit as st
import socket
import time
import requests
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Amit GPS Master Hybrid", layout="wide", page_icon="🛰️")

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# --- SESSION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'running' not in st.session_state: st.session_state.running = False
if 'logs' not in st.session_state: st.session_state.logs = []
if 'sock' not in st.session_state: st.session_state.sock = None
if 'extended_tags' not in st.session_state:
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0

# --- HELPERS ---
def get_checksum(body):
    cs = 0
    for c in body:
        cs ^= ord(c)
    return f"{cs:02X}"

def connect_socket(host, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        return s
    except Exception:
        return None

def send_packet(sock, pkt):
    try:
        sock.sendall(pkt.encode("ascii"))
        try:
            resp = sock.recv(1024)
            return True, resp.decode(errors="ignore")
        except socket.timeout:
            return True, "NO_ACK"
    except Exception as e:
        return False, str(e)

def log_to_supabase(data):
    try:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/gps_logs",
            json=data,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            },
            timeout=1
        )
    except:
        pass

# --- LOGIN ---
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align:center;'>🛰️ Amit GPS Master</h1>", unsafe_allow_html=True)
    with st.form("login"):
        u = st.text_input("Email", value="amit@admin.com")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                res = requests.post(
                    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                    json={"email": u, "password": p},
                    headers={"apikey": SUPABASE_KEY}
                )
                if res.status_code == 200:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid login")
            except Exception as e:
                st.error(e)
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Config")
    imei_val = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    gap = st.slider("Interval", 0.5, 5.0, 1.0)

    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

st.title("🛰️ VLTS Console")

# --- ENGINE ---
def run_engine(sel_tags, lat, lon):
    if not st.session_state.sock:
        st.session_state.sock = connect_socket(srv_ip, int(srv_port))

    sock = st.session_state.sock

    if not sock:
        st.session_state.logs.insert(0, "❌ Connection failed")
        return

    tag = sel_tags[st.session_state.current_idx % len(sel_tags)]
    now = datetime.now()

    body = (
        f"PVT,{tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,"
        f"{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},"
        f"{lat:.6f},N,{lon:.6f},E,"
        "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83"
    )

    pkt = f"${body},{get_checksum(body)}*\r\n"

    ok, resp = send_packet(sock, pkt)

    if ok:
        st.session_state.logs.insert(0, f"🟢 {tag} | {resp}")
    else:
        st.session_state.logs.insert(0, f"🔴 ERROR: {resp}")
        st.session_state.sock = None  # reconnect next time

    st.session_state.current_idx += 1

    # limit logs
    st.session_state.logs = st.session_state.logs[:100]

# --- UI ---
t1, t2 = st.tabs(["🔄 Live", "📥 Bulk"])

with t1:
    lat = st.number_input("Lat", value=25.650945, format="%.6f")
    lon = st.number_input("Lon", value=84.784773, format="%.6f")

    sel_tags = [t for t in st.session_state.extended_tags if st.checkbox(t, True)]

    col1, col2 = st.columns(2)

    if col1.button("START"):
        st.session_state.running = True

    if col2.button("STOP"):
        st.session_state.running = False
        if st.session_state.sock:
            st.session_state.sock.close()
            st.session_state.sock = None

    if st.session_state.running and sel_tags:
        run_engine(sel_tags, lat, lon)
        time.sleep(gap)
        st.rerun()

    st.code("\n".join(st.session_state.logs[:15]))

with t2:
    m_count = st.number_input("Count", 1, 500, 10)
    m_gap = st.number_input("Interval", 0.1, 5.0, 1.0)

    if st.button("SEND BULK"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((srv_ip, int(srv_port)))

                for i in range(int(m_count)):
                    body = f"PVT,GRL,2.1.1,NR,01,L,{imei_val},{veh_no},1,{datetime.now().strftime('%d%m%Y')},{datetime.now().strftime('%H%M%S')},25.650945,N,84.784773,E,0.00,0.0,0,0,0,0,airtel,1,1,12.0,4.0,0,C,0,0,0,0"
                    pkt = f"${body},{get_checksum(body)}*\r\n"
                    s.sendall(pkt.encode("ascii"))
                    time.sleep(m_gap)

            st.success("Bulk sent")

        except Exception as e:
            st.error(e)
