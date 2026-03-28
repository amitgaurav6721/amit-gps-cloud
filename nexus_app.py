import streamlit as st
import socket
import time
from datetime import datetime

# --- 1. SMART CHECKSUM LOGIC ---
def get_bihar_checksum(payload, length=4):
    checksum = 0
    for char in payload:
        checksum ^= ord(char)
    return f"{checksum:0{length}X}"

# --- 2. CONFIG & UI ---
st.set_page_config(page_title="Amit GPS Hybrid Console", layout="wide")
st.title("🛰️ Bihar VLTS Hybrid Bypass Console")

with st.sidebar:
    st.header("⚙️ Global Settings")
    imei = st.text_input("IMEI", "862567075041793")
    veh_no = st.text_input("Vehicle", "BR04GA5974")
    srv_ip = st.text_input("Host", "vlts.bihar.gov.in")
    srv_port = st.number_input("Port", value=9999)
    
    st.markdown("---")
    mode = st.radio("Select Mode:", ["Static (Manual)", "Experimental (Live Auto)"])

# --- 3. SECTIONS ---

# --- SECTION A: STATIC MODE ---
if mode == "Static (Manual)":
    st.subheader("📝 Static String Lab")
    st.info("Yahan Date/Time aur Checksum fix rahega. Sirf IMEI/Vehicle No badlein.")
    
    static_templates = {
        "String 1 ($GPRMC)": f"$GPRMC,WTEX,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.290684,N,84.643164,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*",
        "String 2 ($PVT)": f"$PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,04022026,023800,25.6501550,N,84.7851780,E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*",
        "String 3 ($,100)": f"$,100,WTEX,1.0.01,NR,01,L,{imei},{veh_no},1,11062025,014226,25.6509430,N,84.7847740,E,0.0,284.7,23,64.0,0.9,0.5,Airtel,0,1,11.9,3.8,0,C,10,405,70,1506,4c74,4c75,1506,10,10e1,1506,08,10e3,1506,07,2662,1506,06,0000,11,000021,A486*"
    }
    
    selected_template = st.selectbox("Choose Template", list(static_templates.keys()))
    manual_string = st.text_area("Edit Raw Packet:", value=static_templates[selected_template], height=100)
    
    if st.button("🚀 SEND STATIC PACKET"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((srv_ip, srv_port))
                s.sendall((manual_string.strip() + "\r\n").encode('ascii'))
                st.success("Sent Successfully!")
        except Exception as e:
            st.error(f"Error: {e}")

# --- SECTION B: EXPERIMENTAL LIVE MODE ---
else:
    st.subheader("🧪 Experimental Logic Rotator")
    st.warning("Yeh mode automatic logic change karega agar data accept nahi hua.")
    
    lat = st.number_input("Lat", value=25.6509450, format="%.7f")
    lon = st.number_input("Lon", value=84.7847730, format="%.7f")
    
    if st.button("▶️ START EXPERIMENT"):
        st.session_state.running = True
        
    if st.button("⏹️ STOP"):
        st.session_state.running = False

    if st.session_state.get('running', False):
        status_box = st.empty()
        log_box = st.empty()
        
        # Logics to rotate
        logics = ["PVT_EGAS_2.1.1", "GPRMC_WTEX_2.1.1", "DOLLAR_100_1.0.01"]
        idx = 0
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((srv_ip, srv_port))
                while st.session_state.running:
                    now = datetime.now()
                    d, t = now.strftime('%d%m%Y'), now.strftime('%H%M%S')
                    current_logic = logics[idx % len(logics)]
                    
                    # Constructing Experimental Packet
                    if current_logic == "PVT_EGAS_2.1.1":
                        body = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{d},{t},{lat:.7f},N,{lon:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                        packet = f"${body},{get_bihar_checksum(body, 4)}*\r\n"
                    elif current_logic == "GPRMC_WTEX_2.1.1":
                        body = f"GPRMC,WTEX,2.1.1,NR,01,L,{imei},{veh_no},1,{d},{t},{lat:.6f},N,{lon:.6f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
                        packet = f"${body},{get_bihar_checksum(body, 4)}*\r\n"
                    else: # Legacy 1.0.01
                        body = f",100,WTEX,1.0.01,NR,01,L,{imei},{veh_no},1,{d},{t},{lat:.7f},N,{lon:.7f},E,0.0,284.7,23,64.0,0.9,0.5,Airtel,0,1,11.9,3.8,0,C,10,405,70,1506,4c74,4c75,1506,10,10e1,1506,08,10e3,1506,07,2662,1506,06,0000,11,000021"
                        packet = f"${body},{get_bihar_checksum(body, 4)}*\r\n"

                    s.sendall(packet.encode('ascii'))
                    status_box.info(f"Trying Logic: {current_logic} | Checksum: {get_bihar_checksum(body, 4)}")
                    log_box.text(f"Sent: {packet.strip()}")
                    
                    idx += 1
                    time.sleep(2)
        except Exception as e:
            st.error(f"Error: {e}")
