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
    
    # --- TAB 3: TAG MANAGER (FIXED) ---
    with t3:
        st.subheader("🏷️ Database Tag Inventory")
        
        c_in, c_btn = st.columns([3, 1])
        new_t = c_in.text_input("New Tag Name", placeholder="e.g. BBOX77").upper().strip()
        if c_btn.button("➕ SAVE", use_container_width=True):
            if new_t:
                supabase.table("custom_tags").upsert({"tag_name": new_t}).execute()
                st.success(f"{new_t} Saved!"); time.sleep(0.5); st.rerun()

        st.divider()
        all_tags = get_tags() # database.py se fresh data
        if all_tags:
            st.write(f"Total Tags: {len(all_tags)}")
            grid = st.columns(4)
            for i, tag in enumerate(all_tags):
                with grid[i % 4]:
                    st.markdown(f"<div style='background-color:#262730; border:1px solid #FF4B4B; padding:10px; border-radius:5px; text-align:center;'><b>{tag}</b></div>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_{tag}"):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.rerun()
        else:
            st.warning("No tags found in 'custom_tags' table.")

    # --- TAB 4: USER MANAGEMENT (FULL EDITOR) ---
    with t4:
        st.subheader("👤 User Master Editor")
        with st.expander("✨ Create New User (Location Fix)"):
            with st.form("create_u"):
                f1, f2 = st.columns(2)
                nu = f1.text_input("Username")
                np = f2.text_input("Password")
                la = f1.number_input("Lat", value=25.5940, format="%.6f")
                lo = f2.number_input("Lon", value=85.1370, format="%.6f")
                if st.form_submit_button("🔥 Create Account"):
                    exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                    supabase.table("user_profiles").insert({"username":nu, "password":np, "expiry_date":exp, "status":"active", "latitude":la, "longitude":lo}).execute()
                    st.success("User Created!"); st.rerun()

        st.divider()
        search_u = st.text_input("🔍 Search User to Edit Full Data")
        if search_u:
            users = supabase.table("user_profiles").select("*").ilike("username", f"%{search_u}%").execute()
            for u in users.data:
                with st.container(border=True):
                    st.write(f"**ID:** CID-{1000 + u['cid_id']} | **User:** {u['username']}")
                    e1, e2 = st.columns(2)
                    upass = e1.text_input("Password", u['password'], key=f"p_{u['id']}")
                    uexp = e2.text_input("Expiry (YYYY-MM-DD)", u['expiry_date'], key=f"ex_{u['id']}")
                    elat = e1.number_input("Lat", value=float(u['latitude']), format="%.6f", key=f"la_{u['id']}")
                    elon = e2.number_input("Lon", value=float(u['longitude']), format="%.6f", key=f"lo_{u['id']}")
                    
                    b1, b2 = st.columns(2)
                    if b1.button("💾 Save Changes", key=f"sv_{u['id']}", use_container_width=True):
                        supabase.table("user_profiles").update({"password":upass, "expiry_date":uexp, "latitude":elat, "longitude":elon}).eq("id", u['id']).execute()
                        st.success("Updated!"); st.rerun()
                    if b2.button("🚫 Toggle Status", key=f"st_{u['id']}", use_container_width=True):
                        ns = "inactive" if u['status'] == "active" else "active"
                        supabase.table("user_profiles").update({"status": ns}).eq("id", u['id']).execute()
                        st.rerun()

    with t1: st.info("Reports Tab Ready")
    with t2: st.info("Injector Tab Ready")
    with t5: st.info("Recharges Tab Ready")
