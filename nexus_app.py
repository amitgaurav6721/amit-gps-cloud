# --- Is loop ko replace karein (Line 104-140 approx) ---
while st.session_state.running:
    now = datetime.now()
    d = now.strftime('%d%m%Y')
    t = now.strftime('%H%M%S')
    
    # FORMAT 1: Jo aapne manga (DDE3 Style)
    p1 = f"PVT,EGAS,2.1.1,NR,01,L,{imei},{veh_no},1,{d},{t},{lat_v},N,{lon_v},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
    cs1 = get_ais140_checksum(p1)
    packet_a = f"${p1},{cs1}*\r\n"
    
    # FORMAT 2: Advanced Version (No extra comma)
    p2 = f"PVT,{comp_name},2.1.1,NR,01,L,{imei},{veh_no},1,{d}{t},{lat_v:.7f},N,{lon_v:.7f},E,0.00,0.0,11,73,0.8,0.8,airtel,1,1,11.5,4.3,0,C,26,404,73,0a83,e3c8,e3c7,0a83,7,e3fb,0a83,7,c79d,0a83,10,e3f9,0a83,0,0001,00,000041"
    cs2 = get_ais140_checksum(p2)
    packet_b = f"${p2}{cs2}*\r\n"
    
    # SENDING DUAL DATA
    for p in [packet_a, packet_b]:
        try:
            with socket.create_connection((srv_ip, srv_port), timeout=1) as s:
                s.sendall(p.encode('ascii'))
        except: pass
    
    cur.execute("INSERT INTO gps_data (imei, latitude, longitude, raw_packet, vehicle_no) VALUES (%s, %s, %s, %s, %s)", (imei, lat_v, lon_v, f"DUAL_SENT", veh_no))
    conn.commit()
    status_msg.info(f"Dual Packets Sent | Time: {now.strftime('%H:%M:%S')}")
    time.sleep(interval)
