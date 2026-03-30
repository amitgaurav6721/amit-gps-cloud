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

# Supabase Project Credentials
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# Permanent QR Code URL for Recharge
QR_URL = "https://i.ibb.co/99P60H1z/Whats-App-Image-2026-03-30-at-23-26-19.jpg"

# Initialize Supabase Connection
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Streamlit Page Setup
st.set_page_config(
    page_title="Bihar VLTS Pro Max",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INITIALIZE SESSION STATES ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.page = "dashboard"
    st.session_state.u_data = None

if 'running' not in st.session_state:
    st.session_state.running = False

if 'admin_running' not in st.session_state:
    st.session_state.admin_running = False

# ==========================================================
# --- 2. CORE DATABASE FUNCTIONS ---
# ==========================================================

def get_contact_details():
    """Fetches support number, email, and UPI from the database"""
    try:
        res = supabase.table("contact_settings").select("*").eq("id", 1).execute()
        if res.data:
            return res.data[0]
        else:
            return {
                "whatsapp_no": "Not Set",
                "email_id": "Not Set",
                "support_time": "10 AM - 6 PM",
                "upi_id": "admin@upi"
            }
    except Exception:
        return {"whatsapp_no": "Error", "email_id": "Error", "support_time": "Error"}

def check_login(user, pwd):
    """Verifies credentials for both Admin and regular Users"""
    if user == "admin" and pwd == "admin77": 
        return {"username": "admin", "role": "admin"}
    try:
        res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
        if res.data:
            return {
                "username": res.data[0]['username'], 
                "role": "user", 
                "data": res.data[0]
            }
        else:
            return None
    except Exception:
        return None

def get_tags():
    """Loads all system tags. Returns default list if table is empty"""
    default_req = [
        "RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", 
        "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", 
        "MIJO", "EMR", "HB", "HA", "RT", "OS", "IDL", "PWR"
    ]
    try:
        res = supabase.table("custom_tags").select("tag_name").execute()
        if res.data:
            return [item['tag_name'] for item in res.data]
        else:
            return default_req
    except Exception:
        return default_req

def log_activity(username, vehicle_no, action):
    """Saves START/STOP actions to activity_logs with FIXED column names"""
    try:
        # Match Supabase columns: user_id, vehicle_no, action
        # Database handles 'created_at' automatically
        log_payload = {
            "user_id": str(username),
            "vehicle_no": str(vehicle_no).upper(),
            "action": str(action)
        }
        supabase.table("activity_logs").insert(log_payload).execute()
    except Exception as e:
        # Silently fail for user, but captures error for sync
        pass

def get_vehicle_data(v_no):
    """Fetches saved IMEI number for a specific vehicle from the master table"""
    try:
        if v_no:
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no.upper()).execute()
            if res.data:
                return res.data[0]['imei_no']
        return ""
    except Exception:
        return ""

def send_packet_thread(host, port, packet, results, show_tag=False):
    """Handles TCP connection and data delivery to VLTS server"""
    try:
        # Adding required carriage return
        raw_packet = packet + "\r\n"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.sendall(raw_packet.encode('ascii'))
        time.sleep(0.1)
        sock.close()
        
        tag_disp = packet.split(',')[1] if show_tag else "📡 GPS Sync"
        results.append({
            "Tag/Packet": tag_disp, 
            "Status": "✅ Accepted", 
            "Time": datetime.now().strftime("%H:%M:%S")
        })
    except Exception:
        results.append({
            "Tag/Packet": "Network", 
            "Status": "❌ Failed", 
            "Time": datetime.now().strftime("%H:%M:%S")
        })

# ==========================================================
# --- 3. NAVIGATION PAGES (SUPPORT & RECHARGE) ---
# ==========================================================

