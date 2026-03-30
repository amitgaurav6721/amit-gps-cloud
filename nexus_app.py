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
# QR Code Link - Direct raw link for GitHub images
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
def get_contact_details():
    res = supabase.table("contact_settings").select("*").eq("id", 1).execute()
    return res.data[0] if res.data else {"whatsapp_no": "Not Set", "email_id": "Not Set", "support_time": "Not Set", "upi_id": "Not Set"}

def check_login(user, pwd):
    if user == "admin" and pwd == "admin77": 
        return {"username": "admin", "role": "admin"}
    res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
    if res.data:
        return {"username": res.data[0]['username'], "role": "user", "data": res.data[0]}
    return None

def get_plans():
    res = supabase.table("plan_settings").select("*").execute()
    return res.data

def get_tags():
    required_tags = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR", "HB", "HA", "RT", "OS", "IDL", "PWR"]
    res = supabase.table("custom_tags").select("tag_name").execute()
    existing = [item['tag_name'] for item in res.data]
    missing = [t for t in required_tags if t not in existing]
    if missing:
        for t in missing: supabase.table("custom_tags").upsert({"tag_name": t}).execute()
        res = supabase.table("custom_tags").select("tag_name").execute()
        return [item['tag_name'] for item in res.data]
    return existing

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
        time.sleep(0.1)
        s.close()
        tag_disp = "📡 Syncing..." if not show_tag else packet.split(',')[1]
        results_list.append({"Tag/Signal": tag_disp, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except:
        results_list.append({"Tag/Signal": "Error", "Status": "❌ Failed", "Time": datetime.now().strftime("%H:%M:%S")})

# --- PAGES ---
def contact_us_page(reason="general"):
    contact = get_contact_details()
    st.title("📞 Contact Us")
    if reason == "deactivated":
        st.error("⚠️ **Aapka account Deactivated hai.** Re-activate ke liye sampark karein:")
    else:
        st.info("Sahayata ke liye humein sampark karein:")
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📱 WhatsApp Support")
        st.write(contact.get('whatsapp_no'))
        # Direct WhatsApp Link
        clean_no = ''.join(filter(str.isdigit, contact.get('whatsapp_no', '')))
        if clean_no:
            st.markdown(f"[![Chat on WhatsApp](https://img.shields.io/badge/WhatsApp-Chat-green?style=for-the-badge&logo=whatsapp)](https://wa.me/{clean_no})")
        
        st.subheader("📧 Email Support")
        st.write(contact.get('email_id'))

    with c2:
        st.subheader("🕒 Support Timings")
        st.write(contact.get('support_time'))
        st.subheader("🆔 Your Customer ID")
        st.code(f"CID-{1000 + st.session_state.u_data.get('cid_id', 0)}")

    if st.session_state.u_data and st.session_state.u_data.get('status') == 'active':
        if st.button("⬅️ Back to Dashboard"): 
            st.session_state.page = "dashboard"
            st.rerun()
    else:
        if st.sidebar.button("Logout"): 
            st.session_state.logged_in = False
            st.rerun()

def admin_panel():
    st.sidebar.title("Admin Panel")
    if st.sidebar.button("Logout"): 
        st.session_state.logged_in = False
        st.rerun()
    
    menu = st.tabs(["Users Control", "Master Injector", "Recharges", "Settings", "Manage Tags"])
    
    with menu[0]:
        st.subheader("🔍 Search & Manual Control")
        search_q = st.text_input("Enter Username")
        if search_q:
            u_search = supabase.table("user_profiles").select("*").ilike("username", f"%{search_q}%").execute()
            for usr in u_search.data:
                exp_date = datetime.strptime(usr['expiry_date'], '%Y-%m-%d')
                d_left = (exp_date - datetime.now()).days + 1
                status = usr.get('status', 'active')
                with st.expander(f"👤 {usr['username']} (CID-{1000 + usr['cid_id']})"):
                    st.info(f"Validity: {d_left} Days | Status: {status.upper()}")
                    c1, c2, c3 = st.columns(3)
                    if c1.button("+28 Days", key=f"e1_{usr['username']}"):
                        new_exp = max(exp_date, datetime.now()) + timedelta(days=28)
                        supabase.table("user_profiles").update({"expiry_date": new_exp.strftime("%Y-%m-%d")}).eq("username", usr['username']).execute(); st.rerun()
                    if c2.button("+84 Days", key=f"e3_{usr['username']}"):
                        new_exp = max(exp_date, datetime.now()) + timedelta(days=84)
                        supabase.table("user_profiles").update({"expiry_date": new_exp.strftime("%Y-%m-%d")}).eq("username", usr['username']).execute(); st.rerun()
                    new_s = 'inactive' if status == 'active' else 'active'
                    if c3.button(f"Mark {new_s.upper()}", key=f"s_{usr['username']}"):
                        supabase.table("user_profiles").update({"status": new_s}).eq("username", usr['username']).execute(); st.rerun()

    with menu[1]:
        st.subheader("🚀 Master Injector (Raw Preview)")
        vno, imei = st.text_input("Test Vehicle No", "BR01P1234"), st.text_input("Test IMEI", "865432109876543")
        lat, lon = st.number_input("Test Lat", 25.5941, format="%.7f"), st.number_input("Test Lon", 85.1376, format="%.7f")
        speed = st.slider("Interval (Seconds)", 0.5, 5.0, 1.0)
        
        if not st.session_state.admin_running:
            if st.button("🔥 START INJECTION", use_container_width=True): st.session_state.admin_running = True; st.rerun()
        else:
            if st.button("🛑 STOP INJECTION", use_container_width=True): st.session_state.admin_running = False; st.rerun()
            str_area = st.empty()
            while st.session_state.admin_running:
                res = []; tags = get_tags(); dt = datetime.now().strftime("%d%m%Y,%H%M%S")
                sample_p = f"$PVT,{tags[0]},2.1.1,NR,01,L,{imei},{vno},1,{dt},{lat:.7f},N,{lon:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                str_area.code(f"Sending: {sample_p}")
                for t in tags:
                    p = f"$PVT,{t},2.1.1,NR,01,L,{imei},{vno},1,{dt},{lat:.7f},N,{lon:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                    th = threading.Thread(target=send_packet_thread, args=("vlts.bihar.gov.in", 9999, p, res, True))
                    th.start(); th.join()
                st.table(pd.DataFrame(res)); time.sleep(speed)

    with menu[3]:
        st.subheader("⚙️ Update Contact & Payment Details")
        curr = get_contact_details()
        with st.form("settings"):
            w = st.text_input("WhatsApp Number", curr.get('whatsapp_no'))
            e = st.text_input("Support Email", curr.get('email_id'))
            t = st.text_input("Working Hours", curr.get('support_time'))
            u = st.text_input("Recharge UPI ID", curr.get('upi_id'))
            if st.form_submit_button("Save Settings"):
                # Upsert to ensure row 1 always exists
                supabase.table("contact_settings").upsert({"id": 1, "whatsapp_no": w, "email_id": e, "support_time": t, "upi_id": u}).execute()
                st.success("Settings Updated Live!")

# --- (Other Page Functions: recharge_page, user_panel, login_page remain as previously optimized) ---
# ... [Keeping the logic same to avoid redundant code] ...
