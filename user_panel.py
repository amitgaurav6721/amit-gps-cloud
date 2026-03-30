import streamlit as st
import pandas as pd
import time
from database import supabase, get_vehicle_data, log_activity, get_tags

def user_panel(send_packet_func):
    st.sidebar.write(f"👤 User: {st.session_state.user}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("🚀 Bihar VLTS Control")
    # Baaki user panel ka logic yahan...
    st.info("User Panel Loaded Successfully")
