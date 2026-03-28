import streamlit as st
import socket
import time
from datetime import datetime
import pandas as pd
import requests

# --- 1. CONFIG & INITIALIZATION ---
st.set_page_config(page_title="Amit GPS Master Hybrid", layout="wide", page_icon="🛰️")

# Supabase Credentials
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# Initialize Session States
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_token' not in st.session_state:
    st.session_state.user_token = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'tag_status' not in st.session_state:
    st.session_state.tag_status = {}
if 'extended_tags' not in st.session_state:
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'running' not in st.session_state:
    st.session_state.running = False
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0

# --- 2. AUTHENTICATION FUNCTIONS ---
def login_user(email, password):
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            st.session_state.authenticated = True
            st.session_state.user_token = data['access_token']
            st.session_state.user_email = data['user']['email']
            st.rerun()
        else:
            st.error("❌ Invalid Email or Password")
    except Exception as e:
        st.error(f"⚠️ Auth Error: {e}")

def logout_user():
    st.session_state.authenticated = False
    st.session_state.user_token = None
    st.session_state.user_email = ""
    st.session_state.running = False
    st.rerun()

# --- 3. CORE GPS LOGIC ---
def get_bihar_checksum(payload):
    checksum = 0
    for char in payload:
        checksum ^= ord(char)
    return f"{checksum:04X}"

def format_coord(val, is_lat=True):
    if is_lat:
        return f"{val:08.6f}"
    else:
        return f"{val:09.6f}"

# --- 4. DB LOGGER ---
def log_to_supabase(imei, lat, lon, packet):
    if not st.session_state.user_token:
        return # Don't log if not authenticated properly

    url = f"{SUPABASE_URL}/rest/v1/gps_data"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {st.session_state.user_token}", # Use User's Token
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {
        "imei": str(imei),
        "latitude": float(lat),
        "longitude": float(lon),
        "raw_packet": str(packet)
    }
    try:
        requests.post(url, json=payload, headers=headers, timeout=0.5)
    except:
        pass # Background log

# --- 5. UI LOGIC ---

# Reset running state on mode switch
def reset_running():
    st.session_state.running = False

# --- MAIN RENDER ---
if not st.session_state.authenticated:
    # --- LOGIN SCREEN ---
    st.markdown("<h1 style='text-align: center;'>🛰️ Amit GPS Master Hybrid</h1>", unsafe_with_html=True)
    st.markdown("<h3 style='text-align: center;'>Secure Access Login</h3>", unsafe_with_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("Email Address", placeholder="amit@admin.com")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("🚪 Login", use_container_width=True)
            
            if submit:
                if email and password:
                    login_user(email, password)
                else:
                    st.warning("⚠️ Please enter both Email and Password")

else:
    # --- DASHBOARD SCREEN ---
    
    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Global Settings")
        st.write(f"👤 Logged in as: **{st.session_state.user_email}**")
        
        imei = st.text_input("IMEI", "862567075041793")
        veh_no = st.text_input("Vehicle", "BR04GA5974")
        srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
        srv_port = st.number_input("Port", value=9999)
        interval = st.slider("Latency Gap (Sec)", 0.05, 2.0, 0.80)
        
        st.markdown("---")
        new_tag = st.text_input("➕ Add New Tag:")
        if st.button("Save Tag") and new_tag:
            t = new_tag.upper().strip()
            if t and t not in st.session_state.extended_tags:
                st.session_state.extended_tags.append(t)
                st.rerun()
        
        if st.button("🧹 Clear Status Logs"):
            st.session_state.tag_status = {}
            st.rerun()

        st.markdown("---")
        mode = st.radio("Select Mode:", ["Static (Manual)", "Experimental (Live Auto)"], on_change=reset_running)
        
        st.markdown("---")
        if st.button("🚪 Log Out", use_container_width=True):
            logout_user()

    # --- 7. COMMON UI ---
    st.title("🛰️ Bihar VLTS Master Hybrid Console")
    col_lat, col_lon = st.columns(2)
    lat = col_lat.number_input("Latitude", value=25.650945, format="%.6f")
    lon = col_lon.number_input("Longitude", value=84.784773, format="%.6f")

    map_df = pd.DataFrame({'lat': [lat], 'lon': [lon]})
    st.map(map_df)

    st.markdown("---")

    # --- 8. MODE LOGIC ---

    if mode == "Static (Manual)":
        # Static Mode... (Unchanged)
        st.subheader("📝 Static Lab")
        static_templates = {
            "String 1 ($GPRMC)": f"$GPRMC,WTEX,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.290684,N,84.643164,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*",
            "String 2 ($PVT)": f"$PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.6501550,N,84.7851780,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
        }
        sel_template = st.selectbox("Choose Template", list(static_templates.keys()))
        manual_packet = st.text_area("Packet:", value=static_templates[sel_template], height=100)
        
        if st.button("🚀 SEND STATIC"):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5); s.connect((srv_ip, srv_port))
                    full_p = manual_packet.strip() + "\r\n"
                    s.sendall(full_p.encode('ascii'))
                    log_to_supabase(imei, lat, lon, full_p.strip())
                    st.success("Sent & Logged!")
            except Exception as e: st.error(f"Failed: {e}")

    else:
        # Turbo Mode... (Unchanged)
        st.subheader("🧪 Turbo Discovery & DB Logging")
        selected_tags = []
        tag_cols = st.columns(5)
        for i, t_tag in enumerate(st.session_state.extended_tags):
            status = st.session_state.tag_status.get(t_tag, "⚪")
            if tag_cols[i % 5].checkbox(f"{status} {t_tag}", value=True, key=f"check_{t_tag}"):
                selected_tags.append(t_tag)

        col_btn1, col_btn2 = st.columns(2)
        if col_btn1.button("🚀 START SUPER-CHARGE ROTATOR", use_container_width=True):
            if not selected_tags: st.error("Tag select karo!")
            else: st.session_state.running = True
        
        if col_btn2.button("⏹️ STOP", use_container_width=True):
            st.session_state.running = False

        if st.session_state.running:
            log_placeholder = st.empty()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5); s.connect((srv_ip, srv_port))
                    while st.session_state.running:
                        current_tag = selected_tags[st.session_state.current_idx % len(selected_tags)]
                        t_start = time.time()
                        
                        now = datetime.now()
                        d_live, t_live = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                        body = f"PVT,{current_tag},2.1.1,NR,01,L,{imei},{veh_no},1,{d_live},{t_live},{format_coord(lat,True)},N,{format_coord(lon,False)},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                        packet = f"${body},{get_bihar_checksum(body)}*\r\n"
                        
                        try:
                            s.sendall(packet.encode('ascii'))
                            log_to_supabase(imei, lat, lon, packet.strip()) # Using dynamic token
                            latency = round((time.time() - t_start) * 1000, 2)
                            st.session_state.tag_status[current_tag] = "✅"
                            log_placeholder.success(f"🚀 SUPER CHARGED & LOGGED: {current_tag} | {latency}ms")
                        except:
                            st.session_state.tag_status[current_tag] = "❌"
                            break
                        
                        st.session_state.current_idx += 1
                        time.sleep(interval)
                        st.rerun()
            except:
                st.warning("🔄 Reconnecting...")
                time.sleep(1); st.rerun()
