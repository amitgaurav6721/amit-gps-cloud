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
        # ⚠️ YAHAN DEKH: BILKUL BHI SPACE NAHI HAI
        final_to_send = raw_packet.strip() + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(8) # Timeout thoda badha diya hai
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
    
    # --- TAB 1: REPORTS (FIXED) ---
    with t1:
        st.subheader("📊 Live Activity Reports")
        if st.button("🔄 Refresh Logs", use_container_width=True):
            st.rerun()
        try:
            # Sidhe activity_logs table se data fetch
            res = supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(25).execute()
            if res.data:
                df = pd.DataFrame(res.data)
                # Purana kachra columns hatana
                cols_to_show = [c for c in ['created_at', 'vehicle_no', 'user_id'] if c in df.columns]
                st.dataframe(df[cols_to_show], use_container_width=True)
            else:
                st.info("Log table khali hai. Simulator chalao pehle.")
        except Exception as e:
            st.error(f"Report fetch nahi hui: {e}")

    # --- TAB 2: BULK SIMULATOR (STRICT FORMAT) ---
    with t2:
        st.subheader("🛰️ Bihar VLTS Movement Simulator")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            v_no = c1.text_input("Vehicle No", value="BR04GA5974").upper().strip()
            i_no = c2.text_input("IMEI No", value="862567075041793").strip()
            gap = c3.slider("Gap (Seconds)", 0.1, 5.0, 1.0)
            base_lat = c1.number_input("Starting Latitude", value=25.6501550, format="%.7f")
            base_lon = c2.number_input("Starting Longitude", value=84.7851780, format="%.7f")
            simulate_move = c3.checkbox("🚀 Live Movement", value=True)

        all_db_tags = get_tags()
        st.write(f"✅ **{len(all_db_tags)} Tags** ready to fire.")

        suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
        fixed_cs = "DDE3"

        st.divider()
        if 'injecting' not in st.session_state:
            st.session_state.injecting = False

        col_btn, col_txt = st.columns([1, 2])
        if not st.session_state.injecting:
            if col_btn.button("🚀 START TRANSMISSION", type="primary", use_container_width=True):
                st.session_state.injecting = True
                st.rerun()
        else:
            if col_btn.button("🛑 STOP IMMEDIATELY", type="primary", use_container_width=True):
                st.session_state.injecting = False
                st.rerun()
            
            status_box = st.empty()
            preview_box = st.empty()
            log_box = st.empty()
            cur_lat, cur_lon = base_lat, base_lon
            
            while st.session_state.injecting:
                d_now = datetime.now().strftime("%d%m%Y")
                t_now = datetime.now().strftime("%H%M%S")
                
                if simulate_move:
                    cur_lat += random.uniform(0.00001, 0.00005)
                    cur_lon += random.uniform(0.00001, 0.00005)
                
                loc_str = f"{cur_lat:.7f},N,{cur_lon:.7f},E"
                all_tags_preview = ""
                sent_count = 0
                
                for tag in all_db_tags:
                    # EXACT STRING FORMAT - NO SPACES
                    packet = f"$PVT,{tag},2.1.1,NR,01,L,{i_no},{v_no},1,{d_now},{t_now},{loc_str},{suffix},{fixed_cs}*"
                    all_tags_preview += f"🔹 [{tag}]: {packet}\n\n"
                    
                    if send_vlts_raw(HOST_URL, PORT, packet):
                        sent_count += 1
                
                status_box.success(f"✅ Sent {sent_count}/{len(all_db_tags)} tags at {t_now}")
                preview_box.text_area("Live Bulk Preview", value=all_tags_preview, height=300)
                
                # --- LOGGING TO SUPABASE ---
                try:
                    supabase.table("activity_logs").insert({
                        "user_id": 1, 
                        "vehicle_no": f"BATCH: {v_no} ({sent_count} Tags)"
                    }).execute()
                except: pass
                
                time.sleep(gap)
