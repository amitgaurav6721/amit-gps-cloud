import streamlit as st
from supabase import create_client, Client

# --- DB CONNECTION SETTINGS ---
SUPABASE_URL = "https://grdgexcjyrhkoffimsuw.supabase.co"
SUPABASE_KEY = "sb_publishable_48s5EvLGqu_gLXDxmRiqMQ_E34kVKqW"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_tags():
    """
    Database se saare tags fetch karne ke liye. 
    Agar DB khali hai toh empty list bhejega.
    """
    try:
        # Direct select from your 'custom_tags' table
        res = supabase.table("custom_tags").select("tag_name").execute()
        if res.data:
            # Table se sirf tag_name ki values nikal rahe hain
            return [item['tag_name'] for item in res.data]
        return []
    except Exception as e:
        # Error aane par empty list taaki app crash na ho
        return []

def get_vehicle_data(v_no):
    """Vehicle number se uska IMEI dhoondne ke liye."""
    try:
        res = supabase.table("vehicle_master").select("imei_no").eq("vehicle_no", v_no.upper()).execute()
        return res.data[0]['imei_no'] if res.data else ""
    except:
        return ""

def log_activity(username, vehicle_no, action):
    """User ki activity (START/STOP) save karne ke liye."""
    try:
        # Database columns: user_id, vehicle_no
        supabase.table("activity_logs").insert({
            "user_id": str(username), 
            "vehicle_no": f"{str(vehicle_no).upper()} ({action})"
        }).execute()
    except Exception as e:
        pass

def check_login(user, pwd):
    """Admin aur User dono ka login check karne ke liye."""
    # Master Admin Login
    if user == "admin" and pwd == "admin77":
        return {"username": "admin", "role": "admin"}
    
    try:
        # Check from user_profiles table
        res = supabase.table("user_profiles").select("*").eq("username", user).eq("password", pwd).execute()
        if res.data:
            return {
                "username": res.data[0]['username'], 
                "role": "user", 
                "data": res.data[0]
            }
        return None
    except:
        return None
