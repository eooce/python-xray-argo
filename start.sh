#!/bin/bash
export UUID=${UUID:-'de823d1f-9a68-4f79-b82e-0267132b6a99'}
export NEZHA_SERVER=${NEZHA_SERVER:-'nz.abc.com'}
export NEZHA_PORT=${NEZHA_PORT:-'5555'}
export NEZHA_KEY=${NEZHA_KEY:-'eOLJC0tJpf8abcdefg'}
export ARGO_DOMAIN=${ARGO_DOMAIN:-''}
export ARGO_TOK=${ARGO_TOK:-''}
export CFIP=${CFIP:-'skk.moe'}
export NAME=${NAME:-'ABCD'}
export FILE_PATH=${FILE_PATH:-'./temp'}

if [ ! -d "${FILE_PATH}" ]; then
    mkdir ${FILE_PATH}
fi

#清理历史运行文件
cleanup_oldfiles() {
  rm -rf ${FILE_PATH}/boot.log ${FILE_PATH}/sub.txt 
}
cleanup_oldfiles
sleep 2

#生成xr-ay配置文件
generate_config() {
  cat > ${FILE_PATH}/config.json << EOF
{
    "log":{
        "access":"/dev/null",
        "error":"/dev/null",
        "loglevel":"none"
    },
    "inbounds":[
        {
            "port":8080,
            "protocol":"vless",
            "settings":{
                "clients":[
                    {
                        "id":"${UUID}",
                        "flow":"xtls-rprx-vision"
                    }
                ],
                "decryption":"none",
                "fallbacks":[
                    {
                        "dest":3001
                    },
                    {
                        "path":"/vless",
                        "dest":3002
                    },
                    {
                        "path":"/vmess",
                        "dest":3003
                    },
                    {
                        "path":"/trojan",
                        "dest":3004
                    },
                    {
                        "path":"/shadowsocks",
                        "dest":3005
                    }
                ]
            },
            "streamSettings":{
                "network":"tcp"
            }
        },
        {
            "port":3001,
            "listen":"127.0.0.1",
            "protocol":"vless",
            "settings":{
                "clients":[
                    {
                        "id":"${UUID}"
                    }
                ],
                "decryption":"none"
            },
            "streamSettings":{
                "network":"ws",
                "security":"none"
            }
        },
        {
            "port":3002,
            "listen":"127.0.0.1",
            "protocol":"vless",
            "settings":{
                "clients":[
                    {
                        "id":"${UUID}",
                        "level":0
                    }
                ],
                "decryption":"none"
            },
            "streamSettings":{
                "network":"ws",
                "security":"none",
                "wsSettings":{
                    "path":"/vless"
                }
            },
            "sniffing":{
                "enabled":true,
                "destOverride":[
                    "http",
                    "tls",
                    "quic"
                ],
                "metadataOnly":false
            }
        },
        {
            "port":3003,
            "listen":"127.0.0.1",
            "protocol":"vmess",
            "settings":{
                "clients":[
                    {
                        "id":"${UUID}",
                        "alterId":0
                    }
                ]
            },
            "streamSettings":{
                "network":"ws",
                "wsSettings":{
                    "path":"/vmess"
                }
            },
            "sniffing":{
                "enabled":true,
                "destOverride":[
                    "http",
                    "tls",
                    "quic"
                ],
                "metadataOnly":false
            }
        },
        {
            "port":3004,
            "listen":"127.0.0.1",
            "protocol":"trojan",
            "settings":{
                "clients":[
                    {
                        "password":"${UUID}"
                    }
                ]
            },
            "streamSettings":{
                "network":"ws",
                "security":"none",
                "wsSettings":{
                    "path":"/trojan"
                }
            },
            "sniffing":{
                "enabled":true,
                "destOverride":[
                    "http",
                    "tls",
                    "quic"
                ],
                "metadataOnly":false
            }
        },
        {
            "port":3005,
            "listen":"127.0.0.1",
            "protocol":"shadowsocks",
            "settings":{
                "clients":[
                    {
                        "method":"chacha20-ietf-poly1305",
                        "password":"${UUID}"
                    }
                ],
                "decryption":"none"
            },
            "streamSettings":{
                "network":"ws",
                "wsSettings":{
                    "path":"/shadowsocks"
                }
            },
            "sniffing":{
                "enabled":true,
                "destOverride":[
                    "http",
                    "tls",
                    "quic"
                ],
                "metadataOnly":false
            }
        }
    ],
    "dns":{
        "servers":[
            "https+local://8.8.8.8/dns-query"
        ]
    },
    "outbounds":[
        {
            "protocol":"freedom"
        },
        {
            "tag":"WARP",
            "protocol":"wireguard",
            "settings":{
                "secretKey":"YFYOAdbw1bKTHlNNi+aEjBM3BO7unuFC5rOkMRAz9XY=",
                "address":[
                    "172.16.0.2/32",
                    "2606:4700:110:8a36:df92:102a:9602:fa18/128"
                ],
                "peers":[
                    {
                        "publicKey":"bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                        "allowedIPs":[
                            "0.0.0.0/0",
                            "::/0"
                        ],
                        "endpoint":"162.159.193.10:2408"
                    }
                ],
                "reserved":[78, 135, 76],
                "mtu":1280
            }
        }
    ],
    "routing":{
        "domainStrategy":"AsIs",
        "rules":[
            {
                "type":"field",
                "domain":[
                    "domain:openai.com",
                    "domain:ai.com"
                ],
                "outboundTag":"WARP"
            }
        ]
    }
}
EOF
}
generate_config
sleep 3

