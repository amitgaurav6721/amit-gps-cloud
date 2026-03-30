import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import supabase, get_tags

def admin_panel():
    st.sidebar.title("🛠️ System Admin")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
    
    t1, t2, t3, t4, t5 = st.tabs(["📊 Reports", "🚀 Master", "🏷️ Tags", "👤 Users", "💳 Recharges"])
    
    with t1:
        st.subheader("Activity Logs")
        d = st.date_input("Filter Date", datetime.now())
        act = supabase.table("activity_logs").select("*").gte("created_at", f"{d}T00:00:00").lte("created_at", f"{d}T23:59:59").execute()
        if act.data:
            df = pd.DataFrame(act.data)
            st.dataframe(df[['created_at', 'user_id', 'vehicle_no']], use_container_width=True)
            st.download_button("📥 Download CSV", df.to_csv(index=False).encode('utf-8'), f"Logs_{d}.csv", "text/csv")

    with t2:
        st.info("Master Injector Logic remains in nexus_app for threading sync.")

    with t3:
        st.subheader("Manage Tags")
        nt = st.text_input("Enter New Tag").upper()
        if st.button("Add Tag"):
            if nt: supabase.table("custom_tags").upsert({"tag_name": nt}).execute(); st.rerun()
        for t_val in get_tags():
            c1, c2 = st.columns([5,1])
            c1.code(t_val)
            if c2.button("❌", key=f"del_{t_val}"): supabase.table("custom_tags").delete().eq("tag_name", t_val).execute(); st.rerun()

    with t4:
        st.subheader("Manage Users")
        with st.form("create_user_form"):
            new_u = st.text_input("Username")
            new_p = st.text_input("Password")
            if st.form_submit_button("Create User"):
                supabase.table("user_profiles").insert({"username": new_u, "password": new_p, "expiry_date": (datetime.now()+timedelta(days=28)).strftime('%Y-%m-%d'), "status": "active", "latitude": 25.594, "longitude": 85.137}).execute()
                st.success("User Created!"); st.rerun()

    with t5:
        st.subheader("Recharge Requests")
        reqs = supabase.table("recharge_requests").select("*").eq("status", "pending").execute()
        for r in reqs.data:
            st.write(f"User: {r['username']} | UTR: {r['utr_number']}")
            if st.button(f"Approve {r['username']}", key=f"app_{r['id']}"):
                supabase.table("recharge_requests").update({"status": "approved"}).eq("id", r['id']).execute(); st.rerun()
