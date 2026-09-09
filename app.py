from flask import Flask, render_template, request, redirect, url_for, session
from cisco_helper import get_switch_status, parse_status, change_port_state, load_whitelist, save_whitelist

app = Flask(__name__)
app.secret_key = 'kunci_doang'

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'RebG' and password == 'admin123':
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
    whitelist_data = load_whitelist() # Tarik data JSON buat ditampilin di web
    
    if raw_data["error"]:
        port_data = []
        error_msg = f"GAGAL KONEK: {raw_data['error']}"
    else:
        port_data = parse_status(raw_data)
        error_msg = None
        
        #auto block
        for port in port_data:
            if port['state'] == 'Up' and 'Unknown Device' in port['ip']:
                print(f"Penyusup terdeteksi di {port['port']}! Melakukan Auto-Block...")
                change_port_state(port['port'], 'block')
                port['state'] = 'Down' 
                port['ip'] = 'Penyusup Auto-Blocked!'
                
    return render_template('dashboard.html', username=session['user'], ports=port_data, error=error_msg, whitelist=whitelist_data)

#tambah whitelist
@app.route('/add_whitelist', methods=['POST'])
def add_whitelist():
    if 'user' not in session: return redirect(url_for('login'))
    
    port = request.form.get('port')
    ip_device = request.form.get('ip_device')
    
    whitelist = load_whitelist()
    whitelist[port] = ip_device # Tambah/Update data
    save_whitelist(whitelist)
    
    return redirect(url_for('dashboard'))

#apus whitelist
@app.route('/delete_whitelist/<port>')
def delete_whitelist(port):
    if 'user' not in session: return redirect(url_for('login'))
    
    whitelist = load_whitelist()
    if port in whitelist:
        del whitelist[port] # Hapus data
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