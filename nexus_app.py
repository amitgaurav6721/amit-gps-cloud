import streamlit as st
import socket
import psycopg2
import time
from datetime import datetime
from supabase import create_client, Client

# --- SUPABASE CONFIG ---
# अपनी API Keys यहाँ डालें (Settings > API में मिलेगी)
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "YOUR_SERVICE_ROLE_KEY" # यह Key सिर्फ Admin के पास होनी चाहिए
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DB_PARAMS = {
    "host": "db.grdgexcjyrhkoffimsuw.supabase.co",
    "database": "postgres",
    "user": "postgres",
    "password": "Amitgaurav6721@",
    "port": "5432"
}

st.set_page_config(page_title="Amit GPS - Admin Controlled", layout="wide")

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None # 'admin' or 'user'
    st.session_state.user_email = ""

# --- LOGIN SYSTEM ---
if not st.session_state.logged_in:
    st.title("🔐 Amit GPS Login")
    with st.form("login"):
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                # Supabase Auth से लॉगिन चेक करना
                res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                st.session_state.logged_in = True
                st.session_state.user_email = email
                # चेक करें कि क्या यह सुपर एडमिन है
                st.session_state.user_role = "admin" if email == "amit@admin.com" else "user"
                st.rerun()
            except:
                st.error("Invalid Login. सिर्फ एडमिन द्वारा बनाए गए यूजर ही लॉगिन कर सकते हैं।")
    st.stop()

# --- SIDEBAR & LOGOUT ---
st.sidebar.write(f"Logged in as: **{st.session_state.user_email}**")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# --- SUPER ADMIN PANEL ---
if st.session_state.user_role == "admin":
    st.title("⭐ Super Admin Dashboard")
    st.subheader("👤 Create New User Account")
    
    with st.expander("New User Registration"):
        with st.form("create_user"):
            new_email = st.text_input("New User Email")
            new_password = st.text_input("Set Password")
            assigned_imei = st.text_input("Assign IMEI Number")
            if st.form_submit_button("Generate User ID"):
                try:
                    # 1. Supabase Auth में यूजर बनाना
                    user = supabase.auth.admin.create_user({
                        "email": new_email,
                        "password": new_password,
                        "email_confirm": True
                    })
                    # 2. user_profiles टेबल में डेटा डालना
                    conn = psycopg2.connect(**DB_PARAMS, sslmode="require")
                    cur = conn.cursor()
                    cur.execute("INSERT INTO user_profiles (id, username, imei_assigned, role) VALUES (%s, %s, %s, %s)", 
                                (user.user.id, new_email, assigned_imei, 'user'))
                    conn.commit()
                    st.success(f"User {new_email} created successfully!")
                except Exception as e:
                    st.error(f"Error creating user: {e}")

# --- USER PANEL (GPS TRACKER) ---
else:
    st.title("🚀 GPS Tracking Dashboard")
    # यहाँ आपका पुराना START/STOP और Progress Bar वाला कोड पेस्ट करें
    st.info("आपका IMEI एडमिन द्वारा सेट किया गया है।")
    # डेटा भेजते समय 'user_id' के साथ भेजें ताकि डेटा मिक्स न हो।