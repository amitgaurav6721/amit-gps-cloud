import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import supabase, get_tags

def admin_panel():
    st.sidebar.title("🛠️ System Admin")
    if st.sidebar.button("Logout Admin", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    t1, t2, t3, t4, t5 = st.tabs([
        "📊 Reports", 
        "🚀 Master Injector", 
        "🏷️ Tag Control", 
        "👤 User Management", 
        "💳 Recharges"
    ])
    
    # --- POINT 1: MASTER INJECTOR (FULL CONTROL) ---
    with t2:
        st.subheader("🚀 Global Master Control")
        col1, col2 = st.columns(2)
        with col1:
            m_v = st.text_input("Vehicle No", value="BR01AB1234").upper()
            m_i = st.text_input("IMEI No", value="123456789012345")
        with col2:
            m_lat = st.number_input("Lat", value=25.5940, format="%.4f")
            m_lon = st.number_input("Lon", value=85.1370, format="%.4f")
        
        m_interval = st.slider("Time Interval (Seconds)", 1, 10, 1)
        m_tag = st.text_input("Test Specific Tag (Optional)").upper()

        st.markdown("### 📋 Live Data String")
        dt = datetime.now().strftime("%d%m%Y,%H%M%S")
        curr_tag = m_tag if m_tag else "VLT"
        test_packet = f"$PVT,{curr_tag},2.1.1,NR,01,L,{m_i},{m_v},1,{dt},{m_lat},N,{m_lon},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
        st.code(test_packet, language="text")

        if not st.session_state.get('admin_running', False):
            if st.button("🔥 START MASTER SYNC", type="primary"):
                st.session_state.admin_running = True
                st.rerun()
        else:
            st.error("SYNC RUNNING...")
            if st.button("🛑 STOP"):
                st.session_state.admin_running = False
                st.rerun()

    # --- POINT 2: TAG CONTROL (CAPITAL AUTO-SYNC) ---
    with t3:
        st.subheader("🏷️ Database Tags")
        raw_t = st.text_input("Add Tag (Auto-Capital)")
        if st.button("Save Tag"):
            if raw_t:
                supabase.table("custom_tags").upsert({"tag_name": raw_t.upper()}).execute()
                st.rerun()
        st.divider()
        all_tags = get_tags()
        st.write(f"Total Tags in DB: {len(all_tags)}")
        for t in all_tags:
            c1, c2 = st.columns([4,1])
            c1.code(t)
            if c2.button("❌", key=f"del_{t}"):
                supabase.table("custom_tags").delete().eq("tag_name", t).execute()
                st.rerun()

    # --- POINT 3 & NEW: USER MANAGEMENT (ADVANCED LIST) ---
    with t4:
        st.subheader("👤 Master User Control")
        
        # Section A: Create User with Real-time Check
        with st.expander("➕ Create New Account"):
            new_u = st.text_input("Enter Username")
            if new_u:
                check = supabase.table("user_profiles").select("username").eq("username", new_u).execute()
                if check.data: st.error("❌ Username Already Taken!")
                else: st.success("✅ Username Available")
            
            new_p = st.text_input("Password")
            v_days = st.number_input("Validity (Days)", value=28)
            if st.button("🔥 Create User"):
                exp = (datetime.now() + timedelta(days=v_days)).strftime('%Y-%m-%d')
                supabase.table("user_profiles").insert({"username": new_u, "password": new_p, "expiry_date": exp, "status": "active"}).execute()
                st.rerun()

        st.divider()

        # Section B: Dedicated User List & Search
        users_res = supabase.table("user_profiles").select("*").execute()
        if users_res.data:
            df_users = pd.DataFrame(users_res.data)
            st.metric("Total Users", len(df_users))
            
            search_name = st.text_input("🔍 Search User by Name")
            filtered_users = df_users[df_users['username'].str.contains(search_name, case=False)] if search_name else df_users

            for index, row in filtered_users.iterrows():
                with st.container():
                    col_u, col_v, col_a = st.columns([2, 2, 3])
                    with col_u:
                        st.write(f"**{row['username']}**")
                        status_color = "🟢" if row['status'] == "active" else "🔴"
                        st.write(f"{status_color} {row['status'].upper()}")
                    with col_v:
                        st.write(f"📅 {row['expiry_date']}")
                    with col_a:
                        c1, c2, c3 = st.columns(3)
                        # Active/Inactive Toggle
                        if c1.button("🔄", key=f"tg_{row['username']}", help="Toggle Status"):
                            new_s = "inactive" if row['status'] == "active" else "active"
                            supabase.table("user_profiles").update({"status": new_s}).eq("username", row['username']).execute()
                            st.rerun()
                        # Validity Increase (+7 Days)
                        if c2.button("➕", key=f"up_{row['username']}", help="Add 7 Days"):
                            new_ex = (datetime.strptime(row['expiry_date'], '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
                            supabase.table("user_profiles").update({"expiry_date": new_ex}).eq("username", row['username']).execute()
                            st.rerun()
                        # Validity Decrease (-7 Days)
                        if c3.button("➖", key=f"dn_{row['username']}", help="Remove 7 Days"):
                            new_ex = (datetime.strptime(row['expiry_date'], '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
                            supabase.table("user_profiles").update({"expiry_date": new_ex}).eq("username", row['username']).execute()
                            st.rerun()
                st.divider()

    # Reports & Recharges (Keeping them as they were)
    with t1:
        st.info("Activity Reports Section")
    with t5:
        st.info("Recharge Requests Section")
