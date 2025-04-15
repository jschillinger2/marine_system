import time
import os
import psutil
import requests
import threading
import websocket
import json
from flask import Flask, request, render_template_string
from requests.auth import HTTPBasicAuth

# === Load config from properties file ===
def load_properties(file_path):
    props = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    props[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error reading config file: {e}")
    return props

# === Config ===
config = load_properties('config.properties')
SIGNALK_SERVER = config.get('signalk_url', 'localhost:3000').replace('http://', '').replace('/', '')
USERNAME = config.get('signalk_username', '')
PASSWORD = config.get('signalk_password', '')

token = ""
ws = None

app = Flask(__name__)

# === Authenticate to Signal K ===
def authenticate_signal_k():
    global token
    login_url = f"http://{SIGNALK_SERVER}/signalk/v1/auth/login"
    payload = {"username": USERNAME, "password": PASSWORD}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(login_url, json=payload, headers=headers)
        response.raise_for_status()
        token = response.json().get('token', '')
        print(f"Authenticated with Signal K. Token: {token}")
    except Exception as e:
        print(f"Authentication failed: {e}")
        exit(1)


# === Send value to Signal K over WebSocket ===
def send_to_signalk(path, value):
    global ws
    if not ws or not hasattr(ws, 'sock') or not ws.sock or not ws.sock.connected:
        print("WebSocket not connected.")
        return

    data = {
        "context": "vessels.self",
        "updates": [
            {
                "source": {"label": "marine_system"},
                "values": [
                    {"path": path, "value": value}
                ]
            }
        ]
    }
    try:
        ws.send(json.dumps(data))
        print(f"Sent to Signal K: {path} = {value} \n {data}")
    except Exception as e:
        print(f"WebSocket send error: {e}")
        
# === WebSocket connection ===
def connect_websocket():
    global ws
    url = f"ws://{SIGNALK_SERVER}/signalk/v1/stream?token={token}"
    print(f"Connecting to WebSocket: {url}")

    def on_open(ws):
        print("WebSocket connection opened.")

    def on_close(ws, close_status_code, close_msg):
        print("WebSocket closed. Code:", close_status_code, "Msg:", close_msg)

    def on_error(ws, error):
        print("WebSocket error:", error)

    ws = websocket.WebSocketApp(url,
                                 on_open=on_open,
                                 on_close=on_close,
                                 on_error=on_error)
    threading.Thread(target=ws.run_forever, daemon=True).start()

# === Get LTE signal strength via mmcli ===
def get_lte_signal_strength():
    try:
        output = os.popen("mmcli -m 0 | grep 'signal quality'").read()
        if '%' in output:
            strength_str = output.split(':')[-1].strip().replace('%', '')
            return float(strength_str)
    except Exception as e:
        print(f"Error getting LTE signal: {e}")
    return None

# === System monitoring function ===
def monitor_and_send():

    while True:
        try:
            cpu_temp_output = os.popen("vcgencmd measure_temp").readline()
            if "temp=" in cpu_temp_output:
                temp_val = cpu_temp_output.split('=')[1].replace("'C\n", "")
                cpu_temp = float(temp_val)
                send_to_signalk("environment.rpi.cpu.temperature", cpu_temp)
        except Exception as e:
            print(f"CPU temp error: {e}")

        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            send_to_signalk("environment.rpi.cpu.usage", cpu_usage)
        except Exception as e:
            print(f"CPU usage error: {e}")

        try:
            with open('/proc/uptime', 'r') as f:
                uptime = float(f.readline().split()[0])
                send_to_signalk("environment.rpi.uptime", uptime)
        except Exception as e:
            print(f"Uptime error: {e}")

        try:
            lte_signal = get_lte_signal_strength()
            if lte_signal is not None:
                send_to_signalk("environment.lte.signal.strength", lte_signal)
        except Exception as e:
            print(f"LTE signal error: {e}")

        time.sleep(10)

# === Flask HTML UI ===
@app.route("/")
def index():
    return render_template_string("""

   

        <!DOCTYPE html>
        <html>
        <head>
            <title>Shutdown Control</title>
            <style>
                body {
                    background-color: #121212;
                    color: #ffffff;
                    font-family: Arial, sans-serif;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                }
                h1 {
                    margin-bottom: 2em;
                }
                button {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 1em 2em;
                    font-size: 1.2em;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: background-color 0.3s;
                }
                button:hover {
                    background-color: #1976D2;
                }
            </style>
            <script>
                function confirmShutdown() {
                    if (confirm("Are you sure you want to shut down?")) {
                        document.getElementById('shutdownForm').submit();
                    }
                }
            </script>
        </head>
        <body>
            <form id="shutdownForm" action="/trigger_shutdown" method="post">
                <button type="button" onclick="confirmShutdown()">Trigger Shutdown</button>
            </form>
        </body>
        </html>
    
    """)

@app.route("/trigger_shutdown", methods=["POST"])
def trigger_shutdown():
    print("SHUTDOWN")
    os.system("sudo shutdown -h now")
    return "Shutdown Triggered via Signal K"

# === Main entry point ===
if __name__ == "__main__":
    authenticate_signal_k()
    connect_websocket()

    threading.Thread(target=monitor_and_send, daemon=True).start()

    app.run(host='0.0.0.0', port=8080)
