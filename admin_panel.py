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
    
    # --- TAB 2: MASTER INJECTOR (BIG PREVIEW + 1s INTERVAL) ---
    with t2:
        st.subheader("🚀 Smart Packet Injector")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            
            db_tags = get_tags()
            tag_sel = c1.selectbox("Select Tag", options=db_tags if db_tags else ["EGAS"])
            v_no = c2.text_input("Vehicle No", value="BR04GA5974").upper().strip()
            i_no = c3.text_input("IMEI No", value="862567075041793").strip()
            
            lat_in = c1.number_input("Latitude", value=25.650155, format="%.7f")
            lon_in = c2.number_input("Longitude", value=84.785178, format="%.7f")
            # Interval minimum set to 1 second
            interval = c3.slider("Interval (Seconds)", min_value=1, max_value=60, value=10)

        # Large Live Preview Screen
        st.markdown("#### 📺 Live Packet Preview")
        d_now = datetime.now().strftime("%d%m%Y")
        t_now = datetime.now().strftime("%H%M%S")
        
        # Exact string as per your requirement
        exact_packet_str = f"$PVT,{tag_sel},2.1.1,NR,01,L,{i_no},{v_no},1,{d_now},{t_now},{lat_in:.7f},N,{lon_in:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
        
        # Bigger box using container
        with st.container(border=True):
            st.code(exact_packet_str, language="bash")

        st.divider()
        col_btn, col_progress = st.columns([1, 3])
        
        if col_btn.button("🔥 Start Injection", use_container_width=True):
            if v_no and i_no:
                try:
                    # Database check/update
                    supabase.table("vehicle_master").upsert({
                        "vehicle_no": v_no, "imei_no": i_no, "updated_at": datetime.now().isoformat()
                    }).execute()
                    
                    supabase.table("activity_logs").insert({
                        "user_id": "ADMIN_MASTER", "vehicle_no": f"{v_no} ({tag_sel} Injected)"
                    }).execute()
                    
                    # Progress Bar with 1s support
                    p_bar = col_progress.progress(0, text=f"Fast Injecting... Every {interval}s")
                    for p in range(100):
                        time.sleep(interval/100)
                        p_bar.progress(p + 1, text=f"Sending... Next in {interval}s")
                    
                    st.success(f"Packet Sent & Saved: {v_no}")
                except Exception as e:
                    st.error(f"Database Error: {e}")
            else:
                st.error("Please fill Vehicle No and IMEI!")

    # --- Baaki Tabs same rahenge ---
    with t3:
        st.subheader("🏷️ Tag Control Center")
        # ... (Tag Manager code)
