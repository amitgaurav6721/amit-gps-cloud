import streamlit as st
import socket
import time
import pandas as pd
import threading
from datetime import datetime, timedelta
from supabase import create_client, Client

# ==========================================================
# --- 1. GLOBAL APP CONFIGURATION & DATABASE SETUP ---
# ==========================================================

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
QR_URL = "https://i.ibb.co/99P60H1z/Whats-App-Image-2026-03-30-at-23-26-19.jpg"

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="Bihar VLTS Pro Max",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INITIALIZE SESSION STATES ---
if 'logged_in' not in st.session_state:
    st.session_state.update({
        'logged_in': False,
        'user': None,
        'role': None,
        'page': 'dashboard',
        'u_data': None
    })

if 'running' not in st.session_state:
    st.session_state.running = False

if 'admin_running' not in st.session_state:
    st.session_state.admin_running = False

# ==========================================================
# --- 2. CORE DATABASE FUNCTIONS ---
# ==========================================================

def get_contact_details():
    try:
        res = supabase.table("contact_settings").select("*").eq("id", 1).execute()
        if res.data:
            return res.data[0]
        return {"whatsapp_no": "Not Set", "email_id": "Not Set", "support_time": "10 AM - 6 PM", "upi_id": "admin@upi"}
    except Exception:
        return {"whatsapp_no": "Error", "email_id": "Error", "support_time": "Not Set", "upi_id": "admin@upi"}

def check_login(user, pwd):
    if user == "admin" and pwd == "admin77": 
        return {"username": "admin", "role": "admin"}
    try:
        res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
        if res.data:
            return {"username": res.data[0]['username'], "role": "user", "data": res.data[0]}
        return None
    except Exception:
        return None

def get_tags():
    default_req = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR", "HB", "HA", "RT", "OS", "IDL", "PWR"]
    try:
        res = supabase.table("custom_tags").select("tag_name").execute()
        if res.data:
            return [item['tag_name'] for item in res.data]
        return default_req
    except Exception:
        return default_req

