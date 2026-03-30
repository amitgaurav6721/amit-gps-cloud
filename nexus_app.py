import streamlit as st
import socket
import time
import pandas as pd
import threading
from datetime import datetime, timedelta
from supabase import create_client, Client
import io

# ==========================================================
# --- 1. GLOBAL APP CONFIGURATION & DATABASE SETUP ---
# ==========================================================

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
QR_URL = "https://i.ibb.co/99P60H1z/Whats-App-Image-2026-03-30-at-23-26-19.jpg"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Bihar VLTS Pro Max", layout="wide", initial_sidebar_state="expanded")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user': None, 'role': None, 'page': 'dashboard', 'u_data': None})
if 'running' not in st.session_state: st.session_state.running = False
if 'admin_running' not in st.session_state: st.session_state.admin_running = False

# ==========================================================
# --- 2. CORE DATABASE FUNCTIONS ---
# ==========================================================

def get_contact_details():
    try:
        res = supabase.table("contact_settings").select("*").eq("id", 1).execute()
        return res.data[0] if res.data else {"whatsapp_no": "Not Set", "upi_id": "admin@upi"}
    except: return {"whatsapp_no": "Not Set", "upi_id": "admin@upi"}

def check_login(user, pwd):
    if user == "admin" and pwd == "admin77": return {"username": "admin", "role": "admin"}
    try:
        res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
        return {"username": res.data[0]['username'], "role": "user", "data": res.data[0]} if res.data else None
    except: return None

def log_activity(username, vehicle_no, action):
    try:
        supabase.table("activity_logs").insert({
            "user_id": str(username), 
            "vehicle_no": f"{str(vehicle_no).upper()} ({action})"
        }).execute()
    except: pass

def get_vehicle_data(v_no):
    try:
        res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no.upper()).execute()
        return res.data[0]['imei_no'] if res.data else ""
    except: return ""

def get_tags():
    req = ["RA18", "WTEX", "MARK", "ASPL", "LOCT14A", "ACT1", "AIS140", "VLTD", "VLT", "GPS"]
    try:
        res = supabase.table("custom_tags").select("tag_name").execute()
        return [i['tag_name'] for i in res.data] if res.data else req
    except: return req

def send_packet_thread(host, port, packet, results, show_tag=False):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5); s.connect((host, port))
        s.sendall((packet + "\r\n").encode('ascii')); time.sleep(0.1); s.close()
        tag = packet.split(',')[1] if show_tag else "📡 Sync"
        results.append({"Tag": tag, "Status": "✅ Accepted", "Time": datetime.now().strftime("%H:%M:%S")})
    except: results.append({"Tag": "Error", "Status": "❌ Failed", "Time": datetime.now().strftime("%H:%M:%S")})

# ==========================================================
# --- 3. UI PAGES ---
# ==========================================================

def contact_us_page(reason=""):
    c = get_contact_details(); st.title("📞 Help & Support")
    if reason == "deactivated": st.error("⚠️ ACCOUNT INACTIVE: Recharge Required.")
    st.divider(); col1, col2 = st.columns(2)
    with col1:
        st.subheader("WhatsApp"); st.write(c.get('whatsapp_no'))
        num = ''.join(filter(str.isdigit, str(c.get('whatsapp_no', ''))))
        if num: st.markdown(f"[![Chat](https://img.shields.io/badge/WhatsApp-Chat-green?style=for-the-badge&logo=whatsapp)](https://wa.me/{num})")
    with col2:
        st.subheader("Your CID")
        if st.session_state.u_data: st.code(f"CID-{1000 + st.session_state.u_data.get('cid_id', 0)}")
    if st.button("🏠 Home"): st.session_state.page = "dashboard"; st.rerun()

def recharge_page():
    c = get_contact_details(); u = st.session_state.u_data
    st.title("💳 Recharge Panel")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.image(QR_URL, width=240); st.info(f"Verify CID-{1000 + u['cid_id']}")
    with col_r:
        st.info(f"**UPI:** `{c.get('upi_id')}`")
        mob = st.text_input("Mobile No", max_chars=10)
        utr = st.text_input("UTR Number")
        if st.button("Submit Request"):
            if utr and len(mob) == 10:
                supabase.table("recharge_requests").insert({"username": st.session_state.user, "utr_number": utr, "mobile_no": mob, "status": "pending"}).execute()
                st.success("Sent!"); time.sleep(1); st.session_state.page = "dashboard"; st.rerun()
    if st.button("🏠 Home"): st.session_state.page = "dashboard"; st.rerun()

# ==========================================================
# --- 4. ORIGINAL ADMIN PANEL ---
# ==========================================================

