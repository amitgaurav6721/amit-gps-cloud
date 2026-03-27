# --- (ऊपर का सारा लॉगिन और Config कोड वही रहेगा) ---

with st.sidebar:
    st.header("⚙️ Advanced Config")
    # ✅ नया फीचर: प्रोटोकॉल चुनने का ऑप्शन
    proto_choice = st.selectbox("📜 Choose Protocol", ["$PVT (EGAS)", "$GPRMC (WTEX)", "$,100 (WTEX)"])
    
    imei = st.text_input("IMEI Number", "862567075041793")
    veh_no = st.text_input("Vehicle No", "BR04GA5974")
    # ... (बाकी साइडबार कोड) ...

# --- LOOPS (Inside Admin Panel) ---
if st.session_state.running:
    # ... (Database Connection) ...
    while st.session_state.running:
        now = datetime.now()
        dt = now.strftime('%d%m%Y')
        tm = now.strftime('%H%M%S')
        
        # ✅ प्रोटोकॉल के हिसाब से पेलोड बदलना
        if proto_choice == "$PVT (EGAS)":
            payload = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{dt},{tm},{lat_v:.7f},N,{lon_v:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3"
            packet = f"${payload}*\r\n"
        
        elif proto_choice == "$GPRMC (WTEX)":
            payload = f"GPRMC,WTEX,2.1.1,NR,01,L,{imei},{veh_no},1,{dt},{tm},{lat_v:.6f},N,{lon_v:.6f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041,DDE3"
            packet = f"${payload}*\r\n"
            
        elif proto_choice == "$,100 (WTEX)":
            # पेलोड 3 का खास फॉर्मेट
            payload = f",100,WTEX,1.0.01,NR,01,L,{imei},{veh_no},1,{dt},{tm},{lat_v:.7f},N,{lon_v:.7f},E,0.0,284.7,23,64.0,0.9,0.5,Airtel,0,1,11.9,3.8,0,C,10,405,70,1506,4c74,4c75,1506,10,10e1,1506,08,10e3,1506,07,2662,1506,06,0000,11,000021,A486"
            packet = f"${payload}*\r\n"

        # ... (Data भेजने का बाकी कोड) ...
