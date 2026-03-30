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
    
    # --- TAB 1: REPORTS (Direct Sync with activity_logs) ---
    with t1:
        st.subheader("📅 Live Activity Reports")
        rep_date = st.date_input("Filter Date", datetime.now())
        try:
            log_res = supabase.table("activity_logs").select("*").gte("created_at", f"{rep_date}T00:00:00").lte("created_at", f"{rep_date}T23:59:59").execute()
            if log_res.data:
                df_log = pd.DataFrame(log_res.data)
                st.dataframe(df_log[['created_at', 'user_id', 'vehicle_no']], use_container_width=True)
                csv = df_log.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, f"Logs_{rep_date}.csv", "text/csv")
            else:
                st.info("Is date ka koi data nahi mila.")
        except:
            st.error("Activity Logs load karne mein dikkat aa rahi hai.")

    # --- TAB 2: MASTER INJECTOR (Full Control) ---
    with t2:
        st.subheader("🚀 Global Master Overrides")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            m_v = c1.text_input("Vehicle No", value="BR01-ADMIN").upper()
            m_i = c2.text_input("IMEI No", value="864231000000001")
            m_lat = c1.number_input("Fixed Lat", value=25.5940, format="%.6f")
            m_lon = c2.number_input("Fixed Lon", value=85.1370, format="%.6f")
        
        dt_p = datetime.now().strftime("%d%m%Y,%H%M%S")
        st.markdown("#### 🛰️ Live Packet Preview")
        st.code(f"$PVT,GPS,2.1.1,NR,01,L,{m_i},{m_v},1,{dt_p},{m_lat},N,{m_lon},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*", language="bash")

    # --- TAB 3: TAG MANAGER (Direct Database Sync) ---
    with t3:
        st.subheader("🏷️ Tag Control Center")
        
        # New Tag Input
        c_in, c_btn = st.columns([3, 1])
        new_t = c_in.text_input("Add New Tag Name").upper().strip()
        if c_btn.button("➕ SAVE", use_container_width=True):
            if new_t:
                supabase.table("custom_tags").upsert({"tag_name": new_t}).execute()
                st.success(f"{new_t} Saved!"); time.sleep(0.5); st.rerun()

        st.divider()
        st.markdown("#### 📋 Current Database Tags")
        
        # Direct fetch to bypass any function delay
        try:
            res_tags = supabase.table("custom_tags").select("tag_name").execute()
            db_tags = [t['tag_name'] for t in res_tags.data] if res_tags.data else []
        except:
            db_tags = []
            
        if db_tags:
            grid = st.columns(4)
            for i, tag in enumerate(db_tags):
                with grid[i % 4]:
                    st.markdown(f"<div style='background-color:#262730; border:1px solid #FF4B4B; padding:10px; border-radius:5px; text-align:center; margin-bottom:5px;'><b>{tag}</b></div>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_{tag}_{i}"):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.rerun()
        else:
            st.warning("⚠️ Database mein koi tag nahi mila. Ek naya tag '➕ SAVE' karke dekhein.")

    # --- TAB 4: USER CONTROL (Full Editor & Location Fix) ---
    with t4:
        st.subheader("👤 User Master Management")
        with st.expander("✨ Create New Account (Set Location)"):
            with st.form("create_u"):
                f1, f2 = st.columns(2)
                nu = f1.text_input("New Username")
                np = f2.text_input("New Password")
                nla = f1.number_input("Set Lat", value=25.5940, format="%.6f")
                nlo = f2.number_input("Set Lon", value=85.1370, format="%.6f")
                if st.form_submit_button("🔥 Finalize"):
                    if nu and np:
                        exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                        supabase.table("user_profiles").insert({
                            "username": nu, "password": np, "expiry_date": exp,
                            "status": "active", "latitude": nla, "longitude": nlo
                        }).execute()
                        st.success(f"User {nu} Created!"); st.rerun()

        st.divider()
        search_q = st.text_input("🔍 Search User to Edit Full Data")
        if search_q:
            u_res = supabase.table("user_profiles").select("*").ilike("username", f"%{search_q}%").execute()
            for u in u_res.data:
                with st.container(border=True):
                    st.write(f"**ID:** CID-{1000 + u['cid_id']} | **User:** {u['username']}")
                    e1, e2 = st.columns(2)
                    ep = e1.text_input("Edit Password", u['password'], key=f"p_{u['id']}")
                    ee = e2.text_input("Edit Expiry", u['expiry_date'], key=f"ex_{u['id']}")
                    if st.button("💾 Save Changes", key=f"sv_{u['id']}", use_container_width=True):
                        supabase.table("user_profiles").update({"password": ep, "expiry_date": ee}).eq("id", u['id']).execute()
                        st.success("Updated!"); st.rerun()

    # --- TAB 5: RECHARGES ---
    with t5:
        st.subheader("💳 Pending Recharge Desk")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            for r in reqs.data:
                st.warning(f"**User:** {r['username']} | **UTR:** {r['utr_number']}")
                if st.button(f"✅ Approve {r['username']}", key=f"app_{r['id']}"):
                    supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute()
                    st.rerun()
        else:
            st.info("No pending requests found.")
