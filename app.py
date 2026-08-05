#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import base64
import re
import time
import platform
import signal
import threading
import subprocess
import ctypes
import shutil
import datetime
import requests
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse, quote
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from cryptography.hazmat.primitives.asymmetric import x25519, ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID

load_dotenv() # .env 环境变量加载

# =========================== 环境变量 ===========================
UPLOAD_URL = os.environ.get('UPLOAD_URL', '')        # 订阅或节点自动上传地址
PROJECT_URL = os.environ.get('PROJECT_URL', '')      # 项目分配的url,用于自动保活或订阅上传
AUTO_ACCESS = os.environ.get('AUTO_ACCESS', '')      # false关闭自动保活，true开启,默认关闭
SUB_PATH = os.environ.get('SUB_PATH', 'sub')         # 订阅token
FILE_PATH = Path(os.getcwd()) / (os.environ.get('FILE_PATH') or '.cache')  # sub.txt订阅文件路径
UUID = os.environ.get('UUID', '0a6568ff-ea3c-4271-9020-450560e10d63')    # UUID
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', '')    # 哪吒面板地址
NEZHA_PORT = os.environ.get('NEZHA_PORT', '')        # v0 agent端口
NEZHA_KEY = os.environ.get('NEZHA_KEY', '')          # v1的NZ_CLIENT_SECRET或v0 agent密钥
ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', '')      # argo固定隧道域名，留空使用临时隧道
ARGO_AUTH = os.environ.get('ARGO_AUTH', '')           # argo固定隧道token或json,留空使用临时隧道
ARGO_PORT = os.environ.get('ARGO_PORT', '8001')       # argo隧道端口,使用token时需在cloudflare里设置和这里一致
S5_PORT = os.environ.get('S5_PORT', '')               # socks5端口
HY2_PORT = os.environ.get('HY2_PORT', '')             # hy2端口
REALITY_PORT = os.environ.get('REALITY_PORT', '')     # reality端口
CFIP = os.environ.get('CFIP', 'saas.sin.fan')         # 优选域名或优选IP
CFPORT = os.environ.get('CFPORT', '443')              # 优选端口
PORT = int(os.environ.get('PORT', '3000'))            # http订阅端口
NAME = os.environ.get('NAME', '')                     # 节点名称
CHAT_ID = os.environ.get('CHAT_ID', '')               # Telegram chat_id
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')           # Telegram bot_token
DISABLE_ARGO = os.environ.get('DISABLE_ARGO', 'false')  # true禁用argo
SHOW_LOG = os.environ.get('SHOW_LOG', 'true').lower() not in ('false', 'disable', 'no') # 是否显示日志，默认显示，no/false/disable 屏蔽

# 日志控制 
def log(msg):
    if SHOW_LOG:
        print(msg)

def log_error(msg):
    if SHOW_LOG:
        print(msg, file=sys.stderr)

def always_log(msg):
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()

# 全局常量 
private_key = ''
public_key = ''
sub_txt_content = ''
services = []
sub_path = FILE_PATH / 'sub.txt'
list_path = FILE_PATH / 'list.txt'
boot_log_path = FILE_PATH / 'boot.log'
config_path = FILE_PATH / 'config.json'
nezha_config_path = FILE_PATH / 'config.yaml'
xray_lib_path = FILE_PATH / 'web.so'
bot_lib_path = FILE_PATH / 'bot.so'
nezha_lib_path = FILE_PATH / 'v1.so'
cert_path = FILE_PATH / 'cert.pem'
key_path = FILE_PATH / 'private.key'

# 创建运行文件夹
FILE_PATH.mkdir(parents=True, exist_ok=True)

# 端口检查
def is_valid_port(port):
    try:
        if port is None or port == '':
            return False
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            return False
        return True
    except (ValueError, TypeError):
        return False

# X25519 密钥对生成
def generate_x25519_keypair():
    """使用 cryptography 库生成 X25519 密钥对，返回 base64url 编码的私钥和公钥"""
    priv = x25519.X25519PrivateKey.generate()
    pub = priv.public_key()
    # Raw 格式直接输出 32 字节私钥/公钥
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    # base64url 编码，去掉 padding
    return {
        'privateKey': base64.urlsafe_b64encode(priv_bytes).decode().rstrip('='),
        'publicKey': base64.urlsafe_b64encode(pub_bytes).decode().rstrip('=')
    }

