import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from database import supabase, get_tags

def admin_panel():
    st.sidebar.markdown("<h2 style='color: #FF4B4B;'>👑 Admin Pro Max</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🔒 Logout Admin", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Injector", "🏷️ Tag Manager", "👤 User Control", "💳 Recharges"])
    
    # --- TAB 2: MASTER INJECTOR (FULL CONTROL + DB SAVE) ---
    with t2:
        st.subheader("🚀 Smart Packet Injector")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            
            # Tags from DB
            all_tags = get_tags()
            tag_sel = c1.selectbox("Select Tag", options=all_tags if all_tags else ["VLT"])
            v_no = c2.text_input("Vehicle No", value="BR01-1234").upper().strip()
            i_no = c3.text_input("IMEI No", value="864231000000001").strip()
            
            lat_in = c1.number_input("Latitude", value=25.5940, format="%.6f")
            lon_in = c2.number_input("Longitude", value=85.1370, format="%.6f")
            interval = c3.slider("Interval (Seconds)", 5, 60, 10)

        # Live String Preview Screen
        st.markdown("#### 📺 Live Packet Preview")
        timestamp = datetime.now().strftime("%d%m%Y,%H%M%S")
        packet_str = f"${tag_sel},GPS,2.1.1,NR,01,L,{i_no},{v_no},1,{timestamp},{lat_in},N,{lon_in},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
        
        st.code(packet_str, language="bash")

        # Control & Progress
        st.divider()
        col_btn, col_progress = st.columns([1, 3])
        
        if col_btn.button("🔥 Start Injection", use_container_width=True):
            if v_no and i_no:
                # 1. Database mein vehicle update/check karna
                try:
                    supabase.table("vehicle_master").upsert({
                        "vehicle_no": v_no, 
                        "imei_no": i_no,
                        "updated_at": datetime.now().isoformat()
                    }).execute()
                    
                    # 2. Activity Log mein entry save karna
                    supabase.table("activity_logs").insert({
                        "user_id": "ADMIN_MASTER",
                        "vehicle_no": f"{v_no} (Injected)"
                    }).execute()
                    
                    st.toast(f"Vehicle {v_no} synced with DB!")
                except:
                    st.error("Database saving error!")

                # 3. Progress Bar Logic
                p_bar = col_progress.progress(0, text="Injecting Packets...")
                for p in range(100):
                    time.sleep(interval/100)
                    p_bar.progress(p + 1, text=f"Next packet in {interval}s...")
                
                st.success(f"Packet Sent & Saved: {v_no}")
            else:
                st.error("Vehicle aur IMEI bhariye!")

    # --- TAB 3: TAG MANAGER ---
    with t3:
        st.subheader("🏷️ Tag Control")
        c_in, c_save = st.columns([3, 1])
        nt = c_in.text_input("New Tag Name").upper().strip()
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
        data = supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(20).execute()
        if data.data:
            st.dataframe(pd.DataFrame(data.data), use_container_width=True)

    # --- TAB 4: USER CONTROL ---
    with t4:
        st.subheader("👤 User Editor")
        st.info("User details can be edited here.")

    # --- TAB 5: RECHARGES ---
    with t5:
        st.subheader("💳 Recharges")
        st.info("Pending recharge requests.")
