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
    
    # --- TAG MANAGER (TAB 3) ---
    with t3:
        st.subheader("🏷️ Database Tag Inventory")
        
        # New Tag Input
        c1, c2 = st.columns([3, 1])
        new_tag = c1.text_input("Enter New Tag Name").upper().strip()
        if c2.button("➕ SAVE", use_container_width=True):
            if new_tag:
                # Direct Database Insert
                supabase.table("custom_tags").upsert({"tag_name": new_tag}).execute()
                st.success(f"{new_tag} Saved!"); time.sleep(0.5); st.rerun()

        st.divider()
        
        # Fetching tags using your get_tags() function
        all_tags = get_tags() 
        
        if all_tags:
            st.write(f"Found {len(all_tags)} Tags in Database")
            grid = st.columns(4)
            for i, tag in enumerate(all_tags):
                with grid[i % 4]:
                    st.markdown(f"<div style='background-color:#262730; border:1px solid #FF4B4B; padding:10px; border-radius:5px; text-align:center; margin-bottom:5px;'><b>{tag}</b></div>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"del_{tag}_{i}"):
                        supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                        st.rerun()
        else:
            st.error("⚠️ Supabase se connect nahi ho raha ya table 'custom_tags' khali hai.")

    # --- USER CONTROL (TAB 4) ---
    with t4:
        st.subheader("👤 Master User Editor")
        with st.expander("✨ Create New User (Fixed Lat/Lon)"):
            with st.form("create_form"):
                u_n, u_p = st.text_input("Username"), st.text_input("Password")
                la = st.number_input("Latitude", value=25.5940, format="%.6f")
                lo = st.number_input("Longitude", value=85.1370, format="%.6f")
                if st.form_submit_button("Create User"):
                    exp = (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d')
                    supabase.table("user_profiles").insert({"username":u_n, "password":u_p, "expiry_date":exp, "status":"active", "latitude":la, "longitude":lo}).execute()
                    st.success("User Created!"); st.rerun()

    with t1: st.info("Reports Logic Active")
    with t2: st.info("Injector Logic Active")
    with t5: st.info("Recharge Logic Active")
