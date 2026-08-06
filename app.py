#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import json
import time
import base64
import random
import string
import shutil
import asyncio
import platform
import signal
import threading
import subprocess
import datetime
import requests
from pathlib import Path
from urllib.parse import urlparse, quote
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from cryptography.hazmat.primitives.asymmetric import x25519, ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography import x509
from cryptography.x509.oid import NameOID

# =========================== 环境变量 ===========================
UPLOAD_URL = os.environ.get('UPLOAD_URL', '')          # 节点或订阅上传地址
PROJECT_URL = os.environ.get('PROJECT_URL', '')        # 项目url,用于自动保活或上传订阅
AUTO_ACCESS = os.environ.get('AUTO_ACCESS', '').lower() == 'true'  # true开启自动保活,默认关闭
FILE_PATH = os.environ.get('FILE_PATH', '.cache')      # 运行目录,sub.txt保存路径
SUB_PATH = os.environ.get('SUB_PATH', 'sub')           # 订阅token
UUID = os.environ.get('UUID', '20e6e496-cf19-45c8-b883-14f5e11cd9f1')  # UUID
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', '')      # 哪吒面板域名,v0：nezha.xxx.com  v1: nezha.xxx.com:8008
NEZHA_PORT = os.environ.get('NEZHA_PORT', '')          # v1留空, v0填agent通信端口
NEZHA_KEY = os.environ.get('NEZHA_KEY', '')            # v1的NZ_CLIENT_SECRET或v0 agent密钥
ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', '')        # Argo固定隧道域名,留空使用临时隧道
ARGO_AUTH = os.environ.get('ARGO_AUTH', '')            # Argo固定隧道token或json,留空使用临时隧道
ARGO_PORT = int(os.environ.get('ARGO_PORT', '8001'))   # Argo隧道端口
S5_PORT = os.environ.get('S5_PORT', '')                # socks5端口,留空不开启
HY2_PORT = os.environ.get('HY2_PORT', '')              # hy2端口,留空不开启
REALITY_PORT = os.environ.get('REALITY_PORT', '')      # reality端口,留空不开启
CFIP = os.environ.get('CFIP', 'cf.877774.xyz')         # 优选ip或域名
CFPORT = int(os.environ.get('CFPORT', '443'))          # 优选端口
NAME = os.environ.get('NAME', '')                      # 节点名称
CHAT_ID = os.environ.get('CHAT_ID', '')                # Telegram chat_id
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')            # Telegram bot_token
PORT = int(os.environ.get('PORT') or '3000')           # http订阅端口
SHOW_LOG = os.environ.get('SHOW_LOG', 'true').lower() not in ('false', 'disable', 'no')  # 是否显示日志,默认显示，no/false/disable 不显示

# =========================== 日志控制 ===========================
def log(msg):
    if SHOW_LOG:
        print(msg)

def log_error(msg):
    if SHOW_LOG:
        print(msg, file=sys.stderr)

def always_log(msg):
    sys.stdout.write(msg + '\n')
    sys.stdout.flush()

# =========================== 全局变量 ===========================
private_key = ''
public_key = ''
sub_txt_content = ''
FILE_PATH = Path(FILE_PATH).resolve()

def generate_random_name(length=6):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

web_name = generate_random_name()
bot_name = generate_random_name()
npm_name = generate_random_name()
php_name = generate_random_name()

web_path = FILE_PATH / web_name
bot_path = FILE_PATH / bot_name
npm_path = FILE_PATH / npm_name
php_path = FILE_PATH / php_name
sub_path = FILE_PATH / 'sub.txt'
list_path = FILE_PATH / 'list.txt'
boot_log_path = FILE_PATH / 'boot.log'
config_path = FILE_PATH / 'config.json'
nezha_config_path = FILE_PATH / 'config.yaml'
cert_path = FILE_PATH / 'cert.pem'
key_path = FILE_PATH / 'private.key'

# =========================== 端口检查 ===========================
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

