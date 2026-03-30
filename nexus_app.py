import streamlit as st
import socket
import time
import pandas as pd
import threading
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- SUPABASE CONFIG ---
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Bihar VLTS Pro Max", layout="wide")

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.page = "dashboard"

# --- DB FUNCTIONS ---
def get_tags():
    res = supabase.table("custom_tags").select("tag_name").execute()
    return [item['tag_name'] for item in res.data]

def add_new_tag(new_tag):
    if new_tag:
        supabase.table("custom_tags").upsert({"tag_name": new_tag.upper().strip()}).execute()

def get_vehicle_data(v_no):
    res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no).execute()
    return res.data[0]['imei_no'] if res.data else ""

# --- PAGES ---
def recharge_page():
    st.title("💳 Recharge Your Plan")
    st.info("### Payment Details")
    st.write("**UPI ID:** amit@upi") # Apni UPI ID yahan dalein
    st.write("**Admin Contact:** +91 XXXXX XXXXX")
    st.warning("Payment ke baad screenshot WhatsApp karein.")
    if st.button("⬅️ Back to Home"):
        st.session_state.page = "dashboard"
        st.rerun()

def user_panel():
    u_data = st.session_state.u_data
    expiry = datetime.strptime(u_data['expiry_date'], '%Y-%m-%d')
    days_left = (expiry - datetime.now()).days + 1

    # Sidebar
    st.sidebar.title(f"👋 Welcome, {st.session_state.user}")
    if days_left > 0:
        st.sidebar.success(f"📅 Validity: {days_left} Days Left")
    else:
        st.sidebar.error("❌ Plan Expired")
        st.error("🚫 YOUR PLAN HAS EXPIRED. PLEASE RECHARGE.")
        if st.sidebar.button("💳 Recharge Now"):
            st.session_state.page = "recharge"
            st.rerun()
        return

    if st.sidebar.button("💳 Recharge / Renew"):
        st.session_state.page = "recharge"
        st.rerun()
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if st.session_state.page == "recharge":
        recharge_page()
        return

    # --- MAIN UI ---
    col1, col2 = st.columns([2, 1])
    with col1:
        v_no = st.text_input("Vehicle Number", value="").upper() # Privacy: Box is Blank
        imei_val = get_vehicle_data(v_no) if v_no else ""
        imei = st.text_input("IMEI Number", value=imei_val, max_chars=15)
        
        # --- NEW CUSTOM TAG SYSTEM ---
        all_tags = get_tags()
        st.write(f"**Current Active Tags:** `{', '.join(all_tags)}`")
        
        with st.expander("➕ Add Custom Tag (If old tags don't work)"):
            new_tag_input = st.text_input("Enter New Tag Name (e.g. TEMP1)")
            if st.button("Save Tag Forever"):
                add_new_tag(new_tag_input)
                st.success(f"Tag {new_tag_input} saved to Database!")
                st.rerun()

    with col2:
        st.write("📍 Assigned Location")
        map_data = pd.DataFrame({'lat': [u_data['latitude']], 'lon': [u_data['longitude']]})
        st.map(map_data, zoom=12)

    st.divider()
    
    if not st.get('running', False):
        if st.button("🚀 START SESSION", type="primary", use_container_width=True):
            if v_no and imei:
                st.session_state.running = True
                supabase.table("vehicle_master").upsert({"vehicle_no": v_no, "imei_no": imei}).execute()
                supabase.table("activity_logs").insert({"user_id": st.session_state.user, "vehicle_no": v_no}).execute()
                st.rerun()

    if st.get('running', False):
        st.success(f"🟢 {v_no} Active | 1s Interval")
        if st.button("🛑 STOP"):
            st.session_state.running = False
            st.rerun()
        
        # Original Packet Logic
        status_area = st.empty()
        server_host, server_port = "vlts.bihar.gov.in", 9999
        while st.session_state.running:
            results = []
            threads = []
            tag_list = get_tags() # Fetch latest tags from DB
            dt = datetime.now().strftime("%d%m%Y,%H%M%S")
            for t in tag_list:
                packet = f"$PVT,{t},2.1.1,NR,01,L,{imei},{v_no},1,{dt},{u_data['latitude']:.7f},N,{u_data['longitude']:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                # Note: 'send_packet_thread' function is same as before
                # (Skipping thread code here for brevity, use your existing function)
                # ... (threading logic) ...
            time.sleep(1.0)

# (Rest of the code like login_page and admin_panel remains same)
