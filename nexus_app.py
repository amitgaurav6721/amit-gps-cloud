import streamlit as st
import socket
import time
import pandas as pd
import threading
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- SUPABASE CONFIG ---
# Yahan apni details bharein
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Bihar VLTS Pro Max", layout="wide")

# --- SESSION STATE INIT ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None
if 'running' not in st.session_state:
    st.session_state.running = False

# --- DB FUNCTIONS ---
def check_login(user, pwd):
    if user == "admin" and pwd == "admin77": # Default Admin
        return {"username": "admin", "role": "admin"}
    res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
    if res.data:
        return {"username": res.data[0]['username'], "role": "user", "data": res.data[0]}
    return None

def get_vehicle_data(v_no):
    res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no).execute()
    return res.data[0]['imei_no'] if res.data else ""

def save_vehicle_log(v_no, imei):
    supabase.table("vehicle_master").upsert({"vehicle_no": v_no, "imei_no": imei}).execute()

def log_activity(u_name, v_no):
    supabase.table("activity_logs").insert({"user_id": u_name, "vehicle_no": v_no}).execute()

# --- CORE INJECTOR (YOUR ORIGINAL LOGIC) ---
def send_packet_thread(host, port, packet, tag, results_list):
    try:
        final_to_send = packet + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        time.sleep(0.2)
        s.close()
        results_list.append({"TAG": tag, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except:
        results_list.append({"TAG": tag, "Status": "❌ Error", "Time": datetime.now().strftime("%H:%M:%S")})

# --- UI COMPONENTS ---
def login_page():
    st.title("🔐 Secure Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        user = check_login(u, p)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user['username']
            st.session_state.role = user['role']
            st.session_state.u_data = user.get('data')
            st.rerun()
        else:
            st.error("Invalid ID or Password")

def admin_panel():
    st.sidebar.title("Admin Dashboard")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    menu = st.tabs(["User Management", "Usage Logs", "Active Users"])
    
    with menu[0]:
        st.subheader("Create New User")
        with st.form("new_user"):
            new_u = st.text_input("New User ID")
            new_p = st.text_input("New Password")
            lat = st.number_input("Assign Latitude", format="%.7f")
            lon = st.number_input("Assign Longitude", format="%.7f")
            plan = st.selectbox("Plan", ["1 Month (28 Days)", "3 Months (84 Days)", "Custom"])
            custom_date = st.date_input("Select Date (if custom)")
            
            if st.form_submit_button("Create User"):
                exp = datetime.now() + timedelta(days=28) if "1 Month" in plan else datetime.now() + timedelta(days=84)
                if plan == "Custom": exp = datetime.combine(custom_date, datetime.min.time())
                supabase.table("user_profiles").insert({
                    "username": new_u, "password": new_p, "latitude": lat, 
                    "longitude": lon, "expiry_date": exp.strftime("%Y-%m-%d")
                }).execute()
                st.success("User Created Successfully!")

    with menu[1]:
        st.subheader("Recent Activity")
        logs = supabase.table("activity_logs").select("*").order("created_at", desc=True).limit(50).execute()
        st.table(pd.DataFrame(logs.data))

def user_panel():
    u_data = st.session_state.u_data
    expiry = datetime.strptime(u_data['expiry_date'], '%Y-%m-%d')
    
    if datetime.now() > expiry:
        st.error("🚫 YOUR PLAN HAS EXPIRED. PLEASE CONTACT ADMIN.")
        return

    st.sidebar.title(f"Welcome, {st.session_state.user}")
    if expiry - datetime.now() < timedelta(days=3):
        st.sidebar.warning(f"⚠️ Plan expires on: {u_data['expiry_date']}")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- INPUTS ---
    col1, col2 = st.columns([2, 1])
    with col1:
        v_no = st.text_input("Vehicle Number", placeholder="BR29GC1365").upper()
        imei_val = get_vehicle_data(v_no) if v_no else ""
        imei = st.text_input("IMEI Number", value=imei_val, max_chars=15)
        
    with col2:
        st.write("📍 Assigned Location")
        map_data = pd.DataFrame({'lat': [u_data['latitude']], 'lon': [u_data['longitude']]})
        st.map(map_data, zoom=12)

    # Hardcoded/Locked Settings
    server_host = "vlts.bihar.gov.in"
    server_port = 9999
    gap = 1.0 # 1 Second Lock
    default_tags = "RA18, WTEX, MARK, ASPL, LOCT14A, ACT1, AIS140, VLTD, VLT, GPS"
    tag_list = [t.strip() for t in default_tags.split(',')]

    st.divider()
    
    if not st.session_state.running:
        if st.button("🚀 START SESSION", type="primary", use_container_width=True):
            if v_no and imei:
                st.session_state.running = True
                save_vehicle_log(v_no, imei)
                log_activity(st.session_state.user, v_no)
                st.rerun()
            else:
                st.warning("Please enter Vehicle and IMEI")

    if st.session_state.running:
        st.success(f"🟢 ACTIVE SESSION: {v_no} | Syncing at 1s interval")
        if st.button("🛑 STOP SESSION", type="secondary", use_container_width=True):
            st.session_state.running = False
            st.rerun()
        
        # --- BACKGROUND PROCESSING ---
        status_area = st.empty()
        preview_area = st.empty()
        curr_lat, curr_lon = u_data['latitude'], u_data['longitude']
        dt = datetime.now().strftime("%d%m%Y,%H%M%S")
        suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
        
        while st.session_state.running:
            results = []
            threads = []
            for t in tag_list:
                packet = f"$PVT,{t},2.1.1,NR,01,L,{imei},{v_no},1,{dt},{curr_lat:.7f},N,{curr_lon:.7f},E,{suffix},DDE3*"
                thread = threading.Thread(target=send_packet_thread, args=(server_host, server_port, packet, t, results))
                threads.append(thread)
                thread.start()
            
            for t in threads: t.join()
            status_area.table(pd.DataFrame(results))
            time.sleep(gap)

# --- MAIN NAVIGATION ---
if not st.session_state.logged_in:
    login_page()
else:
    if st.session_state.role == 'admin':
        admin_panel()
    else:
        user_panel()
