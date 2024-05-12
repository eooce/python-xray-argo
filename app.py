import os
import re
import shutil
import subprocess
import http.server
import socketserver
import threading
import requests
from flask import Flask
import json
import time
import base64

app = Flask(__name__)

# Set environment variables
FILE_PATH = os.environ.get('FILE_PATH', './temp')
PROJECT_URL = os.environ.get('URL', '') # 填写项目分配的url可实现自动访问，例如：https://www.google.com，留空即不启用该功能
INTERVAL_SECONDS = int(os.environ.get("TIME", 120))                   # 访问间隔时间，默认120s，单位：秒
UUID = os.environ.get('UUID', 'abe2f2de-13ae-4f1f-bea5-d6c881ca3888')
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'nz.abcd.com')        # 哪吒3个变量不全不运行
NEZHA_PORT = os.environ.get('NEZHA_PORT', '5555')                  # 哪吒端口为{443,8443,2096,2087,2083,2053}其中之一时开启tls
NEZHA_KEY = os.environ.get('NEZHA_KEY', '')
ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', '')                   # 国定隧道域名，留空即启用临时隧道
ARGO_AUTH = os.environ.get('ARGO_AUTH', '')                      # 国定隧道json或token，留空即启用临时隧道
CFIP = os.environ.get('CFIP', 'skk.moe')
NAME = os.environ.get('NAME', 'Vls')
PORT = int(os.environ.get('SERVER_PORT') or os.environ.get('PORT') or 3000)  # 订阅端口，游戏玩具类若无法订阅可改为分配的端口
ARGO_PORT = int(os.environ.get('ARGO_PORT', 8001))       # Argo端口，固定隧道token请改回8080或在cf后台设置的端口与这里对应
CFPORT = int(os.environ.get('CFPORT', 443))           # 节点端口

# Create directory if it doesn't exist
if not os.path.exists(FILE_PATH):
    os.makedirs(FILE_PATH)
    print(f"{FILE_PATH} has been created")
else:
    print(f"{FILE_PATH} already exists")

# Clean old files
paths_to_delete = ['boot.log', 'list.txt','sub.txt', 'npm', 'web', 'bot', 'tunnel.yml', 'tunnel.json']
for file in paths_to_delete:
    file_path = os.path.join(FILE_PATH, file)
    try:
        os.unlink(file_path)
        print(f"{file_path} has been deleted")
    except Exception as e:
        print(f"Skip Delete {file_path}")

# http server
class MyHandler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Hello, world')
        elif self.path == '/sub':
            try:
                with open(os.path.join(FILE_PATH, 'sub.txt'), 'rb') as file:
                    content = file.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'Error reading file')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')

httpd = socketserver.TCPServer(('', PORT), MyHandler)
server_thread = threading.Thread(target=httpd.serve_forever)
server_thread.daemon = True
server_thread.start()