def log_activity(username, vehicle_no, action):
    """Saves activity to activity_logs with FIXED column names"""
    try:
        # Columns match your Supabase: user_id, vehicle_no, action, created_at
        supabase.table("activity_logs").insert({
            "user_id": str(username),
            "vehicle_no": str(vehicle_no).upper(),
            "action": str(action),
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception:
        pass

def get_vehicle_data(v_no):
    try:
        if v_no:
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no.upper()).execute()
            if res.data:
                return res.data[0]['imei_no']
        return ""
    except Exception:
        return ""

def send_packet_thread(host, port, packet, results, show_tag=False):
    try:
        raw_data = packet + "\r\n"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.sendall(raw_data.encode('ascii'))
        time.sleep(0.1)
        sock.close()
        tag_name = packet.split(',')[1] if show_tag else "📡 GPS Sync"
        results.append({"Tag/Packet": tag_name, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except Exception:
        results.append({"Tag/Packet": "Error", "Status": "❌ Failed", "Time": datetime.now().strftime("%H:%M:%S")})

# ==========================================================
# --- 3. UI PAGES (SUPPORT & RECHARGE) ---
# ==========================================================

def contact_us_page(reason="general"):
    contact = get_contact_details()
    st.title("📞 Customer Support")
    if reason == "deactivated":
        st.error("⚠️ Account Inactive. Kripya Recharge karein.")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📱 WhatsApp Support")
        st.write(contact.get('whatsapp_no', 'Not Set'))
        clean_no = ''.join(filter(str.isdigit, str(contact.get('whatsapp_no', ''))))
        if clean_no:
            st.markdown(f"[![Chat](https://img.shields.io/badge/WhatsApp-Chat-green?style=for-the-badge&logo=whatsapp)](https://wa.me/{clean_no})")
        st.subheader("📧 Email Support")
        st.write(contact.get('email_id', 'Not Set'))
    with c2:
        st.subheader("🕒 Support Timings")
        st.write(contact.get('support_time', 'Not Set'))
        st.subheader("🆔 Your Customer ID")
        if st.session_state.u_data:
            st.code(f"CID: {1000 + st.session_state.u_data.get('cid_id', 0)}")
    st.divider()
    if st.button("🏠 Back to Home", use_container_width=True):
        st.session_state.page = "dashboard"; st.rerun()

def recharge_page():
    contact = get_contact_details()
    u_data = st.session_state.u_data
    cid = u_data.get('cid_id', 0)
    user_id = st.session_state.user
    st.title("💳 Recharge Your Account")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(QR_URL, width=240, caption="Scan QR to Pay")
        st.info(f"Verify ID: **CID-{1000 + cid}**")
        st.subheader("📜 History")
        history = supabase.table("recharge_requests").select("*").eq("username", user_id).order("id", desc=True).limit(3).execute()
        if history.data:
            for h in history.data:
                st.write(f"{'⏳' if h['status'] == 'pending' else '✅'} {h['amount']} - {h['status'].title()}")
    
    with col2:
        st.info(f"**UPI ID:** `{contact.get('upi_id', 'admin@upi')}`")
        m_no = st.text_input("Mobile No", max_chars=10, placeholder="10 Digits")
        utr = st.text_input("Enter UTR Number")
        
        plans_res = supabase.table("plan_settings").select("*").execute()
        plans = plans_res.data
        plan_options = [f"₹{p['amount']} - {p['plan_name']} ({p['days']} Days)" for p in plans] if plans else ["Standard Plan"]
            
        amt = st.selectbox("Select Plan", plan_options)
        
        if st.button("Submit Request", use_container_width=True):
            if utr and len(m_no) == 10:
                supabase.table("recharge_requests").insert({"username": user_id, "utr_number": utr, "amount": amt, "mobile_no": m_no, "cid_display": f"CID-{1000+cid}", "status": "pending"}).execute()
                st.success("✅ Sent! Wait for approval."); time.sleep(2)
                st.session_state.page = "dashboard"; st.rerun()
            else:
                st.warning("Check Mobile No (10 Digits) & UTR.")
                
    if st.button("🏠 Back to Home"):
        st.session_state.page = "dashboard"; st.rerun()

# ==========================================================
# --- 4. ADMIN CONTROL PANEL ---
# ==========================================================

def admin_panel():
    st.sidebar.title("🛠️ Admin Control")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False; st.rerun()
        
    t1, t2, t3, t4 = st.tabs(["📊 Activity Logs", "🚀 Master", "🏷️ Tags", "👤 Users"])
    
    with t1:
        st.subheader("📅 Activity Reports")
        d = st.date_input("Date", datetime.now())
        act = supabase.table("activity_logs").select("*").gte("created_at", f"{d}T00:00:00").lte("created_at", f"{d}T23:59:59").execute()
        if act.data:
            st.dataframe(pd.DataFrame(act.data)[['created_at', 'user_id', 'vehicle_no', 'action']], use_container_width=True)
        else:
            st.info("No activity recorded.")
            
    with t2:
        adm_v = st.text_input("V-No (Admin)").upper()
        adm_i = st.text_input("IMEI (Admin)")
        if not st.session_state.admin_running:
            if st.button("🔥 START MASTER"):
                st.session_state.admin_running = True; st.rerun()
        else:
            if st.button("🛑 STOP MASTER"):
                st.session_state.admin_running = False; st.rerun()
            tbl_area = st.empty()
            while st.session_state.admin_running:
                res, tags, dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
                for t in tags:
                    send_packet_thread("vlts.bihar.gov.in", 9999, f"$PVT,{t.upper()},2.1.1,NR,01,L,{adm_i},{adm_v},1,{dt},25.594,N,85.137,E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*", res, True)
                tbl_area.table(pd.DataFrame(res)); time.sleep(1)

    with t3:
        nt = st.text_input("Add Tag").upper()
        if st.button("Add"):
            supabase.table("custom_tags").upsert({"tag_name": nt}).execute(); st.rerun()

    with t4:
        s = st.text_input("Search User")
        if s:
            users = supabase.table("user_profiles").select("*").ilike("username", f"%{s}%").execute()
            for u in users.data:
                with st.expander(f"{u['username']}"):
                    if st.button(f"Extend 28 Days", key=f"e_{u['username']}"):
                        new_exp = (datetime.strptime(u['expiry_date'], '%Y-%m-%d') + timedelta(days=28)).strftime('%Y-%m-%d')
                        supabase.table("user_profiles").update({"expiry_date": new_exp}).eq("username", u['username']).execute(); st.rerun()

# ==========================================================
# --- 5. USER PANEL ---
# ==========================================================

def user_panel():
    u_data = st.session_state.u_data
    exp_dt = datetime.strptime(u_data['expiry_date'], '%Y-%m-%d')
    days_left = (exp_dt - datetime.now()).days + 1
    
    st.sidebar.title(f"👋 Welcome, {st.session_state.user}")
    st.sidebar.info(f"🆔 CID-{1000 + u_data.get('cid_id', 0)}")
    
    if u_data.get('status') == 'inactive' or days_left <= 0:
        if st.sidebar.button("💳 Recharge Now", use_container_width=True):
            st.session_state.page = "recharge"; st.rerun()
        if st.session_state.page == "recharge": recharge_page()
        else: contact_us_page(reason="deactivated")
        return

    st.sidebar.success(f"📅 {days_left} Days Remaining")
    if st.sidebar.button("🏠 Home", use_container_width=True): st.session_state.page = "dashboard"; st.rerun()
    if st.sidebar.button("💳 Recharge", use_container_width=True): st.session_state.page = "recharge"; st.rerun()
    if st.sidebar.button("📞 Support", use_container_width=True): st.session_state.page = "contact"; st.rerun()
    if st.sidebar.button("Logout", use_container_width=True): st.session_state.logged_in = False; st.rerun()

    if st.session_state.page == "recharge": recharge_page(); return
    if st.session_state.page == "contact": contact_us_page(); return

    st.title("🚀 Bihar VLTS Live Sync")
    c_l, c_r = st.columns([2, 1])
    with c_r:
        st.subheader("🏷️ Custom Tag")
        u_t = st.text_input("New Tag").upper()
        if st.button("Save Tag"):
            if u_t:
                supabase.table("custom_tags").upsert({"tag_name": u_t.strip()}).execute()
                st.success("Saved!"); time.sleep(0.5); st.rerun()
    with c_l:
        v = st.text_input("Vehicle No").upper()
        im = st.text_input("IMEI No", value=get_vehicle_data(v) if v else "", max_chars=15)
    
    st.map(pd.DataFrame({'lat': [u_data['latitude']], 'lon': [u_data['longitude']]}), height=400)
    
    st.divider()
    if not st.session_state.running:
        if st.button("🚀 START SYNC", type="primary", use_container_width=True):
            if v and im:
                supabase.table("vehicle_master").upsert({"vehicle_no": v.upper(), "imei_no": im}, on_conflict="vehicle_no").execute()
                log_activity(st.session_state.user, v, "START")
                st.session_state.running = True; st.rerun()
    else:
        if st.button("🛑 STOP SYNC", use_container_width=True):
            log_activity(st.session_state.user, v if v else "Unknown", "STOP")
            st.session_state.running = False; st.rerun()
            
        status_area = st.empty()
        while st.session_state.running:
            res_data, tags = [], get_tags()
            dt = datetime.now().strftime("%d%m%Y,%H%M%S")
            for t in tags:
                p = f"$PVT,{t.upper()},2.1.1,NR,01,L,{im},{v},1,{dt},{u_data['latitude']:.7f},N,{u_data['longitude']:.7f},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                send_packet_thread("vlts.bihar.gov.in", 9999, p, res_data)
            status_area.table(pd.DataFrame(res_data)); time.sleep(1)

def main():
    if not st.session_state.logged_in:
        st.title("🔐 Login")
        u_in = st.text_input("Username")
        p_in = st.text_input("Password", type="password")
        if st.button("Login"):
            res = check_login(u_in, p_in)
            if res:
                st.session_state.update({'logged_in': True, 'user': res['username'], 'role': res['role'], 'u_data': res.get('data')}); st.rerun()
            else: st.error("Invalid credentials.")
    elif st.session_state.role == 'admin': admin_panel()
    else: user_panel()

if __name__ == "__main__": main()
