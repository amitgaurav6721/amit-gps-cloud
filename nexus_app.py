import streamlit as st
import socket
import time
import pandas as pd
import threading
from datetime import datetime, timedelta
from supabase import create_client, Client

# ==========================================================
# --- 1. GLOBAL APP CONFIGURATION & SUPABASE CONNECTION ---
# ==========================================================

# Database credentials for Supabase
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# Payment QR Code Image URL (Permanent Hosting)
QR_URL = "https://i.ibb.co/99P60H1z/Whats-App-Image-2026-03-30-at-23-26-19.jpg"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Page configuration for Streamlit UI
st.set_page_config(
    page_title="Bihar VLTS Pro Max",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INITIALIZE SESSION STATES FOR NAVIGATION & DATA ---
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
# --- 2. CORE DATABASE OPERATIONS (CRUD) ---
# ==========================================================

def get_contact_details():
    """Fetches support phone, email, and UPI ID from contact_settings table"""
    try:
        res = supabase.table("contact_settings").select("*").eq("id", 1).execute()
        if res.data:
            return res.data[0]
        return {"whatsapp_no": "Not Set", "email_id": "Not Set", "upi_id": "admin@upi"}
    except Exception as e:
        return {"whatsapp_no": "Error", "email_id": "Error", "upi_id": "admin@upi"}

def check_login(user, pwd):
    """Authenticates user. Handles both hardcoded Admin and DB Users"""
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
    """Returns all tags. If DB is empty, uses a default list of 22 tags"""
    default_tags = [
        "RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", 
        "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", 
        "MIJO", "EMR", "HB", "HA", "RT", "OS", "IDL", "PWR"
    ]
    try:
        res = supabase.table("custom_tags").select("tag_name").execute()
        if res.data and len(res.data) > 0:
            return [item['tag_name'] for item in res.data]
        return default_tags
    except Exception:
        return default_tags

def log_activity(username, vehicle_no, action):
    """Saves every START/STOP action to activity_logs table for Admin reporting"""
    try:
        payload = {
            "username": username,
            "vehicle_no": str(vehicle_no).upper(),
            "action": action,
            "timestamp": datetime.now().isoformat()
        }
        supabase.table("activity_logs").insert(payload).execute()
    except Exception as e:
        st.sidebar.error(f"Log Error: {e}")

def get_vehicle_data(v_no):
    """Retrieves saved IMEI for a vehicle to speed up user entry"""
    try:
        if v_no:
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no.upper()).execute()
            if res.data:
                return res.data[0]['imei_no']
        return ""
    except Exception:
        return ""

def send_packet_thread(host, port, packet, results, show_tag=False):
    """Main network function to communicate with the Bihar VLTS Government Server"""
    try:
        # Construct the raw hex/string packet with required termination
        raw_data = packet + "\r\n"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.sendall(raw_data.encode('ascii'))
        time.sleep(0.1)
        sock.close()
        
        # Determine display name for the result table
        tag_name = packet.split(',')[1] if show_tag else "📡 GPS Sync"
        results.append({
            "Tag/Packet": tag_name, 
            "Status": "✅ Accepted", 
            "Time": datetime.now().strftime("%H:%M:%S")
        })
    except Exception:
        results.append({
            "Tag/Packet": "Connection", 
            "Status": "❌ Failed", 
            "Time": datetime.now().strftime("%H:%M:%S")
        })

# ==========================================================
# --- 3. ADMINISTRATIVE CONTROL PANEL ---
# ==========================================================