# Generate xr-ay config file
def generate_config():
    config ={"log":{"access":"/dev/null","error":"/dev/null","loglevel":"none",},"inbounds":[{"port":ARGO_PORT ,"protocol":"vless","settings":{"clients":[{"id":UUID ,"flow":"xtls-rprx-vision",},],"decryption":"none","fallbacks":[{"dest":3001 },{"path":"/vless","dest":3002 },{"path":"/vmess","dest":3003 },{"path":"/trojan","dest":3004 },],},"streamSettings":{"network":"tcp",},},{"port":3001 ,"listen":"127.0.0.1","protocol":"vless","settings":{"clients":[{"id":UUID },],"decryption":"none"},"streamSettings":{"network":"ws","security":"none"}},{"port":3002 ,"listen":"127.0.0.1","protocol":"vless","settings":{"clients":[{"id":UUID ,"level":0 }],"decryption":"none"},"streamSettings":{"network":"ws","security":"none","wsSettings":{"path":"/vless"}},"sniffing":{"enabled":True ,"destOverride":["http","tls","quic"],"metadataOnly":False }},{"port":3003 ,"listen":"127.0.0.1","protocol":"vmess","settings":{"clients":[{"id":UUID ,"alterId":0 }]},"streamSettings":{"network":"ws","wsSettings":{"path":"/vmess"}},"sniffing":{"enabled":True ,"destOverride":["http","tls","quic"],"metadataOnly":False }},{"port":3004 ,"listen":"127.0.0.1","protocol":"trojan","settings":{"clients":[{"password":UUID },]},"streamSettings":{"network":"ws","security":"none","wsSettings":{"path":"/trojan"}},"sniffing":{"enabled":True ,"destOverride":["http","tls","quic"],"metadataOnly":False }},],"dns":{"servers":["https+local://8.8.8.8/dns-query"]},"outbounds":[{"protocol":"freedom"},{"tag":"WARP","protocol":"wireguard","settings":{"secretKey":"YFYOAdbw1bKTHlNNi+aEjBM3BO7unuFC5rOkMRAz9XY=","address":["172.16.0.2/32","2606:4700:110:8a36:df92:102a:9602:fa18/128"],"peers":[{"publicKey":"bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=","allowedIPs":["0.0.0.0/0","::/0"],"endpoint":"162.159.193.10:2408"}],"reserved":[78 ,135 ,76 ],"mtu":1280 }},],"routing":{"domainStrategy":"AsIs","rules":[{"type":"field","domain":["domain:openai.com","domain:ai.com"],"outboundTag":"WARP"},]}}
    with open(os.path.join(FILE_PATH, 'config.json'), 'w', encoding='utf-8') as config_file:
        json.dump(config, config_file, ensure_ascii=False, indent=2)

generate_config()

# Determine system architecture
def get_system_architecture():
    arch = os.uname().machine
    if 'arm' in arch or 'aarch64' in arch or 'arm64' in arch:
        return 'arm'
    else:
        return 'amd'

# Download file
def download_file(file_name, file_url):
    file_path = os.path.join(FILE_PATH, file_name)
    with requests.get(file_url, stream=True) as response, open(file_path, 'wb') as file:
        shutil.copyfileobj(response.raw, file)

# Download and run files
def download_files_and_run():
    architecture = get_system_architecture()
    files_to_download = get_files_for_architecture(architecture)

    if not files_to_download:
        print("Can't find a file for the current architecture")
        return

    for file_info in files_to_download:
        try:
            download_file(file_info['file_name'], file_info['file_url'])
            print(f"Downloaded {file_info['file_name']} successfully")
        except Exception as e:
            print(f"Download {file_info['file_name']} failed: {e}")

    # Authorize and run
    files_to_authorize = ['./npm', './web', './bot']
    authorize_files(files_to_authorize)

    # Run ne-zha
    NEZHA_TLS = ''
    valid_ports = ['443', '8443', '2096', '2087', '2083', '2053']
    if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
        if NEZHA_PORT in valid_ports:
          NEZHA_TLS = '--tls'
        command = f"nohup {FILE_PATH}/npm -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {NEZHA_TLS} >/dev/null 2>&1 &"
        try:
            subprocess.run(command, shell=True, check=True)
            print('npm is running')
            subprocess.run('sleep 1', shell=True)  # Wait for 1 second
        except subprocess.CalledProcessError as e:
            print(f'npm running error: {e}')
    else:
        print('NEZHA variable is empty, skip running')

    # Run xr-ay
    command1 = f"nohup {FILE_PATH}/web -c {FILE_PATH}/config.json >/dev/null 2>&1 &"
    try:
        subprocess.run(command1, shell=True, check=True)
        print('web is running')
        subprocess.run('sleep 1', shell=True)  # Wait for 1 second
    except subprocess.CalledProcessError as e:
        print(f'web running error: {e}')

    # Run cloud-fared
    if os.path.exists(os.path.join(FILE_PATH, 'bot')):
	# Get command line arguments for cloud-fared
        args = get_cloud_flare_args()
        # print(args)
        try:
            subprocess.run(f"nohup {FILE_PATH}/bot {args} >/dev/null 2>&1 &", shell=True, check=True)
            print('bot is running')
            subprocess.run('sleep 2', shell=True)  # Wait for 2 seconds
        except subprocess.CalledProcessError as e:
            print(f'Error executing command: {e}')

    subprocess.run('sleep 3', shell=True)  # Wait for 3 seconds
	
   
