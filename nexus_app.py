import streamlit as st
import socket
import time
from database import check_login
from admin_panel import admin_panel
from user_panel import user_panel

def send_packet_thread(host, port, packet, results, show_tag=False):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5); s.connect((host, port))
        s.sendall((packet + "\r\n").encode('ascii')); time.sleep(0.1); s.close()
        tag = packet.split(',')[1] if show_tag else "📡 Sync"
        results.append({"Tag": tag, "Status": "✅ Accepted", "Time": time.strftime("%H:%M:%S")})
    except:
        results.append({"Tag": "Error", "Status": "❌ Failed", "Time": time.strftime("%H:%M:%S")})

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user': None, 'role': None, 'page': 'dashboard'})

if not st.session_state.logged_in:
    st.title("🔐 Secure Login")
    u, p = st.text_input("Username"), st.text_input("Password", type="password")
    if st.button("Login"):
        res = check_login(u, p)
        if res:
            st.session_state.update({'logged_in': True, 'user': res['username'], 'role': res['role'], 'u_data': res.get('data')})
            st.rerun()
else:
    if st.session_state.role == 'admin':
        admin_panel()
    else:
        user_panel(send_packet_thread)