# sha-256证书指纹计算 
def get_certificate_fingerprint(cert_file):
    """计算证书的 SHA-256 指纹，优先用 openssl，不可用时用 cryptography 兜底"""
    # 方案1: 优先用 openssl
    try:
        result = subprocess.run(
            ['openssl', 'x509', '-noout', '-fingerprint', '-sha256', '-in', str(cert_file)],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            match = re.search(r'=(.+)$', output)
            if match and match.group(1):
                return match.group(1).upper()
    except Exception:
        pass

    # 方案2: cryptography 兜底
    try:
        with open(cert_file, 'rb') as f:
            cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data)
        fingerprint = cert.fingerprint(hashes.SHA256())
        return ':'.join(f'{b:02X}' for b in fingerprint)
    except Exception as e:
        log_error(f'Failed to calculate certificate fingerprint: {e}')
        return ''

# ctypes 服务管理 
class Service:
    """使用 ctypes 加载 .so 共享库，管理原生服务的启动和停止"""
    def __init__(self, name, library_path, start_symbol, stop_symbol, payload):
        self.name = name
        self.lib = ctypes.CDLL(str(library_path))
        # 配置 start 函数: int start(char* payload)
        self.start_fn = getattr(self.lib, start_symbol)
        self.start_fn.argtypes = [ctypes.c_char_p]
        self.start_fn.restype = ctypes.c_int
        # 配置 stop 函数: int stop()
        self.stop_fn = getattr(self.lib, stop_symbol)
        self.stop_fn.argtypes = []
        self.stop_fn.restype = ctypes.c_int
        self.payload = payload or ''
        self.thread = None

    def start(self):
        """在守护线程中启动服务（Go 的 Start 函数会阻塞直到 Stop 被调用）"""
        def run():
            try:
                code = self.start_fn(self.payload.encode('utf-8') if self.payload else b'')
                if code != 0:
                    log(f'{self.name} native service exited with code {code}')
            except Exception as e:
                log(f'{self.name} native service failed: {e}')
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        """停止服务（Go 的 Stop 函数是非阻塞的，只发送关闭信号）"""
        try:
            return self.stop_fn()
        except Exception:
            return -1

# Payload 配置生成 
def xray_payload():
    return json.dumps({'config': str(config_path)}, separators=(',', ':'))

def cloudflared_payload():
    if DISABLE_ARGO == 'true':
        return None
    if ARGO_AUTH and ARGO_DOMAIN:
        if re.match(r'^[A-Z0-9a-z=]{120,250}$', ARGO_AUTH):
            return json.dumps({
                'args': ['tunnel', '--edge-ip-version', 'auto', '--no-autoupdate',
                         '--protocol', 'http2', 'run', '--token', ARGO_AUTH]
            }, separators=(',', ':'))
        elif 'TunnelSecret' in ARGO_AUTH:
            return json.dumps({
                'args': ['tunnel', '--edge-ip-version', 'auto',
                         '--config', str(FILE_PATH / 'tunnel.yml'), 'run']
            }, separators=(',', ':'))
    # Quick tunnel
    return json.dumps({
        'args': [
            'tunnel', '--edge-ip-version', 'auto', '--no-autoupdate',
            '--protocol', 'http2', '--logfile', str(boot_log_path),
            '--loglevel', 'info', '--url', f'http://localhost:{ARGO_PORT}'
        ]
    }, separators=(',', ':'))

def nezha_payload():
    if NEZHA_PORT:
        # v0 模式 - 使用命令行参数
        tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']
        use_tls = NEZHA_PORT in tls_ports
        args = [
            '-s', f'{NEZHA_SERVER}:{NEZHA_PORT}',
            '-p', NEZHA_KEY,
            '--disable-auto-update',
            '--report-delay', '4',
            '--skip-conn',
            '--skip-procs'
        ]
        if use_tls:
            args.append('--tls')
        return json.dumps({'args': args}, separators=(',', ':'))
    # v1 模式 - 使用配置文件
    return json.dumps({'config': str(nezha_config_path)}, separators=(',', ':'))