def get_cloud_flare_args():
    
    processed_auth = ARGO_AUTH
    try:
        auth_data = json.loads(ARGO_AUTH)
        if 'TunnelSecret' in auth_data and 'AccountTag' in auth_data and 'TunnelID' in auth_data:
            processed_auth = 'TunnelSecret'
    except json.JSONDecodeError:
        pass

    # Determines the condition and generates the corresponding args
    if not processed_auth and not ARGO_DOMAIN:
        args = f'tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{ARGO_PORT}'
    elif processed_auth == 'TunnelSecret':
        args = f'tunnel --edge-ip-version auto --config {FILE_PATH}/tunnel.yml run'
    elif processed_auth and ARGO_DOMAIN and 120 <= len(processed_auth) <= 250:
        args = f'tunnel --edge-ip-version auto --no-autoupdate --protocol http2 run --token {processed_auth}'
    else:
        # Default args for other cases
        args = f'tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{ARGO_PORT}'

    return args

# Return file information based on system architecture
def get_files_for_architecture(architecture):
    if architecture == 'arm':
        return [
            {'file_name': 'npm', 'file_url': 'https://github.com/eooce/test/releases/download/ARM/swith'},
            {'file_name': 'web', 'file_url': 'https://github.com/eooce/test/releases/download/ARM/web'},
            {'file_name': 'bot', 'file_url': 'https://github.com/eooce/test/releases/download/arm64/bot13'},
        ]
    elif architecture == 'amd':
        return [
            {'file_name': 'npm', 'file_url': 'https://github.com/eooce/test/releases/download/amd64/npm'},
            {'file_name': 'web', 'file_url': 'https://github.com/eooce/test/releases/download/amd64/web'},
            {'file_name': 'bot', 'file_url': 'https://github.com/eooce/test/releases/download/amd64/bot13'},
        ]
    return []

# Authorize files
def authorize_files(file_paths):
    new_permissions = 0o775

    for relative_file_path in file_paths:
        absolute_file_path = os.path.join(FILE_PATH, relative_file_path)
        try:
            os.chmod(absolute_file_path, new_permissions)
            print(f"Empowerment success for {absolute_file_path}: {oct(new_permissions)}")
        except Exception as e:
            print(f"Empowerment failed for {absolute_file_path}: {e}")


# Get fixed tunnel JSON and yml
def argo_config():
    if not ARGO_AUTH or not ARGO_DOMAIN:
        print("ARGO_DOMAIN or ARGO_AUTH is empty, use quick Tunnels")
        return

    if 'TunnelSecret' in ARGO_AUTH:
        with open(os.path.join(FILE_PATH, 'tunnel.json'), 'w') as file:
            file.write(ARGO_AUTH)
        tunnel_yaml = f"""
tunnel: {ARGO_AUTH.split('"')[11]}
credentials-file: {os.path.join(FILE_PATH, 'tunnel.json')}
protocol: http2

ingress:
  - hostname: {ARGO_DOMAIN}
    service: http://localhost:{ARGO_PORT}
    originRequest:
      noTLSVerify: true
  - service: http_status:404
  """
        with open(os.path.join(FILE_PATH, 'tunnel.yml'), 'w') as file:
            file.write(tunnel_yaml)
    else:
        print("Use token connect to tunnel")

argo_config()

