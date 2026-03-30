import streamlit as st
from supabase import create_client, Client

def get_supabase():
    URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
    KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
    return create_client(URL, KEY)

# Global client for other files
supabase = get_supabase()

def get_tags():
    try:
        res = supabase.table("custom_tags").select("tag_name").execute()
        return [item['tag_name'] for item in res.data] if res.data else []
    except:
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
