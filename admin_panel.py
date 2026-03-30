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
    
    # Sabhi 5 Tabs ko wapas activate kar raha hoon
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Injector", "🏷️ Tag Manager", "👤 User Control", "💳 Recharges"])
    
    # --- 1. REPORTS TAB (Live from activity_logs) ---
    with t1:
        st.subheader("📅 Live Activity Reports")
        rep_date = st.date_input("Select Date", datetime.now())
        log_res = supabase.table("activity_logs").select("*").gte("created_at", f"{rep_date}T00:00:00").lte("created_at", f"{rep_date}T23:59:59").execute()
        
        if log_res.data:
            df_log = pd.DataFrame(log_res.data)
            st.dataframe(df_log[['created_at', 'user_id', 'vehicle_no']], use_container_width=True)
            csv = df_log.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, f"Logs_{rep_date}.csv", "text/csv")
        else:
            st.info("Is date ka koi data nahi mila.")

    # --- 2. INJECTOR TAB (Full Control) ---
    with t2:
        st.subheader("🚀 Master Injector Overrides")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            v_no = c1.text_input("Vehicle No", value="BR01-ADMIN").upper()
            i_no = c2.text_input("IMEI No", value="864231000000001")
            lat_fix = c1.number_input("Fixed Lat", value=25.5940, format="%.6f")
            lon_fix = c2.number_input("Fixed Lon", value=85.1370, format="%.6f")
        
        dt_now = datetime.now().strftime("%d%m%Y,%H%M%S")
        st.markdown("#### Live String Preview")
        st.code(f"$PVT,GPS,2.1.1,NR,01,L,{i_no},{v_no},1,{dt_now},{lat_fix},N,{lon_fix},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*")

    # --- 3. TAG MANAGER (Database Sync) ---
    with t3:
        st.subheader("🏷️ Tag Control Center")
        new_tag = st.text_input("Add New Tag").upper()
        if st.button("➕ Save Tag"):
            if new_tag:
                supabase.table("custom_tags").upsert({"tag_name": new_tag}).execute()
                st.success("Tag Saved!"); time.sleep(0.5); st.rerun()
        
        st.divider()
        st.markdown("#### 📋 Database Tag Inventory")
        all_db_tags = get_tags()
        if all_db_tags:
            cols = st.columns(4)
            for i, tag in enumerate(all_db_tags):
                with cols[i % 4]:
                    st.info(f"**{tag}**")
                    if st.button("🗑️", key=f"del_{tag}"):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.rerun()
        else:
            st.warning("No tags found in DB.")

    # --- 4. USER CONTROL (Creation + Master Editor) ---
    with t4:
        st.subheader("👤 User Management")
        with st.expander("✨ Create New User (With Location)"):
            with st.form("new_user"):
                cx, cy = st.columns(2)
                u_n, u_p = cx.text_input("Username"), cy.text_input("Password")
                la, lo = cx.number_input("Lat", value=25.5941), cy.number_input("Lon", value=85.1371)
                if st.form_submit_button("🚀 Create Account"):
                    exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                    supabase.table("user_profiles").insert({"username": u_n, "password": u_p, "expiry_date": exp, "status": "active", "latitude": la, "longitude": lo}).execute()
                    st.success("User Created!"); st.rerun()

        st.divider()
        st.markdown("### 🔍 Master Data Editor")
        search_u = st.text_input("Search Username to Edit")
        if search_u:
            res_u = supabase.table("user_profiles").select("*").ilike("username", f"%{search_u}%").execute()
            for row in res_u.data:
                with st.container(border=True):
                    st.write(f"**Editing: {row['username']}**")
                    new_pass = st.text_input("Password", value=row['password'], key=f"p_{row['id']}")
                    new_lat = st.number_input("Lat", value=float(row['latitude']), key=f"la_{row['id']}")
                    new_lon = st.number_input("Lon", value=float(row['longitude']), key=f"lo_{row['id']}")
                    if st.button("💾 Save Changes", key=f"s_{row['id']}"):
                        supabase.table("user_profiles").update({"password": new_pass, "latitude": new_lat, "longitude": new_lon}).eq("id", row['id']).execute()
                        st.success("Updated!"); st.rerun()

    # --- 5. RECHARGE TAB ---
    with t5:
        st.subheader("💳 Pending Recharges")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            for r in reqs.data:
                st.warning(f"User: {r['username']} | UTR: {r['utr_number']}")
                if st.button(f"✅ Approve {r['username']}", key=f"ok_{r['id']}"):
                    supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute()
                    st.rerun()
        else:
            st.info("No pending requests.")
