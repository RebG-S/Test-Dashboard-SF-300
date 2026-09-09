import json
import os
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# file database mini
WHITELIST_FILE = 'whitelist.json'

# mini database ---
def load_whitelist():
    # Kalau file json belum ada, otomatis dibikinin sama Python
    if not os.path.exists(WHITELIST_FILE):
        default_data = {
            'fa1': '192.168.1.100 (Laptop Percobaan)',
            'fa2': '192.168.1.50 (Router Dapur)',
            'fa3': '192.168.1.126 (PC Admin)',
            'gi1': '192.168.1.1 (Router Utama)'
        }
        save_whitelist(default_data)
        return default_data
    
    with open(WHITELIST_FILE, 'r') as f:
        return json.load(f)

def save_whitelist(data):
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# cisco
def get_switch_status():
    cisco_sf300 = {
        'device_type': 'cisco_s300', 
        'host': '192.168.1.2',     
        'username': 'cisco',         
        'password': 'PowerOver3t-s',   
    }

    try:
        net_connect = ConnectHandler(**cisco_sf300)
        raw_status = net_connect.send_command('show interfaces status')
        net_connect.disconnect()
        return {"status": raw_status, "error": None}
    except Exception as e:
        return {"status": None, "error": str(e)}

def parse_status(raw_data):
    if raw_data["error"]:
        return []

    raw_status = raw_data["status"]
    parsed_data = []
    
    # data whitelist dari file JSON
    current_whitelist = load_whitelist()
    
    if raw_status:
        lines = raw_status.strip().split('\n')
        start_parsing = False
        
        for line in lines:
            if line.startswith('--------'):
                start_parsing = True
                continue
            
            if start_parsing:
                if not line.strip() or line.startswith('Ch ') or line.startswith('Po'):
                    break
                
                parts = line.split()
                if len(parts) >= 7:
                    port_id = parts[0]
                    state = parts[6]
                    
                    if state == 'Up':
                        # cocokin sama database JSON
                        ip_str = current_whitelist.get(port_id, "Unknown Device (Penyusup?)")
                    else:
                        ip_str = "-"

                    status = {
                        "port": port_id,             
                        "type": parts[1],             
                        "speed": parts[3] if parts[3] != '--' else '-', 
                        "state": state,
                        "ip": ip_str  
                    }
                    parsed_data.append(status)
                
    return parsed_data

def change_port_state(port_interface, action):
    cisco_sf300 = {
        'device_type': 'cisco_s300', 
        'host': '192.168.1.2',     
        'username': 'cisco',         
        'password': 'PowerOver3t-s',   
    }

    try:
        net_connect = ConnectHandler(**cisco_sf300)
        config_commands = [f'interface {port_interface}']
        
        if action == 'block':
            config_commands.append('shutdown')
        elif action == 'unblock':
            config_commands.append('no shutdown')
            
        net_connect.send_config_set(config_commands)
        net_connect.disconnect()
        return True
        
    except Exception as e:
        print(f"Error eksekusi: {e}")
        return False