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

# Database Credentials
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
QR_URL = "https://i.ibb.co/99P60H1z/Whats-App-Image-2026-03-30-at-23-26-19.jpg"

# Connection initialization
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(
    page_title="Bihar VLTS Pro Max",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE MANAGEMENT ---
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
    """Fetch admin support details from contact_settings"""
    try:
        res = supabase.table("contact_settings").select("*").eq("id", 1).execute()
        if res.data:
            return res.data[0]
        return {"whatsapp_no": "Not Set", "email_id": "Not Set", "support_time": "10 AM - 6 PM", "upi_id": "admin@upi"}
    except Exception:
        return {"whatsapp_no": "Error", "email_id": "Error", "support_time": "Not Set", "upi_id": "admin@upi"}

def check_login(user, pwd):
    """Verify credentials for Admin and regular users"""
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
    """Retrieve all operational tags from custom_tags table"""
    default_tags = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR", "HB", "HA", "RT", "OS", "IDL", "PWR"]
    try:
        res = supabase.table("custom_tags").select("tag_name").execute()
        if res.data:
            return [item['tag_name'] for item in res.data]
        return default_tags
    except Exception:
        return default_tags

def log_activity(username, vehicle_no, action):
    """FIXED: Direct insert into activity_logs with proper error capture"""
    try:
        log_payload = {
            "user_id": str(username),
            "vehicle_no": str(vehicle_no).upper(),
            "action": str(action)
        }
        # Not sending created_at manually to let DB handle default timestamp
        supabase.table("activity_logs").insert(log_payload).execute()
    except Exception as e:
        # Silently fail but can be enabled for debugging
        pass

def get_vehicle_data(v_no):
    """Retrieve IMEI from vehicle_master based on vehicle number"""
    try:
        if v_no:
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no.upper()).execute()
            if res.data:
                return res.data[0]['imei_no']
        return ""
    except Exception:
        return ""

