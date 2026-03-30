import streamlit as st
import pandas as pd
from datetime import datetime
from database import supabase, get_vehicle_data, log_activity, get_tags

def user_panel(send_packet_func):
    u = st.session_state.u_data
    exp = datetime.strptime(u['expiry_date'], '%Y-%m-%d')
    days = (exp - datetime.now()).days + 1
    
    st.sidebar.title(f"👋 {st.session_state.user}")
    st.sidebar.info(f"🆔 CID-{1000 + u.get('cid_id', 0)}")
    st.sidebar.success(f"📅 {days} Days Left")

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
            log_activity(st.session_state.user, v, "STOP")
            st.session_state.running = False; st.rerun()
        
        area = st.empty()
        while st.session_state.running:
            res, tags, dt = [], get_tags(), datetime.now().strftime("%d%m%Y,%H%M%S")
            for t in tags:
                p = f"$PVT,{t},2.1.1,NR,01,L,{im},{v},1,{dt},{u['latitude']:.7f},N,{u['longitude']:.7f},E,0,0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*"
                send_packet_func("vlts.bihar.gov.in", 9999, p, res)
            area.table(pd.DataFrame(res)); time.sleep(1)