# =========================== X25519 密钥对生成 ===========================
def generate_x25519_keypair():
    """使用 cryptography 库生成 X25519 密钥对,返回 base64url 编码的私钥和公钥"""
    priv = x25519.X25519PrivateKey.generate()
    pub = priv.public_key()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return {
        'privateKey': base64.urlsafe_b64encode(priv_bytes).decode().rstrip('='),
        'publicKey': base64.urlsafe_b64encode(pub_bytes).decode().rstrip('=')
    }

def generate_or_load_keypair():
    """生成或加载 X25519 密钥对"""
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

# =========================== TLS 证书生成 ===========================
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
    """生成自签名 TLS 证书 (用于 Hysteria2)"""
    if cert_file.exists() and key_file.exists():
        return
    cert_file.parent.mkdir(parents=True, exist_ok=True)
    try:
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
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
            .not_valid_after((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650)).replace(tzinfo=None))
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

# =========================== 证书指纹计算 ===========================
def get_certificate_fingerprint(cert_file):
    """计算证书的 SHA-256 指纹,优先用 openssl,不可用时用 cryptography 兜底"""
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
    try:
        with open(cert_file, 'rb') as f:
            cert_data = f.read()
        cert = x509.load_pem_x509_certificate(cert_data)
        fingerprint = cert.fingerprint(hashes.SHA256())
        return ':'.join(f'{b:02X}' for b in fingerprint)
    except Exception as e:
        log_error(f'Failed to calculate certificate fingerprint: {e}')
        return ''

# =========================== 创建运行文件夹 ===========================
def create_directory():
    if not SHOW_LOG:
        print('\033c', end='')
    FILE_PATH.mkdir(parents=True, exist_ok=True)
    # log(f'{FILE_PATH} is ready')

# =========================== 删除旧节点 ===========================
def delete_nodes():
    try:
        if not UPLOAD_URL:
            return
        if not sub_path.exists():
            return
        content = sub_path.read_text(encoding='utf-8')
        decoded = base64.b64decode(content).decode('utf-8')
        nodes = [line for line in decoded.split('\n')
                 if re.match(r'(vless|vmess|trojan|hysteria2|socks)://', line)]
        if not nodes:
            return
        requests.post(f'{UPLOAD_URL}/api/delete-nodes',
                       json={'nodes': nodes}, timeout=10)
    except Exception:
        pass

# =========================== 清理历史文件 ===========================
def cleanup_old_files():
    """清理 FILE_PATH 目录下的所有文件, 保留 key.txt/cert.pem/private.key"""
    # key.txt: Reality 密钥对, cert.pem/private.key: Hysteria2 证书, 删除后重启指纹变化导致节点失效
    preserve_files = {FILE_PATH / 'key.txt', cert_path, key_path}
    try:
        for item in FILE_PATH.iterdir():
            if item in preserve_files:
                continue
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception:
                pass
    except Exception:
        pass

# =========================== 判断系统架构 ===========================
def get_system_architecture():
    arch = platform.machine().lower()
    if arch in ('arm', 'arm64', 'aarch64'):
        return 'arm'
    return 'amd'

# =========================== 下载文件 ===========================
def download_file(file_name, file_url):
    file_path = FILE_PATH / file_name
    try:
        response = requests.get(file_url, stream=True, timeout=180)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        log(f'Download {file_name} successfully')
        return True
    except Exception as e:
        log_error(f'Download {file_name} failed: {e}')
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass
        return False

def download_all_files():
    """下载所需二进制文件"""
    architecture = get_system_architecture()
    base_url = 'https://arm64.ssss.nyc.mn' if architecture == 'arm' else 'https://amd64.ssss.nyc.mn'

    downloads = [
        {'name': web_name, 'url': f'{base_url}/web'},
        {'name': bot_name, 'url': f'{base_url}/bot'},
    ]

    if NEZHA_SERVER and NEZHA_KEY:
        if NEZHA_PORT:
            downloads.append({'name': npm_name, 'url': f'{base_url}/agent'})
        else:
            downloads.append({'name': php_name, 'url': f'{base_url}/v1'})
    else:
        log('NEZHA variable is empty, skipping nezha-agent')

    for item in downloads:
        download_file(item['name'], item['url'])

