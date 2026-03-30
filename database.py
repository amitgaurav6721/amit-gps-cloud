import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta

SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
