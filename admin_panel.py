import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from database import supabase, get_tags # Dono import hone chahiye

def admin_panel():
    st.sidebar.markdown("<h2 style='color: #FF4B4B;'>👑 Admin Pro Max</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🔒 Logout Admin", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Injector", "🏷️ Tag Manager", "👤 User Control", "💳 Recharges"])
    
    # --- TAG MANAGER (TAB 3) ---
    with t3:
        st.subheader("🏷️ Database Tag Inventory")
        
        c1, c2 = st.columns([3, 1])
        new_tag = c1.text_input("Enter New Tag Name", placeholder="e.g. BBOX77").upper().strip()
        
        if c2.button("➕ SAVE", use_container_width=True):
            if new_tag:
                # Direct try-catch for better debugging
                try:
                    supabase.table("custom_tags").upsert({"tag_name": new_tag}).execute()
                    st.success(f"Tag {new_tag} Saved!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")

        st.divider()
        
        # Ab Fresh data fetch hoga
        db_tags = get_tags() 
        
        if db_tags:
            st.success(f"Successfully connected! Found {len(db_tags)} Tags.")
            grid = st.columns(4)
            for i, t_name in enumerate(db_tags):
                with grid[i % 4]:
                    st.markdown(f"<div style='background-color:#262730; border:1px solid #FF4B4B; padding:10px; border-radius:5px; text-align:center;'><b>{t_name}</b></div>", unsafe_allow_html=True)
                    if st.button("🗑️", key=f"d_{t_name}_{i}"):
                        supabase.table("custom_tags").delete().eq("tag_name", t_name).execute()
                        st.rerun()
        else:
            st.warning("⚠️ Database se connection toh hai, par 'custom_tags' table mein koi data nahi mila.")

    # --- REPORTS & USER CONTROL (Keep Previous Logic) ---
    with t1:
        st.info("Reports tab connects to 'activity_logs'")
    with t4:
        st.info("User Control connects to 'user_profiles'")