def admin_panel():
    """Full access dashboard for the owner/admin"""
    st.sidebar.title("🛠️ System Administrator")
    
    if st.sidebar.button("Secure Logout"):
        st.session_state.logged_in = False
        st.rerun()
    
    # Tabs for different admin sections
    tab_reports, tab_master, tab_tags, tab_users = st.tabs([
        "📊 Activity Reports", 
        "🚀 Master Injector", 
        "🏷️ Global Tags", 
        "👤 User Management"
    ])
    
    with tab_reports:
        st.subheader("📅 User Activity Tracking")
        search_date = st.date_input("Select Report Date", datetime.now())
        
        # Filter logs by date range
        date_start = f"{search_date}T00:00:00"
        date_end = f"{search_date}T23:59:59"
        
        log_res = supabase.table("activity_logs").select("*").gte("timestamp", date_start).lte("timestamp", date_end).execute()
        
        if log_res.data:
            df_logs = pd.DataFrame(log_res.data)
            st.metric("Total Packets Triggered", len(df_logs))
            st.dataframe(df_logs[['timestamp', 'username', 'vehicle_no', 'action']], use_container_width=True)
        else:
            st.info("No user activity recorded for this specific date.")

    with tab_master:
        st.subheader("🚀 Admin Master Injector (Raw Stream)")
        adm_v = st.text_input("Vehicle Number (Admin)").upper()
        adm_i = st.text_input("IMEI Number (Admin)")
        
        if not st.session_state.admin_running:
            if st.button("🔥 START GLOBAL INJECTION", type="primary", use_container_width=True):
                if adm_v and adm_i:
                    st.session_state.admin_running = True
                    st.rerun()
        else:
            if st.button("🛑 STOP GLOBAL INJECTION", use_container_width=True):
                st.session_state.admin_running = False
                st.rerun()
            
            # Live monitoring area
            monitor_text = st.empty()
            monitor_table = st.empty()
            
            while st.session_state.admin_running:
                results_list = []
                tags_to_use = get_tags()
                current_time_str = datetime.now().strftime("%d%m%Y,%H%M%S")
                
                for t in tags_to_use:
                    # Construct admin master packet
                    p_master = f"$PVT,{t.upper()},2.1.1,NR,01,L,{adm_i},{adm_v},1,{current_time_str},25.5940,N,85.1376,E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                    monitor_text.text_area(f"Streaming Tag: {t}", value=p_master, height=70)
                    send_packet_thread("vlts.bihar.gov.in", 9999, p_master, results_list, True)
                
                monitor_table.table(pd.DataFrame(results_list))
                time.sleep(1)

    with tab_tags:
        st.subheader("🏷️ System-Wide Tag Control")
        new_tag_input = st.text_input("Enter New Tag Name").upper()
        if st.button("➕ Add to System"):
            if new_tag_input:
                supabase.table("custom_tags").upsert({"tag_name": new_tag_input}).execute()
                st.success(f"Tag {new_tag_input} added successfully!")
                st.rerun()
        
        st.divider()
        current_tags = get_tags()
        for tag_item in current_tags:
            col_tag, col_del = st.columns([5, 1])
            col_tag.code(tag_item)
            if col_del.button("❌", key=f"del_{tag_item}"):
                supabase.table("custom_tags").delete().eq("tag_name", tag_item).execute()
                st.rerun()

    with tab_users:
        st.subheader("👤 User Account Controls")
        search_q = st.text_input("Search User by Name or ID")
        if search_q:
            user_list = supabase.table("user_profiles").select("*").ilike("username", f"%{search_q}%").execute()
            for u_row in user_list.data:
                with st.expander(f"User: {u_row['username']} (CID-{1000 + u_row['cid_id']})"):
                    st.write(f"Plan Expiry: {u_row['expiry_date']}")
                    if st.button(f"Extend 28 Days for {u_row['username']}", key=f"ext_{u_row['username']}"):
                        old_exp = datetime.strptime(u_row['expiry_date'], '%Y-%m-%d')
                        new_exp = (max(old_exp, datetime.now()) + timedelta(days=28)).strftime('%Y-%m-%d')
                        supabase.table("user_profiles").update({"expiry_date": new_exp}).eq("username", u_row['username']).execute()
                        st.success("Plan extended!")
                        st.rerun()
# ==========================================================
# --- 4. USER INTERFACE & VEHICLE DASHBOARD ---
# ==========================================================