#  核心文件下载
def download_file(file_name, file_url):
    file_path = FILE_PATH / file_name
    try:
        response = requests.get(file_url, stream=True, timeout=180)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        log(f'Download {file_name} successfully')
        return str(file_path)
    except Exception as e:
        log_error(f'Download {file_name} failed: {e}')
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass
        raise

def download_all_files():
    architecture = get_system_architecture()
    base_url = 'https://arm64.ssss.nyc.mn' if architecture == 'arm' else 'https://amd64.ssss.nyc.mn'

    downloads = []
    # web.so
    downloads.append({'name': 'web.so', 'url': f'{base_url}/web.so'})
    # bot.so (cloudflared)
    if DISABLE_ARGO != 'true':
        downloads.append({'name': 'bot.so', 'url': f'{base_url}/bot.so'})
    # v1.so (nezha)
    if NEZHA_SERVER and NEZHA_KEY:
        downloads.append({'name': 'v1.so', 'url': f'{base_url}/v1.so'})
    else:
        log('NEZHA variable is empty, skipping nezha-agent')

    for item in downloads:
        try:
            download_file(item['name'], item['url'])
        except Exception as e:
            log_error(f'Error downloading {item["name"]}: {e}')

# 清理历史文件 
PATHS_TO_DELETE = ['boot.log', 'list.txt', 'web.so', 'bot.so', 'v1.so', 'config.json', 'config.yaml']

def cleanup_old_files():
    for file_name in PATHS_TO_DELETE:
        file_path = FILE_PATH / file_name
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass
    tmp_dir = Path(os.getcwd()) / '.tmp'
    if tmp_dir.exists():
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass

# Argo 隧道配置
def argo_type():
    if DISABLE_ARGO == 'true':
        log('DISABLE_ARGO is set to true, disable argo tunnel')
        return

    if not ARGO_AUTH or not ARGO_DOMAIN:
        log('ARGO_DOMAIN or ARGO_AUTH variable is empty, use quick tunnels')
        return

    if 'TunnelSecret' in ARGO_AUTH:
        (FILE_PATH / 'tunnel.json').write_text(ARGO_AUTH, encoding='utf-8')
        tunnel_id = ARGO_AUTH.split('"')[11]
        tunnel_yaml = f"""
tunnel: {tunnel_id}
credentials-file: {FILE_PATH / 'tunnel.json'}
protocol: http2

ingress:
  - hostname: {ARGO_DOMAIN}
    service: http://localhost:{ARGO_PORT}
    originRequest:
      noTLSVerify: true
  - service: http_status:404
"""
        (FILE_PATH / 'tunnel.yml').write_text(tunnel_yaml, encoding='utf-8')
    else:
        log(f'Using token connect to tunnel, please set {ARGO_PORT} in cloudflare')

# 判断系统架构
def get_system_architecture():
    arch = platform.machine()
    if arch in ('arm', 'arm64', 'aarch64'):
        return 'arm'
    return 'amd'

# 删除订阅器上的旧节点
def delete_nodes():
    try:
        if not UPLOAD_URL:
            return
        if not sub_path.exists():
            return
        content = sub_path.read_text(encoding='utf-8')
        decoded = base64.b64decode(content).decode('utf-8')
        nodes = [line for line in decoded.split('\n')
                 if re.match(r'(vless|vmess|trojan|hysteria2)://', line)]
        if not nodes:
            return
        requests.post(f'{UPLOAD_URL}/api/delete-nodes',
                       json={'nodes': nodes},
                       timeout=10)
    except Exception:
        pass