# Get temporary tunnel domain
def extract_domains():
    argo_domain = ''

    if ARGO_AUTH and ARGO_DOMAIN:
        argo_domain = ARGO_DOMAIN
        print('ARGO_DOMAIN:', argo_domain)
        generate_links(argo_domain)
    else:
        try:
            with open(os.path.join(FILE_PATH, 'boot.log'), 'r', encoding='utf-8') as file:
                content = file.read()
                # Use regular expressions to match domain ending in trycloudflare.com
                match = re.search(r'https://([^ ]+\.trycloudflare\.com)', content)
                if match:
                    argo_domain = match.group(1)
                    print('ArgoDomain:', argo_domain)
                    generate_links(argo_domain)
                else:
                    print('ArgoDomain not found, re-running bot to obtain ArgoDomain')
                    # delete boot.log file
                    os.remove(os.path.join(FILE_PATH, 'boot.log'))
                    # Rerun the bot directly to get the ArgoDomain.
                    args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {FILE_PATH}/boot.log --loglevel info --url http://localhost:{ARGO_PORT}"
                    try:
                        subprocess.run(f"nohup {FILE_PATH}/bot {args} >/dev/null 2>&1 &", shell=True, check=True)
                        print('bot is running')
                        time.sleep(3)
                        # Retrieve domain name
                        extract_domains()
                    except subprocess.CalledProcessError as e:
                        print(f"Error executing command: {e}")
        except IndexError as e:
            print(f"IndexError while reading boot.log: {e}")
        except Exception as e:
            print(f"Error reading boot.log: {e}")


# Generate list and sub info
def generate_links(argo_domain):
    meta_info = subprocess.run(['curl', '-s', 'https://speed.cloudflare.com/meta'], capture_output=True, text=True)
    meta_info = meta_info.stdout.split('"')
    ISP = f"{meta_info[25]}-{meta_info[17]}".replace(' ', '_').strip()

    time.sleep(2)
    VMESS = {"v": "2", "ps": f"{NAME}-{ISP}", "add": CFIP, "port": CFPORT, "id": UUID, "aid": "0", "scy": "none", "net": "ws", "type": "none", "host": argo_domain, "path": "/vmess?ed=2048", "tls": "tls", "sni": argo_domain, "alpn": ""}
 
    list_txt = f"""
vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2Fvless%3Fed%3D2048#{NAME}-{ISP}
  
vmess://{ base64.b64encode(json.dumps(VMESS).encode('utf-8')).decode('utf-8')}

trojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2Ftrojan%3Fed%3D2048#{NAME}-{ISP}
    """
    
    with open(os.path.join(FILE_PATH, 'list.txt'), 'w', encoding='utf-8') as list_file:
        list_file.write(list_txt)

    sub_txt = base64.b64encode(list_txt.encode('utf-8')).decode('utf-8')
    with open(os.path.join(FILE_PATH, 'sub.txt'), 'w', encoding='utf-8') as sub_file:
        sub_file.write(sub_txt)
        
    try:
        with open(os.path.join(FILE_PATH, 'sub.txt'), 'rb') as file:
            sub_content = file.read()
        print(f"\n{sub_content.decode('utf-8')}")
    except FileNotFoundError:
        print(f"sub.txt not found")
    
    print(f'{FILE_PATH}/sub.txt saved successfully')
    time.sleep(20)

    # cleanup files
    files_to_delete = ['boot.log', 'list.txt','config.json','tunnel.yml','tunnel.json']
    for file_to_delete in files_to_delete:
        file_path_to_delete = os.path.join(FILE_PATH, file_to_delete)
        try:
            os.remove(file_path_to_delete)
            print(f"{file_path_to_delete} has been deleted")
        except Exception as e:
            print(f"Error deleting {file_path_to_delete}: {e}")

    print('\033c', end='')
    print('App is running')
    print('Thank you for using this script, enjoy!')
         
# Run the callback
def start_server():
    download_files_and_run()
    extract_domains()
    
start_server()

# auto visit project page
has_logged_empty_message = False

def visit_project_page():
    try:
        if not PROJECT_URL or not INTERVAL_SECONDS:
            global has_logged_empty_message
            if not has_logged_empty_message:
                print("URL or TIME variable is empty, Skipping visit web")
                has_logged_empty_message = True
            return

        response = requests.get(PROJECT_URL)
        response.raise_for_status() 

        # print(f"Visiting project page: {PROJECT_URL}")
        print("Page visited successfully")
        print('\033c', end='')
    except requests.exceptions.RequestException as error:
        print(f"Error visiting project page: {error}")

if __name__ == "__main__":
    while True:
        visit_project_page()
        time.sleep(INTERVAL_SECONDS)
