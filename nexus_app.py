import streamlit as st
import socket
import time
from datetime import datetime
import pandas as pd

# --- UI & STATE ---
st.set_page_config(page_title="Amit GPS Turbo Lab", layout="wide")
if 'tag_status' not in st.session_state:
    st.session_state.tag_status = {} # Tag -> Status (Success/Error)

st.title("🛰️ Bihar VLTS Master Turbo Console")

# --- SIDEBAR & SETTINGS ---
with st.sidebar:
    st.header("⚙️ Global Settings")
    imei = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    interval = st.slider("Latency Gap (Sec)", 0.1, 2.0, 0.5)
    
    st.markdown("---")
    if st.button("🧹 Clear Tag Logs"):
        st.session_state.tag_status = {}

# --- MAP SECTION (Wapas Aa Gaya!) ---
st.subheader("📍 Live Target Location")
lat = st.number_input("Lat", value=25.650945, format="%.6f")
lon = st.number_input("Lon", value=84.784773, format="%.6f")
map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
st.map(map_data)

# --- EXPERIMENTAL ZONE ---
st.subheader("🧪 Turbo Logic Rotator & Discovery")

# Tag Highlighting Logic
cols = st.columns(len(st.session_state.extended_tags))
for i, tag in enumerate(st.session_state.extended_tags):
    status = st.session_state.tag_status.get(tag, "⚪")
    cols[i % 5].write(f"{status} **{tag}**")

if st.button("🚀 START DISCOVERY"):
    st.session_state.running = True

if st.session_state.get('running', False):
    log_area = st.empty()
    idx = 0
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((srv_ip, srv_port))
            
            while st.session_state.running:
                tag = st.session_state.extended_tags[idx % len(st.session_state.extended_tags)]
                t_start = time.time() # Latency check start
                
                # Packet Building
                now = datetime.now()
                d, t = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                body = f"PVT,{tag},2.1.1,NR,01,L,{imei},{veh_no},1,{d},{t},{format_coord(lat,True)},N,{format_coord(lon,False)},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                packet = f"${body},{get_bihar_checksum(body)}*\r\n"
                
                try:
                    s.sendall(packet.encode('ascii'))
                    t_end = time.time()
                    latency = round((t_end - t_start) * 1000, 2) # Latency in MS
                    
                    st.session_state.tag_status[tag] = "✅" # Success!
                    log_area.success(f"🚀 Sent: {tag} | Latency: {latency}ms | Time: {t}")
                    
                except Exception as e:
                    st.session_state.tag_status[tag] = "❌" # Broken Pipe/Error
                    log_area.error(f"❌ Failed: {tag} | Error: {e}")
                    break # Reconnect for next tag
                
                idx += 1
                time.sleep(interval)
    except:
        st.warning("🔄 Reconnecting to Bihar Server...")
        time.sleep(1)
