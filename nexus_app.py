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
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.page = "dashboard"
if 'running' not in st.session_state:
    st.session_state.running = False

# --- DB FUNCTIONS ---
def check_login(user, pwd):
    if user == "admin" and pwd == "admin77": 
        return {"username": "admin", "role": "admin"}
    res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
    if res.data:
        return {"username": res.data[0]['username'], "role": "user", "data": res.data[0]}
    return None

def get_tags():
    res = supabase.table("custom_tags").select("tag_name").execute()
    return [item['tag_name'] for item in res.data]

def add_new_tag(new_tag):
    if new_tag:
        supabase.table("custom_tags").upsert({"tag_name": new_tag.upper().strip()}).execute()

def get_vehicle_data(v_no):
    res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no).execute()
    return res.data[0]['imei_no'] if res.data else ""

# --- PACKET SENDING LOGIC (SECURE) ---
def send_packet_thread(host, port, packet, results_list):
    try:
        final_to_send = packet + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        time.sleep(0.2)
        s.close()
        results_list.append({"Signal": "📡 Syncing...", "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except:
        results_list.append({"Signal": "📡 Syncing...", "Status": "❌ Error", "Time": datetime.now().strftime("%H:%M:%S")})

# --- PAGES ---
def login_page():
    st.title("🔐 Secure Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        user = check_login(u, p)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user['username']
            st.session_state.role = user['role']
            st.session_state.u_data = user.get('data')
            st.rerun()
        else:
            st.error("Invalid ID or Password")

def recharge_page():
    st.title("💳 Recharge Your Plan")
    st.info("### Payment Details")
    st.write("**UPI ID:** amit@upi") 
    st.write("**Admin Contact:** +91 XXXXX XXXXX")
    st.warning("Payment ke baad screenshot WhatsApp karein taaki hum aapka account turant extend kar sakein.")
    if st.button("⬅️ Back to Home"):
        st.session_state.page = "dashboard"
        st.rerun()

def admin_panel():
    st.sidebar.title("Admin Dashboard")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    menu = st.tabs(["User Management", "Usage Logs", "Manage Protocols"])
    
    with menu[0]:
        st.subheader("Create New User")
        with st.form("new_user"):
            new_u = st.text_input("New User ID")
            new_p = st.text_input("New Password")
            lat = st.number_input("Assign Latitude", format="%.7f", value=25.5941)
            lon = st.number_input("Assign Longitude", format="%.7f", value=85.1376)
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
        
    with menu[2]:
        st.subheader("Manage Global Protocols (Tags)")
        tags = get_tags()
        st.write(f"Current Protocols: {tags}")
        tag_to_add = st.text_input("Add Protocol Code")
        if st.button("Add"):
            add_new_tag(tag_to_add)
            st.rerun()

def user_panel():
    u_data = st.session_state.u_data
    expiry = datetime.strptime(u_data['expiry_date'], '%Y-%m-%d')
    days_left = (expiry - datetime.now()).days + 1

    # Sidebar Login Info
    st.sidebar.title(f"👋 Welcome, {st.session_state.user}")
    
    if st.session_state.page == "recharge":
        recharge_page()
        return

    # Validity Check and Sidebar
    if days_left <= 0:
        st.sidebar.error("❌ Plan Expired")
        st.error("🚫 YOUR PLAN HAS EXPIRED. PLEASE RECHARGE TO CONTINUE.")
        if st.sidebar.button("💳 Recharge Now"):
            st.session_state.page = "recharge"
            st.rerun()
        return
    else:
        st.sidebar.success(f"📅 Validity: {days_left} Days Left")

    # --- RECHARGE ALERT LOGIC (NEW) ---
    if days_left <= 5:
        st.warning(f"🔔 **URGENT:** Aapka plan {days_left} dinon mein expire ho jayega. Kripya band hone se pehle recharge karalein.")
        if st.button("💳 Click here to Recharge Now", use_container_width=True):
            st.session_state.page = "recharge"
            st.rerun()
        st.divider()

    if st.sidebar.button("💳 Recharge / Renew"):
        st.session_state.page = "recharge"
        st.rerun()
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- MAIN UI (SECURE) ---
    col1, col2 = st.columns([2, 1])
    with col1:
        v_no = st.text_input("Vehicle Number", value="").upper()
        imei_val = get_vehicle_data(v_no) if v_no else ""
        imei = st.text_input("IMEI Number", value=imei_val, max_chars=15)
        
        with st.expander("🛠️ Advanced Settings (Add Protocol)"):
            st.write("Naya protocol code dalein agar purana kaam na kare:")
            new_tag_input = st.text_input("Protocol Code", type="password") 
            if st.button("Update Protocol"):
                if new_tag_input:
                    add_new_tag(new_tag_input)
                    st.success("Protocol Updated!")
                    time.sleep(1)
                    st.rerun()

    with col2:
        st.write("📍 Assigned Location")
        map_data = pd.DataFrame({'lat': [u_data['latitude']], 'lon': [u_data['longitude']]})
        st.map(map_data, zoom=12)

    st.divider()
    
    if not st.session_state.running:
        if st.button("🚀 START SESSION", type="primary", use_container_width=True):
            if v_no and imei:
                st.session_state.running = True
                supabase.table("vehicle_master").upsert({"vehicle_no": v_no, "imei_no": imei}).execute()
                supabase.table("activity_logs").insert({"user_id": st.session_state.user, "vehicle_no": v_no}).execute()
                st.rerun()
            else:
                st.warning("Please enter Vehicle and IMEI")

    if st.session_state.running:
        st.success(f"🟢 {v_no} Active | Syncing...")
        if st.button("🛑 STOP SESSION", type="secondary", use_container_width=True):
            st.session_state.running = False
            st.rerun()
        
        status_area = st.empty()
        server_host, server_port = "vlts.bihar.gov.in", 9999
        suffix = "0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
        
        while st.session_state.running:
            results = []
            threads = []
            tag_list = get_tags()
            dt = datetime.now().strftime("%d%m%Y,%H%M%S")
            for t in tag_list:
                packet = f"$PVT,{t},2.1.1,NR,01,L,{imei},{v_no},1,{dt},{u_data['latitude']:.7f},N,{u_data['longitude']:.7f},E,{suffix},DDE3*"
                th = threading.Thread(target=send_packet_thread, args=(server_host, server_port, packet, results))
                threads.append(th)
                th.start()
            
            for th in threads: th.join()
            status_area.table(pd.DataFrame(results))
            time.sleep(1.0)

# --- MAIN NAVIGATION ---
if not st.session_state.logged_in:
    login_page()
else:
    if st.session_state.role == 'admin':
        admin_panel()
    else:
        user_panel()
