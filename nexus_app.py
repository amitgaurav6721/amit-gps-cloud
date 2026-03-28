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

# --- 2. UI & STATE ---
st.set_page_config(page_title="Amit GPS Master Hybrid", layout="wide")

if 'tag_status' not in st.session_state:
    st.session_state.tag_status = {}
if 'extended_tags' not in st.session_state:
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]

st.title("🛰️ Bihar VLTS Master Hybrid Console")

# --- 3. SIDEBAR (Global Settings) ---
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
        if new_tag.upper() not in st.session_state.extended_tags:
            st.session_state.extended_tags.append(new_tag.upper())
    
    if st.button("🧹 Clear Tag Logs"):
        st.session_state.tag_status = {}

    st.markdown("---")
    mode = st.radio("Select Mode:", ["Static (Manual)", "Experimental (Live Auto)"])

# --- 4. COMMON SECTION (Map & Location) ---
st.subheader("📍 Target Location & Map")
col_lat, col_lon = st.columns(2)
lat = col_lat.number_input("Lat", value=25.650945, format="%.6f")
lon = col_lon.number_input("Lon", value=84.784773, format="%.6f")

map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
st.map(map_data)

st.markdown("---")

# --- 5. MODE SECTIONS ---

if mode == "Static (Manual)":
    st.subheader("📝 Static Lab (Fixed Checksum)")
    static_templates = {
        "String 1 ($GPRMC)": f"$GPRMC,WTEX,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.290684,N,84.643164,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*",
        "String 2 ($PVT)": f"$PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.6501550,N,84.7851780,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*",
        "String 3 ($,100)": f"$,100,WTEX,1.0.01,NR,01,L,{imei},{veh_no},1,11062025,014226,25.6509430,N,84.7847740,E,0.0,284.7,23,64.0,0.9,0.5,Airtel,0,1,11.9,3.8,0,C,10,405,70,1506,4c74,4c75,1506,10,10e1,1506,08,10e3,1506,07,2662,1506,06,0000,11,000021,A486*"
    }
    sel = st.selectbox("Choose Working Template", list(static_templates.keys()))
    manual_string = st.text_area("Edit Packet (Checksum won't change):", value=static_templates[sel], height=100)
    
    if st.button("🚀 SEND STATIC PACKET"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5); s.connect((srv_ip, srv_port))
                s.sendall((manual_string.strip() + "\r\n").encode('ascii'))
                st.success("Static Packet Sent!")
        except Exception as e: st.error(f"Error: {e}")

else:
    st.subheader("🧪 Turbo Discovery Mode")
    
    # Tag Discovery UI
    st.write("Tag Status Tracker:")
    tag_cols = st.columns(5)
    for i, t_tag in enumerate(st.session_state.extended_tags):
        status = st.session_state.tag_status.get(t_tag, "⚪")
        tag_cols[i % 5].write(f"{status} **{t_tag}**")

    if st.button("🚀 START AUTO-ROTATOR"): st.session_state.running = True
    if st.button("⏹️ STOP"): st.session_state.running = False

    if st.session_state.get('running', False):
        log_area = st.empty()
        idx = 0
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5); s.connect((srv_ip, srv_port))
                while st.session_state.running:
                    tag = st.session_state.extended_tags[idx % len(st.session_state.extended_tags)]
                    now = datetime.now()
                    d_live, t_live = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                    
                    t_start = time.time()
                    # Experimental Body
                    body = f"PVT,{tag},2.1.1,NR,01,L,{imei},{veh_no},1,{d_live},{t_live},{format_coord(lat,True)},N,{format_coord(lon,False)},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                    packet = f"${body},{get_bihar_checksum(body)}*\r\n"
                    
                    try:
                        s.sendall(packet.encode('ascii'))
                        latency = round((time.time() - t_start) * 1000, 2)
                        st.session_state.tag_status[tag] = "✅"
                        log_area.success(f"Sent {tag} | Latency: {latency}ms | Time: {t_live}")
                    except Exception as e:
                        st.session_state.tag_status[tag] = "❌"
                        log_area.error(f"Failed {tag} | Error: {e}")
                        break # Reconnect
                    
                    idx += 1
                    time.sleep(interval)
        except:
            st.warning("🔄 Server disconnected. Reconnecting...")
            time.sleep(1)
