from flask import Flask, render_template, jsonify
import os
import requests
import subprocess
import re
import a2s  # Using python-a2s for server querying
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

API_TOKEN = os.getenv("API_TOKEN")
API_BASE_URL = "https://api.zerotier.com/api/v1"

# Function to fetch the ZeroTier virtual IP from the command line using `zerotier-cli`
def get_zerotier_ip():
    try:
        # Correct path to the zerotier-cli.bat script
        result = subprocess.run(
            [r"C:\Program Files (x86)\ZeroTier\One\zerotier-cli.bat", "listnetworks"], 
            capture_output=True, text=True
        )
        
        # Check for errors in running the command
        if result.returncode != 0:
            print(f"Error running zerotier-cli: {result.stderr}")
            return "Not Found"
        
        # Process the output to extract the IP address
        output = result.stdout
        print(f"Output from zerotier-cli: {output}")  # Debug log
        
        # Updated regex to handle CIDR notation
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)(?:/\d+)?", output)
        if match:
            ip = match.group(1)  # Extract only the IP address without the CIDR
            return ip
        else:
            print("No IP address found in the output.")
            return "Not Found"
    
    except Exception as e:
        print(f"Error: {e}")
        return "Not Found"


# Function to query the CS2 server using python-a2s
def get_server_info():
    server_ip = get_zerotier_ip()
    server_port = 27015  # Default CS2 server port
    if server_ip == "Not Found":
        return {"error": "ZeroTier IP not found"}
    
    try:
        # Query server info using python-a2s
        info = a2s.info((server_ip, server_port))
        players = a2s.players((server_ip, server_port))
        
        return {
            "name": info.server_name,
            "map": info.map_name,
            "players": len(players),
            "max_players": info.max_players,
            "ip": f"{server_ip}:{server_port}",
        }
    except Exception as e:
        print(f"Error querying server: {e}")
        return {"error": "Unable to fetch server info", "details": str(e)}

# Flask route to display the main page
@app.route("/")
def home():
    networks = get_networks()
    zerotier_ip = get_zerotier_ip()
    print(f"ZeroTier IP: {zerotier_ip}")
    
    return render_template("index.html", networks=networks, zerotier_ip=zerotier_ip)

# Flask route to fetch server info dynamically
@app.route("/server-info")
def server_info():
    return jsonify(get_server_info())

# Function to get networks from ZeroTier API
def get_networks():
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }
    response = requests.get(f"{API_BASE_URL}/network", headers=headers)
    if response.status_code == 200:
        networks = response.json()
        return [
            {
                "name": network.get("config", {}).get("name", "N/A"),
                "id": network.get("id", "N/A"),
                "status": "Active" if network.get("config", {}).get("enabled") else "Disabled"
            }
            for network in networks
        ]
    else:
        print("Failed to fetch networks from ZeroTier API")
        return []

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
