import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from database import supabase, get_tags

def admin_panel():
    st.sidebar.markdown("### 👑 Admin Control")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Injector", "🏷️ Tags", "👤 Users", "💳 Recharges"])
    
    with t3:
        st.subheader("🏷️ Tag Manager")
        new_tag = st.text_input("New Tag").strip().upper()
        if st.button("➕ Save Tag"):
            if new_tag:
                supabase.table("custom_tags").upsert({"tag_name": new_tag}).execute()
                st.success("Saved!"); time.sleep(0.5); st.rerun()
        
        st.divider()
        all_tags = get_tags()
        if all_tags:
            cols = st.columns(4)
            for i, tag in enumerate(all_tags):
                with cols[i % 4]:
                    st.info(f"**{tag}**")
                    if st.button("🗑️", key=f"del_{tag}_{i}"):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.rerun()

    with t4:
        st.subheader("👤 User Editor")
        with st.expander("✨ Create User (With Location)"):
            with st.form("nu"):
                u, p = st.text_input("User"), st.text_input("Pass")
                la = st.number_input("Lat", value=25.5940, format="%.6f")
                lo = st.number_input("Lon", value=85.1370, format="%.6f")
                if st.form_submit_button("Create"):
                    exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                    supabase.table("user_profiles").insert({"username": u, "password": p, "expiry_date": exp, "status": "active", "latitude": la, "longitude": lo}).execute()
                    st.success("Created!"); st.rerun()
        
        st.divider()
        search = st.text_input("Search User to Edit")
        if search:
            res = supabase.table("user_profiles").select("*").ilike("username", f"%{search}%").execute()
            for r in res.data:
                with st.container(border=True):
                    st.write(f"Editing: {r['username']}")
                    np = st.text_input("New Pass", value=r['password'], key=f"p_{r['id']}")
                    nla = st.number_input("Lat", value=float(r['latitude']), key=f"la_{r['id']}")
                    nlo = st.number_input("Lon", value=float(r['longitude']), key=f"lo_{r['id']}")
                    if st.button("Save Changes", key=f"s_{r['id']}"):
                        supabase.table("user_profiles").update({"password": np, "latitude": nla, "longitude": nlo}).eq("id", r['id']).execute()
                        st.success("Updated!"); st.rerun()

    with t1: st.info("Reports Active")
    with t2: st.info("Injector Active")
    with t5: st.info("Recharge Active")
