import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import supabase, get_tags

def admin_panel():
    st.sidebar.title("🛠️ System Admin")
    if st.sidebar.button("Logout Admin", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    # --- 5 TABS AS DISCUSSED ---
    t1, t2, t3, t4, t5 = st.tabs([
        "📊 Activity Reports", 
        "🚀 Master Injector", 
        "🏷️ Tag Control", 
        "👤 User Management", 
        "💳 Recharge Desk"
    ])
    
    # 1. ACTIVITY REPORTS (DIRECT DB SYNC)
    with t1:
        st.subheader("📅 Live Activity Logs")
        report_date = st.date_input("Select Date", datetime.now())
        # Fetching based on your 'activity_logs' table columns: user_id, vehicle_no, created_at
        log_res = supabase.table("activity_logs").select("*").gte("created_at", f"{report_date}T00:00:00").lte("created_at", f"{report_date}T23:59:59").execute()
        
        if log_res.data:
            log_df = pd.DataFrame(log_res.data)
            # Displaying columns as per your Supabase Screenshot
            st.dataframe(log_df[['created_at', 'user_id', 'vehicle_no']], use_container_width=True)
            
            # Export to CSV (Simple & Safe)
            csv_data = log_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Report (CSV)", csv_data, f"Bihar_VLTS_{report_date}.csv", "text/csv")
        else:
            st.info("Is tareekh ka koi log nahi mila.")

    # 2. MASTER INJECTOR (GLOBAL CONTROL)
    with t2:
        st.subheader("🚀 Global Master Injector")
        st.write("Admin yahan se poore system ke liye data sync test kar sakta hai.")
        m_v_no = st.text_input("Master Vehicle No").upper()
        m_imei = st.text_input("Master IMEI No")
        
        if not st.session_state.get('admin_running', False):
            if st.button("🔥 START MASTER SYNC", type="primary"):
                st.session_state.admin_running = True
                st.rerun()
        else:
            st.error("Master Sync is currently RUNNING...")
            if st.button("🛑 STOP MASTER SYNC"):
                st.session_state.admin_running = False
                st.rerun()

    # 3. TAG CONTROL (CUSTOMIZABLE)
    with t3:
        st.subheader("🏷️ Manage Operational Tags")
        new_t = st.text_input("Enter New Tag (Ex: BBOX77)").upper()
        if st.button("Add New Tag"):
            if new_t:
                supabase.table("custom_tags").upsert({"tag_name": new_t}).execute()
                st.success(f"Tag {new_t} added!")
                st.rerun()
        
        st.divider()
        st.write("Current System Tags:")
        all_tags = get_tags()
        for t in all_tags:
            c1, c2 = st.columns([4,1])
            c1.code(t)
            if c2.button("❌", key=f"del_{t}"):
                supabase.table("custom_tags").delete().eq("tag_name", t).execute()
                st.rerun()

    # 4. USER MANAGEMENT (CREATE & SEARCH)
    with t4:
        st.subheader("👤 User Account Control")
        
        # Section A: Create User
        with st.expander("➕ Create New User Account", expanded=False):
            with st.form("new_user_form"):
                u_name = st.text_input("Username")
                u_pass = st.text_input("Password")
                lat = st.number_input("Default Latitude", value=25.594, format="%.4f")
                lon = st.number_input("Default Longitude", value=85.137, format="%.4f")
                if st.form_submit_button("Create Account"):
                    if u_name and u_pass:
                        try:
                            # 28 Days Expiry automatically
                            exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                            supabase.table("user_profiles").insert({
                                "username": u_name, 
                                "password": u_pass, 
                                "expiry_date": exp,
                                "status": "active",
                                "latitude": lat,
                                "longitude": lon
                            }).execute()
                            st.success(f"User {u_name} created with 28 days validity!")
                        except:
                            st.error("Error: Username pehle se maujood hai.")
        
        st.divider()
        
        # Section B: Search & Extend
        search_q = st.text_input("🔍 Search User (Username)")
        if search_q:
            u_data = supabase.table("user_profiles").select("*").ilike("username", f"%{search_q}%").execute()
            if u_data.data:
                for user in u_data.data:
                    with st.container():
                        st.write(f"**ID:** CID-{1000 + user['cid_id']} | **User:** {user['username']}")
                        st.write(f"**Expiry:** {user['expiry_date']} | **Status:** {user['status']}")
                        
                        col1, col2 = st.columns(2)
                        if col1.button(f"➕ Extend 28 Days", key=f"ext_{user['username']}"):
                            curr_exp = datetime.strptime(user['expiry_date'], '%Y-%m-%d')
                            new_exp = (max(curr_exp, datetime.now()) + timedelta(days=28)).strftime('%Y-%m-%d')
                            supabase.table("user_profiles").update({"expiry_date": new_exp}).eq("username", user['username']).execute()
                            st.success(f"Extended to {new_exp}")
                            st.rerun()
                        
                        if col2.button(f"🚫 Block/Unblock", key=f"stat_{user['username']}"):
                            new_stat = "inactive" if user['status'] == "active" else "active"
                            supabase.table("user_profiles").update({"status": new_stat}).eq("username", user['username']).execute()
                            st.rerun()
            else:
                st.warning("User nahi mila.")

    # 5. RECHARGE DESK (PENDING APPROVALS)
    with t5:
        st.subheader("💳 Pending Recharge Requests")
        pending = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        
        if pending.data:
            for r in pending.data:
                with st.chat_message("user"):
                    st.write(f"**Username:** {r['username']} | **Mobile:** {r['mobile_no']}")
                    st.write(f"**UTR No:** {r['utr_number']} | **Date:** {r['created_at'][:10]}")
                    
                    if st.button(f"✅ Approve Recharge for {r['username']}", key=f"rch_{r['id']}"):
                        # 1. Update request status
                        supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute()
                        # 2. Extend User Expiry automatically on approval
                        u_res = supabase.table("user_profiles").select("expiry_date").eq("username", r['username']).execute()
                        if u_res.data:
                            c_exp = datetime.strptime(u_res.data[0]['expiry_date'], '%Y-%m-%d')
                            n_exp = (max(c_exp, datetime.now()) + timedelta(days=28)).strftime('%Y-%m-%d')
                            supabase.table("user_profiles").update({"expiry_date": n_exp, "status": "active"}).eq("username", r['username']).execute()
                        st.success(f"Recharge approved for {r['username']}!")
                        st.rerun()
        else:
            st.info("Koi bhi pending recharge request nahi hai.")
