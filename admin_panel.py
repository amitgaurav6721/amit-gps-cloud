import streamlit as st
import pandas as pd
import time
import socket
import random
from datetime import datetime, timedelta
from database import supabase, get_tags

# --- OFFICIAL BIHAR VLTS SETTINGS ---
HOST_URL = "vlts.bihar.gov.in"
PORT = 9999

def send_vlts_raw(host, port, raw_packet):
    try:
        # Aapke simulator wala exact logic: packet + \r\n
        final_to_send = raw_packet + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        s.close()
        return True
    except:
        return False

def admin_panel():
    st.sidebar.markdown("<h2 style='color: #FF4B4B;'>👑 Admin Pro Max</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🔒 Logout Admin", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Bulk Simulator", "🏷️ Tag Manager", "👤 User Control", "💳 Recharges"])
    
    # --- TAB 2: HIGH-SPEED BULK SIMULATOR ---
    with t2:
        st.subheader("🛰️ Bihar VLTS Movement Simulator (Bulk)")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            v_no = c1.text_input("Vehicle No", value="BR04GA5974").upper().strip()
            i_no = c2.text_input("IMEI No", value="862567075041793").strip()
            gap = c3.slider("Gap (Seconds)", 0.1, 5.0, 1.0)
            
            base_lat = c1.number_input("Starting Latitude", value=25.6501550, format="%.7f")
            base_lon = c2.number_input("Starting Longitude", value=84.7851780, format="%.7f")
            simulate_move = c3.checkbox("🚀 Live Movement", value=True)

        all_db_tags = get_tags()
        st.write(f"✅ **{len(all_db_tags)} Tags** loaded from DB.")

        # Fixed Suffix and Checksum from your example
        suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
        fixed_cs = "DDE3"

        st.divider()
        col_btn, col_preview = st.columns([1, 2])
        
        if 'injecting' not in st.session_state:
            st.session_state.injecting = False

        if not st.session_state.injecting:
            if col_btn.button("🚀 START TRANSMISSION", type="primary", use_container_width=True):
                st.session_state.injecting = True
                st.rerun()
        else:
            if col_btn.button("🛑 STOP IMMEDIATELY", type="primary", use_container_width=True):
                st.session_state.injecting = False
                st.rerun()
            
            preview_box = st.empty()
            cur_lat, cur_lon = base_lat, base_lon
            
            # --- HIGH SPEED LOOP ---
            while st.session_state.injecting:
                d_now = datetime.now().strftime("%d%m%Y")
                t_now = datetime.now().strftime("%H%M%S")
                
                if simulate_move:
                    cur_lat += random.uniform(0.00001, 0.00005)
                    cur_lon += random.uniform(0.00001, 0.00005)
                
                loc_str = f"{cur_lat:.7f},N,{cur_lon:.7f},E"
                
                # Burst send for all tags in DB
                for tag in all_db_tags:
                    # EXACT FORMAT AS YOUR SIMULATOR
                    packet = f"$PVT,{tag},2.1.1,NR,01,L,{i_no},{v_no},1,{d_now},{t_now},{loc_str},{suffix},{fixed_cs}*"
                    send_vlts_raw(HOST_URL, PORT, packet)
                
                preview_box.text_area("Last Packet Sent:", value=packet, height=100)
                time.sleep(gap)

    # --- OTHER TABS (Same as your database setup) ---
    with t3:
        st.subheader("🏷️ Tag Manager")
        res_t = supabase.table("custom_tags").select("tag_name").execute()
        if res_t.data:
            cols = st.columns(4)
            for i, t in enumerate(res_t.data):
                with cols[i % 4]: st.info(f"**{t['tag_name']}**")
