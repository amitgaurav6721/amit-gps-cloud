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
# Stable ImgBB Link for QR
QR_URL = "https://i.ibb.co/99P60H1z/Whats-App-Image-2026-03-30-at-23-26-19.jpg"

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
    try:
        res = supabase.table("contact_settings").select("*").eq("id", 1).execute()
        if res.data:
            return res.data[0]
        return {"whatsapp_no": "Not Set", "email_id": "Not Set", "support_time": "Not Set", "upi_id": "Not Set"}
    except:
        return {"whatsapp_no": "Not Set", "email_id": "Not Set", "support_time": "Not Set", "upi_id": "Not Set"}

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
    if res.data:
        return res.data[0]['imei_no']
    return ""

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
        tag_disp = packet.split(',')[1] if show_tag else "📡 Syncing..."
        results_list.append({"Tag/Signal": tag_disp, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except:
        results_list.append({"Tag/Signal": "Error", "Status": "❌ Failed", "Time": datetime.now().strftime("%H:%M:%S")})

# --- PAGES ---
def login_page():
    st.title("🔐 Bihar VLTS Pro Max Login")
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

def contact_us_page(reason="general"):
    contact = get_contact_details()
    st.title("📞 Contact Support")
    if reason == "deactivated":
        st.error("⚠️ Account Deactivated. Dubara active karne ke liye Recharge karein.")
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📱 WhatsApp Support")
        st.write(contact.get('whatsapp_no'))
        clean_no = ''.join(filter(str.isdigit, str(contact.get('whatsapp_no', ''))))
        if clean_no:
            st.markdown(f"[![Chat](https://img.shields.io/badge/WhatsApp-Chat-green?style=for-the-badge&logo=whatsapp)](https://wa.me/{clean_no})")
        
        st.subheader("📧 Email Support")
        st.write(contact.get('email_id'))

    with c2:
        st.subheader("🕒 Support Timings")
        st.write(contact.get('support_time'))
        
        st.subheader("🆔 Customer ID")
        st.code(f"CID-{1000 + st.session_state.u_data.get('cid_id', 0)}")

    if st.session_state.u_data and st.session_state.u_data.get('status') == 'active':
        st.divider()
        if st.button("⬅️ Back to Dashboard"): 
            st.session_state.page = "dashboard"
            st.rerun()

def recharge_page():
    contact = get_contact_details()
    u_data = st.session_state.u_data
    cid = u_data.get('cid_id', 0)
    user_id = st.session_state.user
    st.title("💳 Recharge Your Plan")
    
    pending_check = supabase.table("recharge_requests").select("id").eq("username", user_id).eq("status", "pending").execute()
    is_pending = len(pending_check.data) > 0
    
    col_img, col_form = st.columns([1, 2])
    with col_img:
        st.image(QR_URL, caption="Scan QR to Pay", width=200)
        st.info(f"Verify ID: **CID-{1000 + cid}**")
        st.subheader("📜 History")
        history = supabase.table("recharge_requests").select("*").eq("username", user_id).order("id", desc=True).limit(3).execute()
        if history.data:
            for h in history.data:
                icon = "⏳" if h['status'] == 'pending' else "✅"
                st.write(f"{icon} {h['amount']} - {h['status'].title()}")
        else:
            st.write("No records found.")

    with col_form:
        st.subheader("Step 1: Pay via UPI")
        st.info(f"**UPI ID:** `{contact.get('upi_id', 'admin@upi')}`")
        st.divider()
        st.subheader("Step 2: Submit Details")
        
        c1, c2 = st.columns(2)
        c1.text_input("CID Number", value=f"CID-{1000+cid}", disabled=True)
        mobile_no = c2.text_input("Mobile No (10 Digit)", placeholder="XXXXXXXXXX", max_chars=10)
        
        utr = st.text_input("UTR / Transaction ID", placeholder="12 digit number")
        plans = get_plans()
        amt = st.selectbox("Choose Plan", [f"₹{p['amount']} - {p['plan_name']} ({p['days']} Days)" for p in plans])
        
        if is_pending:
            st.warning("⚠️ Request Pending...")
            st.button("Submit Request", disabled=True, use_container_width=True)
        else:
            if st.button("Submit Recharge Request", use_container_width=True):
                if utr and len(mobile_no) == 10:
                    existing_utr = supabase.table("recharge_requests").select("id").eq("utr_number", utr).execute()
                    if len(existing_utr.data) > 0:
                        st.error(f"❌ UTR `{utr}` pehle hi use ho chuka hai.")
                    else:
                        try:
                            supabase.table("recharge_requests").insert({
                                "username": user_id, "utr_number": utr, "amount": amt,
                                "mobile_no": mobile_no, "cid_display": f"CID-{1000+cid}", "status": "pending"
                            }).execute()
                            st.success("✅ Request Sent!"); time.sleep(2); st.session_state.page = "dashboard"; st.rerun()
                        except:
                            st.error("System Error")
                else:
                    st.warning("Check Mobile & UTR")
    
    if st.button("⬅️ Back"): 
        st.session_state.page = "dashboard"
        st.rerun()

def admin_panel():
    st.sidebar.title("Admin Dashboard")
    if st.sidebar.button("Logout"): 
        st.session_state.logged_in = False
        st.rerun()
    
    menu = st.tabs(["Users Control", "Master Injector", "Recharges", "Settings", "Manage Tags"])
    
    with menu[0]:
        st.subheader("🔍 Search & Control")
        search_input = st.text_input("Search (Name, 1001, or CID-1001)")
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
                    exp_date = datetime.strptime(usr['expiry_date'], '%Y-%m-%d')
                    d_left = (exp_date - datetime.now()).days + 1
                    status = usr.get('status', 'active')
                    with st.expander(f"👤 {usr['username']} (CID-{1000 + usr['cid_id']})"):
                        st.write(f"Days Left: {d_left} | Status: {status.upper()}")
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
        
        st.divider()
        st.subheader("➕ Create New User")
        with st.form("new_user_form"):
            nu, np = st.text_input("New Username"), st.text_input("New Password")
            plans = get_plans()
            selected_plan = st.selectbox("Assign Active Plan", [f"{p['plan_name']} ({p['days']} Days)" for p in plans])
            lat, lon = st.number_input("Lat", 25.5941, format="%.7f"), st.number_input("Lon", 85.1376, format="%.7f")
            if st.form_submit_button("Create User"):
                if nu and np:
                    try: days = int(selected_plan.split('(')[1].split(' ')[0])
                    except: days = 28
                    exp = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                    supabase.table("user_profiles").insert({"username": nu, "password": np, "latitude": lat, "longitude": lon, "expiry_date": exp, "status": "active"}).execute()
                    st.success(f"User Created!"); st.rerun()

    with menu[1]:
        st.subheader("🚀 Master Injector (Live Console)")
        vno, imei = st.text_input("V-No", "BR01P1234").upper(), st.text_input("IMEI", "865432109876543")
        lat_m, lon_m = st.number_input("Lat Master", 25.5941, format="%.7f"), st.number_input("Lon Master", 85.1376, format="%.7f")
        if not st.session_state.admin_running:
            if st.button("🔥 START MASTER", type="primary", use_container_width=True): 
                st.session_state.admin_running = True; st.rerun()
        else:
            if st.button("🛑 STOP MASTER", use_container_width=True): 
                st.session_state.admin_running = False; st.rerun()
            str_area, status_area = st.empty(), st.empty()
            while st.session_state.admin_running:
                res, tags, dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
                for i, t in enumerate(tags):
                    p = f"$PVT,{t},2.1.1,NR,01,L,{imei},{vno},1,{dt},{lat_m:.7f},N,{lon_m:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                    str_area.text_area(f"Injecting [{i+1}/{len(tags)}]: {t}", value=p, height=100)
                    th = threading.Thread(target=send_packet_thread, args=("vlts.bihar.gov.in", 9999, p, res, True))
                    th.start(); th.join()
                status_area.table(pd.DataFrame(res)); time.sleep(1.0)
    
    with menu[2]:
        st.subheader("Pending Recharges")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            st.dataframe(pd.DataFrame(reqs.data))
            for r in reqs.data:
                if st.button(f"Approve {r['username']} ({r['utr_number']})", key=f"app_{r['id']}"):
                    try: days = int(r['amount'].split('(')[1].split(' ')[0])
                    except: days = 28
                    user_res = supabase.table("user_profiles").select("expiry_date").eq("username", r['username']).execute()
                    new_exp = max(datetime.strptime(user_res.data[0]['expiry_date'], '%Y-%m-%d'), datetime.now()) + timedelta(days=days)
                    supabase.table("user_profiles").update({"expiry_date": new_exp.strftime("%Y-%m-%d"), "status": "active"}).eq("username", r['username']).execute()
                    supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute()
                    st.success("Approved!"); st.rerun()
        else: st.write("No requests.")

    with menu[3]:
        st.subheader("⚙️ Settings")
        curr = get_contact_details()
        with st.form("settings_form"):
            w, e, t, u = st.text_input("WhatsApp", curr.get('whatsapp_no')), st.text_input("Email", curr.get('email_id')), st.text_input("Hours", curr.get('support_time')), st.text_input("UPI ID", curr.get('upi_id'))
            if st.form_submit_button("Save All Settings"):
                supabase.table("contact_settings").upsert({"id": 1, "whatsapp_no": w, "email_id": e, "support_time": t, "upi_id": u}).execute(); st.success("Saved!"); st.rerun()

    with menu[4]:
        st.subheader("Manage Tags")
        ta = st.text_input("Add New Tag Name")
        if st.button("➕ Add Tag"):
            if ta: add_new_tag(ta); st.success(f"Tag Added!"); st.rerun()
        st.divider()
        tags = get_tags()
        for t in tags:
            c1, c2 = st.columns([4, 1])
            c1.code(t)
            if c2.button("❌", key=f"del_{t}"): delete_tag(t); st.rerun()

def user_panel():
    u_data = st.session_state.u_data
    exp = datetime.strptime(u_data['expiry_date'], '%Y-%m-%d')
    days = (exp - datetime.now()).days + 1
    st.sidebar.title(f"👋 {st.session_state.user}")
    st.sidebar.info(f"🆔 CID-{1000 + u_data.get('cid_id', 0)}")
    
    if u_data.get('status') == 'inactive' or days <= 0:
        if u_data.get('status') == 'inactive': st.sidebar.error("❌ Account Deactivated")
        else: st.sidebar.error("🚫 Plan Expired")
        if st.sidebar.button("💳 Recharge Now", use_container_width=True): st.session_state.page = "recharge"; st.rerun()
        if st.sidebar.button("📞 Contact Support", use_container_width=True): st.session_state.page = "contact"; st.rerun()
        if st.sidebar.button("Logout", use_container_width=True): st.session_state.logged_in = False; st.rerun()
        if st.session_state.page == "recharge": recharge_page()
        else: contact_us_page(reason="deactivated")
        return

    st.sidebar.success(f"📅 {days} Days Left")
    if st.sidebar.button("💳 Recharge Plan", use_container_width=True): st.session_state.page = "recharge"; st.rerun()
    if st.sidebar.button("📞 Help / Contact", use_container_width=True): st.session_state.page = "contact"; st.rerun()
    if st.sidebar.button("Logout", use_container_width=True): st.session_state.logged_in = False; st.rerun()
    
    if st.session_state.page == "recharge": recharge_page(); return
    if st.session_state.page == "contact": contact_us_page(); return
    
    v = st.text_input("Vehicle Number").upper()
    im = st.text_input("IMEI Number", value=get_vehicle_data(v) if v else "", max_chars=15)
    st.divider()
    if not st.session_state.running:
        if st.button("🚀 START", type="primary", use_container_width=True):
            if v and im: st.session_state.running = True; st.rerun()
    else:
        if st.button("🛑 STOP", use_container_width=True): st.session_state.running = False; st.rerun()
        status_area = st.empty()
        while st.session_state.running:
            res, tags, dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
            for t in tags:
                p = f"$PVT,{t},2.1.1,NR,01,L,{im},{v},1,{dt},{u_data['latitude']:.7f},N,{u_data['longitude']:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3*"
                th = threading.Thread(target=send_packet_thread, args=("vlts.bihar.gov.in", 9999, p, res))
                th.start(); th.join()
            status_area.table(pd.DataFrame(res)); time.sleep(1.0)

def main():
    if not st.session_state.logged_in: login_page()
    elif st.session_state.role == 'admin': admin_panel()
    else: user_panel()

if __name__ == "__main__":
    main()