def user_panel():
    """Main dashboard for Bihar VLTS users"""
    user_info = st.session_state.u_data
    
    # Calculate Remaining Days
    expiry_dt = datetime.strptime(user_info['expiry_date'], '%Y-%m-%d')
    days_left = (expiry_dt - datetime.now()).days + 1
    
    st.sidebar.title(f"👋 Welcome, {st.session_state.user}")
    st.sidebar.info(f"🆔 CID-{1000 + user_info.get('cid_id', 0)}")
    
    # Check for Expired or Inactive Account
    if user_info.get('status') == 'inactive' or days_left <= 0:
        st.sidebar.error("❌ Account Expired or Disabled")
        if st.sidebar.button("💳 Recharge Now", use_container_width=True):
            st.session_state.page = "recharge"
            st.rerun()
        
        # Router for inactive state
        if st.session_state.page == "recharge":
            recharge_page()
        else:
            st.title("🚫 Account Access Restricted")
            st.warning("Aapka account expire ho chuka hai. Kripya recharge karein.")
            st.info("Support ke liye side menu mein Support button ka use karein.")
        return

    # Active User Sidebar Controls
    st.sidebar.success(f"📅 {days_left} Days Remaining")
    
    if st.sidebar.button("🏠 Home Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"
        st.rerun()
    
    if st.sidebar.button("💳 Recharge Plan", use_container_width=True):
        st.session_state.page = "recharge"
        st.rerun()
        
    if st.sidebar.button("📞 Support Center", use_container_width=True):
        st.session_state.page = "contact"
        st.rerun()

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    # Page Routing
    if st.session_state.page == "recharge":
        recharge_page()
        return
    elif st.session_state.page == "contact":
        contact_us_page()
        return

    # --- MAIN INJECTOR DASHBOARD ---
    st.title("🚀 Bihar VLTS Live Injector")
    
    col_input_left, col_input_right = st.columns([2, 1])
    
    with col_input_right:
        st.subheader("🏷️ Custom Tag")
        tag_user_input = st.text_input("Enter New Tag (ex: TEST)").upper()
        if st.button("Save Tag Permanently"):
            if tag_user_input:
                supabase.table("custom_tags").upsert({"tag_name": tag_user_input.strip()}).execute()
                st.success(f"Tag {tag_user_input} saved to database!")
                time.sleep(0.5)
                st.rerun()
    
    with col_input_left:
        # VEHICLE NUMBER (Auto-Capitalized)
        v_num = st.text_input("Vehicle Number (Bihar)", placeholder="BR01...").upper()
        
        # IMEI NUMBER (Fetch automatically if exists)
        imei_saved = get_vehicle_data(v_num) if v_num else ""
        i_num = st.text_input("IMEI Number (15 Digits)", value=imei_saved, max_chars=15)

    # --- LIVE MAP SECTION ---
    st.markdown("### 🗺️ Live Vehicle Tracking")
    location_data = pd.DataFrame({
        'lat': [user_info['latitude']], 
        'lon': [user_info['longitude']]
    })
    st.map(location_data, height=450)
    
    st.divider()

    # --- PROCESS EXECUTION CONTROL ---
    if not st.session_state.running:
        if st.button("🚀 START DATA SYNC", type="primary", use_container_width=True):
            if v_num and i_num:
                try:
                    # FIX: Save Vehicle and IMEI to Master Table
                    payload_master = {"vehicle_no": v_num.upper(), "imei_no": i_num}
                    supabase.table("vehicle_master").upsert(payload_master, on_conflict="vehicle_no").execute()
                    
                    # FIX: Log the START activity
                    log_activity(st.session_state.user, v_num, "START")
                    
                    st.session_state.running = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Database Sync Error: {e}")
            else:
                st.warning("Kripya Vehicle Number aur IMEI sahi se bharein.")
    else:
        if st.button("🛑 STOP DATA SYNC", use_container_width=True):
            # FIX: Log the STOP activity
            log_activity(st.session_state.user, v_num if v_num else "Unknown", "STOP")
            st.session_state.running = False
            st.rerun()
        
        # Display Live Result Table
        live_status_area = st.empty()
        
        while st.session_state.running:
            res_table_data = []
            available_tags = get_tags()
            dt_now = datetime.now().strftime("%d%m%Y,%H%M%S")
            
            for tag in available_tags:
                # Construct official government packet
                packet_str = f"$PVT,{tag.upper()},2.1.1,NR,01,L,{i_num},{v_num},1,{dt_now},{user_info['latitude']:.7f},N,{user_info['longitude']:.7f},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                send_packet_thread("vlts.bihar.gov.in", 9999, packet_str, res_table_data)
            
            live_status_area.table(pd.DataFrame(res_table_data))
            time.sleep(1)

# ==========================================================
# --- 5. SUPPORT & RECHARGE PAGES (FULL DEFINITION) ---
# ==========================================================

def contact_us_page():
    contact = get_contact_details()
    st.title("📞 Customer Support")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**WhatsApp:** {contact.get('whatsapp_no')}")
        st.write(f"**Email:** {contact.get('email_id')}")
    with c2:
        st.write(f"**Timings:** {contact.get('support_time', '10 AM - 6 PM')}")
        st.code(f"CID: {1000 + st.session_state.u_data.get('cid_id', 0)}")
    if st.button("Back"):
        st.session_state.page = "dashboard"; st.rerun()

def recharge_page():
    contact = get_contact_details()
    st.title("💳 Recharge Panel")
    u_data = st.session_state.u_data
    st.image(QR_URL, width=240)
    st.info(f"Pay to: {contact.get('upi_id')}")
    utr = st.text_input("Enter UTR Number")
    if st.button("Submit"):
        if utr:
            st.success("Recharge request sent!")
            time.sleep(2)
            st.session_state.page = "dashboard"; st.rerun()

# ==========================================================
# --- 6. MAIN APPLICATION ENTRY POINT ---
# ==========================================================

def main():
    if not st.session_state.logged_in:
        st.title("🔐 Secure Login")
        u_input = st.text_input("Username")
        p_input = st.text_input("Password", type="password")
        if st.button("Login"):
            login_res = check_login(u_input, p_input)
            if login_res:
                st.session_state.update({
                    'logged_in': True,
                    'user': login_res['username'],
                    'role': login_res['role'],
                    'u_data': login_res.get('data')
                })
                st.rerun()
            else:
                st.error("Invalid credentials.")
    elif st.session_state.role == 'admin':
        admin_panel()
    else:
        user_panel()

if __name__ == "__main__":
    main()