# Nezha 配置生成
def generate_nezha_config():
    if not NEZHA_SERVER or not NEZHA_KEY:
        return
    if NEZHA_PORT:
        return  # v0 模式不需要 config.yaml

    nzport = NEZHA_SERVER.split(':')[-1] if ':' in NEZHA_SERVER else ''
    tls_ports = {'443', '8443', '2096', '2087', '2083', '2053'}
    nezhatls = 'true' if nzport in tls_ports else 'false'
    config_yaml = f"""client_secret: {NEZHA_KEY}
debug: false
disable_auto_update: true
disable_command_execute: false
disable_force_update: true
disable_nat: false
disable_send_query: false
gpu: false
insecure_tls: true
ip_report_period: 1800
report_delay: 4
server: {NEZHA_SERVER}
skip_connection_count: true
skip_procs_count: true
temperature: false
tls: {nezhatls}
use_gitee_to_upgrade: false
use_ipv6_country_code: false
uuid: {UUID}"""
    nezha_config_path.write_text(config_yaml, encoding='utf-8')

# TLS 证书生成
FALLBACK_EC_KEY = (
    '-----BEGIN EC PARAMETERS-----\n'
    'BggqhkjOPQMBBw==\n'
    '-----END EC PARAMETERS-----\n'
    '-----BEGIN EC PRIVATE KEY-----\n'
    'MHcCAQEEIM4792SEtPqIt1ywqTd/0bYidBqpYV/++siNnfBYsdUYoAoGCCqGSM49\n'
    'AwEHoUQDQgAE1kHafPj07rJG+HboH2ekAI4r+e6TL38GWASANnngZreoQDF16ARa\n'
    '/TsyLyFoPkhLxSbehH/NBEjHtSZGaDhMqQ==\n'
    '-----END EC PRIVATE KEY-----\n'
)

FALLBACK_CERT = (
    '-----BEGIN CERTIFICATE-----\n'
    'MIIBejCCASGgAwIBAgIUfWeQL3556PNJLp/veCFxGNj9crkwCgYIKoZIzj0EAwIw\n'
    'EzERMA8GA1UEAwwIYmluZy5jb20wHhcNMjUwOTE4MTgyMDIyWhcNMzUwOTE2MTgy\n'
    'MDIyWjATMREwDwYDVQQDDAhiaW5nLmNvbTBZMBMGByqGSM49AgEGCCqGSM49AwEH\n'
    'A0IABNZB2nz49O6yRvh26B9npACOK/nuky9/BlgEgDZ54Ga3qEAxdegEWv07Mi8h\n'
    'aD5IS8Um3oR/zQRIx7UmRmg4TKmjUzBRMB0GA1UdDgQWBBTV1cFID7UISE7PLTBR\n'
    'BfGbgkrMNzAfBgNVHSMEGDAWgBTV1cFID7UISE7PLTBRBfGbgkrMNzAPBgNVHRMB\n'
    'Af8EBTADAQH/MAoGCCqGSM49BAMCA0cAMEQCIAIDAJvg0vd/ytrQVvEcSm6XTlB+\n'
    'eQ6OFb9LbLYL9f+sAiAffoMbi4y/0YUSlTtz7as9S8/lciBF5VCUoVIKS+vX2g==\n'
    '-----END CERTIFICATE-----\n'
)

def ensure_tls_certificates(cert_file, key_file):
    if cert_file.exists() and key_file.exists():
        return
    cert_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        # 成 EC 密钥和自签名证书
        ec_private_key = ec.generate_private_key(ec.SECP256R1())
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, 'bing.com')
        ])
        cert_obj = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(ec_private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
            .sign(ec_private_key, hashes.SHA256())
        )
        key_pem = ec_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        cert_pem = cert_obj.public_bytes(serialization.Encoding.PEM)
        key_file.write_bytes(key_pem)
        cert_file.write_bytes(cert_pem)
    except Exception as e:
        log_error(f'Failed to generate TLS certificate: {e}')
        key_file.write_text(FALLBACK_EC_KEY, encoding='utf-8')
        cert_file.write_text(FALLBACK_CERT, encoding='utf-8')

# X25519 密钥对生成或加载 
def generate_or_load_keypair():
    global private_key, public_key
    key_file_path = FILE_PATH / 'key.txt'
    if key_file_path.exists():
        content = key_file_path.read_text(encoding='utf-8')
        priv_match = re.search(r'PrivateKey:\s*(.*)', content)
        pub_match = re.search(r'PublicKey:\s*(.*)', content)
        if priv_match and pub_match:
            private_key = priv_match.group(1).strip()
            public_key = pub_match.group(1).strip()
            log(f'Private Key: {private_key}')
            log(f'Public Key: {public_key}')
            return
    keypair = generate_x25519_keypair()
    private_key = keypair['privateKey']
    public_key = keypair['publicKey']
    key_file_path.write_text(
        f'PrivateKey: {private_key}\nPublicKey: {public_key}\n', encoding='utf-8')
    log(f'Private Key: {private_key}')
    log(f'Public Key: {public_key}')