# 下载依赖文件
set_download_url() {
  local program_name="$1"
  local default_url="$2"
  local x64_url="$3"

  if [ "$(uname -m)" = "x86_64" ] || [ "$(uname -m)" = "amd64" ] || [ "$(uname -m)" = "x64" ]; then
    download_url="$x64_url"
  else
    download_url="$default_url"
  fi
}

download_program() {
  local program_name="$1"
  local default_url="$2"
  local x64_url="$3"

  set_download_url "$program_name" "$default_url" "$x64_url"

  if [ ! -f "$program_name" ]; then
    if [ -n "$download_url" ]; then
      curl -sSL -C - "$download_url" -o "$program_name" > /dev/null 2>&1
      if [ $? -eq 33 ]; then
        echo "Resuming download $program_name..."
        curl -sSL "$download_url" -o "$program_name" > /dev/null 2>&1
      fi
      if [ $? -eq 0 ]; then
        dd if=/dev/urandom bs=1024 count=1024 | base64 >> "$program_name" > /dev/null 2>&1
        echo "$program_name download finished"
      else
        echo "Failed to download $program_name"
      fi
    else
      echo "Skipping download $program_name"
    fi
  else
    dd if=/dev/urandom bs=1024 count=1024 | base64 >> "$program_name" > /dev/null 2>&1
    echo "$program_name already exists, skipping download"
  fi
}

download_program "${FILE_PATH}/swith" "https://github.com/eoovve/test/releases/download/ARM/swith" "https://github.com/eoovve/test/raw/main/swith"
sleep 5

download_program "${FILE_PATH}/web" "https://github.com/eoovve/test/releases/download/ARM/web" "https://github.com/eoovve/test/raw/main/web"
sleep 5

download_program "${FILE_PATH}/server" "https://github.com/eoovve/test/releases/download/ARM/server" "https://github.com/eoovve/test/raw/main/server"
sleep 5

# 运行ne-zha
run_swith() {
  chmod 755 ${FILE_PATH}/swith
  if [ "$NEZHA_PORT" = "443" ]; then
    NEZHA_TLS="--tls"
  else
    NEZHA_TLS=""
  fi
  nohup ${FILE_PATH}/swith -s ${NEZHA_SERVER}:${NEZHA_PORT} -p ${NEZHA_KEY} ${NEZHA_TLS} >/dev/null 2>&1 &
}
run_swith
sleep 2

