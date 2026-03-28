import streamlit as st
import socket
import time
import requests
import pandas as pd
from datetime import datetime

# --- 1. CONFIG & UI SETUP ---
st.set_page_config(page_title="Amit GPS Master Hybrid", layout="wide", page_icon="🛰️")

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# Session State Initialization (Crucial for stability)
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'running' not in st.session_state: st.session_state.running = False
if 'logs' not in st.session_state: st.session_state.logs = []
if 'stats' not in st.session_state: st.session_state.stats = {"ok": 0, "fail": 0}
if 'tag_status' not in st.session_state: st.session_state.tag_status = {}
if 'extended_tags' not in st.session_state: 
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0

# --- 2. HELPERS ---
def get_checksum(body):
    cs = 0
    for c in body: cs ^= ord(c)
    return f"{cs:02X}"

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

# --- 3. MAIN RENDER ---
if not st.session_state.authenticated:
    # --- Login Screen ---
    st.markdown("<h1 style='text-align: center;'>🛰️ Amit GPS Master Hybrid</h1>", unsafe_with_html=True)
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            u_email = st.text_input("Email", value="amit@admin.com")
            u_pass = st.text_input("Password", type="password")
            if st.form_submit_button("🚪 Login", use_container_width=True):
                login_user(u_email, u_pass)
    st.stop()

# --- 4. DASHBOARD (Will run only if authenticated) ---
with st.sidebar:
    st.header("⚙️ Configuration")
    imei_val = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    gap = st.slider("Speed (Sec)", 0.05, 2.0, 0.50)
    
    st.markdown("---")
    # ✅ Feature: Add New Tags
    st.subheader("➕ Add Custom Tag")
    new_tag = st.text_input("New Tag Name", max_chars=10).upper().strip()
    if st.button("Add Tag") and new_tag:
        if new_tag not in st.session_state.extended_tags:
            st.session_state.extended_tags.append(new_tag)
            st.success(f"Tag {new_tag} Added")
            st.rerun()
        else: st.warning("Tag already exists")

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.running = False
        st.rerun()

# --- 5. MAIN UI LAYOUT ---
st.title("🛰️ Bihar VLTS Live Console")

# Row 1: Map and Controls
r1c1, r1c2 = st.columns([2, 1])
with r1c1:
    # ✅ Feature: Map Wapas Aa Gaya
    st.subheader("🗺️ Live Location Map")
    lat_val = st.number_input("Latitude", value=25.650945, format="%.6f")
    lon_val = st.number_input("Longitude", value=84.784773, format="%.6f")
    st.map(pd.DataFrame({'lat': [lat_val], 'lon': [lon_val]}))

with r1c2:
    st.subheader("🎮 Rotation Controls")
    # ✅ Feature: Tag Selection with Status Icon
    selected_tags = [t for t in st.session_state.extended_tags if st.checkbox(f"{st.session_state.tag_status.get(t,'⚪')} {t}", value=True, key=f"t_{t}")]
    
    c1, c2 = st.columns(2)
    if c1.button("🚀 START"): st.session_state.running = True
    if c2.button("⏹️ STOP"): st.session_state.running = False
    
    stat_placeholder = st.empty()

# ✅ Feature: Niche Information Section Wapas Aa Gaya
st.markdown("---")
with st.expander("📊 Transmission Details & Logs", expanded=True):
    r2c1, r2c2 = st.columns([3, 2])
    
    with r2c1:
        st.subheader("📡 Live Packets & Logs")
        log_box = st.code("Waiting for transmission...")

    with r2c2:
        st.subheader("📝 Static & Raw Packet Info")
        static_info = st.empty()
        raw_pkt_box = st.empty()

# --- 6. TRANSMISSION LOGIC ---
if st.session_state.running:
    if not selected_tags:
        st.error("Select at least one tag")
        st.session_state.running = False
    else:
        try:
            # Main stable loop
            while st.session_state.running:
                tag = selected_tags[st.session_state.current_idx % len(selected_tags)]
                now = datetime.now()
                
                # Update Status Box in Sidebar part
                stat_placeholder.markdown(f"**Current Status:** Running 🚀 | **Tag:** `{tag}`")

                # Packet Body (Static + Dynamic parts)
                body_dynamic = f"{now.strftime('%d%m%Y')},{now.strftime('%H%M%S')},{lat_val:08.6f},N,{lon_val:09.6f},E"
                body_static = f",0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83"
                body_full = f"PVT,{tag},2.1.1,NR,01,L,{imei_val},{veh_no},1,{body_dynamic}{body_static}"
                
                pkt = f"${body_full},{get_checksum(body_full)}*\r\n"
                
                # Send Packet
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)
                        s.connect((srv_ip, srv_port))
                        s.sendall(pkt.encode('ascii'))
                        st.session_state.tag_status[tag] = "✅"
                        status_text = f"🟢 {tag} SENT"
                except:
                    st.session_state.tag_status[tag] = "❌"
                    status_text = f"🔴 {tag} FAILED"

                # Update Logs & Info Boxes
                st.session_state.logs.insert(0, f"{now.strftime('%H:%M:%S')} | {status_text}")
                log_box.text("\n".join(st.session_state.logs[:20]))
                
                static_info.markdown(f"**IMEI:** `{imei_val}` | **Vehicle:** `{veh_no}`\n**Host:** `{srv_ip}:{srv_port}`")
                raw_pkt_box.code(pkt.strip())
                
                # Advance Index and Sleep
                st.session_state.current_idx += 1
                time.sleep(gap)
                st.rerun() # Refreshing to update map and info
                
        except Exception as e:
            st.error(f"Transmission Loop Error: {e}")
            st.session_state.running = False
