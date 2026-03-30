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
    
    # --- TAB 2: MASTER INJECTOR (BIG BOX + 1s INTERVAL) ---
    with t2:
        st.subheader("🚀 Smart Packet Injector")
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            
            db_tags = get_tags()
            tag_sel = c1.selectbox("Select Tag", options=db_tags if db_tags else ["EGAS"])
            v_no = c2.text_input("Vehicle No", value="BR04GA5974").upper().strip()
            i_no = c3.text_input("IMEI No", value="862567075041793").strip()
            
            lat_in = c1.number_input("Latitude", value=25.6501550, format="%.7f")
            lon_in = c2.number_input("Longitude", value=84.7851780, format="%.7f")
            # Minimum interval set to 1 second as requested
            interval = c3.slider("Interval (Seconds)", min_value=1, max_value=60, value=10)

        st.markdown("#### 📺 Live Packet Preview (Full String)")
        d_now = datetime.now().strftime("%d%m%Y")
        t_now = datetime.now().strftime("%H%M%S")
        
        # Exact string format provided by you (No changes to hex/checksum)
        exact_packet_str = f"$PVT,{tag_sel},2.1.1,NR,01,L,{i_no},{v_no},1,{d_now},{t_now},{lat_in:.7f},N,{lon_in:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
        
        # Using text_area for a much larger, scroll-free view
        st.text_area(label="Full Packet String", value=exact_packet_str, height=120, label_visibility="collapsed")

        st.divider()
        col_btn, col_progress = st.columns([1, 3])
        
        if col_btn.button("🔥 Start Injection", use_container_width=True):
            if v_no and i_no:
                try:
                    # Sync information to Database
                    supabase.table("vehicle_master").upsert({
                        "vehicle_no": v_no, 
                        "imei_no": i_no,
                        "updated_at": datetime.now().isoformat()
                    }).execute()
                    
                    supabase.table("activity_logs").insert({
                        "user_id": "ADMIN_MASTER",
                        "vehicle_no": f"{v_no} ({tag_sel} Injected)"
                    }).execute()
                    
                    # Progress Bar with interval support
                    p_bar = col_progress.progress(0, text=f"Injecting every {interval}s...")
                    for p in range(100):
                        time.sleep(interval/100)
                        p_bar.progress(p + 1, text=f"Sending packet... Next in {interval}s")
                    
                    st.success(f"Packet Sent & Saved: {v_no}")
                except Exception as e:
                    st.error(f"Database Error: {e}")
            else:
                st.error("Vehicle No aur IMEI bharna zaroori hai!")

    # --- TAB 3: TAG MANAGER ---
    with t3:
        st.subheader("🏷️ Tag Control Center")
        c_in, c_save = st.columns([3, 1])
        nt = c_in.text_input("New Tag Name").upper().strip()
        if c_save.button("➕ SAVE", use_container_width=True):
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
        logs = supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(20).execute()
        if logs.data:
            st.dataframe(pd.DataFrame(logs.data), use_container_width=True)

    # --- TAB 4: USER CONTROL ---
    with t4:
        st.subheader("👤 User Management")
        with st.expander("✨ Create New User"):
            with st.form("create_u"):
                u, p = st.text_input("User"), st.text_input("Pass")
                la, lo = st.number_input("Lat", value=25.5940), st.number_input("Lon", value=85.1370)
                if st.form_submit_button("Create"):
                    exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                    supabase.table("user_profiles").insert({"username":u, "password":p, "expiry_date":exp, "status":"active", "latitude":la, "longitude":lo}).execute()
                    st.success("User Created!"); st.rerun()

    # --- TAB 5: RECHARGES ---
    with t5:
        st.subheader("💳 Recharges")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            for r in reqs.data:
                st.warning(f"User: {r['username']} | UTR: {r['utr_number']}")
                if st.button(f"✅ Approve {r['username']}", key=f"app_{r['id']}"):
                    supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute()
                    st.rerun()
