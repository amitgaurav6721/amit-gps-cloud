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
        return {"whatsapp_no": "Error", "email_id": "Error"}

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

def log_activity(username, vehicle_no, action_status):
    """Saves activity to activity_logs. Matches Table: user_id, vehicle_no"""
    try:
        # Note: Aapke table mein 'action' column nahi hai. 
        # Hum action ko vehicle_no ke saath merge kar rahe hain: "BR01 (START)"
        log_payload = {
            "user_id": str(username),
            "vehicle_no": f"{str(vehicle_no).upper()} ({action_status})"
        }
        # created_at automatically DB handle karega
        supabase.table("activity_logs").insert(log_payload).execute()
    except Exception as e:
        pass

def get_vehicle_data(v_no):
    """Fetches IMEI from vehicle_master"""
    try:
        if v_no:
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no.upper()).execute()
            if res.data:
                return res.data[0]['imei_no']
        return ""
    except Exception:
        return ""

def send_packet_thread(host, port, packet, results, show_tag=False):
    """TCP delivery logic"""
    try:
        raw_string = packet + "\r\n"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.sendall(raw_string.encode('ascii'))
        time.sleep(0.1)
        sock.close()
        tag_disp = packet.split(',')[1] if show_tag else "📡 GPS Sync"
        results.append({"Tag/Packet": tag_disp, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except Exception:
        results.append({"Tag/Packet": "Network", "Status": "❌ Failed", "Time": datetime.now().strftime("%H:%M:%S")})

# ==========================================================
# --- 3. PAGES (SUPPORT & RECHARGE) ---
# ==========================================================

def contact_us_page(reason="general"):
    contact = get_contact_details()
    st.title("📞 Official Support Center")
    if reason == "deactivated":
        st.error("⚠️ ACCOUNT EXPIRED: Recharge to continue.")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📱 WhatsApp")
        st.write(contact.get('whatsapp_no', 'Not Set'))
        num = ''.join(filter(str.isdigit, str(contact.get('whatsapp_no', ''))))
        if num:
            st.markdown(f"[![Chat](https://img.shields.io/badge/WhatsApp-Chat-green?style=for-the-badge&logo=whatsapp)](https://wa.me/{num})")
        st.subheader("📧 Email")
        st.write(contact.get('email_id', 'Not Set'))
    with c2:
        st.subheader("🕒 Timings")
        st.write(contact.get('support_time', '10 AM - 6 PM'))
        st.subheader("🆔 CID")
        if st.session_state.u_data:
            st.code(f"CID: {1000 + st.session_state.u_data.get('cid_id', 0)}")
    st.divider()
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "dashboard"; st.rerun()

def recharge_page():
    contact = get_contact_details()
    u_data = st.session_state.u_data
    cid_v = u_data.get('cid_id', 0)
    user_n = st.session_state.user
    st.title("💳 Secure Recharge Panel")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.image(QR_URL, width=240, caption="Scan & Pay")
        st.info(f"ID: **CID-{1000 + cid_v}**")
        st.subheader("📜 History")
        h_res = supabase.table("recharge_requests").select("*").eq("username", user_n).order("id", desc=True).limit(3).execute()
        if h_res.data:
            for entry in h_res.data:
                st.write(f"{'⏳' if entry['status'] == 'pending' else '✅'} {entry['amount']}")
    with col_r:
        st.info(f"**UPI:** `{contact.get('upi_id', 'admin@upi')}`")
        mob = st.text_input("Mobile No", max_chars=10)
        utr = st.text_input("UTR ID")
        p_res = supabase.table("plan_settings").select("*").execute()
        plans = [f"₹{p['amount']} - {p['plan_name']} ({p['days']} Days)" for p in p_res.data] if p_res.data else ["₹999"]
        amt = st.selectbox("Select Plan", plans)
        if st.button("Submit Proof", use_container_width=True):
            if utr and len(mob) == 10:
                supabase.table("recharge_requests").insert({"username": user_n, "utr_number": utr, "amount": amt, "mobile_no": mob, "cid_display": f"CID-{1000+cid_v}", "status": "pending"}).execute()
                st.success("✅ Sent!"); time.sleep(2); st.session_state.page = "dashboard"; st.rerun()
    if st.button("🏠 Back to Home"):
        st.session_state.page = "dashboard"; st.rerun()

# ==========================================================
# --- 4. ADMIN PANEL ---
# ==========================================================

def admin_panel():
    st.sidebar.title("🛠️ Admin Control")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False; st.rerun()
    t1, t2, t3, t4 = st.tabs(["📊 Logs", "🚀 Master", "🏷️ Tags", "👤 Users"])
    with t1:
        st.subheader("📅 Activity Reports")
        d = st.date_input("Filter Date", datetime.now())
        act = supabase.table("activity_logs").select("*").gte("created_at", f"{d}T00:00:00").lte("created_at", f"{d}T23:59:59").execute()
        if act.data:
            st.dataframe(pd.DataFrame(act.data)[['created_at', 'user_id', 'vehicle_no']], use_container_width=True)
    with t2:
        av, ai = st.text_input("V-No").upper(), st.text_input("IMEI")
        if not st.session_state.admin_running:
            if st.button("🔥 START"): st.session_state.admin_running = True; st.rerun()
        else:
            if st.button("🛑 STOP"): st.session_state.admin_running = False; st.rerun()
            area = st.empty()
            while st.session_state.admin_running:
                res, tags, dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
                for t in tags:
                    p = f"$PVT,{t.upper()},2.1.1,NR,01,L,{ai},{av},1,{dt},25.594,N,85.137,E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                    send_packet_thread("vlts.bihar.gov.in", 9999, p, res, True)
                area.table(pd.DataFrame(res)); time.sleep(1)
    with t3:
        nt = st.text_input("New Tag").upper()
        if st.button("Add"): supabase.table("custom_tags").upsert({"tag_name": nt}).execute(); st.rerun()
    with t4:
        s = st.text_input("Search")
        if s:
            u_query = supabase.table("user_profiles").select("*").ilike("username", f"%{s}%").execute()
            for u in u_query.data:
                with st.expander(f"{u['username']}"):
                    if st.button("Extend 28 Days", key=u['username']):
                        new_ex = (datetime.strptime(u['expiry_date'], '%Y-%m-%d') + timedelta(days=28)).strftime('%Y-%m-%d')
                        supabase.table("user_profiles").update({"expiry_date": new_ex}).eq("username", u['username']).execute(); st.rerun()

# ==========================================================
# --- 5. USER PANEL (MAIN) ---
# ==========================================================

def user_panel():
    u_info = st.session_state.u_data
    exp = datetime.strptime(u_info['expiry_date'], '%Y-%m-%d')
    days = (exp - datetime.now()).days + 1
    st.sidebar.title(f"👋 {st.session_state.user}")
    st.sidebar.info(f"🆔 CID-{1000 + u_info.get('cid_id', 0)}")
    if u_info.get('status') == 'inactive' or days <= 0:
        if st.sidebar.button("💳 Recharge Now"): st.session_state.page = "recharge"; st.rerun()
        if st.session_state.page == "recharge": recharge_page()
        else: contact_us_page(reason="deactivated")
        return
    st.sidebar.success(f"📅 {days} Days Left")
    if st.sidebar.button("🏠 Home Dashboard"): st.session_state.page = "dashboard"; st.rerun()
    if st.sidebar.button("💳 Recharge"): st.session_state.page = "recharge"; st.rerun()
    if st.sidebar.button("📞 Support"): st.session_state.page = "contact"; st.rerun()
    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
    if st.session_state.page == "recharge": recharge_page(); return
    if st.session_state.page == "contact": contact_us_page(); return

    st.title("🚀 Bihar VLTS Live Sync")
    l_col, r_col = st.columns([2, 1])
    with r_col:
        st.subheader("🏷️ Custom Tag")
        utag = st.text_input("Save My Tag").upper()
        if st.button("Permanent Save"):
            if utag: supabase.table("custom_tags").upsert({"tag_name": utag.strip()}).execute(); st.success("Saved!"); st.rerun()
    with l_col:
        v_no = st.text_input("Vehicle Number").upper()
        i_no = st.text_input("IMEI Number", value=get_vehicle_data(v_no) if v_no else "", max_chars=15)
    
    st.markdown("### 🗺️ Live Vehicle Map Tracking")
    st.map(pd.DataFrame({'lat': [u_info['latitude']], 'lon': [u_info['longitude']]}), height=450)
    st.divider()

    if not st.session_state.running:
        if st.button("🚀 START DATA SYNC", type="primary", use_container_width=True):
            if v_no and i_no:
                try:
                    supabase.table("vehicle_master").upsert({"vehicle_no": v_no.upper(), "imei_no": i_no}, on_conflict="vehicle_no").execute()
                    log_activity(st.session_state.user, v_no, "START")
                    st.session_state.running = True; st.rerun()
                except Exception as e: st.error(f"Sync Failure: {e}")
            else: st.warning("Please provide Vehicle Number and IMEI.")
    else:
        if st.button("🛑 STOP DATA SYNC", use_container_width=True):
            log_activity(st.session_state.user, v_no if v_no else "NA", "STOP")
            st.session_state.running = False; st.rerun()
        status_table = st.empty()
        while st.session_state.running:
            rows, tags = [], get_tags(); dt_p = datetime.now().strftime("%d%m%Y,%H%M%S")
            for t in tags:
                p_s = f"$PVT,{t.upper()},2.1.1,NR,01,L,{i_no},{v_no},1,{dt_p},{u_info['latitude']:.7f},N,{u_info['longitude']:.7f},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                send_packet_thread("vlts.bihar.gov.in", 9999, p_s, rows)
            status_table.table(pd.DataFrame(rows)); time.sleep(1)

def main():
    if not st.session_state.logged_in:
        st.title("🔐 Project Login")
        u, p = st.text_input("User"), st.text_input("Pass", type="password")
        if st.button("Login"):
            res = check_login(u, p)
            if res: st.session_state.update({'logged_in': True, 'user': res['username'], 'role': res['role'], 'u_data': res.get('data')}); st.rerun()
            else: st.error("Login Error.")
    elif st.session_state.role == 'admin': admin_panel()
    else: user_panel()

if __name__ == "__main__": main()
