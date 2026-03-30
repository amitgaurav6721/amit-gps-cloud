import streamlit as st
import socket
import time
import pandas as pd
import random

st.set_page_config(page_title="Bihar VLTS Master Control", layout="wide")

if 'running' not in st.session_state:
    st.session_state.running = False

def send_raw(host, port, raw_packet):
    try:
        final_to_send = raw_packet + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        time.sleep(0.2) 
        s.close()
        return True, "Accepted"
    except Exception as e:
        return False, str(e)

st.title("🛰️ Bihar VLTS Movement Simulator")

# --- EMERGENCY STOP BUTTON ---
if st.session_state.running:
    if st.button("🛑 STOP IMMEDIATELY", type="primary", use_container_width=True):
        st.session_state.running = False
        st.rerun()

# --- SIDEBAR ---
st.sidebar.header("⚙️ Server Settings")
server_host = st.sidebar.text_input("Host IP", "vlts.bihar.gov.in")
server_port = st.sidebar.number_input("Port", value=9999)
loop_cnt = st.sidebar.number_input("Total Packets", 1, 5000, 20)
gap = st.sidebar.slider("Gap (sec)", 0.1, 5.0, 1.0)
simulate_move = st.sidebar.checkbox("🚀 Simulate Movement (Live Change)", value=True)

# --- INPUTS ---
c1, c2, c3 = st.columns(3)
with c1:
    tag = st.text_input("TAG", "EGAS")
    imei = st.text_input("IMEI", "860560068639352")
with c2:
    veh = st.text_input("Vehicle", "BR29GC1365")
    base_lat = st.number_input("Starting Latitude", value=25.6489270, format="%.7f")
    base_lon = st.number_input("Starting Longitude", value=84.7841180, format="%.7f")
with c3:
    dt = st.text_input("Date/Time", "04022026,023800")
    fixed_cs = st.text_input("Checksum", "DDE3")

suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"

st.divider()

# --- LIVE STRING PREVIEW BOX ---
st.subheader("📝 Live Packet String (Server Update)")
preview_area = st.empty() # Ye box har packet par update hoga

if not st.session_state.running:
    # Initial preview
    init_loc = f"{base_lat:.7f},N,{base_lon:.7f},E"
    init_str = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{veh},1,{dt},{init_loc},{suffix},{fixed_cs}*"
    preview_area.text_area("Final Packet:", value=init_str, height=150)
    if st.button("🚀 START TRANSMISSION", type="secondary", use_container_width=True):
        st.session_state.running = True
        st.rerun()

# --- EXECUTION ---
if st.session_state.running:
    status_area = st.empty()
    history = []
    current_lat, current_lon = base_lat, base_lon

    for i in range(int(loop_cnt)):
        if not st.session_state.running: break
        
        if simulate_move:
            # Coordinates ko thoda zyada badla hai taaki dikhe (approx 15-20 meters)
            current_lat += random.uniform(0.00010, 0.00020)
            current_lon += random.uniform(0.00010, 0.00020)
        
        loc_str = f"{current_lat:.7f},N,{current_lon:.7f},E"
        final_packet = f"$PVT,{tag},2.1.1,NR,01,L,{imei},{veh},1,{dt},{loc_str},{suffix},{fixed_cs}*"
        
        # UI UPDATE: Ab ye box har bar naya location dikhayega
        preview_area.text_area("Final Packet (Current):", value=final_packet, height=150, key=f"ta_{i}")
        
        success, msg = send_raw(server_host, server_port, final_packet)
        history.insert(0, {"Pkt": i+1, "Location": f"{current_lat:.6f}, {current_lon:.6f}", "Status": "✅" if success else "❌"})
        status_area.table(pd.DataFrame(history))
        time.sleep(gap)
    
    st.session_state.running = False
    st.rerun()
