import streamlit as st
import socket
import time
from datetime import datetime

# --- 1. SMART LOGIC: 4-DIGIT CHECKSUM & PADDING ---
def get_bihar_checksum(payload):
    checksum = 0
    for char in payload:
        checksum ^= ord(char)
    return f"{checksum:04X}" # Exact 4-digit Hex as per working strings

def format_coord(val, is_lat=True):
    # Bihar server leading zero mangta hai (e.g., 084... for Lon)
    if is_lat:
        return f"{val:08.6f}" # 28.123456
    else:
        return f"{val:09.6f}" # 084.123456

# --- 2. CONFIG & TAG LIST ---
st.set_page_config(page_title="Amit GPS Ultra Hybrid", layout="wide")

# Excel/Portal se nikale gaye top Tags
if 'extended_tags' not in st.session_state:
    st.session_state.extended_tags = ["GRL", "ASPL", "WTEX", "EGAS", "VLT", "MENT", "BBOX", "TNGR", "RCON", "GPST"]

st.title("🛰️ Bihar VLTS Master Console")

with st.sidebar:
    st.header("⚙️ Global Settings")
    imei = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    
    st.markdown("---")
    # Future Tag Entry: Naya tag yahan se add karein
    new_tag = st.text_input("➕ Add New Tag for Future:")
    if st.button("Save Tag") and new_tag:
        if new_tag.upper() not in st.session_state.extended_tags:
            st.session_state.extended_tags.append(new_tag.upper())
            st.success(f"Tag {new_tag} Added!")

    mode = st.radio("Select Mode:", ["Static (Manual)", "Experimental (Live Auto)"])

# --- 3. MODES ---

if mode == "Static (Manual)":
    st.subheader("📝 Static Lab (Fixed Checksum)")
    # Aapki working strings (DDE3/A486 fixed)
    static_templates = {
        "String 1 ($GPRMC)": f"$GPRMC,WTEX,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.290684,N,84.643164,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*",
        "String 2 ($PVT)": f"$PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.6501550,N,84.7851780,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*",
    }
    sel = st.selectbox("Template", list(static_templates.keys()))
    raw_p = st.text_area("Packet:", value=static_templates[sel], height=100)
    if st.button("🚀 SEND STATIC"):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((srv_ip, srv_port))
            s.sendall((raw_p.strip() + "\r\n").encode('ascii'))
            st.success("Static Packet Sent!")

else:
    st.subheader("🧪 Live Auto-Logic Rotator")
    col1, col2 = st.columns(2)
    lat = col1.number_input("Lat", value=25.650945, format="%.6f")
    lon = col2.number_input("Lon", value=84.784773, format="%.6f")
    
    if st.button("▶️ START EXPERIMENT"): st.session_state.running = True
    if st.button("⏹️ STOP"): st.session_state.running = False

    if st.session_state.get('running', False):
        st.info("Rotating Tags, Protocols, and Checksums...")
        log_area = st.empty()
        idx = 0
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((srv_ip, srv_port))
                while st.session_state.running:
                    now = datetime.now()
                    d, t = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                    
                    # Logic Rotation
                    tag = st.session_state.extended_tags[idx % len(st.session_state.extended_tags)]
                    lat_f = format_coord(lat, True)
                    lon_f = format_coord(lon, False)
                    
                    # Protocol 1: Standard PVT
                    body = f"PVT,{tag},2.1.1,NR,01,L,{imei},{veh_no},1,{d},{t},{lat_f},N,{lon_f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                    packet = f"${body},{get_bihar_checksum(body)}*\r\n"
                    
                    s.sendall(packet.encode('ascii'))
                    log_area.code(f"Logic: {tag} | Packet: {packet.strip()}")
                    
                    idx += 1
                    time.sleep(2)
        except Exception as e:
            st.error(f"Error: {e}")
