import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_tags():
    try:
        # Exact table name: custom_tags | Exact column: tag_name
        res = supabase.table("custom_tags").select("tag_name").execute()
        if res.data:
            return [item['tag_name'] for item in res.data]
        return []
    except Exception as e:
        st.error(f"DB Error (Tags): {e}")
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
