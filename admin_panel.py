import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from database import supabase, get_tags

def admin_panel():
    # --- Sidebar Styling ---
    st.sidebar.markdown("## 👑 Admin Control Center")
    st.sidebar.divider()
    if st.sidebar.button("🔒 Secure Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    # --- Main Tabs Layout ---
    t1, t2, t3, t4, t5 = st.tabs([
        "📊 Activity Reports", 
        "🚀 Master Injector", 
        "🏷️ Tag Management", 
        "👤 User Management", 
        "💳 Recharge Desk"
    ])
    
    # --- 1. ACTIVITY REPORTS ---
    with t1:
        st.markdown("### 📅 Live Activity Reports")
        rep_date = st.date_input("Filter by Date", datetime.now())
        log_res = supabase.table("activity_logs").select("*").gte("created_at", f"{rep_date}T00:00:00").lte("created_at", f"{rep_date}T23:59:59").execute()
        
        if log_res.data:
            df_log = pd.DataFrame(log_res.data)
            st.dataframe(df_log[['created_at', 'user_id', 'vehicle_no']], use_container_width=True)
            csv = df_log.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Excel/CSV", csv, f"Bihar_Logs_{rep_date}.csv", "text/csv")
        else:
            st.info("No logs found for this date.")

    # --- 2. MASTER INJECTOR (FULL CONTROL) ---
    with t2:
        st.markdown("### 🚀 Global Injector Overrides")
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                m_v = st.text_input("Vehicle No", value="BR01-8888").upper()
                m_i = st.text_input("IMEI No", value="864231000000001")
            with c2:
                m_lat = st.number_input("Fixed Lat", value=25.5940, format="%.6f")
                m_lon = st.number_input("Fixed Lon", value=85.1370, format="%.6f")
            with c3:
                m_int = st.select_slider("Interval (Sec)", options=[1, 2, 5, 10], value=1)
                m_tag_over = st.text_input("Force Tag (Optional)").upper()

        st.markdown("#### 🛰️ Outgoing Server Packet")
        dt_p = datetime.now().strftime("%d%m%Y,%H%M%S")
        final_tag = m_tag_over if m_tag_over else "GPS"
        packet_str = f"$PVT,{final_tag},2.1.1,NR,01,L,{m_i},{m_v},1,{dt_p},{m_lat},N,{m_lon},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
        st.code(packet_str, language="bash")

        if not st.session_state.get('admin_running', False):
            if st.button("🔥 START INJECTION", type="primary", use_container_width=True):
                st.session_state.admin_running = True
                st.rerun()
        else:
            st.error("⚠️ MASTER SYNC ACTIVE")
            if st.button("🛑 EMERGENCY STOP", use_container_width=True):
                st.session_state.admin_running = False
                st.rerun()

    # --- 3. TAG CONTROL (FULL LIST FIX) ---
    with t3:
        st.markdown("### 🏷️ System Tag Manager")
        new_tag_raw = st.text_input("Add New Tag (Auto-Capitalize)")
        if st.button("➕ Save Tag to Database"):
            if new_tag_raw:
                supabase.table("custom_tags").upsert({"tag_name": new_tag_raw.upper()}).execute()
                st.success("Tag Saved Successfully!"); time.sleep(0.5); st.rerun()
        
        st.divider()
        st.markdown("#### 📋 Full Tag Inventory (All Entry)")
        # Fetching ALL tags without any limit
        db_tags = supabase.table("custom_tags").select("tag_name").execute()
        if db_tags.data:
            tag_list = [t['tag_name'] for t in db_tags.data]
            grid = st.columns(4)
            for idx, tag in enumerate(tag_list):
                with grid[idx % 4]:
                    st.info(f"**{tag}**")
                    if st.button("🗑️", key=f"rm_{tag}"):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.rerun()
        else:
            st.warning("No tags found in database.")

    # --- 4. USER MANAGEMENT (ADVANCED EDITOR) ---
    with t4:
        st.markdown("### 👤 User Master Control")
        
        # A. Create User with Location Fix
        with st.expander("✨ Create New User with Fixed Location"):
            with st.form("create_form"):
                ca, cb = st.columns(2)
                u_n = ca.text_input("Username")
                u_p = cb.text_input("Password")
                la = ca.number_input("Fix Latitude", value=25.5941, format="%.6f")
                lo = cb.number_input("Fix Longitude", value=85.1371, format="%.6f")
                val_days = st.number_input("Validity Days", value=28)
                
                if st.form_submit_button("🚀 Finalize & Create"):
                    if u_n and u_p:
                        # Real-time Duplicate Check
                        dup = supabase.table("user_profiles").select("username").eq("username", u_n).execute()
                        if dup.data:
                            st.error("❌ Username already exists!")
                        else:
                            exp = (datetime.now() + timedelta(days=val_days)).strftime('%Y-%m-%d')
                            supabase.table("user_profiles").insert({
                                "username": u_n, "password": u_p, "expiry_date": exp,
                                "status": "active", "latitude": la, "longitude": lo
                            }).execute()
                            st.success(f"User {u_n} created successfully!"); time.sleep(1); st.rerun()

        st.divider()
        
        # B. Full Data Editor & Search
        all_u = supabase.table("user_profiles").select("*").execute()
        if all_u.data:
            df_u = pd.DataFrame(all_u.data)
            st.metric("Total Registered Users", len(df_u))
            
            search_key = st.text_input("🔍 Search User Database (Username/CID)")
            f_u = df_u[df_u['username'].str.contains(search_key, case=False)] if search_key else df_u

            for _, row in f_u.iterrows():
                with st.container(border=True):
                    c_head, c_body, c_act = st.columns([1, 2, 2])
                    with c_head:
                        st.markdown(f"**ID:** CID-{1000 + row['cid_id']}")
                        st.markdown(f"### {row['username']}")
                    with c_body:
                        st.write(f"🔑 Password: `{row['password']}`")
                        st.write(f"📍 Location: `{row['latitude']}, {row['longitude']}`")
                        st.write(f"📅 Expiry: **{row['expiry_date']}**")
                    with c_act:
                        st.write("**--- Actions ---**")
                        ca1, ca2, ca3 = st.columns(3)
                        # Toggle Status
                        if ca1.button("🟢" if row['status']=='active' else "🔴", key=f"t_{row['username']}"):
                            n_s = "inactive" if row['status'] == "active" else "active"
                            supabase.table("user_profiles").update({"status": n_s}).eq("username", row['username']).execute()
                            st.rerun()
                        # Validity Control
                        if ca2.button("➕ 7D", key=f"p_{row['username']}"):
                            n_e = (datetime.strptime(row['expiry_date'], '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
                            supabase.table("user_profiles").update({"expiry_date": n_e}).eq("username", row['username']).execute()
                            st.rerun()
                        if ca3.button("➖ 7D", key=f"m_{row['username']}"):
                            n_e = (datetime.strptime(row['expiry_date'], '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
                            supabase.table("user_profiles").update({"expiry_date": n_e}).eq("username", row['username']).execute()
                            st.rerun()

    # --- 5. RECHARGE APPROVALS ---
    with t5:
        st.markdown("### 💳 Pending Payments")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            for r in reqs.data:
                st.warning(f"**User:** {r['username']} | **UTR:** {r['utr_number']} | **Mob:** {r['mobile_no']}")
                if st.button(f"✅ Approve {r['username']}", key=f"ok_{r['id']}"):
                    supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute()
                    st.rerun()
        else:
            st.info("No pending requests found.")
