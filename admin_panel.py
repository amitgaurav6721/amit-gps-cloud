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
    
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Injector", "🏷️ Tag Manager", "👤 User Control", "💳 Recharges"])
    
    with t3:
        st.subheader("🏷️ Tag Control Center")
        new_tag = st.text_input("Add New Tag").upper()
        if st.button("➕ Save Tag"):
            if new_tag:
                supabase.table("custom_tags").upsert({"tag_name": new_tag}).execute()
                st.success("Tag Added!"); time.sleep(0.5); st.rerun()
        
        st.divider()
        st.markdown("#### 📋 Full Database Tag List")
        all_db_tags = get_tags()
        if all_db_tags:
            cols = st.columns(4)
            for i, tag in enumerate(all_db_tags):
                with cols[i % 4]:
                    st.info(f"**{tag}**")
                    if st.button("🗑️", key=f"del_{tag}"):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.rerun()
        else: st.warning("No tags found.")

    with t4:
        st.subheader("👤 Advanced User Management")
        with st.expander("✨ Create User (Set Location)"):
            with st.form("new_user"):
                c1, c2 = st.columns(2)
                u_n, u_p = c1.text_input("Username"), c2.text_input("Password")
                u_la = c1.number_input("Fix Latitude", value=25.5940, format="%.6f")
                u_lo = c2.number_input("Fix Longitude", value=85.1370, format="%.6f")
                if st.form_submit_button("🚀 Create Account"):
                    exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                    supabase.table("user_profiles").insert({"username": u_n, "password": u_p, "expiry_date": exp, "status": "active", "latitude": u_la, "longitude": u_lo}).execute()
                    st.success("User Created!"); st.rerun()

        st.divider()
        st.markdown("### 🔍 Master Data Editor")
        search = st.text_input("Search Username to Edit Full Data")
        if search:
            u_query = supabase.table("user_profiles").select("*").ilike("username", f"%{search}%").execute()
            for row in u_query.data:
                with st.container(border=True):
                    st.markdown(f"#### Editing: {row['username']}")
                    e_p = st.text_input("Password", value=row['password'], key=f"p_{row['id']}")
                    e_la = st.number_input("Lat", value=float(row['latitude']), format="%.6f", key=f"la_{row['id']}")
                    e_lo = st.number_input("Lon", value=float(row['longitude']), format="%.6f", key=f"lo_{row['id']}")
                    if st.button("💾 Save Changes", key=f"s_{row['id']}"):
                        supabase.table("user_profiles").update({"password": e_p, "latitude": e_la, "longitude": e_lo}).eq("id", row['id']).execute()
                        st.success("Updated!"); st.rerun()
    
    with t1: st.info("Reports Tab")
    with t2: st.info("Injector Tab")
    with t5: st.info("Recharge Tab")