def admin_panel():
    st.sidebar.title("🛠️ System Admin")
    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Master", "🏷️ Tags", "👤 Users", "💳 Recharges"])
    
    with t1:
        st.subheader("Activity Logs")
        d = st.date_input("Filter Date", datetime.now())
        act = supabase.table("activity_logs").select("*").gte("created_at", f"{d}T00:00:00").lte("created_at", f"{d}T23:59:59").execute()
        if act.data:
            df = pd.DataFrame(act.data); st.dataframe(df[['created_at', 'user_id', 'vehicle_no']], use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, f"Logs_{d}.csv", "text/csv")
            
    with t2:
        av, ai = st.text_input("Admin V-No").upper(), st.text_input("Admin IMEI")
        if not st.session_state.admin_running:
            if st.button("🔥 START MASTER"): st.session_state.admin_running = True; st.rerun()
        else:
            if st.button("🛑 STOP MASTER"): st.session_state.admin_running = False; st.rerun()
            area = st.empty()
            while st.session_state.admin_running:
                res, tags, dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
                for t in tags: send_packet_thread("vlts.bihar.gov.in", 9999, f"$PVT,{t},2.1.1,NR,01,L,{ai},{av},1,{dt},25.594,N,85.137,E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*", res, True)
                area.table(pd.DataFrame(res)); time.sleep(1)

    with t3:
        nt = st.text_input("New Tag").upper()
        if st.button("Add Tag"): supabase.table("custom_tags").upsert({"tag_name": nt}).execute(); st.rerun()

    with t4:
        st.subheader("Manage Users")
        with st.form("add_user"):
            new_u, new_p = st.text_input("Username"), st.text_input("Password")
            if st.form_submit_button("Create User"):
                supabase.table("user_profiles").insert({"username": new_u, "password": new_p, "expiry_date": (datetime.now()+timedelta(days=28)).strftime('%Y-%m-%d'), "status": "active", "latitude": 25.594, "longitude": 85.137}).execute()
                st.success("User Created!"); st.rerun()
        s = st.text_input("Search User")
        if s:
            users = supabase.table("user_profiles").select("*").ilike("username", f"%{s}%").execute()
            for u in users.data:
                with st.expander(f"{u['username']} (CID-{1000+u['cid_id']})"):
                    if st.button("Extend 28 Days", key=u['username']):
                        new_ex = (datetime.strptime(u['expiry_date'], '%Y-%m-%d') + timedelta(days=28)).strftime('%Y-%m-%d')
                        supabase.table("user_profiles").update({"expiry_date": new_ex}).eq("username", u['username']).execute(); st.rerun()

    with t5:
        st.subheader("Pending Recharges")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        if reqs.data:
            for r in reqs.data:
                st.write(f"User: {r['username']} | Mob: {r['mobile_no']} | UTR: {r['utr_number']}")
                if st.button(f"Approve {r['username']}", key=f"app_{r['id']}"):
                    supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute(); st.rerun()

# ==========================================================
# --- 5. USER PANEL ---
# ==========================================================

def user_panel():
    u = st.session_state.u_data; exp = datetime.strptime(u['expiry_date'], '%Y-%m-%d')
    days = (exp - datetime.now()).days + 1
    st.sidebar.title(f"👋 {st.session_state.user}")
    st.sidebar.info(f"🆔 CID-{1000 + u.get('cid_id', 0)}")
    if u.get('status') == 'inactive' or days <= 0:
        if st.sidebar.button("Recharge Now"): st.session_state.page = "recharge"; st.rerun()
        if st.session_state.page == "recharge": recharge_page()
        else: contact_us_page(reason="deactivated")
        return
    st.sidebar.success(f"📅 {days} Days Left")
    if st.sidebar.button("🏠 Home"): st.session_state.page = "dashboard"; st.rerun()
    if st.sidebar.button("💳 Recharge"): st.session_state.page = "recharge"; st.rerun()
    if st.sidebar.button("📞 Support"): st.session_state.page = "contact"; st.rerun()
    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
    if st.session_state.page == "recharge": recharge_page(); return
    if st.session_state.page == "contact": contact_us_page(); return
    st.title("🚀 Bihar VLTS Live Sync")
    v = st.text_input("Vehicle Number").upper()
    im = st.text_input("IMEI Number", value=get_vehicle_data(v) if v else "", max_chars=15)
    st.map(pd.DataFrame({'lat': [u['latitude']], 'lon': [u['longitude']]}), height=450)
    if not st.session_state.running:
        if st.button("🚀 START SYNC", type="primary"):
            if v and im:
                supabase.table("vehicle_master").upsert({"vehicle_no": v, "imei_no": im}, on_conflict="vehicle_no").execute()
                log_activity(st.session_state.user, v, "START")
                st.session_state.running = True; st.rerun()
    else:
        if st.button("🛑 STOP SYNC"):
            log_activity(st.session_state.user, v, "STOP"); st.session_state.running = False; st.rerun()
        area = st.empty()
        while st.session_state.running:
            res, tags, dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
            for t in tags: send_packet_thread("vlts.bihar.gov.in", 9999, f"$PVT,{t},2.1.1,NR,01,L,{im},{v},1,{dt},{u['latitude']:.7f},N,{u['longitude']:.7f},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*", res)
            area.table(pd.DataFrame(res)); time.sleep(1)

def main():
    if not st.session_state.logged_in:
        st.title("🔐 Login")
        u, p = st.text_input("Username"), st.text_input("Password", type="password")
        if st.button("Login"):
            res = check_login(u, p)
            if res: st.session_state.update({'logged_in': True, 'user': res['username'], 'role': res['role'], 'u_data': res.get('data')}); st.rerun()
            else: st.error("Failed")
    elif st.session_state.role == 'admin': admin_panel()
    else: user_panel()

if __name__ == "__main__": main()
