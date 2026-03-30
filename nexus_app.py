import streamlit as st
import socket
import time
import pandas as pd
import threading
from datetime import datetime, timedelta
from supabase import create_client, Client

# ==========================================
# --- APP CONFIGURATION & DATABASE SETUP ---
# ==========================================

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
QR_URL = "https://i.ibb.co/99P60H1z/Whats-App-Image-2026-03-30-at-23-26-19.jpg"

# Initialize Database Connection
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Set UI Layout
st.set_page_config(page_title="Bihar VLTS Pro Max", layout="wide")

# ==========================================
# --- SESSION STATE MANAGEMENT ---
# ==========================================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.page = "dashboard"

if 'running' not in st.session_state:
    st.session_state.running = False

if 'admin_running' not in st.session_state:
    st.session_state.admin_running = False

# ==========================================
# --- CORE DATABASE FUNCTIONS ---
# ==========================================

def get_contact_details():
    """Fetch global support settings from DB"""
    try:
        res = supabase.table("contact_settings").select("*").eq("id", 1).execute()
        if res.data:
            return res.data[0]
        return {"whatsapp_no": "Not Set", "email_id": "Not Set", "support_time": "Not Set", "upi_id": "Not Set"}
    except Exception:
        return {"whatsapp_no": "Not Set", "email_id": "Not Set", "support_time": "Not Set", "upi_id": "Not Set"}

def check_login(user, pwd):
    """Authenticate user or admin"""
    if user == "admin" and pwd == "admin77": 
        return {"username": "admin", "role": "admin"}
    try:
        res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
        if res.data:
            return {"username": res.data[0]['username'], "role": "user", "data": res.data[0]}
    except Exception:
        return None
    return None

def get_plans():
    """Load recharge plans for dropdowns"""
    try:
        res = supabase.table("plan_settings").select("*").execute()
        return res.data
    except Exception:
        return []

def get_tags():
    """Load tags from DB and capitalization is enforced"""
    required_tags = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR", "HB", "HA", "RT", "OS", "IDL", "PWR"]
    try:
        res = supabase.table("custom_tags").select("tag_name").execute()
        existing = [item['tag_name'] for item in res.data]
        missing = [t for t in required_tags if t not in existing]
        if missing:
            for t in missing:
                supabase.table("custom_tags").upsert({"tag_name": t.upper()}).execute()
            res = supabase.table("custom_tags").select("tag_name").execute()
            return [item['tag_name'] for item in res.data]
        return existing
    except Exception:
        return required_tags

def add_new_tag(new_tag):
    """Add a new custom tag to permanent database in CAPITAL LETTERS"""
    if new_tag:
        try:
            clean_tag = str(new_tag).upper().strip()
            supabase.table("custom_tags").upsert({"tag_name": clean_tag}).execute()
            return True
        except Exception:
            return False
    return False

def delete_tag(tag_name):
    """Delete a tag from system"""
    try:
        supabase.table("custom_tags").delete().eq("tag_name", tag_name).execute()
    except Exception:
        pass

def get_vehicle_data(v_no):
    """Fetch IMEI based on vehicle number input"""
    try:
        if v_no:
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no.upper()).execute()
            if res.data:
                return res.data[0]['imei_no']
    except Exception:
        return ""
    return ""

# ==========================================
# --- NETWORK COMMUNICATION LOGIC ---
# ==========================================