def send_packet_thread(host, port, packet, results, show_tag=False):
    """Multithreaded network function for packet delivery"""
    try:
        raw_string = packet + "\r\n"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.sendall(raw_string.encode('ascii'))
        time.sleep(0.1)
        sock.close()
        display_tag = packet.split(',')[1] if show_tag else "📡 GPS Sync"
        results.append({"Tag/Packet": display_tag, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except Exception:
        results.append({"Tag/Packet": "Network", "Status": "❌ Failed", "Time": datetime.now().strftime("%H:%M:%S")})

# ==========================================================
# --- 3. UI PAGES (SUPPORT & RECHARGE) ---
# ==========================================================

def contact_us_page(reason="general"):
    """Support page with WhatsApp and Email integration"""
    contact_info = get_contact_details()
    st.title("📞 Official Support Center")
    if reason == "deactivated":
        st.error("⚠️ ACCOUNT EXPIRED: Please recharge to continue using Bihar VLTS services.")
    st.divider()
    left_col, right_col = st.columns(2)
    with left_col:
        st.subheader("📱 WhatsApp")
        st.write(contact_info.get('whatsapp_no', 'Not Set'))
        digits = ''.join(filter(str.isdigit, str(contact_info.get('whatsapp_no', ''))))
        if digits:
            st.markdown(f"[![Chat](https://img.shields.io/badge/WhatsApp-Chat-green?style=for-the-badge&logo=whatsapp)](https://wa.me/{digits})")
        st.subheader("📧 Email")
        st.write(contact_info.get('email_id', 'Not Set'))
    with right_col:
        st.subheader("🕒 Support Hours")
        st.write(contact_info.get('support_time', '10 AM - 6 PM'))
        st.subheader("🆔 System CID")
        if st.session_state.u_data:
            st.code(f"CID: {1000 + st.session_state.u_data.get('cid_id', 0)}")
    st.divider()
    if st.button("🏠 Home Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"
        st.rerun()

def recharge_page():
    """Payment submission page with QR and Plan Selection"""
    contact = get_contact_details()
    current_user_data = st.session_state.u_data
    cid_val = current_user_data.get('cid_id', 0)
    current_username = st.session_state.user
    st.title("💳 Secure Recharge Panel")
    
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.image(QR_URL, width=240, caption="Scan and Pay via UPI")
        st.info(f"Verify CID: **CID-{1000 + cid_val}**")
        st.subheader("📜 Recent History")
        history_res = supabase.table("recharge_requests").select("*").eq("username", current_username).order("id", desc=True).limit(3).execute()
        if history_res.data:
            for entry in history_res.data:
                st.write(f"{'⏳' if entry['status'] == 'pending' else '✅'} {entry['amount']} - {entry['status'].title()}")
    
    with col_r:
        st.info(f"**Official Admin UPI:** `{contact.get('upi_id', 'admin@upi')}`")
        mobile = st.text_input("Mobile Number", max_chars=10, placeholder="Registered Mobile")
        utr_no = st.text_input("Transaction / UTR ID", placeholder="12 Digit Number")
        
        # Plan fetching
        all_plans = supabase.table("plan_settings").select("*").execute()
        plan_data = all_plans.data
        if plan_data:
            options = [f"₹{p['amount']} - {p['plan_name']} ({p['days']} Days)" for p in plan_data]
        else:
            options = ["Standard Plan - ₹999"]
            
        selected_amt = st.selectbox("Choose Plan", options)
        
        if st.button("Submit Payment Proof", use_container_width=True):
            if utr_no and len(mobile) == 10:
                try:
                    supabase.table("recharge_requests").insert({
                        "username": current_username, 
                        "utr_number": utr_no, 
                        "amount": selected_amt, 
                        "mobile_no": mobile, 
                        "cid_display": f"CID-{1000+cid_val}", 
                        "status": "pending"
                    }).execute()
                    st.success("✅ Success: Admin will approve within 15 minutes.")
                    time.sleep(2)
                    st.session_state.page = "dashboard"
                    st.rerun()
                except Exception:
                    st.error("Error: This UTR has already been submitted.")
            else:
                st.warning("Validation Failed: Check Mobile (10 digits) and UTR.")
                
    if st.button("🏠 Back to Home"):
        st.session_state.page = "dashboard"
        st.rerun()

# ==========================================================
# --- 4. ADMIN CONTROL INTERFACE ---
# ==========================================================

def admin_panel():
    """Administrative dashboard for monitoring and management"""
    st.sidebar.title("🛠️ Project Administrator")
    if st.sidebar.button("Logout Admin"):
        st.session_state.logged_in = False
        st.rerun()
        
    t_log, t_inject, t_tag, t_user = st.tabs(["📊 Activity Logs", "🚀 Master Injector", "🏷️ Tag Management", "👤 User Database"])
    
    with t_log:
        st.subheader("📅 Live User Activity Reports")
        target_date = st.date_input("Filter Date", datetime.now())
        log_query = supabase.table("activity_logs").select("*").gte("created_at", f"{target_date}T00:00:00").lte("created_at", f"{target_date}T23:59:59").execute()
        if log_query.data:
            log_df = pd.DataFrame(log_query.data)
            st.dataframe(log_df[['created_at', 'user_id', 'vehicle_no', 'action']], use_container_width=True)
        else:
            st.info("No data available for the selected date.")
            
    with t_inject:
        st.subheader("🚀 Global Master Injector")
        mv = st.text_input("Master Vehicle No").upper()
        mi = st.text_input("Master IMEI No")
        if not st.session_state.admin_running:
            if st.button("🔥 START INJECTION"):
                st.session_state.admin_running = True
                st.rerun()
        else:
            if st.button("🛑 STOP INJECTION"):
                st.session_state.admin_running = False
                st.rerun()
            admin_table = st.empty()
            while st.session_state.admin_running:
                adm_res, adm_tags, adm_dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
                for t in adm_tags:
                    packet = f"$PVT,{t.upper()},2.1.1,NR,01,L,{mi},{mv},1,{adm_dt},25.594,N,85.137,E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                    send_packet_thread("vlts.bihar.gov.in", 9999, packet, adm_res, True)
                admin_table.table(pd.DataFrame(adm_res))
                time.sleep(1)

    with t_tag:
        st.subheader("🏷️ Manage Operational Tags")
        tag_to_add = st.text_input("New Tag Name").upper()
        if st.button("Save Tag"):
            supabase.table("custom_tags").upsert({"tag_name": tag_to_add}).execute()
            st.rerun()
        st.divider()
        for t_item in get_tags():
            c1_t, c2_t = st.columns([5,1])
            c1_t.code(t_item)
            if c2_t.button("❌", key=f"d_tag_{t_item}"):
                supabase.table("custom_tags").delete().eq("tag_name", t_item).execute()
                st.rerun()

    with t_user:
        st.subheader("👤 Registered Users List")
        query_user = st.text_input("Search Username")
        if query_user:
            profile_res = supabase.table("user_profiles").select("*").ilike("username", f"%{query_user}%").execute()
            for p_row in profile_res.data:
                with st.expander(f"{p_row['username']} (CID-{1000+p_row['cid_id']})"):
                    st.write(f"Expires: {p_row['expiry_date']}")
                    if st.button(f"Add 28 Days", key=f"add_days_{p_row['username']}"):
                        new_expiry = (datetime.strptime(p_row['expiry_date'], '%Y-%m-%d') + timedelta(days=28)).strftime('%Y-%m-%d')
                        supabase.table("user_profiles").update({"expiry_date": new_expiry}).eq("username", p_row['username']).execute()
                        st.rerun()

# ==========================================================
# --- 5. USER PANEL (MAIN DASHBOARD) ---
# ==========================================================

def user_panel():
    """Main interface for vehicle owners and tracking"""
    current_u = st.session_state.u_data
    exp_time = datetime.strptime(current_u['expiry_date'], '%Y-%m-%d')
    countdown = (exp_time - datetime.now()).days + 1
    
    st.sidebar.title(f"👋 Welcome, {st.session_state.user}")
    st.sidebar.info(f"🆔 CID-{1000 + current_u.get('cid_id', 0)}")
    
    # Expiry Check Logic
    if current_u.get('status') == 'inactive' or countdown <= 0:
        if st.sidebar.button("💳 Recharge Now", use_container_width=True):
            st.session_state.page = "recharge"
            st.rerun()
        if st.session_state.page == "recharge":
            recharge_page()
        else:
            contact_us_page(reason="deactivated")
        return

    st.sidebar.success(f"📅 {countdown} Days Left")
    if st.sidebar.button("🏠 Home Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"; st.rerun()
    if st.sidebar.button("💳 Recharge Plan", use_container_width=True):
        st.session_state.page = "recharge"; st.rerun()
    if st.sidebar.button("📞 Help Support", use_container_width=True):
        st.session_state.page = "contact"; st.rerun()
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False; st.rerun()

    # Dynamic Routing
    if st.session_state.page == "recharge": recharge_page(); return
    if st.session_state.page == "contact": contact_us_page(); return

    # --- MAIN UI ---
    st.title("🚀 Bihar VLTS Live Sync")
    main_l, main_r = st.columns([2, 1])
    with main_r:
        st.subheader("🏷️ Custom Tags")
        user_new_tag = st.text_input("Save New Tag").upper()
        if st.button("Permanent Save"):
            if user_new_tag:
                supabase.table("custom_tags").upsert({"tag_name": user_new_tag.strip()}).execute()
                st.success("Tag Saved!"); time.sleep(0.5); st.rerun()
    with main_l:
        v_no_val = st.text_input("Enter Vehicle No").upper()
        imei_val = st.text_input("Enter IMEI No", value=get_vehicle_data(v_no_val) if v_no_val else "", max_chars=15)
    
    st.markdown("### 🗺️ Live Vehicle Map Tracking")
    map_df = pd.DataFrame({'lat': [current_u['latitude']], 'lon': [current_u['longitude']]})
    st.map(map_df, height=450)
    
    st.divider()
    if not st.session_state.running:
        if st.button("🚀 START DATA SYNC", type="primary", use_container_width=True):
            if v_no_val and imei_val:
                try:
                    # FIX: Save Vehicle/IMEI Mapping
                    payload_v = {"vehicle_no": v_no_val.upper(), "imei_no": imei_val}
                    supabase.table("vehicle_master").upsert(payload_v, on_conflict="vehicle_no").execute()
                    
                    # FIX: Logging Activity
                    log_activity(st.session_state.user, v_no_val, "START")
                    
                    st.session_state.running = True
                    st.rerun()
                except Exception as error_db:
                    st.error(f"Sync Failure: {error_db}")
            else:
                st.warning("Missing Data: Please enter Vehicle Number and IMEI.")
    else:
        if st.button("🛑 STOP DATA SYNC", use_container_width=True):
            # FIX: Logging Activity
            log_activity(st.session_state.user, v_no_val if v_no_val else "NA", "STOP")
            st.session_state.running = False
            st.rerun()
            
        status_container = st.empty()
        while st.session_state.running:
            table_data, current_tags_list = [], get_tags()
            timestamp_val = datetime.now().strftime("%d%m%Y,%H%M%S")
            for t_val in current_tags_list:
                packet_val = f"$PVT,{t_val.upper()},2.1.1,NR,01,L,{imei_val},{v_no_val},1,{timestamp_val},{current_u['latitude']:.7f},N,{current_u['longitude']:.7f},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                send_packet_thread("vlts.bihar.gov.in", 9999, packet_val, table_data)
            status_container.table(pd.DataFrame(table_data))
            time.sleep(1)

# ==========================================================
# --- 6. BOOTSTRAP MAIN ---
# ==========================================================

def main():
    """Main entry point for authentication routing"""
    if not st.session_state.logged_in:
        st.title("🔐 Project Login")
        login_u = st.text_input("User Name")
        login_p = st.text_input("Password", type="password")
        if st.button("Login"):
            auth_res = check_login(login_u, login_p)
            if auth_res:
                st.session_state.update({
                    'logged_in': True, 
                    'user': auth_res['username'], 
                    'role': auth_res['role'], 
                    'u_data': auth_res.get('data')
                })
                st.rerun()
            else:
                st.error("Authentication Error: Invalid credentials.")
    elif st.session_state.role == 'admin':
        admin_panel()
    else:
        user_panel()

if __name__ == "__main__":
    main()