# =========================== 授权文件执行权限 ===========================
def authorize_files(file_names):
    for name in file_names:
        file_path = FILE_PATH / name
        if file_path.exists():
            try:
                os.chmod(str(file_path), 0o775)
                log(f'Empowerment success for {name}: 775')
            except Exception as e:
                log_error(f'Empowerment failed for {name}: {e}')

# =========================== Argo 隧道配置 ===========================
def argo_type():
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

# =========================== Nezha 配置生成 ===========================
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

# =========================== Xray 配置生成 ===========================
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
                "port": ARGO_PORT,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": UUID, "flow": "xtls-rprx-vision"}],
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
            "tag": "vless-reality-in",
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

    # Hysteria2 配置
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

    # SOCKS5 配置
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

# =========================== 执行命令 ===========================
def exec_cmd(command):
    try:
        process = subprocess.Popen(
            command, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        return stdout + stderr
    except Exception as e:
        log_error(f'Error executing command: {e}')
        return str(e)

# =========================== 下载并运行 ===========================
def download_files_and_run():
    architecture = get_system_architecture()

    # 下载文件
    download_all_files()

    # 授权执行权限
    files_to_authorize = [web_name, bot_name]
    if NEZHA_SERVER and NEZHA_KEY:
        if NEZHA_PORT:
            files_to_authorize.append(npm_name)
        else:
            files_to_authorize.append(php_name)
    authorize_files(files_to_authorize)

    # 生成 Nezha 配置
    generate_nezha_config()

    # 运行 Nezha
    if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
        tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']
        nezha_tls = '--tls' if NEZHA_PORT in tls_ports else ''
        command = f"nohup {npm_path} -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {nezha_tls} --disable-auto-update --report-delay 4 --skip-conn --skip-procs >/dev/null 2>&1 &"
        try:
            exec_cmd(command)
            log(f'{npm_name} is running')
            time.sleep(1)
        except Exception as e:
            log_error(f'npm running error: {e}')
    elif NEZHA_SERVER and NEZHA_KEY:
        command = f'nohup {php_path} -c "{nezha_config_path}" >/dev/null 2>&1 &'
        try:
            exec_cmd(command)
            log(f'{php_name} is running')
            time.sleep(1)
        except Exception as e:
            log_error(f'php running error: {e}')
    else:
        log('NEZHA variable is empty, skipping running')

    # 运行 Xray
    command = f'nohup {web_path} -c {config_path} >/dev/null 2>&1 &'
    try:
        exec_cmd(command)
        log(f'{web_name} is running')
        time.sleep(1)
    except Exception as e:
        log_error(f'web running error: {e}')

    # 运行 Cloudflared
    if bot_path.exists():
        if re.match(r'^[A-Z0-9a-z=]{120,250}$', ARGO_AUTH):
            args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 run --token {ARGO_AUTH}"
        elif "TunnelSecret" in ARGO_AUTH:
            args = f"tunnel --edge-ip-version auto --config {FILE_PATH / 'tunnel.yml'} run"
        else:
            args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {boot_log_path} --loglevel info --url http://localhost:{ARGO_PORT}"

        try:
            exec_cmd(f"nohup {bot_path} {args} >/dev/null 2>&1 &")
            log(f'{bot_name} is running')
            time.sleep(2)
        except Exception as e:
            log_error(f'Error executing command: {e}')

    time.sleep(5)

# =========================== 提取隧道域名 ===========================
def extract_domains():
    argo_domain = None

    if ARGO_AUTH and ARGO_DOMAIN:
        argo_domain = ARGO_DOMAIN
        log(f'ARGO_DOMAIN: {argo_domain}')
        generate_links(argo_domain)
    else:
        try:
            if boot_log_path.exists():
                file_content = boot_log_path.read_text(encoding='utf-8')
                lines = file_content.split('\n')
                argo_domains = []

                for line in lines:
                    domain_match = re.search(r'https?://([^ ]*trycloudflare\.com)/?', line)
                    if domain_match:
                        domain = domain_match.group(1)
                        argo_domains.append(domain)

                if argo_domains:
                    argo_domain = argo_domains[0]
                    log(f'ArgoDomain: {argo_domain}')
                    generate_links(argo_domain)
                else:
                    log('ArgoDomain not found, re-running bot to obtain ArgoDomain')
                    try:
                        boot_log_path.unlink()
                    except FileNotFoundError:
                        pass

                    try:
                        exec_cmd(f'pkill -f "[{bot_name[0]}]{bot_name[1:]}" > /dev/null 2>&1')
                    except Exception:
                        pass

                    time.sleep(3)
                    args = f'tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {boot_log_path} --loglevel info --url http://localhost:{ARGO_PORT}'
                    exec_cmd(f'nohup {bot_path} {args} >/dev/null 2>&1 &')
                    log(f'{bot_name} is running')
                    time.sleep(6)
                    extract_domains()
        except Exception as e:
            log_error(f'Error reading boot.log: {e}')

# =========================== 获取 ISP 信息 ===========================
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

# =========================== 获取服务器公网 IP ===========================
def get_server_ip():
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
    return server_ip

# =========================== 生成节点链接 ===========================
def generate_links(argo_domain):
    global sub_txt_content

    isp = get_meta_info()
    node_name = f'{NAME}-{isp}' if NAME else isp
    server_ip = get_server_ip()

    time.sleep(2)

    sub_txt = ''

    # Argo 节点 (VLESS / VMess / Trojan)
    if argo_domain:
        sub_txt += f'\nvless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&fp=firefox&type=ws&host={argo_domain}&path=%2Fvless-argo%3Fed%3D2560#{node_name}'

        vmess_obj = {
            'v': '2', 'ps': node_name, 'add': CFIP, 'port': CFPORT,
            'id': UUID, 'aid': '0', 'scy': 'auto', 'net': 'ws',
            'type': 'none', 'host': argo_domain, 'path': '/vmess-argo?ed=2560',
            'tls': 'tls', 'sni': argo_domain, 'alpn': '', 'fp': 'firefox'
        }
        vmess_b64 = base64.b64encode(json.dumps(vmess_obj, separators=(',', ':')).encode()).decode()
        sub_txt += f'\nvmess://{vmess_b64}'

        sub_txt += f'\ntrojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argo_domain}&fp=firefox&type=ws&host={argo_domain}&path=%2Ftrojan-argo%3Fed%3D2560#{node_name}'

    # Hysteria2 节点
    if is_valid_port(HY2_PORT):
        fingerprint = get_certificate_fingerprint(cert_path)
        fingerprint_param = f'&pinSHA256={quote(fingerprint, safe="")}' if fingerprint else ''
        sub_txt += f'\nhysteria2://{UUID}@{server_ip}:{HY2_PORT}/?sni=www.bing.com&insecure=0&alpn=h3&obfs=none{fingerprint_param}#{node_name}'

    # Reality 节点
    if is_valid_port(REALITY_PORT):
        sub_txt += f'\nvless://{UUID}@{server_ip}:{REALITY_PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.iij.ad.jp&fp=firefox&pbk={public_key}&type=tcp&headerType=none#{node_name}'

    # SOCKS5 节点
    if is_valid_port(S5_PORT):
        s5_auth = base64.b64encode(f'{UUID[:8]}:{UUID[-12:]}'.encode()).decode()
        sub_txt += f'\nsocks://{s5_auth}@{server_ip}:{S5_PORT}#{node_name}'

    sub_txt_b64 = base64.b64encode(sub_txt.encode()).decode()
    if SHOW_LOG:
        print(f'\033[32m{sub_txt_b64}\033[0m')
        print(f'\033[35mLogs will be deleted in 90 seconds, you can copy the above nodes\033[0m')

    sub_path.write_text(sub_txt_b64, encoding='utf-8')
    list_path.write_text(sub_txt, encoding='utf-8')
    log(f'{FILE_PATH}/sub.txt saved successfully')

    sub_txt_content = sub_txt_b64
    return sub_txt

# =========================== Telegram 推送 ===========================
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

# =========================== 上传节点到订阅器 ===========================
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
                 if re.match(r'(vless|vmess|trojan|hysteria2|socks)://', line)]
        if not nodes:
            return
        try:
            resp = requests.post(f'{UPLOAD_URL}/api/add-nodes',
                                 json={'nodes': nodes},
                                 timeout=10)
            if resp.status_code == 200:
                log('Nodes uploaded successfully')
        except Exception:
            pass

