import streamlit as st
import psycopg2
from streamlit_js_eval import streamlit_js_eval
import pandas as pd

# 1. Database Connection Function
def init_connection():
    try:
        return psycopg2.connect(
            host=st.secrets["DB_HOST"],
            database=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            port=st.secrets["DB_PORT"]
        )
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# 2. Get Location Function
def get_location():
    loc = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => {return pos})", target_id='get_location')
    return loc

# --- APP UI ---
st.title("Nexus GPS Tracker")

# Location Logic (Fixed Line 70 Syntax)
loc = get_location()

if loc:
    st.success("Location coordinates received!")
    # Fixed Syntax here:
    lat = st.number_input("Lat", value=float(loc['coords']['latitude']) if loc else 0.0)
    lon = st.number_input("Lon", value=float(loc['coords']['longitude']) if loc else 0.0)
    
    st.write(f"Current Latitude: {lat}")
    st.write(f"Current Longitude: {lon}")
else:
    st.warning("Waiting for GPS location... Please allow location access in your browser.")

# --- Database Operations ---
if st.button("Save to Database"):
    conn = init_connection()
    if conn:
        try:
            cur = conn.cursor()
            query = "INSERT INTO location_logs (latitude, longitude) VALUES (%s, %s)"
            cur.execute(query, (lat, lon))
            conn.commit()
            cur.close()
            conn.close()
            st.success("Data saved successfully!")
        except Exception as e:
            st.error(f"Error saving to DB: {e}")

# --- Login Check (Optional) ---
# Yahan aap apna Supabase Auth logic add kar sakte hain
