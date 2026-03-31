import streamlit as st
import socket
import time
import pandas as pd
import random
from supabase import create_client, Client

st.set_page_config(page_title="Bihar VLTS Master Control", layout="wide")

# --- FIXED SETTINGS ---
SERVER_HOST = "vlts.bihar.gov.in"
SERVER_PORT = 9999
TIME_GAP = 1.0
SIMULATE_MOVE = True

# --- SUPABASE CONNECTION ---
URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
# Yahan apni 'anon' 'public' key hi rehne dein
KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW" 
supabase: Client = create_client(URL, KEY)

# --- SESSION STATE ---
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

# --- LOGIN LOGIC (FIXED FOR 1-CLICK) ---
if not st.session_state.authenticated:
    st.title("🔒 Bihar VLTS - Secure Access")
    input_pin = st.text_input("Enter Access PIN", type="password")
    
    if st.button("Unlock Portal", type="primary", use_container_width=True):
        try:
            # Table fetch
            res = supabase.table("locations_master").select("*").eq("access_pin", input_pin).limit(1).execute()
            if res.data:
                loc = res.data[0]
                # Sabse pehle values set karein
                st.session_state.base_lat = loc['latitude']
                st.session_state.base_lon = loc['longitude']
                st.session_state.loc_name = loc['location_name']
                st.session_state.authenticated = True
                # Turant rerun karein bina delay ke
                st.rerun()
            else:
                st.error("Invalid PIN!")
        except Exception as e:
            st.error(f"DB Error: {e}")
    st.stop()

# --- SIDEBAR MAP ---
with st.sidebar:
    st.subheader(f"📍 {st.session_state.loc_name}")
    map_df = pd.DataFrame({'lat': [st.session_state.base_lat], 'lon': [st.session_state.base_lon]})
    st.map(map_df, zoom=12)

# --- SOCKET SENDER ---
def send_packet(packet):
    try:
        final_packet = packet + " \r \n "
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((SERVER_HOST, SERVER_PORT))
        s.sendall(final_packet.encode('ascii'))
        s.close()
        return True
    except:
        return False

# --- MAIN UI ---
col_title, col_logout = st.columns([0.85, 0.15])
with col_title:
    st.title(f"🛰️ Bihar VLTS Simulator")
with col_logout:
    if st.button("🔒 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.info(f"📍 **Location:** {st.session_state.loc_name} | **Lat:** {st.session_state.base_lat:.7f} | **Lon:** {st.session_state.base_lon:.7f}")

# Inputs logic
def fetch_imei():
    v = st.session_state.veh_input.upper().strip()
    if v:
        try:
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v).limit(1).execute()
            if res.data: st.session_state.imei_val = res.data[0]['imei_no']
        except: pass

c1, c2 = st.columns(2)
with c1:
    veh = st.text_input("Vehicle Number", key="veh_input", on_change=fetch_imei).upper().strip()
with c2:
    imei = st.text_input("IMEI Number", value=st.session_state.imei_val)

st.divider()

# Controls
if not st.session_state.running:
    if st.button("🚀 START TRANSMISSION", type="primary", use_container_width=True):
        if veh and imei:
            try:
                # Store data in vehicle_master
                supabase.table("vehicle_master").upsert({"vehicle_no": veh, "imei_no": imei}, on_conflict="vehicle_no").execute()
                st.session_state.running = True
                st.rerun()
            except Exception as e:
                st.error(f"Storage Error: {e}")
        else:
            st.warning("Vehicle/IMEI bhariye.")
else:
    if st.button("🛑 STOP TRANSMISSION", type="secondary", use_container_width=True):
        st.session_state.running = False
        st.rerun()

# --- EXECUTION ---
if st.session_state.running:
    progress_text = st.empty()
    progress_bar = st.progress(0)
    curr_lat, curr_lon = st.session_state.base_lat, st.session_state.base_lon
    TAGS = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR"]
    suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
    
    while st.session_state.running:
        dt = time.strftime("%d%m%Y,%H%M%S")
        if SIMULATE_MOVE:
            curr_lat += random.uniform(0.00005, 0.0001)
            curr_lon += random.uniform(0.00005, 0.0001)
            
        for i, t in enumerate(TAGS):
            if not st.session_state.running: break
            percent = int((i + 1) / len(TAGS) * 100)
            progress_bar.progress(percent)
            progress_text.markdown(f"**⚡ Sending Tag:** `{t}` ({percent}%)")
            
            pkt = f"$PVT,{t},2.1.1,NR,01,L,{imei},{veh},1,{dt},{curr_lat:.7f},N,{curr_lon:.7f},E,{suffix},DDE3*"
            send_packet(pkt)
            time.sleep(0.05) 
            
        time.sleep(TIME_GAP)
        progress_bar.progress(0)
