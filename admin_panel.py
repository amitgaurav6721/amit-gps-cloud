import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from database import supabase, get_tags

def admin_panel():
    st.sidebar.markdown("<h2 style='color: #FF4B4B;'>👑 Admin Pro Max</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🔒 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    # 5 Tabs Create ho rahe hain
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Injector", "🏷️ Tags", "👤 Users", "💳 Recharges"])
    
    # --- 1. REPORTS (Activity Logs) ---
    with t1:
        st.subheader("📅 Activity Logs")
        rep_date = st.date_input("Filter Date", datetime.now())
        log_res = supabase.table("activity_logs").select("*").gte("created_at", f"{rep_date}T00:00:00").lte("created_at", f"{rep_date}T23:59:59").execute()
        if log_res.data:
            st.dataframe(pd.DataFrame(log_res.data), use_container_width=True)
        else:
            st.info("No data for this date.")

    # --- 2. INJECTOR (Master Control) ---
    with t2:
        st.subheader("🚀 Master Injector")
        c1, c2 = st.columns(2)
        v_no = c1.text_input("Vehicle No", "BR01-ADMIN").upper()
        i_no = c2.text_input("IMEI", "864231000000001")
        st.code(f"$PVT,GPS,2.1.1,NR,01,L,{i_no},{v_no},...*")

    # --- 3. TAG MANAGER (Fixing Empty List) ---
    with t3:
        st.subheader("🏷️ Database Tag Manager")
        new_t = st.text_input("Add Tag").upper()
        if st.button("➕ Save"):
            if new_t:
                supabase.table("custom_tags").upsert({"tag_name": new_t}).execute()
                st.success("Saved!"); time.sleep(0.5); st.rerun()
        
        st.divider()
        db_tags = get_tags() # database.py se tags fetch kar raha hai
        if db_tags:
            cols = st.columns(4)
            for i, tag in enumerate(db_tags):
                with cols[i % 4]:
                    st.info(f"**{tag}**")
                    if st.button("🗑️", key=f"d_{tag}"):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.rerun()
        else:
            st.error("Tags not found in Supabase!")

    # --- 4. USER CONTROL (Location Fix & Editor) ---
    with t4:
        st.subheader("👤 User Management")
        with st.expander("✨ Create New User"):
            with st.form("nu"):
                un, up = st.text_input("Username"), st.text_input("Password")
                la, lo = st.number_input("Lat", 25.5940), st.number_input("Lon", 85.1370)
                if st.form_submit_button("Create"):
                    exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                    supabase.table("user_profiles").insert({"username":un, "password":up, "expiry_date":exp, "status":"active", "latitude":la, "longitude":lo}).execute()
                    st.success("User Created!"); st.rerun()

    # --- 5. RECHARGES ---
    with t5:
        st.subheader("💳 Pending Requests")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            for r in reqs.data:
                st.warning(f"User: {r['username']} | UTR: {r['utr_number']}")
        else:
            st.info("No pending requests.")
