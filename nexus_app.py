import streamlit as st
import socket
import time
import pandas as pd
import random
from supabase import create_client, Client

st.set_page_config(page_title="Bihar VLTS Master Control", layout="wide")

# --- SUPABASE CONNECTION ---
# Inhe apne original database.py ya credentials se match kar lena
URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
KEY = "YOUR_SUPABASE_ANON_KEY" # Yahan apni anon key daal dena
supabase: Client = create_client(URL, KEY)

if 'running' not in st.session_state:
    st.session_state.running = False

# --- TAG LIST (16 TAGS) ---
TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR"]

def send_raw(host, port, raw_packet):
    try:
        # Tera manga hua format with spaces
        final_to_send = raw_packet + " \r \n "
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        time.sleep(0.1) 
        s.close()
        return True, "Accepted"
    except Exception as e:
        return False, str(e)

st.title("🛰️ Bihar VLTS Multi-Tag Simulator")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Server Settings")
server_host = st.sidebar.text_input("Host IP", "vlts.bihar.gov.in")
server_port = st.sidebar.number_input("Port", value=9999)
gap = st.sidebar.slider("Gap (sec)", 0.1, 5.0, 1.0)

# --- INPUTS ---
c1, c2 = st.columns(2)
with c1:
    imei = st.text_input("IMEI", "860560068639352")
    veh = st.text_input("Vehicle", "BR29GC1365")
with c2:
    base_lat = st.number_input("Starting Latitude", value=25.6489270, format="%.7f")
    base_lon = st.number_input("Starting Longitude", value=84.7841180, format="%.7f")

suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
fixed_cs = "DDE3"

# --- BUTTONS ---
if not st.session_state.running:
    if st.button("🚀 START BULK TRANSMISSION", type="primary", use_container_width=True):
        # Database mein store karne ka logic
        try:
            supabase.table("vehicle_master").insert({"vehicle_no": veh, "imei_no": imei}).execute()
        except:
            pass # Agar pehle se hai toh error skip karega
        
        st.session_state.running = True
        st.rerun()
else:
    if st.button("🛑 STOP IMMEDIATELY", type="secondary", use_container_width=True):
        st.session_state.running = False
        st.rerun()

# --- MONITOR SCREEN ---
st.subheader("📺 Live Bulk Strings Monitor")
bulk_preview = st.empty() 

# --- EXECUTION LOOP ---
if st.session_state.running:
    status_area = st.empty()
    history = []
    
    while st.session_state.running:
        dt = time.strftime("%d%m%Y,%H%M%S")
        all_strings = "" 
        
        for current_tag in TAG_LIST:
            if not st.session_state.running: break
            
            final_packet = f"$PVT,{current_tag},2.1.1,NR,01,L,{imei},{veh},1,{dt},{base_lat:.7f},N,{base_lon:.7f},E,{suffix},{fixed_cs}*"
            all_strings += f"🔹 [{current_tag}]: {final_packet}\n\n"
            
            success, msg = send_raw(server_host, server_port, final_packet)
            history.insert(0, {"Time": dt.split(',')[1], "Tag": current_tag, "Status": "✅" if success else "❌"})
        
        bulk_preview.text_area("Live Data Stream:", value=all_strings, height=400)
        status_area.table(pd.DataFrame(history).head(16))
        time.sleep(gap)
