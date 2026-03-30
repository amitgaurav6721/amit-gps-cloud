import streamlit as st
from supabase import create_client, Client

# --- DATABASE CREDENTIALS ---
URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# Create Client (Global variable)
supabase: Client = create_client(URL, KEY)

def get_tags():
    try:
        # Direct fetch from table 'custom_tags'
        res = supabase.table("custom_tags").select("tag_name").execute()
        if res.data:
            return [item['tag_name'] for item in res.data]
        return []
    except Exception as e:
        st.error(f"DB Error: {e}")
        return []

def check_login(user, pwd):
    if user == "admin" and pwd == "admin77":
        return {"username": "admin", "role": "admin"}
    try:
        res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
        if res.data:
            return {"username": res.data[0]['username'], "role": "user", "data": res.data[0]}
        return None
    except:
        return None
