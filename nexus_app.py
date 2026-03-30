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

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Bihar VLTS Pro Max", layout="wide", initial_sidebar_state="expanded")

# --- INITIALIZE SESSION STATES ---
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
    try:
        res = supabase.table("contact_settings").select("*").eq("id", 1).execute()
        return res.data[0] if res.data else {"whatsapp_no": "Not Set", "upi_id": "admin@upi"}
    except Exception: return {"whatsapp_no": "Not Set", "upi_id": "admin@upi"}

def check_login(user, pwd):
    if user == "admin" and pwd == "admin77": return {"username": "admin", "role": "admin"}
    try:
        res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
        if res.data: return {"username": res.data[0]['username'], "role": "user", "data": res.data[0]}
    except Exception: return None
    return None

def get_plans():
    try:
        res = supabase.table("plan_settings").select("*").execute()
        return res.data
    except Exception: return []

def get_tags():
    required_tags = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS", "AMAZON", "BBOX77", "EGAS", "MENT", "MIJO", "EMR", "HB", "HA", "RT", "OS", "IDL", "PWR"]
    try:
        res = supabase.table("custom_tags").select("tag_name").execute()
        existing = [item['tag_name'] for item in res.data]
        missing = [t for t in required_tags if t not in existing]
        if missing:
            for t in missing: supabase.table("custom_tags").upsert({"tag_name": t.upper()}).execute()
            res = supabase.table("custom_tags").select("tag_name").execute()
            return [item['tag_name'] for item in res.data]
        return existing
    except Exception: return required_tags

def add_new_tag(new_tag):
    if new_tag:
        try:
            clean_tag = str(new_tag).upper().strip()
            supabase.table("custom_tags").upsert({"tag_name": clean_tag}).execute()
            return True
        except Exception: return False
    return False

def delete_tag(tag_name):
    try: supabase.table("custom_tags").delete().eq("tag_name", tag_name).execute()
    except Exception: pass

def get_vehicle_data(v_no):
    try:
        if v_no:
            res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no.upper()).execute()
            if res.data: return res.data[0]['imei_no']
    except Exception: return ""
    return ""

def log_activity(username, vehicle_no, action):
    try:
        supabase.table("activity_logs").insert({
            "username": username, "vehicle_no": str(vehicle_no).upper(),
            "action": action, "timestamp": datetime.now().isoformat()
        }).execute()
    except Exception: pass

# ==========================================
# --- NETWORK & PAGES ---
# ==========================================

