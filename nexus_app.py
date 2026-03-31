import streamlit as st
import socket
import time
import pandas as pd
import random
from supabase import create_client, Client

st.set_page_config(page_title="Bihar VLTS Master Control", layout="wide")

# --- SUPABASE CONNECTION ---
URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW" 
supabase: Client = create_client(URL, KEY)

# --- SESSION STATE INITIALIZATION ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'running' not in st.session_state:
    st.session_state.running = False
if 'imei_val' not in st.session_state:
    st.session_state.imei_val = ""
if 'base_lat' not in st.session_state:
    st.session_state.base_lat = 25.6489270
if 'base_lon' not in st.session_state:
    st.session_state.base_lon = 84.7841180
if 'loc_name' not in st.session_state:
    st.session_state.loc_name = "Default"

# --- LOGIN & AUTO-LOCATION FETCH ---
if not st.session_state.authenticated:
    st.title("🔒 Bihar VLTS - Secure Access")
    st.write("Apna 4-digit Location PIN daalein portal unlock karne ke liye.")
    
    input_pin = st.text_input("Enter Access PIN", type="password", help="Ye wahi PIN hai jo locations_master table mein set hai.")
    
    if st.button("Unlock & Set Location", type="primary", use_container_width=True):
        try:
            # Table se PIN match karna aur data nikalna
            res = supabase.table("locations_master").select("*").eq("access_pin", input_pin).limit(1).execute()
            
            if res.data:
                loc_data = res.data[0]
                st.session_state.authenticated = True
                # Location data ko session mein set karna
                st.session_state.base_lat = loc_data['latitude']
                st.session_state.base_lon = loc_data['longitude']
                st.session_state.loc_name = loc_data['location_name']
                st.success(f"✅ Access Granted! Location: {st.session_state.loc_name}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Invalid PIN! Please check your code.")
        except Exception as e:
            st.error(f"Connection Error: {e}")
    st.stop()

# --- SIMULATOR LOGIC (AFTER LOGIN) ---
def fetch_imei_logic():
    v_no = st.session_state.veh_input.upper().strip()
    if v_no:
        try:
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no).limit(1).execute()
            if res.data:
                st.session_state.imei_val = res.data[0]['imei_no']
                st.toast(f"✅ IMEI Found: {st.session_state.imei_val}")
            else:
                st.toast("❓ Vehicle not in DB", icon="⚠️")
        except: pass

TAG_LIST = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR"]

def send_raw(host, port, raw_packet):
    try:
        final_to_send = raw_packet + " \r \n "
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        time.sleep(0.1) 
        s.close()
        return True
    except: return False

# --- UI DESIGN ---
st.title(f"🛰️ Bihar VLTS Simulator - [{st.session_state.loc_name}]")

# Sidebar for logout and settings
st.sidebar.header("⚙️ Server Settings")
server_host = st.sidebar.text_input("Host IP", "vlts.bihar.gov.in")
server_port = st.sidebar.number_input("Port", value=9999)
gap = st.sidebar.slider("Gap (sec)", 0.1, 5.0, 1.0)
simulate_move = st.sidebar.checkbox("🚀 Simulate Movement", value=True)

if st.sidebar.button("🔒 Logout & Lock"):
    st.session_state.authenticated = False
    st.rerun()

# Displaying active location (Read-only)
st.info(f"📍 **Active Location:** {st.session_state.loc_name} | **Lat:** {st.session_state.base_lat} | **Lon:** {st.session_state.base_lon}")

# Main Input Section
c1, c2 = st.columns(2)
with c1:
    veh = st.text_input("Vehicle Number", value="", key="veh_input", on_change=fetch_imei_logic).upper().strip()
with c2:
    imei = st.text_input("IMEI Number", value=st.session_state.imei_val)

st.divider()

if not st.session_state.running:
    if st.button("🚀 START BULK TRANSMISSION", type="primary", use_container_width=True):
        try:
            supabase.table("vehicle_master").upsert({"vehicle_no": veh, "imei_no": imei}, on_conflict="vehicle_no").execute()
        except: pass
        st.session_state.running = True
        st.rerun()
else:
    if st.button("🛑 STOP IMMEDIATELY", type="secondary", use_container_width=True):
        st.session_state.running = False
        st.rerun()

st.subheader("📺 Live Bulk Strings Monitor")
bulk_preview = st.empty() 

# --- EXECUTION LOOP ---
if st.session_state.running:
    status_area = st.empty()
    history = []
    current_lat, current_lon = st.session_state.base_lat, st.session_state.base_lon
    suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
    
    while st.session_state.running:
        dt = time.strftime("%d%m%Y,%H%M%S")
        all_strings = "" 
        if simulate_move:
            current_lat += random.uniform(0.00010, 0.00020)
            current_lon += random.uniform(0.00010, 0.00020)

        for current_tag in TAG_LIST:
            if not st.session_state.running: break
            final_packet = f"$PVT,{current_tag},2.1.1,NR,01,L,{imei},{veh},1,{dt},{current_lat:.7f},N,{current_lon:.7f},E,{suffix},DDE3*"
            all_strings += f"🔹 [{current_tag}]: {final_packet}\n\n"
            success = send_raw(server_host, server_port, final_packet)
            history.insert(0, {"Time": dt.split(',')[1], "Tag": current_tag, "Status": "✅" if success else "❌"})
        
        bulk_preview.text_area("Live Data Stream:", value=all_strings, height=400)
        status_area.table(pd.DataFrame(history).head(16))
        time.sleep(gap)
