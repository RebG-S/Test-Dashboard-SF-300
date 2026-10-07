import json
import os
from dotenv import load_dotenv
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

load_dotenv()

WHITELIST_FILE = 'whitelist.json'

def get_cisco_config():
    return {
        'device_type': 'cisco_s300',
        'host': os.getenv('CISCO_HOST', '192.168.1.2'),
        'username': os.getenv('CISCO_USER', 'cisco'),
        'password': os.getenv('CISCO_PASSWORD', ''),
    }

def load_whitelist():
    if not os.path.exists(WHITELIST_FILE):
        default_data = {
            'fa1': '192.168.1.100 (Host-1)',
            'fa2': '192.168.1.50 (Host-2)',
            'fa3': '192.168.1.126 (Host-3)',
            'gi1': '192.168.1.1 (Gateway)'
        }
        save_whitelist(default_data)
        return default_data

    with open(WHITELIST_FILE, 'r') as f:
        return json.load(f)

def save_whitelist(data):
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_switch_status():
    try:
        net_connect = ConnectHandler(**get_cisco_config())
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
    try:
        net_connect = ConnectHandler(**get_cisco_config())
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