# Xr-ay 配置生成 
def generate_xray_config():
    config = {
        "log": {
            "access": "/dev/null",
            "error": "/dev/null",
            "loglevel": "none"
        },
        "inbounds": [
            {
                "tag": "vless-fallback-in",
                "listen": "::",
                "port": int(ARGO_PORT),
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": UUID}],
                    "decryption": "none",
                    "fallbacks": [
                        {"dest": 3001},
                        {"path": "/vless-argo", "dest": 3002},
                        {"path": "/vmess-argo", "dest": 3003},
                        {"path": "/trojan-argo", "dest": 3004}
                    ]
                },
                "streamSettings": {"network": "tcp"}
            },
            {
                "tag": "vless-tcp-in",
                "port": 3001,
                "listen": "127.0.0.1",
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": UUID}],
                    "decryption": "none"
                },
                "streamSettings": {"network": "tcp", "security": "none"}
            },
            {
                "tag": "vless-ws-in",
                "port": 3002,
                "listen": "127.0.0.1",
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": UUID, "level": 0}],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "ws",
                    "security": "none",
                    "wsSettings": {"path": "/vless-argo"}
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"],
                    "metadataOnly": False
                }
            },
            {
                "tag": "vmess-ws-in",
                "port": 3003,
                "listen": "127.0.0.1",
                "protocol": "vmess",
                "settings": {
                    "clients": [{"id": UUID, "alterId": 0}]
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {"path": "/vmess-argo"}
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"],
                    "metadataOnly": False
                }
            },
            {
                "tag": "trojan-ws-in",
                "port": 3004,
                "listen": "127.0.0.1",
                "protocol": "trojan",
                "settings": {
                    "clients": [{"password": UUID}]
                },
                "streamSettings": {
                    "network": "ws",
                    "security": "none",
                    "wsSettings": {"path": "/trojan-argo"}
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"],
                    "metadataOnly": False
                }
            }
        ],
        "dns": {"servers": ["https+local://8.8.8.8/dns-query"]},
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"}
        ]
    }

    # VLESS Reality 配置
    if is_valid_port(REALITY_PORT):
        config["inbounds"].append({
            "tag": "vless-in",
            "listen": "::",
            "port": int(REALITY_PORT),
            "protocol": "vless",
            "settings": {
                "clients": [{"id": UUID, "flow": "xtls-rprx-vision"}],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "raw",
                "security": "reality",
                "realitySettings": {
                    "show": False,
                    "dest": "www.iij.ad.jp:443",
                    "xver": 0,
                    "serverNames": ["www.iij.ad.jp"],
                    "privateKey": private_key,
                    "shortIds": [""]
                }
            }
        })

    # Hy2 配置
    if is_valid_port(HY2_PORT):
        config["inbounds"].append({
            "tag": "hysteria-in",
            "listen": "::",
            "port": int(HY2_PORT),
            "protocol": "hysteria",
            "settings": {
                "version": 2,
                "clients": [{"auth": UUID}]
            },
            "streamSettings": {
                "network": "hysteria",
                "hysteriaSettings": {
                    "version": 2,
                    "masquerade": {"type": "proxy", "url": "https://bing.com"}
                },
                "security": "tls",
                "tlsSettings": {
                    "alpn": ["h3"],
                    "certificates": [
                        {
                            "certificateFile": str(cert_path),
                            "keyFile": str(key_path)
                        }
                    ]
                }
            }
        })

    # S5 配置
    if is_valid_port(S5_PORT):
        config["inbounds"].append({
            "tag": "s5-in",
            "listen": "::",
            "port": int(S5_PORT),
            "protocol": "socks",
            "settings": {
                "auth": "password",
                "accounts": [{"user": UUID[:8], "pass": UUID[-12:]}],
                "udp": True
            }
        })

    config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

