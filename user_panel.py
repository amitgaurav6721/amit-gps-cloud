import sqlite3
from flask import Flask, render_template, request, jsonify, session, redirect
import socket, datetime, threading, time, re, os

app = Flask(__name__)
app.secret_key = "amit_master_key_999"

def get_db():
    conn = sqlite3.connect('amit_gps.db')
    return conn

# डेटाबेस में टेबल और एडमिन सेटअप
def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, user TEXT, imei TEXT, time TEXT, status TEXT)''')
    # Default Master Admin
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'amit123', 'master')")
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    if 'user' in session: return redirect('/dashboard')
    return '''
    <body style="background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding-top:80px;">
        <h1 style="color:#fbbf24;">🔐 AMIT GPS CONTROL CENTER</h1>
        <form action="/login" method="post" style="background:#1e293b; display:inline-block; padding:40px; border-radius:15px; border:1px solid #334155;">
            <input name="username" placeholder="Username" required style="display:block; margin:10px auto; padding:12px; width:250px; border-radius:5px;"><br>
            <input name="password" type="password" placeholder="Password" required style="display:block; margin:10px auto; padding:12px; width:250px; border-radius:5px;"><br>
            <button type="submit" style="background:#10b981; color:black; padding:12px; width:100%; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">ENTER SYSTEM 🚀</button>
        </form>
    </body>
    '''

@app.route('/login', methods=['POST'])
def login():
    un, pw = request.form['username'], request.form['password']
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, role FROM users WHERE username=? AND password=?", (un, pw))
    user = c.fetchone()
    conn.close()
    if user:
        session['user'], session['role'] = user[0], user[1]
        return redirect('/dashboard')
    return "Wrong Credentials! <a href='/'>Try again</a>"

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    
    user_list_html = ""
    if session['role'] == 'master':
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, role FROM users WHERE role='client'")
        users = c.fetchall()
        conn.close()
        
        user_list_html = "<h3>👥 User Management (Master Only)</h3>"
        user_list_html += "<form action='/add_user' method='post' style='margin-bottom:20px;'><input name='new_un' placeholder='New User' required> <input name='new_pw' placeholder='Password' required> <button type='submit' style='background:green; color:white;'>Add User +</button></form>"
        user_list_html += "<table border='1' style='width:100%; text-align:left;'><tr><th>ID</th><th>Username</th><th>Action</th></tr>"
        for u in users:
            user_list_html += f"<tr><td>{u[0]}</td><td>{u[1]}</td><td><a href='/delete_user/{u[0]}' style='color:red;'>REMOVE ACCESS ❌</a></td></tr>"
        user_list_html += "</table><hr>"

    return f'''
    <body style="background:#0f172a; color:white; font-family:sans-serif; padding:20px;">
        <div style="display:flex; justify-content:space-between;">
            <h1>🛰️ Welcome, {session['user']} ({session['role']})</h1>
            <a href="/logout" style="color:#ef4444; font-weight:bold;">LOGOUT</a>
        </div>
        <hr>
        {user_list_html}
        
        <div style="background:#1e293b; padding:20px; border-radius:10px;">
            <h3>🛠️ GPS Data Sender</h3>
            <input id="imei" placeholder="IMEI Number" style="padding:8px;">
            <input id="ip" placeholder="IP Address" style="padding:8px;">
            <button onclick="send()" style="padding:8px 20px; background:#fbbf24; border:none; border-radius:5px; font-weight:bold;">SEND PACKET 🚀</button>
            <p id="st"></p>
        </div>

        <script>
            function send() {{
                const btn = event.target;
                btn.innerText = "SENDING...";
                fetch('/run_gps', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ imei: document.getElementById('imei').value, ip: document.getElementById('ip').value }})
                }}).then(res => res.json()).then(d => {{
                    btn.innerText = "SEND PACKET 🚀";
                    document.getElementById('st').innerText = "✅ Successfully Sent!";
                }});
            }}
        </script>
    </body>
    '''

@app.route('/add_user', methods=['POST'])
def add_user():
    if session.get('role') != 'master': return "Unauthorized"
    un, pw = request.form['new_un'], request.form['new_pw']
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'client')", (un, pw))
        conn.commit()
    except: pass
    conn.close()
    return redirect('/dashboard')

@app.route('/delete_user/<int:id>')
def delete_user(id):
    if session.get('role') != 'master': return "Unauthorized"
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=? AND role='client'", (id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

@app.route('/run_gps', methods=['POST'])
def run_gps():
    # Simulation logic (Same as before)
    return jsonify({"status": "ok"})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))