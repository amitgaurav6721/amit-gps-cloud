# ... (Upar ka login aur config code same rahega) ...

with tab3: 
    st.subheader("🤖 Auto-Custom Packet")
    
    # Naya input field company name ke liye
    company_tag = st.text_input("GPS Company Name", value="EGAS") 
    
    # Dynamic Packet Preview
    custom_packet_format = f"$PVT,{company_tag},2.1.1,NR,01,L,{imei},{veh_no},1,{datetime.now().strftime('%d%m%Y,%H%M%S')},24.9194,N,83.7905,E,0.0,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041*BABA\r\n"
    
    c_msg = st.text_area("Packet to Loop", value=custom_packet_format, height=150)
    
    c1, c2 = st.columns(2)
    if c1.button("▶️ START CUSTOM", key="c_on"):
        st.session_state.custom_running = True
    if c2.button("⏹️ STOP CUSTOM", key="c_off"):
        st.session_state.custom_running = False
    c_stat = st.empty()

# --- BACKGROUND LOOP UPDATE ---
if st.session_state.custom_running:
    try:
        while st.session_state.custom_running:
            with socket.create_connection((srv_ip, srv_port), timeout=2) as s:
                # Ye line ensure karegi ki naya company name har baar jaye
                s.sendall(c_msg.encode('ascii'))
                c_stat.success(f"🚀 Sent to {srv_ip} | Company: {company_tag} | Time: {datetime.now().strftime('%H:%M:%S')}")
            time.sleep(interval)
            if not st.session_state.custom_running:
                break
    except Exception as e:
        st.error(f"Terminal Error: {e}")
        st.session_state.custom_running = False
