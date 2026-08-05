## Python 版 Xray + Cloudflared + Nezha 使用底层so部署脚本

基于 `ctypes` 加载 `.so` 共享库，使用 `cryptography` 处理加密相关操作

## 快速开始

### 1. 安装依赖

```bash
cd python
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件（与 python 目录同级或在运行目录下）：

```bash
cp .env.example .env
# 编辑 .env 填写你的配置
```

### 3. 运行

```bash
python app.py
```

或使用环境变量直接运行：

```bash
export UUID=your-uuid
export PORT=3000
python index.py
```

## 环境变量
| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `PORT` | 否 | `3000` | HTTP 订阅服务端口 |
| `FILE_PATH` | 否 | `.npm` | 运行目录，存放 `.so` 库、配置文件、订阅文件等 |
| `UUID` | 否 | `0a6568ff-ea3c-4271-9020-450560e10d63` | 节点 UUID，同时用作 Trojan 密码、HY2 认证密码、S5 密码组成部分 |
| `NAME` | 否 | 空 | 节点名称前缀，会与 ISP 信息拼接，例如 `MyNode-US-AWS` |
| `SUB_PATH` | 否 | `sub` | 订阅路径，访问 `http://host:port/{SUB_PATH}` 获取订阅 |
| `SHOW_LOG` | 否 | `true` | 是否显示日志输出，设为 `false` / `disable` / `no` 屏蔽日志 |

### Argo 隧道

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DISABLE_ARGO` | 否 | `false` | 设为 `true` 禁用 Argo 隧道 |
| `ARGO_DOMAIN` | 否 | 空 | Argo 固定隧道域名，留空使用临时隧道 |
| `ARGO_AUTH` | 否 | 空 | Argo 固定隧道 Token 或 JSON，留空使用临时隧道 |
| `ARGO_PORT` | 否 | `8001` | Argo 隧道本地端口，使用 Token 时需与 Cloudflare 控制台一致 |

**Argo 三种模式：**

1. **临时隧道**（Quick Tunnel）：`ARGO_DOMAIN` 和 `ARGO_AUTH` 均留空，自动获取临时域名
2. **Token 模式**：`ARGO_AUTH` 填写 Cloudflare Tunnel Token（120~250 字符的字母数字串）
3. **JSON 模式**：`ARGO_AUTH` 填写包含 `TunnelSecret` 的 JSON，同时填写 `ARGO_DOMAIN`

### Nezha 监控

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `NEZHA_SERVER` | 否 | 空 | 哪吒面板地址，v1 形式 `nz.serv00.net:8008`，v0 形式 `nz.serv00.net` |
| `NEZHA_PORT` | 否 | 空 | v0 agent 端口，v1 留空。端口为 `443/8443/2096/2087/2083/2053` 时自动启用 TLS |
| `NEZHA_KEY` | 否 | 空 | v1 的 `NZ_CLIENT_SECRET` 或 v0 的 agent 密钥 |

**Nezha 两种模式：**

- **v1 模式**：`NEZHA_PORT` 留空，使用 `config.yaml` 配置文件
- **v0 模式**：`NEZHA_PORT` 填写端口，使用命令行参数

### 节点端口

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `REALITY_PORT` | 否 | 空 | VLESS Reality 端口，支持多端口平台可填写，留空不生成 Reality 节点 |
| `HY2_PORT` | 否 | 空 | Hysteria2 端口，支持多端口平台可填写，留空不生成 HY2 节点 |
| `S5_PORT` | 否 | 空 | SOCKS5 端口，支持多端口平台可填写，留空不生成 SOCKS5 节点 |

> **注意**：仅当 `REALITY_PORT` 为有效端口时才会生成 X25519 密钥对

### 优选配置

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `CFIP` | 否 | `saas.sin.fan` | 优选域名或优选 IP |
| `CFPORT` | 否 | `443` | 优选域名或 IP 对应端口 |

### 订阅上传

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `UPLOAD_URL` | 否 | 空 | 订阅/节点自动上传地址，需填写部署 Merge-sub 项目后的首页地址 |
| `PROJECT_URL` | 否 | 空 | 项目分配的 URL，用于上传订阅和保活 |
| `AUTO_ACCESS` | 否 | 空 | 自动保活开关，设为 `true` 开启，需同时填写 `PROJECT_URL` |

**上传逻辑：**

- 同时填写 `UPLOAD_URL` + `PROJECT_URL`：上传订阅 URL
- 仅填写 `UPLOAD_URL`：上传节点列表

### Telegram 推送

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `CHAT_ID` | 否 | 空 | Telegram Chat ID，两个变量都不填则不推送 |
| `BOT_TOKEN` | 否 | 空 | Telegram Bot Token，两个变量都不填则不推送 |

## `.env` 示例

```bash
# ===== 基础配置 =====
PORT=3000
UUID=0a6568ff-ea3c-4271-9020-450560e10d63
NAME=MyNode
SUB_PATH=sub
FILE_PATH=.npm
SHOW_LOG=true

# ===== Argo 隧道 =====
DISABLE_ARGO=false
# 临时隧道: ARGO_DOMAIN 和 ARGO_AUTH 留空
# 固定隧道:
# ARGO_DOMAIN=argo.example.com
# ARGO_AUTH=your-cloudflare-tunnel-token
ARGO_PORT=8001

# ===== Nezha 监控 =====
# NEZHA_SERVER=nz.serv00.net:8008
# NEZHA_PORT=
# NEZHA_KEY=your-nezha-key

# ===== 节点端口 =====
# REALITY_PORT=8443
# HY2_PORT=8444
# S5_PORT=8445

# ===== 优选配置 =====
CFIP=saas.sin.fan
CFPORT=443

# ===== 订阅上传 =====
# UPLOAD_URL=https://merge.example.com
# PROJECT_URL=https://your-project.example.com
# AUTO_ACCESS=true

# ===== Telegram 推送 =====
# CHAT_ID=123456789
# BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```