# =========================== 自动保活 ===========================
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

# =========================== 文件清理 ===========================
def clean_files():
    def cleanup():
        time.sleep(90)
        # 注意: key.txt/cert.pem/private.key 不能删除, 删除后重启会导致 Reality 公钥和 Hysteria2 证书指纹变化, 节点失效
        files_to_delete = [boot_log_path, config_path, list_path, nezha_config_path,
                           web_path, bot_path,
                           FILE_PATH / 'tunnel.json', FILE_PATH / 'tunnel.yml']
        if NEZHA_PORT:
            files_to_delete.append(npm_path)
        elif NEZHA_SERVER and NEZHA_KEY:
            files_to_delete.append(php_path)

        for f in files_to_delete:
            try:
                f.unlink()
            except FileNotFoundError:
                pass

        if SHOW_LOG:
            os.system('clear' if os.name == 'posix' else 'cls')
        always_log('App is running')
        log('Thank you for using this script, enjoy!')

    t = threading.Thread(target=cleanup, daemon=True)
    t.start()

# =========================== HTTP 服务 ===========================
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

# =========================== 主流程 ===========================
def start_server():
    global sub_txt_content

    # 1. 删除旧节点
    delete_nodes()

    # 2. 创建运行目录 + 清理文件
    create_directory()
    cleanup_old_files()

    # 3. 生成 Argo 隧道配置
    argo_type()

    # 4. 生成 Reality 密钥对 (仅当 REALITY_PORT 开启才生成)
    if is_valid_port(REALITY_PORT):
        generate_or_load_keypair()

    # 5. 生成 TLS 证书 (用于 Hysteria2)
    if is_valid_port(HY2_PORT):
        ensure_tls_certificates(cert_path, key_path)

    # 6. 生成 Xray 配置
    generate_xray_config()

    # 7. 下载并运行文件
    download_files_and_run()

    # 8. 提取隧道域名并生成节点
    extract_domains()

    # 9. Telegram 推送 + 节点上传 + 自动保活
    send_telegram()
    upload_nodes()
    add_visit_task()

    # 10. 90秒后清理文件
    clean_files()

# =========================== 信号处理 ===========================
def stop_all(signum=None, frame=None):
    """优雅关闭所有服务"""
    def shutdown():
        log('\nShutting down...')
        try:
            exec_cmd(f'pkill -f "{web_name}" > /dev/null 2>&1')
            exec_cmd(f'pkill -f "{bot_name}" > /dev/null 2>&1')
            if NEZHA_PORT:
                exec_cmd(f'pkill -f "{npm_name}" > /dev/null 2>&1')
            elif NEZHA_SERVER and NEZHA_KEY:
                exec_cmd(f'pkill -f "{php_name}" > /dev/null 2>&1')
        except Exception:
            pass
        time.sleep(1)
        os._exit(0)

    t = threading.Thread(target=shutdown, daemon=True)
    t.start()

# =========================== 入口 ===========================
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
