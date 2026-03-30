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
    
    # --- TAB 3: TAG MANAGER (ALREADY WORKING) ---
    with t3:
        st.subheader("🏷️ Tag Control Center")
        c_in, c_btn = st.columns([3, 1])
        new_t = c_in.text_input("Add New Tag Name").upper().strip()
        if c_btn.button("➕ SAVE", use_container_width=True):
            if new_t:
                supabase.table("custom_tags").insert({"tag_name": new_t}).execute()
                st.success(f"{new_t} Saved!"); time.sleep(0.5); st.rerun()
        
        st.divider()
        res_tags = supabase.table("custom_tags").select("tag_name").execute()
        db_tags = [t['tag_name'] for t in res_tags.data] if res_tags.data else []
        if db_tags:
            grid = st.columns(4)
            for i, tag in enumerate(db_tags):
                with grid[i % 4]:
                    st.markdown(f"<div style='background-color:#262730; border:1px solid #FF4B4B; padding:10px; border-radius:5px; text-align:center; margin-bottom:5px;'><b>{tag}</b></div>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_{tag}_{i}"):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.rerun()

    # --- TAB 4: USER CONTROL (LOCATION FIX & MASTER EDITOR) ---
    with t4:
        st.subheader("👤 User Management")
        
        # Part 1: Create New User with Lat/Lon
        with st.expander("✨ Create New Account (Set Location)"):
            with st.form("create_u"):
                f1, f2 = st.columns(2)
                nu = f1.text_input("New Username")
                np = f2.text_input("New Password")
                nla = f1.number_input("Set Latitude", value=25.5940, format="%.6f")
                nlo = f2.number_input("Set Longitude", value=85.1370, format="%.6f")
                if st.form_submit_button("🔥 Create User"):
                    if nu and np:
                        exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                        supabase.table("user_profiles").insert({
                            "username": nu, "password": np, "expiry_date": exp,
                            "status": "active", "latitude": nla, "longitude": nlo
                        }).execute()
                        st.success(f"User {nu} created!"); st.rerun()

        st.divider()
        
        # Part 2: Edit/Search Full User Data
        search_q = st.text_input("🔍 Search User to Edit Full Data")
        if search_q:
            u_res = supabase.table("user_profiles").select("*").ilike("username", f"%{search_q}%").execute()
            for u in u_res.data:
                with st.container(border=True):
                    st.write(f"**Editing:** {u['username']}")
                    e1, e2 = st.columns(2)
                    ep = e1.text_input("Change Password", u['password'], key=f"p_{u['id']}")
                    ee = e2.text_input("Change Expiry (YYYY-MM-DD)", u['expiry_date'], key=f"ex_{u['id']}")
                    elat = e1.number_input("Edit Lat", value=float(u['latitude']), format="%.6f", key=f"la_{u['id']}")
                    elon = e2.number_input("Edit Lon", value=float(u['longitude']), format="%.6f", key=f"lo_{u['id']}")
                    
                    if st.button("💾 Save Changes", key=f"sv_{u['id']}", use_container_width=True):
                        supabase.table("user_profiles").update({
                            "password": ep, "expiry_date": ee, "latitude": elat, "longitude": elon
                        }).eq("id", u['id']).execute()
                        st.success("Data Updated!"); time.sleep(0.5); st.rerun()

    # --- TAB 1: REPORTS ---
    with t1:
        st.subheader("📊 Activity Reports")
        logs = supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(50).execute()
        if logs.data:
            st.table(pd.DataFrame(logs.data)[['created_at', 'user_id', 'vehicle_no']])
