from flask import Flask, render_template, request, jsonify
import urllib.request
import json
import os
import socket
import subprocess
import re

# Create Flask application serving static files from the current directory
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Attempt to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Optional: Set your Geoapify API key here (or via environment variable) to use it as the primary backend proxy provider
GEOAPIFY_API_KEY = os.environ.get('GEOAPIFY_API_KEY', '')



@app.route('/')
@app.route('/v2')
def index_page():
    """Serve the main dashboard page."""
    return render_template('index.html')



@app.route('/api/lookup')
def lookup():
    """
    Backend GeoIP proxy lookup endpoint.
    Queries external services with server-side network requests to bypass CORS restrictions.
    """
    ip = request.args.get('ip', '').strip()
    
    # Identify target IP
    # If no IP query param, fall back to request remote address (client IP)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Handle multiple proxy IPs if present
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
        
    # If run locally, request.remote_addr is local (127.0.0.1 or ::1).
    # We resolve the server's public IP as an fallback representation of client location.
    if not client_ip or client_ip in ('127.0.0.1', '::1') or client_ip.startswith('192.168.') or client_ip.startswith('10.'):
        try:
            req = urllib.request.Request(
                'https://api.ipify.org?format=json',
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                ipify_data = json.loads(response.read().decode())
                client_ip = ipify_data.get('ip', client_ip)
        except Exception:
            pass # Use local IP fallback if offline or failed
            
    target_ip = ip if ip else client_ip
    
    # --- Try API Candidate 0: Geoapify (if API Key configured) ---
    if GEOAPIFY_API_KEY:
        try:
            url = f"https://api.geoapify.com/v1/ipinfo?ip={target_ip}&apiKey={GEOAPIFY_API_KEY}"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                country_data = data.get('country', {})
                city_data = data.get('city', {})
                loc_data = data.get('location', {})
                tz_data = data.get('timezone', {})
                
                return jsonify({
                    "success": True,
                    "provider": "Geoapify (Backend)",
                    "data": {
                        "ip": data.get("ip", target_ip),
                        "city": city_data.get("name") or "Unknown City",
                        "region": (data.get("subdivisions", [{}])[0].get("name")) if data.get("subdivisions") else "Unknown Region",
                        "country": country_data.get("name") or "Unknown Country",
                        "countryCode": country_data.get("iso_code") or "",
                        "lat": float(loc_data.get("latitude", 0)),
                        "lng": float(loc_data.get("longitude", 0)),
                        "timezone": tz_data.get("name") or "UTC",
                        "isp": "Geoapify Network Provider",
                        "currency": "Local Currency",
                        "zip": "N/A"
                    }
                })
        except Exception as geo_error:
            print(f"Backend Geoapify lookup failed: {geo_error}. Falling back to default proxy chain.")
            
    # --- Try API Candidate 1: ipapi.co ---
    try:
        url = f"https://ipapi.co/{target_ip}/json/"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            
            if data.get('error'):
                raise Exception(data.get('reason', 'IP Lookup Error'))
                
            return jsonify({
                "success": True,
                "provider": "ipapi.co (Backend)",
                "data": {
                    "ip": data.get("ip"),
                    "city": data.get("city") or "Unknown City",
                    "region": data.get("region") or "Unknown Region",
                    "country": data.get("country_name") or "Unknown Country",
                    "countryCode": data.get("country_code") or "",
                    "lat": float(data.get("latitude", 0)),
                    "lng": float(data.get("longitude", 0)),
                    "timezone": data.get("timezone") or "UTC",
                    "isp": data.get("org") or "Unknown Provider",
                    "currency": f"{data.get('currency')} ({data.get('currency_name', '')})" if data.get('currency') else "Unknown",
                    "zip": data.get("postal") or "N/A"
                }
            })
    except Exception as primary_error:
        print(f"Backend Primary lookup failed: {primary_error}. Attempting Failover.")
        
        # --- Try API Candidate 2: ipwhois.app ---
        try:
            url = f"https://ipwhois.app/json/{target_ip}"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                if data.get('success') == False:
                    raise Exception(data.get('message', 'IP Lookup Error'))
                    
                return jsonify({
                    "success": True,
                    "provider": "ipwhois.app (Backend)",
                    "data": {
                        "ip": data.get("ip"),
                        "city": data.get("city") or "Unknown City",
                        "region": data.get("region") or "Unknown Region",
                        "country": data.get("country") or "Unknown Country",
                        "countryCode": data.get("country_code") or "",
                        "lat": float(data.get("latitude", 0)),
                        "lng": float(data.get("longitude", 0)),
                        "timezone": data.get("timezone") or "UTC",
                        "isp": data.get("isp") or data.get("org") or "Unknown Provider",
                        "currency": f"{data.get('currency_code')} ({data.get('currency', '')})" if data.get('currency_code') else "Unknown",
                        "zip": "N/A"
                    }
                })
        except Exception as failover_error:
            return jsonify({
                "success": False,
                "error": f"All backend providers failed: {str(failover_error)}"
            }), 500

def get_port_name(port):
    return {
        21: "FTP",
        22: "SSH",
        80: "HTTP",
        443: "HTTPS",
        3306: "MySQL",
        8080: "HTTP-ALT"
    }.get(port, "Unknown")

@app.route('/api/scan')
def scan():
    """
    Backend port audit utility.
    Attempts TCP handshake to standard ports with short timeout.
    Supports both IPv4 and IPv6 families.
    """
    ip = request.args.get('ip', '').strip()
    if not ip:
        return jsonify({"success": False, "error": "IP address is required"})
    
    # Strip any brackets from IPv6 if sent from client
    ip = ip.replace('[', '').replace(']', '')
    
    # Check family: socket.AF_INET6 for IPv6, else AF_INET
    is_ipv6 = ':' in ip
    family = socket.AF_INET6 if is_ipv6 else socket.AF_INET
    
    ports = [21, 22, 80, 443, 3306, 8080]
    results = []
    
    for port in ports:
        s = socket.socket(family, socket.SOCK_STREAM)
        s.settimeout(0.6)
        try:
            # For connect_ex: IPv6 needs a 4-tuple, IPv4 needs a 2-tuple.
            # socket.connect_ex handles the address tuple accordingly.
            address = (ip, port, 0, 0) if is_ipv6 else (ip, port)
            res = s.connect_ex(address)
            results.append({
                "port": port,
                "name": get_port_name(port),
                "status": "open" if res == 0 else "closed"
            })
        except Exception:
            results.append({
                "port": port,
                "name": get_port_name(port),
                "status": "closed"
            })
        finally:
            s.close()
            
    return jsonify({
        "success": True,
        "ip": ip,
        "ports": results
    })

@app.route('/api/traceroute')
def traceroute():
    """
    Real-time streaming traceroute endpoint.
    Runs system 'tracert' (Windows) or 'traceroute' (Linux) and streams each hop
    via Server-Sent Events (SSE).
    """
    target = request.args.get('ip', '').strip()
    if not target:
        return jsonify({"success": False, "error": "IP address is required"}), 400

    # Clean IP address
    clean_target = target.split(' ')[0].replace('[', '').replace(']', '')

    def generate_hops():
        is_windows = os.name == 'nt'
        cmd = ["tracert", "-d", "-h", "15", clean_target] if is_windows else ["traceroute", "-n", "-m", "15", clean_target]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            for line in iter(process.stdout.readline, ''):
                line_str = line.strip()
                if not line_str:
                    continue

                # Windows tracert regex
                win_match = re.match(r'^(\d+)\s+([\d\*<\s]+ms|[\*]+)\s+([\d\*<\s]+ms|[\*]+)\s+([\d\*<\s]+ms|[\*]+)\s+(.+)$', line_str)
                
                # Linux traceroute regex
                lin_match = re.match(r'^(\d+)\s+([^\s]+)\s+([\d\.\*]+(?:\s+ms)?)\s+([\d\.\*]+(?:\s+ms)?)\s+([\d\.\*]+(?:\s+ms)?)$', line_str)

                if win_match:
                    hop_num = int(win_match.group(1))
                    rtt1 = win_match.group(2).strip()
                    rtt2 = win_match.group(3).strip()
                    rtt3 = win_match.group(4).strip()
                    ip_part = win_match.group(5).strip()

                    is_timeout = "timeout" in ip_part.lower() or ip_part == "*"
                    hop_ip = "" if is_timeout else ip_part

                    data = {
                        "hop": hop_num,
                        "rtt": [rtt1, rtt2, rtt3],
                        "ip": hop_ip,
                        "timeout": is_timeout
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                elif lin_match:
                    hop_num = int(lin_match.group(1))
                    ip_part = lin_match.group(2).strip()
                    rtt1 = lin_match.group(3).strip()
                    rtt2 = lin_match.group(4).strip()
                    rtt3 = lin_match.group(5).strip()

                    is_timeout = ip_part == "*" or "timeout" in ip_part.lower()
                    hop_ip = "" if is_timeout else ip_part

                    data = {
                        "hop": hop_num,
                        "rtt": [rtt1, rtt2, rtt3],
                        "ip": hop_ip,
                        "timeout": is_timeout
                    }
                    yield f"data: {json.dumps(data)}\n\n"

            process.stdout.close()
            process.wait()
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return app.response_class(generate_hops(), mimetype='text/event-stream')


if __name__ == '__main__':
    # Print launch message
    print("\n" + "="*50)
    print(" GeoIP Location Intelligence Server is Running!")
    print(" URL: http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(host='127.0.0.1', port=5000, debug=True)
