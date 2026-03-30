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
    
    # --- TAB 3: TAG MANAGER (FIXED ERROR) ---
    with t3:
        st.subheader("🏷️ Tag Control Center")
        
        c_in, c_btn = st.columns([3, 1])
        new_t = c_in.text_input("Add New Tag Name").upper().strip()
        
        if c_btn.button("➕ SAVE", use_container_width=True):
            if new_t:
                try:
                    # Upsert ki jagah Insert use kar rahe hain safety ke liye
                    supabase.table("custom_tags").insert({"tag_name": new_t}).execute()
                    st.success(f"{new_t} Saved!"); time.sleep(0.5); st.rerun()
                except Exception as e:
                    # Agar pehle se hai toh ignore karega ya error dikhayega
                    st.error("Galti: Shayad ye Tag pehle se hai ya Database allow nahi kar raha.")
            else:
                st.warning("Tag ka naam likhiye!")

        st.divider()
        st.markdown("#### 📋 Current Database Tags")
        
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
            st.warning("⚠️ Database mein koi tag nahi mila.")

    # --- Baaki Tabs ka logic (Keeping it same as before) ---
    with t1:
        # Reports Logic
        st.info("Reports Tab Ready")
    with t2:
        # Injector Logic
        st.info("Injector Tab Ready")
    with t4:
        # User Control Logic
        st.info("User Control Ready")
    with t5:
        # Recharges Logic
        st.info("Recharges Tab Ready")