def send_packet_thread(host, port, packet, results_list, show_tag=False):
    try:
        final_to_send = packet + "\r\n"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.settimeout(5); s.connect((host, port))
        s.sendall(final_to_send.encode('ascii'))
        time.sleep(0.1); s.close()
        tag_disp = packet.split(',')[1] if show_tag else "📡 Sync"
        results_list.append({"Tag/Signal": tag_disp, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except Exception:
        results_list.append({"Tag/Signal": "Error", "Status": "❌ Failed", "Time": datetime.now().strftime("%H:%M:%S")})

def contact_us_page(reason="general"):
    contact = get_contact_details(); st.title("📞 Help & Support Center")
    if reason == "deactivated": st.error("⚠️ ACCOUNT INACTIVE: Please recharge to continue.")
    st.divider(); c1, c2 = st.columns(2)
    with c1:
        st.subheader("📱 WhatsApp Support"); st.write(f"Number: {contact.get('whatsapp_no', 'Not Set')}")
        clean_no = ''.join(filter(str.isdigit, str(contact.get('whatsapp_no', ''))))
        if clean_no: st.markdown(f"[![Chat](https://img.shields.io/badge/WhatsApp-Chat-green?style=for-the-badge&logo=whatsapp)](https://wa.me/{clean_no})")
        st.subheader("📧 Support Email"); st.write(contact.get('email_id', 'Not Set'))
    with c2:
        st.subheader("🕒 Working Hours"); st.write(contact.get('support_time', 'Not Set'))
        st.subheader("🆔 Your System CID")
        if st.session_state.u_data: st.code(f"CID-{1000 + st.session_state.u_data.get('cid_id', 0)}")
    st.divider()
    if st.button("🏠 Back to Home Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"; st.rerun()

def recharge_page():
    contact = get_contact_details(); u_data = st.session_state.u_data
    cid = u_data.get('cid_id', 0); user_id = st.session_state.user; st.title("💳 Recharge Your Account")
    pending_check = supabase.table("recharge_requests").select("id").eq("username", user_id).eq("status", "pending").execute()
    is_pending = len(pending_check.data) > 0
    col_img, col_form = st.columns([1, 2])
    with col_img:
        st.image(QR_URL, caption="Scan QR to Pay", width=250); st.info(f"Verify ID: **CID-{1000 + cid}**")
        st.subheader("📜 Recent History")
        history = supabase.table("recharge_requests").select("*").eq("username", user_id).order("id", desc=True).limit(3).execute()
        if history.data:
            for h in history.data: st.write(f"{'⏳' if h['status'] == 'pending' else '✅'} {h['amount']} - {h['status'].title()}")
    with col_form:
        st.subheader("Step 1: Send UPI Payment"); st.info(f"**Admin UPI ID:** `{contact.get('upi_id', 'admin@upi')}`")
        st.divider(); st.subheader("Step 2: Submit Details")
        c1, c2 = st.columns(2)
        c1.text_input("My CID", value=f"CID-{1000+cid}", disabled=True)
        m_no = c2.text_input("Mobile No", placeholder="10 Digits", max_chars=10)
        utr = st.text_input("UTR / Transaction ID", placeholder="12 Digit Number")
        plans = get_plans(); plan_list = [f"₹{p['amount']} - {p['plan_name']} ({p['days']} Days)" for p in plans]
        amt = st.selectbox("Select Plan", plan_list if plan_list else ["Standard Plan"])
        if is_pending:
            st.warning("⚠️ Request Pending..."); st.button("Request Locked", disabled=True, use_container_width=True)
        else:
            if st.button("Submit Recharge Request", use_container_width=True):
                if utr and len(m_no) == 10:
                    try:
                        supabase.table("recharge_requests").insert({"username": user_id, "utr_number": utr, "amount": amt, "mobile_no": m_no, "cid_display": f"CID-{1000+cid}", "status": "pending"}).execute()
                        st.success("✅ Request Sent!"); time.sleep(2); st.session_state.page = "dashboard"; st.rerun()
                    except Exception: st.error("UTR already submitted or database error.")
                else: st.warning("Please provide a 10-digit Mobile Number and UTR.")
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "dashboard"; st.rerun()

# ==========================================
# --- ADMIN & USER PANELS ---
# ==========================================

def admin_panel():
    st.sidebar.title("🛠️ System Admin")
    if st.sidebar.button("Logout Admin"): st.session_state.logged_in = False; st.rerun()
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Master", "👤 Users", "🏷️ Tags", "⚙️ Settings"])
    with t1:
        st.subheader("📅 Activity Log Report"); d_filter = st.date_input("Filter Date", datetime.now())
        act = supabase.table("activity_logs").select("*").gte("timestamp", f"{d_filter}T00:00:00").lte("timestamp", f"{d_filter}T23:59:59").execute()
        if act.data:
            df_act = pd.DataFrame(act.data); st.metric("Total Hits Today", len(df_act))
            st.dataframe(df_act[['timestamp', 'username', 'vehicle_no', 'action']], use_container_width=True)
        else: st.info("No activity recorded for this date.")
    with t2:
        st.subheader("🚀 Master Injector Console")
        v_m = st.text_input("Vehicle No (Master)").upper(); i_m = st.text_input("IMEI No (Master)")
        lat_m = st.number_input("Lat Master", 25.5941, format="%.7f"); lon_m = st.number_input("Lon Master", 85.1376, format="%.7f")
        if not st.session_state.admin_running:
            if st.button("🔥 START MASTER", type="primary", use_container_width=True): st.session_state.admin_running = True; st.rerun()
        else:
            if st.button("🛑 STOP MASTER", use_container_width=True): st.session_state.admin_running = False; st.rerun()
            str_area, tbl_area = st.empty(), st.empty()
            while st.session_state.admin_running:
                res, tags, dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
                for i, t in enumerate(tags):
                    p = f"$PVT,{t.upper()},2.1.1,NR,01,L,{i_m},{v_m},1,{dt},{lat_m:.7f},N,{lon_m:.7f},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                    str_area.text_area(f"Packet [{i+1}/{len(tags)}]: {t}", value=p, height=100)
                    send_packet_thread("vlts.bihar.gov.in", 9999, p, res, True)
                tbl_area.table(pd.DataFrame(res)); time.sleep(1)
    with t3:
        st.subheader("🔍 Manage User Database"); s_user = st.text_input("Search User Name or CID")
        if s_user:
            s_user = s_user.strip()
            users = supabase.table("user_profiles").select("*").eq("cid_id", int(s_user)-1000).execute() if s_user.isdigit() else supabase.table("user_profiles").select("*").ilike("username", f"%{s_user}%").execute()
            if users.data:
                for usr in users.data:
                    with st.expander(f"👤 {usr['username']} (CID-{1000 + usr['cid_id']})"):
                        st.write(f"Expiry: {usr['expiry_date']} | Status: {usr['status'].upper()}")
                        col_a, col_b = st.columns(2)
                        if col_a.button("+28 Days", key=f"e_{usr['username']}"):
                            n_exp = (max(datetime.strptime(usr['expiry_date'], '%Y-%m-%d'), datetime.now()) + timedelta(days=28)).strftime("%Y-%m-%d")
                            supabase.table("user_profiles").update({"expiry_date": n_exp}).eq("username", usr['username']).execute(); st.rerun()
                        new_stat = 'inactive' if usr['status'] == 'active' else 'active'
                        if col_b.button(f"Mark {new_stat.upper()}", key=f"s_{usr['username']}"):
                            supabase.table("user_profiles").update({"status": new_stat}).eq("username", usr['username']).execute(); st.rerun()
    with t4:
        st.subheader("🏷️ Tag Management"); t_new = st.text_input("New System Tag").upper()
        if st.button("➕ Add Global Tag"):
            if add_new_tag(t_new): st.success("Added!"); st.rerun()
        for t_val in get_tags():
            ca, cb = st.columns([5,1]); ca.code(t_val)
            if cb.button("❌", key=f"d_{t_val}"): delete_tag(t_val); st.rerun()
    with t5:
        st.subheader("⚙️ Global Settings"); curr = get_contact_details()
        with st.form("admin_settings"):
            w_u, e_u, u_u = st.text_input("WhatsApp", curr.get('whatsapp_no')), st.text_input("Email", curr.get('email_id')), st.text_input("UPI ID", curr.get('upi_id'))
            if st.form_submit_button("Save All Settings"):
                supabase.table("contact_settings").upsert({"id": 1, "whatsapp_no": w_u, "email_id": e_u, "upi_id": u_u}).execute(); st.success("Saved!"); st.rerun()

def user_panel():
    u_data = st.session_state.u_data; exp_dt = datetime.strptime(u_data['expiry_date'], '%Y-%m-%d')
    days_left = (exp_dt - datetime.now()).days + 1; st.sidebar.title(f"👋 Welcome, {st.session_state.user}"); st.sidebar.info(f"🆔 System ID: CID-{1000 + u_data.get('cid_id', 0)}")
    if u_data.get('status') == 'inactive' or days_left <= 0:
        if st.sidebar.button("💳 Recharge Account"): st.session_state.page = "recharge"; st.rerun()
        if st.sidebar.button("📞 Contact Support"): st.session_state.page = "contact"; st.rerun()
        if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
        if st.session_state.page == "recharge": recharge_page()
        else: contact_us_page(reason="deactivated")
        return
    st.sidebar.success(f"📅 {days_left} Days Left")
    if st.sidebar.button("🏠 Home Dashboard", use_container_width=True): st.session_state.page = "dashboard"; st.rerun()
    if st.sidebar.button("💳 Recharge Plan", use_container_width=True): st.session_state.page = "recharge"; st.rerun()
    if st.sidebar.button("📞 Help / Support", use_container_width=True): st.session_state.page = "contact"; st.rerun()
    if st.sidebar.button("Logout", use_container_width=True): st.session_state.logged_in = False; st.rerun()
    if st.session_state.page == "recharge": recharge_page(); return
    if st.session_state.page == "contact": contact_us_page(); return
    col_l, col_r = st.columns([2, 1])
    with col_r:
        st.subheader("➕ Your Tags"); u_tag = st.text_input("New Custom Tag").upper()
        if st.button("Save My Tag"):
            if add_new_tag(u_tag): st.success("Saved!"); time.sleep(0.5); st.rerun()
    with col_l:
        v_no = st.text_input("Vehicle Number (Auto-Cap)").upper()
        i_no = st.text_input("IMEI Number", value=get_vehicle_data(v_no) if v_no else "", max_chars=15)
    st.markdown("### 🗺️ Live Vehicle Map View"); st.map(pd.DataFrame({'lat':[u_data['latitude']], 'lon':[u_data['longitude']]}), height=400); st.divider()
    if not st.session_state.running:
        if st.button("🚀 START SYNC", type="primary", use_container_width=True):
            if v_no and i_no:
                try:
                    supabase.table("vehicle_master").upsert({"vehicle_no": v_no.upper(), "imei_no": i_no}, on_conflict="vehicle_no").execute()
                except Exception as e: st.error(f"Database Error: {e}")
                log_activity(st.session_state.user, v_no, "START"); st.session_state.running = True; st.rerun()
    else:
        if st.button("🛑 STOP SYNC", use_container_width=True):
            log_activity(st.session_state.user, v_no if v_no else "Unknown", "STOP"); st.session_state.running = False; st.rerun()
        res_area = st.empty()
        while st.session_state.running:
            r_list, tags, dt_str = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
            for t_val in tags:
                p_str = f"$PVT,{t_val.upper()},2.1.1,NR,01,L,{i_no},{v_no},1,{dt_str},{u_data['latitude']:.7f},N,{u_data['longitude']:.7f},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                send_packet_thread("vlts.bihar.gov.in", 9999, p_str, r_list)
            res_area.table(pd.DataFrame(r_list)); time.sleep(1)

if not st.session_state.logged_in:
    st.title("🔐 Secure System Login")
    u_in, p_in = st.text_input("Username"), st.text_input("Password", type="password")
    if st.button("Login to Dashboard", use_container_width=True):
        res_l = check_login(u_in, p_in)
        if res_l: st.session_state.update({'logged_in': True, 'user': res_l['username'], 'role': res_l['role'], 'u_data': res_l.get('data')}); st.rerun()
        else: st.error("Login Failed")
elif st.session_state.role == 'admin': admin_panel()
else: user_panel()