# 运行xr-ay
run_web() {
  chmod 755 ${FILE_PATH}/web
  nohup ${FILE_PATH}/web -c ${FILE_PATH}/config.json >/dev/null 2>&1 &
}
run_web
sleep 2

# 运行argo
run_argo() {
chmod 755 ${FILE_PATH}/server
if [[ -n "${ARGO_TOK}" ]]; then
ARGO_TOK=$(echo ${ARGO_TOK} | sed 's@cloudflared.exe service install ey@ey@g')
    if [[ "${ARGO_TOK}" =~ TunnelSecret ]]; then
      echo "${ARGO_TOK}" | sed 's@{@{"@g;s@[,:]@"\0"@g;s@}@"}@g' > ${FILE_PATH}/tunnel.json
      cat > ${FILE_PATH}/tunnel.yml << EOF
tunnel: $(sed "s@.*TunnelID:\(.*\)}@\1@g" <<< "${ARGO_TOK}")
credentials-file: ${FILE_PATH}/tunnel.json
protocol: http2

ingress:
  - hostname: $ARGO_DOMAIN
    service: http://localhost:8080
EOF
      cat >> ${FILE_PATH}/tunnel.yml << EOF
  - service: http_status:404
EOF
      nohup ${FILE_PATH}/server tunnel --edge-ip-version auto --config ${FILE_PATH}/tunnel.yml run >/dev/null 2>&1 &
    elif [[ ${ARGO_TOK} =~ ^[A-Z0-9a-z=]{120,250}$ ]]; then
      nohup ${FILE_PATH}/server tunnel --edge-ip-version auto --protocol http2 run --token ${ARGO_TOK} >/dev/null 2>&1 &
    fi
else
 nohup ${FILE_PATH}/server tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile ${FILE_PATH}/boot.log --loglevel info --url http://localhost:8080 >/dev/null 2>&1 &
 sleep 5
 export ARGO_DOMAIN=$(cat ${FILE_PATH}/boot.log | grep -o "info.*https://.*trycloudflare.com" | sed "s@.*https://@@g" | tail -n 1)
fi
}
run_argo
sleep 1

#生成list和sub
generate_links() {
  isp=$(curl -s https://speed.cloudflare.com/meta | awk -F\" '{print $26"-"$18}' | sed -e 's/ /_/g')
  sleep 2
  
  VMESS="{ \"v\": \"2\", \"ps\": \"${NAME}-${isp}\", \"add\": \"${CFIP}\", \"port\": \"443\", \"id\": \"${UUID}\", \"aid\": \"0\", \"scy\": \"none\", \"net\": \"ws\", \"type\": \"none\", \"host\": \"${ARGO_DOMAIN}\", \"path\": \"/vmess?ed=2048\", \"tls\": \"tls\", \"sni\": \"${ARGO_DOMAIN}\", \"alpn\": \"\" }"

  cat > ${FILE_PATH}/list.txt <<EOF
vless://${UUID}@${CFIP}:443?encryption=none&security=tls&sni=${ARGO_DOMAIN}&type=ws&host=${ARGO_DOMAIN}&path=%2Fvless?ed=2048#${NAME}-${isp}

vmess://$(echo "$VMESS" | base64 -w0)

trojan://${UUID}@${CFIP}:443?security=tls&sni=${ARGO_DOMAIN}&type=ws&host=${ARGO_DOMAIN}&path=%2Ftrojan?ed=2048#${NAME}-${isp}
EOF

  base64 -w0 ${FILE_PATH}/list.txt > ${FILE_PATH}/sub.txt
  cat ${FILE_PATH}/sub.txt

  echo -e "\nFile saved successfully"
  sleep 10

  rm ${FILE_PATH}/list.txt ${FILE_PATH}/boot.log ${FILE_PATH}/config.json
}
generate_links
