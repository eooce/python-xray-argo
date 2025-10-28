# 说明

本项目是基于python环境使用,搭建argo-xray节点，集成哪吒探针v0/v1自由选择，包含vless-ws-tls/vmess-ws-tls/trojan-ws-tls三协议组合

# 部署

方式一：常规python环境，例如游戏平台玩具，只需上传app.py和requirements.txt两个文件即可，app.py需授权777,app.py中17至30行填写变量。

方式二：文件+命令结合，app.py需赋权，上传app.py和requirements.tx两个文件，先运行chmod +x app.py 再运行pip install -r requirements.txt 然后运行screen python app.py即可，提示screen not found说明screen未安装，Debian/Ubuntu安装命令：apt install -y screen，centos安装命令：yum install -y screen

方式三：docker部署，右边的packages中已打包好镜像，镜像地址：ghcr.io/eooce/python:latest 支持镜像部署的平台推荐优先使用镜像

# 环境变量
* PaaS 平台设置的环境变量
  | 变量名        | 是否必须 | 默认值 | 备注 |
  | ------------ | ------ | ------ | ------ |
  | UPLOAD_URL   | 否 | 填写部署Merge-sub项目后的首页地址  |订阅上传地址,例如：https://merge.serv00.net|
  | PROJECT_URL  | 否 | https://www.google.com     |项目分配的域名|
  | AUTO_ACCESS  | 否 |  false |false关闭自动访问保活，true开启，需同时填写PROJECT_URL变量|
  | PORT         | 否 |  3000  |http服务监听端口，也是订阅端口     |
  | ARGO_PORT    | 否 |  8001  |argo隧道端口，固定隧道token需和cloudflare后台设置的一致|
  | UUID         | 否 | 89c13786-25aa-4520-b2e7-12cd60fb5202|UUID,使用哪吒v1在不同的平台部署需要修改|
  | NEZHA_SERVER | 否 |        | 哪吒面板域名，v1：nz.aaa.com:8008  v0: nz.aaa.com  |
  | NEZHA_PORT   | 否 |        | 哪吒v1没有此项，哪吒v0端口为{443,8443,2096,2087,2083,2053}其中之一时，开启tls|
  | NEZHA_KEY    | 否 |        | 哪吒v1 或v0 密钥                 |
  | ARGO_DOMAIN  | 否 |        | argo固定隧道域名                  |
  | ARGO_AUTH    | 否 |        | argo固定隧道json或token           |
  | CFIP         | 否 |time.is | 节点优选域名或ip                   |
  | CFPORT       | 否 |  443   |节点端口                           |
  | NAME         | 否 |  Vls   | 节点名称前缀，例如：Koyeb Fly        |
  | FILE_PATH    | 否 |  .cache| 运行目录,节点存放路径                |
  | SUB_PATH     | 否 |  sub   | 节点订阅路径                       | 

# 节点输出
* 输出sub.txt节点文件，默认存放路径为.cache
* 订阅：分配的域名/${SUB_PATH};例如https://www.google.com/${SUB_PATH}
* 非标端口订阅(游戏类):分配的域名:端口/${SUB_PATH},前缀不是https，而是http，例如http://www.google.com:1234/${SUB_PATH}

# 其他
* 此版本为Argo版，直连版本请移步：https://github.com/eoovve/python-xray-direct
* 如需链接github部署，Fork后请先删除此README.md说明文件部署；支持Docker镜像部署又需要链接github部署的平台，只需新建项目，新建一个Dockerfile文件，里面填写FROM ghcr.io/eooce/python:latest部署即可

# 免责声明
本程序仅供学习了解, 非盈利目的，请于下载后 24 小时内删除, 不得用作任何商业用途, 文字、数据及图片均有所属版权, 如转载须注明来源。
使用本程序必循遵守部署免责声明。使用本程序必循遵守部署服务器所在地、所在国家和用户所在国家的法律法规, 程序作者不对使用者任何不当行为负责。