def contact_us_page(reason="general"):
    """Support page showing WhatsApp, Email and CID details"""
    contact = get_contact_details()
    st.title("📞 Official Customer Support")
    
    if reason == "deactivated":
        st.error("⚠️ ACCOUNT INACTIVE: Your plan has expired. Please recharge to continue.")
    
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📱 WhatsApp Support")
        st.write(contact.get('whatsapp_no', 'Not Set'))
        # Generate clickable WhatsApp link
        clean_no = ''.join(filter(str.isdigit, str(contact.get('whatsapp_no', ''))))
        if clean_no:
            st.markdown(f"[![Chat](https://img.shields.io/badge/WhatsApp-Chat-green?style=for-the-badge&logo=whatsapp)](https://wa.me/{clean_no})")
        
        st.subheader("📧 Email Support")
        st.write(contact.get('email_id', 'Not Set'))
    
    with c2:
        st.subheader("🕒 Support Hours")
        st.write(contact.get('support_time', '10 AM - 6 PM'))
        
        st.subheader("🆔 Your Customer ID")
        if st.session_state.u_data:
            st.code(f"CID: {1000 + st.session_state.u_data.get('cid_id', 0)}")
            
    st.divider()
    if st.button("🏠 Back to Home Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"
        st.rerun()

def recharge_page():
    """Payment page with QR code and plan selection"""
    contact = get_contact_details()
    u_data = st.session_state.u_data
    cid = u_data.get('cid_id', 0)
    user_id = st.session_state.user
    
    st.title("💳 Secure Recharge Panel")
    
    col_qr, col_pay = st.columns([1, 2])
    
    with col_qr:
        st.image(QR_URL, width=240, caption="Scan QR to Pay via UPI")
        st.info(f"Verify ID: **CID-{1000 + cid}**")
        
        st.subheader("📜 Recent History")
        hist = supabase.table("recharge_requests").select("*").eq("username", user_id).order("id", desc=True).limit(3).execute()
        if hist.data:
            for entry in hist.data:
                st.write(f"{'⏳' if entry['status'] == 'pending' else '✅'} {entry['amount']} - {entry['status'].title()}")
    
    with col_pay:
        st.info(f"**Admin UPI ID:** `{contact.get('upi_id', 'admin@upi')}`")
        mob = st.text_input("Mobile No", max_chars=10, placeholder="Registered Mobile")
        utr_id = st.text_input("UTR / Transaction ID", placeholder="12 Digit Number")
        
        # Load Plans
        p_res = supabase.table("plan_settings").select("*").execute()
        plans_list = p_res.data
        if plans_list:
            options = [f"₹{p['amount']} - {p['plan_name']} ({p['days']} Days)" for p in plans_list]
        else:
            options = ["Standard Plan - ₹999"]
            
        amt_sel = st.selectbox("Select Plan", options)
        
        if st.button("Submit Payment Proof", use_container_width=True):
            if utr_id and len(mob) == 10:
                try:
                    supabase.table("recharge_requests").insert({
                        "username": user_id, 
                        "utr_number": utr_id, 
                        "amount": amt_sel, 
                        "mobile_no": mob, 
                        "cid_display": f"CID-{1000+cid}", 
                        "status": "pending"
                    }).execute()
                    st.success("✅ Success: Admin will approve your request soon.")
                    time.sleep(2)
                    st.session_state.page = "dashboard"
                    st.rerun()
                except Exception:
                    st.error("Error: This Transaction ID is already submitted.")
            else:
                st.warning("Check: Mobile (10 digits) and UTR (Required).")
                
    if st.button("🏠 Back to Home"):
        st.session_state.page = "dashboard"
        st.rerun()

# ==========================================================
# --- 4. ADMIN CONTROL PANEL ---
# ==========================================================

def admin_panel():
    """Admin dashboard for managing tags, users and viewing logs"""
    st.sidebar.title("🛠️ System Admin")
    
    if st.sidebar.button("Logout Admin"):
        st.session_state.logged_in = False
        st.rerun()
        
    t1, t2, t3, t4 = st.tabs(["📊 Activity Logs", "🚀 Master", "🏷️ Tags", "👤 Users"])
    
    with t1:
        st.subheader("📅 Live User Activity Reports")
        d_input = st.date_input("Filter Date", datetime.now())
        q_log = supabase.table("activity_logs").select("*").gte("created_at", f"{d_input}T00:00:00").lte("created_at", f"{d_input}T23:59:59").execute()
        if q_log.data:
            df_log = pd.DataFrame(q_log.data)
            st.dataframe(df_log[['created_at', 'user_id', 'vehicle_no', 'action']], use_container_width=True)
        else:
            st.info("No activity logs found for this date.")
            
    with t2:
        st.subheader("🚀 Admin Master Injector")
        v_adm = st.text_input("V-No (Admin)").upper()
        i_adm = st.text_input("IMEI (Admin)")
        
        if not st.session_state.admin_running:
            if st.button("🔥 START MASTER"):
                st.session_state.admin_running = True
                st.rerun()
        else:
            if st.button("🛑 STOP MASTER"):
                st.session_state.admin_running = False
                st.rerun()
            
            adm_table = st.empty()
            while st.session_state.admin_running:
                res_adm, tags_adm, dt_adm = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
                for t_item in tags_adm:
                    p_adm = f"$PVT,{t_item.upper()},2.1.1,NR,01,L,{i_adm},{v_adm},1,{dt_adm},25.594,N,85.137,E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                    send_packet_thread("vlts.bihar.gov.in", 9999, p_adm, res_adm, True)
                adm_table.table(pd.DataFrame(res_adm))
                time.sleep(1)

    with t3:
        st.subheader("🏷️ Manage Operational Tags")
        new_tag = st.text_input("New Tag Name").upper()
        if st.button("Add to Database"):
            if new_tag:
                supabase.table("custom_tags").upsert({"tag_name": new_tag}).execute()
                st.rerun()
        st.divider()
        for tag in get_tags():
            col_t, col_d = st.columns([5,1])
            col_t.code(tag)
            if col_d.button("❌", key=f"del_tag_{tag}"):
                supabase.table("custom_tags").delete().eq("tag_name", tag).execute()
                st.rerun()

    with t4:
        st.subheader("👤 User Account Management")
        s_user = st.text_input("Search Username")
        if s_user:
            u_query = supabase.table("user_profiles").select("*").ilike("username", f"%{s_user}%").execute()
            for u_row in u_query.data:
                with st.expander(f"{u_row['username']} (CID-{1000+u_row['cid_id']})"):
                    st.write(f"Expiry: {u_row['expiry_date']}")
                    if st.button(f"Extend Plan 28 Days", key=f"ext_{u_row['username']}"):
                        current_exp = datetime.strptime(u_row['expiry_date'], '%Y-%m-%d')
                        new_expiry = (max(current_exp, datetime.now()) + timedelta(days=28)).strftime('%Y-%m-%d')
                        supabase.table("user_profiles").update({"expiry_date": new_expiry}).eq("username", u_row['username']).execute()
                        st.rerun()

# ==========================================================
# --- 5. USER PANEL (MAIN DASHBOARD) ---
# ==========================================================

def user_panel():
    """Main interface for vehicle owners and sync operations"""
    u_info = st.session_state.u_data
    expiry_date = datetime.strptime(u_info['expiry_date'], '%Y-%m-%d')
    days_left = (expiry_date - datetime.now()).days + 1
    
    st.sidebar.title(f"👋 Welcome, {st.session_state.user}")
    st.sidebar.info(f"🆔 CID-{1000 + u_info.get('cid_id', 0)}")
    
    # Expiry Check
    if u_info.get('status') == 'inactive' or days_left <= 0:
        if st.sidebar.button("💳 Recharge Now", use_container_width=True):
            st.session_state.page = "recharge"
            st.rerun()
        if st.session_state.page == "recharge":
            recharge_page()
        else:
            contact_us_page(reason="deactivated")
        return

    # Active Sidebar
    st.sidebar.success(f"📅 {days_left} Days Remaining")
    
    if st.sidebar.button("🏠 Home Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"; st.rerun()
    if st.sidebar.button("💳 Recharge Plan", use_container_width=True):
        st.session_state.page = "recharge"; st.rerun()
    if st.sidebar.button("📞 Support Center", use_container_width=True):
        st.session_state.page = "contact"; st.rerun()
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False; st.rerun()

    # Routing
    if st.session_state.page == "recharge": recharge_page(); return
    if st.session_state.page == "contact": contact_us_page(); return

    # --- LIVE SYNC INTERFACE ---
    st.title("🚀 Bihar VLTS Live Sync")
    
    col_l, col_r = st.columns([2, 1])
    
    with col_r:
        st.subheader("🏷️ Custom Tags")
        u_new_tag = st.text_input("Save My Tag").upper()
        if st.button("Permanent Save"):
            if u_new_tag:
                supabase.table("custom_tags").upsert({"tag_name": u_new_tag.strip()}).execute()
                st.success("Tag Saved!"); time.sleep(0.5); st.rerun()
    
    with col_l:
        vehicle_no = st.text_input("Enter Vehicle Number (Auto-Cap)").upper()
        # Auto IMEI Fetch
        imei_saved = get_vehicle_data(vehicle_no) if vehicle_no else ""
        imei_no = st.text_input("Enter IMEI (15 Digits)", value=imei_saved, max_chars=15)
    
    st.markdown("### 🗺️ Live Vehicle Map Tracking")
    map_data = pd.DataFrame({'lat': [u_info['latitude']], 'lon': [u_info['longitude']]})
    st.map(map_data, height=450)
    
    st.divider()
    
    if not st.session_state.running:
        if st.button("🚀 START DATA SYNC", type="primary", use_container_width=True):
            if vehicle_no and imei_no:
                try:
                    # Save to Master Table
                    v_payload = {"vehicle_no": vehicle_no.upper(), "imei_no": imei_no}
                    supabase.table("vehicle_master").upsert(v_payload, on_conflict="vehicle_no").execute()
                    
                    # Log START Activity
                    log_activity(st.session_state.user, vehicle_no, "START")
                    
                    st.session_state.running = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Sync Failure: {e}")
            else:
                st.warning("Error: Please provide Vehicle Number and IMEI.")
    else:
        if st.button("🛑 STOP DATA SYNC", use_container_width=True):
            # Log STOP Activity
            log_activity(st.session_state.user, vehicle_no if vehicle_no else "NA", "STOP")
            st.session_state.running = False
            st.rerun()
            
        status_table = st.empty()
        while st.session_state.running:
            res_rows, sys_tags = [], get_tags()
            dt_packet = datetime.now().strftime("%d%m%Y,%H%M%S")
            
            for t in sys_tags:
                packet_str = f"$PVT,{t.upper()},2.1.1,NR,01,L,{imei_no},{vehicle_no},1,{dt_packet},{u_info['latitude']:.7f},N,{u_info['longitude']:.7f},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                send_packet_thread("vlts.bihar.gov.in", 9999, packet_str, res_rows)
            
            status_table.table(pd.DataFrame(res_rows))
            time.sleep(1)

# ==========================================================
# --- 6. MAIN EXECUTION ROUTER ---
# ==========================================================

def main():
    if not st.session_state.logged_in:
        st.title("🔐 Secure System Login")
        u_in = st.text_input("User Name")
        p_in = st.text_input("Password", type="password")
        if st.button("Login"):
            res = check_login(u_in, p_in)
            if res:
                st.session_state.update({
                    'logged_in': True, 
                    'user': res['username'], 
                    'role': res['role'], 
                    'u_data': res.get('data')
                })
                st.rerun()
            else:
                st.error("Login Error: Please check your Username and Password.")
    elif st.session_state.role == 'admin':
        admin_panel()
    else:
        user_panel()

if __name__ == "__main__":
    main()