# 获取临时隧道域名 
def wait_for_quick_tunnel_domain(log_file, timeout_ms):
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        try:
            if log_file.exists():
                content = log_file.read_text(encoding='utf-8')
                matches = re.findall(r'https://([A-Za-z0-9.-]+\.trycloudflare\.com)', content)
                if matches:
                    return matches[-1]
        except Exception:
            pass
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        time.sleep(min(1, remaining))
    return None

def extract_domain():
    if DISABLE_ARGO == 'true':
        return None
    if ARGO_AUTH and ARGO_DOMAIN:
        log(f'ARGO_DOMAIN: {ARGO_DOMAIN}')
        return ARGO_DOMAIN
    # Quick tunnel
    domain = wait_for_quick_tunnel_domain(boot_log_path, 30000)
    if not domain:
        log('Quick tunnel domain not found, retrying...')
        try:
            boot_log_path.unlink()
        except FileNotFoundError:
            pass
        time.sleep(5)
        domain = wait_for_quick_tunnel_domain(boot_log_path, 30000)
    if domain:
        log(f'ArgoDomain: {domain}')
    else:
        log('ArgoDomain not found')
    return domain

# 获取 ISP 信息
def get_meta_info():
    try:
        resp = requests.get('https://api.ip.sb/geoip',
                            headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        data = resp.json()
        if data.get('country_code') and data.get('isp'):
            return f"{data['country_code']}-{data['isp']}".replace(' ', '_')
    except Exception:
        pass
    try:
        resp = requests.get('http://ip-api.com/json',
                            headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        data = resp.json()
        if data.get('status') == 'success' and data.get('countryCode') and data.get('org'):
            return f"{data['countryCode']}-{data['org']}".replace(' ', '_')
    except Exception:
        pass
    return 'Unknown'

# 节点链接生成
def generate_links(argo_domain):
    global sub_txt_content

    server_ip = ''
    try:
        resp = requests.get('http://ipv4.ip.sb', timeout=3)
        server_ip = resp.text.strip()
    except Exception:
        try:
            result = subprocess.run(['curl', '-sm', '3', 'ipv4.ip.sb'],
                                    capture_output=True, text=True, timeout=5)
            server_ip = result.stdout.strip()
        except Exception:
            try:
                resp = requests.get('http://ipv6.ip.sb', timeout=3)
                server_ip = f'[{resp.text.strip()}]'
            except Exception:
                try:
                    result = subprocess.run(['curl', '-sm', '3', 'ipv6.ip.sb'],
                                            capture_output=True, text=True, timeout=5)
                    server_ip = f'[{result.stdout.strip()}]'
                except Exception as e:
                    log_error(f'Failed to get IP address: {e}')

    isp = get_meta_info()
    node_name = f'{NAME}-{isp}' if NAME else isp

    time.sleep(2)

    sub_txt = ''

    # 只有当 DISABLE_ARGO 不为 'true' 且 argoDomain 存在时才生成 Argo 节点
    if DISABLE_ARGO != 'true' and argo_domain:
        # VLESS 节点
        sub_txt += f'\nvless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=/vless-argo#{node_name}'

        # VMess 节点
        vmess_obj = {
            'v': '2', 'ps': node_name, 'add': CFIP, 'port': CFPORT,
            'id': UUID, 'aid': '0', 'scy': 'auto', 'net': 'ws',
            'type': 'none', 'host': argo_domain, 'path': '/vmess-argo?ed=2560',
            'tls': 'tls', 'sni': argo_domain, 'alpn': '', 'fp': 'firefox'
        }
        vmess_b64 = base64.b64encode(json.dumps(vmess_obj, separators=(',', ':')).encode()).decode()
        sub_txt += f'\nvmess://{vmess_b64}'

        # Trojan 节点
        sub_txt += f'\ntrojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=/trojan-argo#{node_name}'

    # HY2_PORT 是有效端口号时生成 hysteria2 节点
    if is_valid_port(HY2_PORT):
        fingerprint = get_certificate_fingerprint(cert_path)
        fingerprint_param = f'&pinSHA256={quote(fingerprint, safe="")}' if fingerprint else ''
        sub_txt += f'\nhysteria2://{UUID}@{server_ip}:{HY2_PORT}/?sni=www.bing.com&insecure=0&alpn=h3&obfs=none{fingerprint_param}#{node_name}'

    # REALITY_PORT 是有效端口号时生成 reality 节点
    if is_valid_port(REALITY_PORT):
        sub_txt += f'\nvless://{UUID}@{server_ip}:{REALITY_PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.iij.ad.jp&fp=firefox&pbk={public_key}&type=tcp&headerType=none#{node_name}'

    # S5_PORT 是有效端口号时生成 socks5 节点
    if is_valid_port(S5_PORT):
        s5_auth = base64.b64encode(f'{UUID[:8]}:{UUID[-12:]}'.encode()).decode()
        sub_txt += f'\nsocks://{s5_auth}@{server_ip}:{S5_PORT}#{node_name}'

    # 打印 sub.txt 内容到控制台
    sub_txt_b64 = base64.b64encode(sub_txt.encode()).decode()
    if SHOW_LOG:
        print(f'\033[32m{sub_txt_b64}\033[0m')
        print(f'\033[35mLogs will be deleted in 90 seconds, you can copy the above nodes\033[0m')
    sub_path.write_text(sub_txt_b64, encoding='utf-8')
    list_path.write_text(sub_txt, encoding='utf-8')
    log(f'{FILE_PATH}/sub.txt saved successfully')

    sub_txt_content = sub_txt_b64
    return sub_txt

# Telegram 推送节点 
def send_telegram():
    if not BOT_TOKEN or not CHAT_ID:
        log('TG variables is empty, Skipping push nodes to TG')
        return
    try:
        message = sub_path.read_text(encoding='utf-8')
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
        escaped_name = re.sub(r'[_*\[\]()~`>#+=|{}.!-]', r'\\\g<0>', NAME)
        params = {
            'chat_id': CHAT_ID,
            'text': f'**{escaped_name}节点推送通知**\n```{message}```',
            'parse_mode': 'MarkdownV2'
        }
        requests.post(url, params=params, timeout=10)
        log('Telegram message sent successfully')
    except Exception as e:
        log_error(f'Failed to send Telegram message: {e}')

# 节点上传到订阅器(如果配置了)
def upload_nodes():
    if UPLOAD_URL and PROJECT_URL:
        subscription_url = f'{PROJECT_URL}/{SUB_PATH}'
        try:
            resp = requests.post(f'{UPLOAD_URL}/api/add-subscriptions',
                                 json={'subscription': [subscription_url]},
                                 timeout=10)
            if resp.status_code == 200:
                log('Subscription uploaded successfully')
        except Exception:
            pass
    elif UPLOAD_URL:
        if not list_path.exists():
            return
        content = list_path.read_text(encoding='utf-8')
        nodes = [line for line in content.split('\n')
                 if re.match(r'(vless|vmess|trojan|hysteria2)://', line)]
        if not nodes:
            return
        try:
            resp = requests.post(f'{UPLOAD_URL}/api/add-nodes',
                                 json={'nodes': nodes},
                                 timeout=10)
            if resp.status_code == 200:
                log('Subscription uploaded successfully')
        except Exception:
            pass

# 推送自动保活 
def add_visit_task():
    if not AUTO_ACCESS or not PROJECT_URL:
        log('Skipping adding automatic access task')
        return
    try:
        requests.post('https://oooo.serv00.net/add-url',
                      json={'url': PROJECT_URL},
                      headers={'Content-Type': 'application/json'},
                      timeout=10)
        log('automatic access task added successfully')
    except Exception as e:
        log_error(f'Add URL failed: {e}')

# 文件清理
def clean_files():
    def cleanup():
        time.sleep(90)
        files_to_delete = [boot_log_path, config_path, list_path, nezha_config_path,
                           xray_lib_path, bot_lib_path, nezha_lib_path, cert_path, key_path]
        for f in files_to_delete:
            try:
                f.unlink()
            except FileNotFoundError:
                pass
        # 清理 .tmp 目录
        tmp_dir = Path(os.getcwd()) / '.tmp'
        if tmp_dir.exists():
            try:
                shutil.rmtree(tmp_dir)
            except Exception:
                pass
        os.system('clear' if os.name == 'posix' else 'cls')
        always_log('App is running')
        log('Thank you for using this script, enjoy!')

    t = threading.Thread(target=cleanup, daemon=True)
    t.start()

# HTTP 服务
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == f'/{SUB_PATH}':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(sub_txt_content.encode('utf-8'))
            return

        if path == '/':
            html_path = Path(__file__).parent / 'index.html'
            try:
                data = html_path.read_text(encoding='utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(data.encode('utf-8'))
            except FileNotFoundError:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(
                    b'Hello world!<br><br>You can access /{SUB_PATH}(Default: /sub) get your nodes!')
            return

        self.send_response(404)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'Not Found')

    def log_message(self, format, *args):
        pass 

# 主流程
def start_server():
    global sub_txt_content, services

    # 1. 删除旧节点
    delete_nodes()

    # 2. 创建运行目录 + 清理文件
    FILE_PATH.mkdir(parents=True, exist_ok=True)
    cleanup_old_files()

    # 3. 生成 Argo 隧道配置
    argo_type()

    # 4. 下载 .so 库文件
    download_all_files()

    # 5. 生成 Reality 密钥对 (仅当 REALITY_PORT 开启才生成)
    if is_valid_port(REALITY_PORT):
        generate_or_load_keypair()

    # 6. 生成 TLS 证书
    ensure_tls_certificates(cert_path, key_path)

    # 7. 生成 nezha config
    generate_nezha_config()

    # 8. 生成 xray config.json
    generate_xray_config()

    # 9. 启动服务
    services = []

    # x-ray
    if xray_lib_path.exists():
        xray_service = Service('xray', xray_lib_path, 'StartXray', 'StopXray', xray_payload())
        services.append(xray_service)
    else:
        log_error('web.so not found')

    # cloud-flared
    if DISABLE_ARGO != 'true' and bot_lib_path.exists():
        cf_payload = cloudflared_payload()
        if cf_payload:
            cf_service = Service('cloudflared', bot_lib_path, 'StartCloudflared', 'StopCloudflared', cf_payload)
            services.append(cf_service)

    # ne-zha
    if NEZHA_SERVER and NEZHA_KEY and nezha_lib_path.exists():
        nezha_service = Service('nezha-agent', nezha_lib_path, 'StartNezhaAgent', 'StopNezhaAgent', nezha_payload())
        services.append(nezha_service)

    # 启动所有服务
    for service in services:
        service.start()
    time.sleep(1)
    log('web is running')
    if any(s.name == 'cloudflared' for s in services):
        log('bot is running')
    if any(s.name == 'nezha-agent' for s in services):
        log('npm is running')

    # 10. 等待并检测隧道域名
    time.sleep(5)
    argo_domain = extract_domain()

    # 11. 生成节点链接
    sub_txt = generate_links(argo_domain)
    sub_txt_content = base64.b64encode(sub_txt.encode()).decode()

    # 12. Telegram 推送 + 节点上传 + 自动保活
    send_telegram()
    upload_nodes()
    add_visit_task()

    # 13. 90秒后清理文件
    clean_files()

# 信号处理 
def stop_all(signum=None, frame=None):
    """优雅关闭所有服务"""
    def shutdown():
        log('\nShutting down...')
        # 逐个停止服务
        for service in reversed(services):
            try:
                service.stop()
            except Exception:
                pass
        time.sleep(1)
        os._exit(0)

    # 在线程中执行关闭，避免阻塞信号处理器
    t = threading.Thread(target=shutdown, daemon=True)
    t.start()

# 入口 
if __name__ == '__main__':
    signal.signal(signal.SIGINT, stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    # 启动 HTTP 服务 (主线程)
    server = ThreadingHTTPServer(('0.0.0.0', PORT), RequestHandler)

    always_log(f'server is running on {PORT}!')

    # 在后台线程中启动主流程
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # 主线程阻塞在 HTTP 服务器上
    server.serve_forever()
