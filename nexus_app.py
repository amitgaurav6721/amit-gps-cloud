import streamlit as st
import socket
import time
import pandas as pd
import random
from supabase import create_client, Client

st.set_page_config(page_title="Bihar VLTS Master Control", layout="wide")

# --- SUPABASE CONNECTION ---
URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
KEY = "YOUR_ACTUAL_ANON_KEY" # Apni asli key yahan rehne dena
supabase: Client = create_client(URL, KEY)

if 'running' not in st.session_state:
    st.session_state.running = False
if 'imei_val' not in st.session_state:
    st.session_state.imei_val = "860560068639352"

# --- FUNCTION: AUTO-FETCH IMEI ---
def fetch_imei():
    v_no = st.session_state.veh_input.upper().strip()
    if v_no:
        try:
            # vehicle_master se IMEI nikaalna
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no).limit(1).execute()
            if res.data:
                st.session_state.imei_val = res.data[0]['imei_no']
                st.toast(f"✅ IMEI Found for {v_no}", icon="🔍")
            else:
                st.toast("⚠️ Vehicle not in DB", icon="❓")
        except:
            pass

# --- TAG LIST ---
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
        return True, "Accepted"
    except Exception as e:
        return False, str(e)

st.title("🛰️ Bihar VLTS Multi-Tag Simulator")

# --- INPUTS ---
c1, c2 = st.columns(2)
with c1:
    # Vehicle input with on_change trigger
    veh = st.text_input("Vehicle", value="BR29GC1365", key="veh_input", on_change=fetch_imei).upper().strip()
    # IMEI value session_state se aayegi
    imei = st.text_input("IMEI", value=st.session_state.imei_val)
with c2:
    base_lat = st.number_input("Starting Latitude", value=25.6489270, format="%.7f")
    base_lon = st.number_input("Starting Longitude", value=84.7841180, format="%.7f")

# --- BUTTONS ---
if not st.session_state.running:
    if st.button("🚀 START BULK TRANSMISSION", type="primary", use_container_width=True):
        # Naya data bhi store kar lete hain agar pehle se nahi hai
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

if st.session_state.running:
    status_area = st.empty()
    history = []
    suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
    
    while st.session_state.running:
        dt = time.strftime("%d%m%Y,%H%M%S")
        all_strings = "" 
        for current_tag in TAG_LIST:
            if not st.session_state.running: break
            final_packet = f"$PVT,{current_tag},2.1.1,NR,01,L,{imei},{veh},1,{dt},{base_lat:.7f},N,{base_lon:.7f},E,{suffix},DDE3*"
            all_strings += f"🔹 [{current_tag}]: {final_packet}\n\n"
            success, _ = send_raw("vlts.bihar.gov.in", 9999, final_packet)
            history.insert(0, {"Time": dt.split(',')[1], "Tag": current_tag, "Status": "✅" if success else "❌"})
        
        bulk_preview.text_area("Live Data Stream:", value=all_strings, height=400)
        status_area.table(pd.DataFrame(history).head(16))
        time.sleep(1.0)
