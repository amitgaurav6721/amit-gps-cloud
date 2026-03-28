import streamlit as st
import socket
import time
from datetime import datetime
import pandas as pd

# --- 1. CORE LOGIC ---
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

# --- 2. INITIALIZATION ---
st.set_page_config(page_title="Amit GPS Master Hybrid", layout="wide")

if 'tag_status' not in st.session_state:
    st.session_state.tag_status = {}
if 'extended_tags' not in st.session_state:
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]
if 'running' not in st.session_state:
    st.session_state.running = False

# Function to stop auto-run on mode switch
def reset_running():
    st.session_state.running = False

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Global Settings")
    imei = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Latency Gap (Sec)", 0.1, 2.0, 0.5)
    
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
    # FIX APPLIED HERE
    mode = st.radio(
        "Select Operational Mode:", 
        ["Static (Manual)", "Experimental (Live Auto)"],
        on_change=reset_running
    )

# --- 4. COMMON UI ---
st.title("🛰️ Bihar VLTS Master Hybrid Console")
st.subheader("📍 Target Location Settings")
col_lat, col_lon = st.columns(2)
lat = col_lat.number_input("Latitude", value=25.650945, format="%.6f")
lon = col_lon.number_input("Longitude", value=84.784773, format="%.6f")

map_df = pd.DataFrame({'lat': [lat], 'lon': [lon]})
st.map(map_df)

st.markdown("---")

# --- 5. MODE LOGIC ---

if mode == "Static (Manual)":
    st.subheader("📝 Static Lab (Fixed Checksum Mode)")
    static_templates = {
        "String 1 ($GPRMC)": f"$GPRMC,WTEX,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.290684,N,84.643164,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*",
        "String 2 ($PVT)": f"$PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.6501550,N,84.7851780,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*",
        "String 3 ($,100)": f"$,100,WTEX,1.0.01,NR,01,L,{imei},{veh_no},1,11062025,014226,25.6509430,N,84.7847740,E,0.0,284.7,23,64.0,0.9,0.5,Airtel,0,1,11.9,3.8,0,C,10,405,70,1506,4c74,4c75,1506,10,10e1,1506,08,10e3,1506,07,2662,1506,06,0000,11,000021,A486*"
    }
    sel_template = st.selectbox("Choose Template", list(static_templates.keys()))
    manual_packet = st.text_area("Final Raw Packet:", value=static_templates[sel_template], height=100)
    
    if st.button("🚀 SEND STATIC PACKET"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((srv_ip, srv_port))
                s.sendall((manual_packet.strip() + "\r\n").encode('ascii'))
                st.success("Static Packet Sent!")
        except Exception as e:
            st.error(f"Failed: {e}")

else:
    st.subheader("🧪 Turbo Discovery & Filter Mode")
    selected_tags = []
    tag_cols = st.columns(5)
    for i, t_tag in enumerate(st.session_state.extended_tags):
        status = st.session_state.tag_status.get(t_tag, "⚪")
        if tag_cols[i % 5].checkbox(f"{status} {t_tag}", value=True, key=f"check_{t_tag}"):
            selected_tags.append(t_tag)

    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("🚀 START AUTO-ROTATOR", use_container_width=True):
        if not selected_tags: st.error("Tag select karo!")
        else: st.session_state.running = True
    
    if col_btn2.button("⏹️ STOP", use_container_width=True):
        st.session_state.running = False

    if st.session_state.running:
        log_placeholder = st.empty()
        idx = 0
        while st.session_state.running:
            current_tag = selected_tags[idx % len(selected_tags)]
            t_start = time.time()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    s.connect((srv_ip, srv_port))
                    now = datetime.now()
                    d_live, t_live = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                    body = f"PVT,{current_tag},2.1.1,NR,01,L,{imei},{veh_no},1,{d_live},{t_live},{format_coord(lat,True)},N,{format_coord(lon,False)},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                    packet = f"${body},{get_bihar_checksum(body)}*\r\n"
                    s.sendall(packet.encode('ascii'))
                    latency = round((time.time() - t_start) * 1000, 2)
                    st.session_state.tag_status[current_tag] = "✅"
                    log_placeholder.success(f"Sent: {current_tag} | {latency}ms")
            except Exception as e:
                st.session_state.tag_status[current_tag] = "❌"
                log_placeholder.error(f"Failed: {current_tag}")
                time.sleep(1)
            
            idx += 1
            time.sleep(interval)
            st.rerun()
