import streamlit as st
import socket
import psycopg2
import time
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# --- 1. SECRETS & SUPABASE ---
try:
    DB_PASSWORD = st.secrets["DB_PASSWORD"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception as e:
    st.error(f"Secrets missing: {e}")
    st.stop()

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()
st.set_page_config(page_title="Amit GPS Ultra Console", layout="wide")

# --- 2. SESSION STATE ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'running' not in st.session_state: st.session_state.running = False

# --- 3. AIS-140 CHECKSUM ---
def get_ais140_checksum(payload):
    checksum = 0
    for char in payload: checksum ^= ord(char)
    return f"{checksum:02X}"

# --- 4. LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Ultra Login")
    with st.form("login_gate"):
        u_input = st.text_input("Email").strip().lower()
        p_input = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": u_input, "password": p_input})
                if res.user:
                    st.session_state.logged_in, st.session_state.user_email = True, u_input
                    st.rerun()
                else: st.error("Invalid Login")
            except Exception as e: st.error(f"Error: {e}")
    st.stop()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Config")
    super_charge = st.toggle("🚀 Super Charge Mode", help="Keep-Alive Socket uses a single connection.")
    comp_name = st.text_input("Tag", "WTEX") 
    imei = st.text_input("IMEI", "862491076910809")
    veh_no = st.text_input("Vehicle", "BR01GH9898")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Interval", 0.5, 5.0, 1.0)
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# --- 6. UI ---
st.title("🚀 Ultra-Fast Tracking Console")
col_l, col_r = st.columns([1, 1])
with col_l:
    lat_v = st.number_input("Lat", value=25.6509450, format="%.7f")
    lon_v = st.number_input("Lon", value=84.7847730, format="%.7f")
    if st.button("▶️ START", type="primary", use_container_width=True): st.session_state.running = True
    if st.button("⏹️ STOP", use_container_width=True): 
        st.session_state.running = False
        st.rerun()
    status_msg = st.empty()

with col_r:
    st.map(pd.DataFrame({'lat': [lat_v], 'lon': [lon_v]}), zoom=14)

# --- 7. ULTRA LOOP ---
if st.session_state.running:
    try:
        conn = psycopg2.connect(host="aws-1-ap-northeast-2.pooler.supabase.com", database="postgres", user="postgres.grdgexcjyrhkoffimsuw", password=DB_PASSWORD, port="6543", sslmode="require")
        cur = conn.cursor()
        p_count = 0
        
        persistent_socket = None
        if super_charge:
            try:
                persistent_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                persistent_socket.settimeout(2)
                persistent_socket.connect((srv_ip, srv_port))
            except:
                st.warning("Super Charge connection failed. Using Normal.")
                super_charge = False

        while st.session_state.running:
            s_time = time.perf_counter() # High precision timer
            now = datetime.now()
            d, t = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
            p_count += 1
            
            base = f"2.1.1,NR,01,L,{imei},{veh_no},1"
            loc = f"{lat_v},N,{lon_v},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            
            p1_pay = f"PVT,EGAS,{base},{d},{t},{loc}"
            packet_a = f"${p1_pay},{get_ais140_checksum(p1_pay)}*\r\n"
            
            p2_pay = f"PVT,{comp_name},{base},{d}{t},{lat_v:.7f},N,{lon_v:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
            packet_b = f"${p2_pay}{get_ais140_checksum(p2_pay)}*\r\n"
            
            if super_charge and persistent_socket:
                try:
                    persistent_socket.sendall(packet_a.encode('ascii'))
                    persistent_socket.sendall(packet_b.encode('ascii'))
                except:
                    persistent_socket.close()
                    persistent_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    persistent_socket.connect((srv_ip, srv_port))
            else:
                for p in [packet_a, packet_b]:
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.settimeout(0.5)
                            s.connect((srv_ip, srv_port))
                            s.sendall(p.encode('ascii'))
                    except: pass
            
            db_s = "⚡"
            if p_count % 10 == 0:
                cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_v, lon_v, packet_b.strip(), veh_no))
                conn.commit()
                db_s = "💾 Saved"

            lcy = (time.perf_counter() - s_time) * 1000 # Convert to ms
            mode_label = "Super 🚀" if super_charge else "Normal 🐢"
            status_msg.info(f"Mode: {mode_label} | Count: {p_count} | Latency: {lcy:.2f}ms | DB: {db_s}")
            
            time.sleep(max(0, interval - (time.perf_counter() - s_time)))
            if not st.session_state.running: break
            
        if persistent_socket: persistent_socket.close()
            
    except Exception as e:
        st.error(f"Loop Error: {e}")
        st.session_state.running = False
