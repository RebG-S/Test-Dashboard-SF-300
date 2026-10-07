import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session
from cisco_helper import get_switch_status, parse_status, change_port_state, load_whitelist, save_whitelist

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default-dev-secret-key')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        valid_user = os.getenv('WEB_USERNAME')
        valid_pass = os.getenv('WEB_PASSWORD')

        if username == valid_user and password == valid_pass:
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            return "Login Gagal! Cek lagi username atau password-nya."

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    raw_data = get_switch_status()
    whitelist_data = load_whitelist()

    if raw_data["error"]:
        port_data = []
        error_msg = f"GAGAL KONEK: {raw_data['error']}"
    else:
        port_data = parse_status(raw_data)
        error_msg = None

        for port in port_data:
            if port['state'] == 'Up' and 'Unknown Device' in port['ip']:
                print(f"Penyusup terdeteksi di {port['port']}! Melakukan Auto-Block...")
                change_port_state(port['port'], 'block')
                port['state'] = 'Down' 
                port['ip'] = 'Penyusup Auto-Blocked!'

    return render_template('dashboard.html', username=session['user'], ports=port_data, error=error_msg, whitelist=whitelist_data)

@app.route('/add_whitelist', methods=['POST'])
def add_whitelist():
    if 'user' not in session: return redirect(url_for('login'))

    port = request.form.get('port')
    ip_device = request.form.get('ip_device')

    whitelist = load_whitelist()
    whitelist[port] = ip_device
    save_whitelist(whitelist)

    return redirect(url_for('dashboard'))

@app.route('/delete_whitelist/<port>')
def delete_whitelist(port):
    if 'user' not in session: return redirect(url_for('login'))

    whitelist = load_whitelist()
    if port in whitelist:
        del whitelist[port]
        save_whitelist(whitelist)

    return redirect(url_for('dashboard'))

@app.route('/action/<action_type>/<port_id>')
def port_action(action_type, port_id):
    if 'user' not in session: return redirect(url_for('login'))
    if action_type in ['block', 'unblock']:
        change_port_state(port_id, action_type)
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)