def send_packet_thread(host, port, packet, results_list, show_tag=False):
    """Core function to send hex/string packets to server"""
    try:
        # Enforce line termination for VLTS servers
        final_to_send = packet + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5)
        s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        time.sleep(0.1)
        s.close()
        # Extract tag name from packet string for status display
        try:
            tag_disp = packet.split(',')[1] if show_tag else "📡 Syncing..."
        except:
            tag_disp = "📡 Packet"
        results_list.append({"Tag/Signal": tag_disp, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except Exception:
        results_list.append({"Tag/Signal": "Error", "Status": "❌ Failed", "Time": datetime.now().strftime("%H:%M:%S")})

# ==========================================
# --- UI NAVIGATION PAGES ---
# ==========================================

def login_page():
    """Secure Login Interface"""
    st.title("🔐 Bihar VLTS Pro Max Login")
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login Account", use_container_width=True):
            user = check_login(u, p)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user['username']
                st.session_state.role = user['role']
                st.session_state.u_data = user.get('data')
                st.success("Login Successful!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid Username or Password. Please try again.")

def contact_us_page(reason="general"):
    """Customer Support Information Page"""
    contact = get_contact_details()
    st.title("📞 Help & Support Center")
    
    if reason == "deactivated":
        st.error("⚠️ ACCOUNT DEACTIVATED: Your plan has expired or account is disabled. Please recharge.")
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📱 Contact Admin (WhatsApp)")
        st.write(f"Number: {contact.get('whatsapp_no', 'Not Set')}")
        clean_no = ''.join(filter(str.isdigit, str(contact.get('whatsapp_no', ''))))
        if clean_no:
            st.markdown(f"[![WhatsApp Chat](https://img.shields.io/badge/WhatsApp-Chat-green?style=for-the-badge&logo=whatsapp)](https://wa.me/{clean_no})")
        
        st.subheader("📧 Email Address")
        st.write(contact.get('email_id', 'Not Set'))

    with c2:
        st.subheader("🕒 Support Working Hours")
        st.write(contact.get('support_time', 'Not Set'))
        
        st.subheader("🆔 System Customer ID")
        if st.session_state.u_data:
            st.code(f"CID-{1000 + st.session_state.u_data.get('cid_id', 0)}")
        else:
            st.info("Log in to view your unique ID.")

    st.divider()
    # Global Navigation Button
    if st.button("🏠 Back to Home Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"
        st.rerun()

def recharge_page():
    """Wallet and Recharge Request Interface"""
    contact = get_contact_details()
    u_data = st.session_state.u_data
    cid = u_data.get('cid_id', 0)
    user_id = st.session_state.user
    
    st.title("💳 Add Credits / Recharge Plan")
    st.divider()
    
    # Check if a request is already in process to prevent spam
    pending_check = supabase.table("recharge_requests").select("id").eq("username", user_id).eq("status", "pending").execute()
    is_pending = len(pending_check.data) > 0
    
    col_img, col_form = st.columns([1, 2])
    with col_img:
        st.image(QR_URL, caption="Scan QR via Any UPI App", width=200)
        st.info(f"Verify ID Before Payment: **CID-{1000 + cid}**")
        st.subheader("📜 Recent History")
        history = supabase.table("recharge_requests").select("*").eq("username", user_id).order("id", desc=True).limit(5).execute()
        if history.data:
            for h in history.data:
                st.write(f"{'⏳' if h['status'] == 'pending' else '✅'} {h['amount']} - {h['status'].title()}")
        else:
            st.write("No payment history found.")

    with col_form:
        st.subheader("Step 1: Send Payment")
        st.info(f"**Admin UPI ID:** `{contact.get('upi_id', 'admin@upi')}`")
        st.divider()
        st.subheader("Step 2: Enter Transaction Details")
        
        c1, c2 = st.columns(2)
        c1.text_input("My Registered CID", value=f"CID-{1000+cid}", disabled=True)
        mobile_no = c2.text_input("Confirm Mobile No", placeholder="10 Digit Number Only", max_chars=10)
        
        utr = st.text_input("UTR / Transaction ID (12 Digit)", placeholder="Ex: 4031XXXXXXXX")
        
        plans = get_plans()
        plan_options = [f"₹{p['amount']} - {p['plan_name']} ({p['days']} Days)" for p in plans]
        amt = st.selectbox("Select Recharge Plan", plan_options if plan_options else ["Standard Plan"])
        
        if is_pending:
            st.warning("⚠️ Request Status: PENDING. Please wait for admin approval.")
            st.button("Submit Request Locked", disabled=True, use_container_width=True)
        else:
            if st.button("Submit Payment Request", use_container_width=True):
                if utr and len(mobile_no) == 10:
                    try:
                        # Permanent save to DB
                        supabase.table("recharge_requests").insert({
                            "username": user_id, "utr_number": utr, "amount": amt,
                            "mobile_no": mobile_no, "cid_display": f"CID-{1000+cid}", "status": "pending"
                        }).execute()
                        st.success("✅ Request Sent Successfully! Approval usually takes 5-10 mins.")
                        time.sleep(2)
                        st.session_state.page = "dashboard"
                        st.rerun()
                    except Exception:
                        st.error("Error: This UTR was already submitted or database connection failed.")
                else:
                    st.warning("Validation Error: Mobile Number must be 10 digits and UTR cannot be empty.")

    if st.button("🏠 Return to Home Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

# ==========================================
# --- ADMIN CONTROL PANEL SECTION ---
# ==========================================

def admin_panel():
    """Full Control for Admin (Users, Recharges, Tags, Settings)"""
    st.sidebar.title("🛠️ Administrator")
    if st.sidebar.button("Logout System"):
        st.session_state.logged_in = False
        st.rerun()
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["👥 Users", "🚀 Injector", "💳 Recharges", "⚙️ Settings", "🏷️ Tags"])
    
    with tab1:
        st.subheader("🔍 Find User and Manage Days")
        search_input = st.text_input("Search by Username or CID (e.g. 1001)")
        if search_input:
            search_input = search_input.strip()
            if search_input.isdigit():
                u_search = supabase.table("user_profiles").select("*").eq("cid_id", int(search_input)-1000).execute()
            elif search_input.upper().startswith("CID-"):
                u_search = supabase.table("user_profiles").select("*").eq("cid_id", int(search_input.split("-")[1])-1000).execute()
            else:
                u_search = supabase.table("user_profiles").select("*").ilike("username", f"%{search_input}%").execute()
            
            if u_search.data:
                for usr in u_search.data:
                    with st.expander(f"👤 {usr['username']} (CID-{1000 + usr['cid_id']})"):
                        st.write(f"Expiry: {usr['expiry_date']} | Status: {usr['status'].upper()}")
                        col_a, col_b, col_c = st.columns(3)
                        if col_a.button("+28 Days", key=f"e1_{usr['username']}"):
                            curr_dt = datetime.strptime(usr['expiry_date'], '%Y-%m-%d')
                            new_exp = (max(curr_dt, datetime.now()) + timedelta(days=28)).strftime("%Y-%m-%d")
                            supabase.table("user_profiles").update({"expiry_date": new_exp}).eq("username", usr['username']).execute(); st.rerun()
                        
                        new_s = 'inactive' if usr['status'] == 'active' else 'active'
                        if col_c.button(f"Mark {new_s.upper()}", key=f"s_{usr['username']}"):
                            supabase.table("user_profiles").update({"status": new_s}).eq("username", usr['username']).execute(); st.rerun()
            else:
                st.warning("No users found matching that criteria.")
        
        st.divider()
        st.subheader("➕ Add New System User")
        with st.form("admin_create_user"):
            nu = st.text_input("New ID / Username")
            np = st.text_input("Account Password")
            all_plans = get_plans()
            plan_choices = [f"{p['plan_name']} ({p['days']} Days)" for p in all_plans]
            sel_plan = st.selectbox("Assign Active Plan", plan_choices if plan_choices else ["Standard (28 Days)"])
            
            lat = st.number_input("Set User Lat", 25.5941, format="%.7f")
            lon = st.number_input("Set User Lon", 85.1376, format="%.7f")
            
            if st.form_submit_button("Create Active User"):
                if nu and np:
                    try:
                        days_val = int(sel_plan.split('(')[1].split(' ')[0])
                    except: days_val = 28
                    exp_date = (datetime.now() + timedelta(days=days_val)).strftime("%Y-%m-%d")
                    supabase.table("user_profiles").insert({
                        "username": nu, "password": np, "latitude": lat, "longitude": lon, 
                        "expiry_date": exp_date, "status": "active"
                    }).execute()
                    st.success(f"Success: {nu} created with {days_val} days plan!")
                    time.sleep(1); st.rerun()

    with tab2:
        st.subheader("🚀 Master Injector (Live Stream Console)")
        v_m = st.text_input("Vehicle No (Admin)").upper()
        i_m = st.text_input("IMEI No (Admin)")
        lat_m = st.number_input("Lat Master", 25.5941, format="%.7f")
        lon_m = st.number_input("Lon Master", 85.1376, format="%.7f")
        
        if not st.session_state.admin_running:
            if st.button("🔥 START INJECTION", type="primary", use_container_width=True):
                if v_m and i_m:
                    st.session_state.admin_running = True
                    st.rerun()
        else:
            if st.button("🛑 STOP INJECTION", use_container_width=True):
                st.session_state.admin_running = False
                st.rerun()
            
            str_area = st.empty()
            status_area = st.empty()
            while st.session_state.admin_running:
                res, tags, dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
                for index, t in enumerate(tags):
                    # Automatic capitalization in packet construction
                    full_pvt = f"$PVT,{t.upper()},2.1.1,NR,01,L,{i_m},{v_m.upper()},1,{dt},{lat_m:.7f},N,{lon_m:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                    str_area.text_area(f"🔴 Live Packet [{index+1}/{len(tags)}]: Tag {t}", value=full_pvt, height=100)
                    th = threading.Thread(target=send_packet_thread, args=("vlts.bihar.gov.in", 9999, full_pvt, res, True))
                    th.start(); th.join()
                status_area.table(pd.DataFrame(res))
                time.sleep(1.0)

    with tab3:
        st.subheader("Pending Approval Requests")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            st.dataframe(pd.DataFrame(reqs.data))
            for r in reqs.data:
                if st.button(f"Approve {r['username']} (UTR: {r['utr_number']})", key=f"app_{r['id']}"):
                    try:
                        days_add = int(r['amount'].split('(')[1].split(' ')[0])
                    except: days_add = 28
                    user_res = supabase.table("user_profiles").select("expiry_date").eq("username", r['username']).execute()
                    current_exp = datetime.strptime(user_res.data[0]['expiry_date'], '%Y-%m-%d')
                    new_exp = max(current_exp, datetime.now()) + timedelta(days=days_add)
                    supabase.table("user_profiles").update({"expiry_date": new_exp.strftime("%Y-%m-%d"), "status": "active"}).eq("username", r['username']).execute()
                    supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute()
                    st.success("User Plan Updated!"); st.rerun()
        else:
            st.write("No pending requests currently.")

    with tab4:
        st.subheader("⚙️ System Global Settings")
        curr = get_contact_details()
        with st.form("master_settings"):
            w_up = st.text_input("Support WhatsApp", curr.get('whatsapp_no'))
            e_up = st.text_input("Support Email", curr.get('email_id'))
            h_up = st.text_input("Support Hours", curr.get('support_time'))
            u_up = st.text_input("Admin UPI ID", curr.get('upi_id'))
            if st.form_submit_button("Update System Settings"):
                supabase.table("contact_settings").upsert({
                    "id": 1, "whatsapp_no": w_up, "email_id": e_up, 
                    "support_time": h_up, "upi_id": u_up
                }).execute()
                st.success("Global Settings Saved Successfully!"); st.rerun()

    with tab5:
        st.subheader("System Global Tags")
        t_in = st.text_input("Add New System Tag (Auto-Cap)")
        if st.button("➕ Add Global Tag"):
            if add_new_tag(t_in):
                st.success(f"Tag {t_in.upper()} added to DB!"); st.rerun()
        st.divider()
        tags_list = get_tags()
        for t_val in tags_list:
            col1, col2 = st.columns([5, 1])
            col1.code(t_val)
            if col2.button("❌", key=f"del_{t_val}"):
                delete_tag(t_val); st.rerun()

# ==========================================
# --- USER DASHBOARD SECTION ---
# ==========================================

def user_panel():
    """Main User Application Interface"""
    u_data = st.session_state.u_data
    # Expiry Check Logic
    exp_dt = datetime.strptime(u_data['expiry_date'], '%Y-%m-%d')
    days_left = (exp_dt - datetime.now()).days + 1
    
    st.sidebar.title(f"👋 Welcome, {st.session_state.user}")
    st.sidebar.info(f"🆔 System ID: CID-{1000 + u_data.get('cid_id', 0)}")
    
    # Check if Account is Active
    if u_data.get('status') == 'inactive' or days_left <= 0:
        if u_data.get('status') == 'inactive':
            st.sidebar.error("❌ Account Disabled")
        else:
            st.sidebar.error("🚫 Plan Expired")
        
        if st.sidebar.button("💳 Recharge Account Now", use_container_width=True):
            st.session_state.page = "recharge"; st.rerun()
        if st.sidebar.button("📞 Help & Contact Admin", use_container_width=True):
            st.session_state.page = "contact"; st.rerun()
        if st.sidebar.button("Logout System", use_container_width=True):
            st.session_state.logged_in = False; st.rerun()
        
        # Router for inactive state
        if st.session_state.page == "recharge":
            recharge_page()
        else:
            contact_us_page(reason="deactivated")
        return

    # Active User Sidebar
    st.sidebar.success(f"📅 {days_left} Days Remaining")
    if st.sidebar.button("🏠 Home Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"; st.rerun()
    if st.sidebar.button("💳 Recharge Plan", use_container_width=True):
        st.session_state.page = "recharge"; st.rerun()
    if st.sidebar.button("📞 Help / Contact Support", use_container_width=True):
        st.session_state.page = "contact"; st.rerun()
    if st.sidebar.button("Logout System", use_container_width=True):
        st.session_state.logged_in = False; st.rerun()

    # Page Router
    if st.session_state.page == "recharge":
        recharge_page()
        return
    if st.session_state.page == "contact":
        contact_us_page()
        return

    # --- MAIN INJECTOR INTERFACE ---
    c_left, c_right = st.columns([2, 1])
    
    with c_right:
        st.subheader("➕ Add Custom Tag")
        tag_user = st.text_input("New Tag Name", placeholder="e.g. BIHAR")
        if st.button("Save Tag to DB"):
            if add_new_tag(tag_user):
                st.success(f"Tag {tag_user.upper()} saved permanently!"); time.sleep(0.5); st.rerun()
    
    with c_left:
        # Enforce uppercase on vehicle number input
        veh_no = st.text_input("Bihar Vehicle Number (Auto-Cap)").upper()
        imei_no = st.text_input("15 Digit IMEI Number", value=get_vehicle_data(veh_no) if veh_no else "", max_chars=15)
    
    # Live Map Section (User Location from Profile)
    st.markdown("### 🗺️ Live Vehicle Tracking View")
    location_df = pd.DataFrame({'lat': [u_data['latitude']], 'lon': [u_data['longitude']]})
    st.map(location_df, height=300)
    
    st.divider()
    
    # Process Control
    if not st.session_state.running:
        if st.button("🚀 START SYNC", type="primary", use_container_width=True):
            if veh_no and imei_no:
                st.session_state.running = True
                st.rerun()
            else:
                st.warning("Please enter both Vehicle Number and IMEI.")
    else:
        if st.button("🛑 STOP SYNC", use_container_width=True):
            st.session_state.running = False
            st.rerun()
        
        log_status = st.empty()
        while st.session_state.running:
            res_list, tags_list, dt_str = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
            for t_item in tags_list:
                # String building with server-side requirements (All caps)
                packet_str = f"$PVT,{t_item.upper()},2.1.1,NR,01,L,{imei_no},{veh_no.upper()},1,{dt_str},{u_data['latitude']:.7f},N,{u_data['longitude']:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                th = threading.Thread(target=send_packet_thread, args=("vlts.bihar.gov.in", 9999, packet_str, res_list))
                th.start()
                th.join()
            log_status.table(pd.DataFrame(res_list))
            time.sleep(1.0)

# ==========================================
# --- SYSTEM ENTRY POINT ---
# ==========================================

def main():
    """Application Flow Controller"""
    if not st.session_state.logged_in:
        login_page()
    elif st.session_state.role == 'admin':
        admin_panel()
    else:
        user_panel()

if __name__ == "__main__":
    main()
