# 说明

本项目是基于python环境使用xray，引用argo隧道，集成哪吒探针(可选)搭建科学上网节点。
文件说明：app.py为主运行文件，requirements.txt为需要的组件库，swith为哪吒，bot为cloudfared，web为xray。
已适配FreeBSD，自行在右边的Releases中下载

# 部署

方式一：常规python环境，例如游戏平台玩具，只需上传app.py和requirements.txt两个文件即可，app.py需授权777,app.py中17至30行填写变量。

方式二：文件+命令结合，app.py需赋权，上传app.py和requirements.tx两个文件，先运行chmod +x app.py 再运行pip install -r requirements.txt 然后运行screen python app.py即可，提示screen not found说明screen未安装，Debian/Ubuntu安装命令：apt install -y screen，centos安装命令：yum install -y screen

方式三：docker部署，右边的packages中已打包好镜像，镜像地址：ghcr.io/eooce/python:latest 支持镜像部署的平台推荐优先使用镜像

# 环境变量
* PaaS 平台设置的环境变量
  | 变量名        | 是否必须 | 默认值 | 备注 |
  | ------------ | ------ | ------ | ------ |
  | PORT         | 否 |  3000  |http服务监听端口，也是订阅端口     |
  | FILE_PATH    | 否 |  temp  | 运行目录                         | 
  | URL          | 否 | https://www.google.com     |项目分配的域名|
  | TIME         | 否 | 120    |自动访问间隔时间（默认2分钟）单位:秒|
  | UUID         | 否 | abe2f2de-13ae-4f1f-bea5-d6c881ca3888|UUID|
  | ARGO_PORT    | 否 |  8001  |argo隧道端口，固定隧道token需和cloudflare后台设置的一致|
  | NEZHA_SERVER | 否 |        | 哪吒服务端域名，例如nz.aaa.com    |
  | NEZHA_PORT   | 否 |  5555  | 当哪吒端口为443时，自动开启tls    |
  | NEZHA_KEY    | 否 |        | 哪吒客户端专用KEY                |
  | ARGO_DOMAIN  | 否 |        | argo固定隧道域名                 |
  | ARGO_AUTH    | 否 |        | argo固定隧道json或token          |
  | CFIP         | 否 |skk.moe | 节点优选域名或ip                 |
  | CFPORT       | 否 |  443   |节点端口                          |
  | NAME         | 否 |  Vls   | 节点名称前缀，例如：Glitch，Replit|

# 节点输出
* 输出sub.txt节点文件，默认存放路径为temp
* 订阅：分配的域名/sub;例如https://www.google.com/sub
* 非标端口订阅(游戏类):分配的域名:端口/sub,前缀不是https，而是http，例如http://www.google.com:1234/sub

# 其他
* 此版本为Argo版，直连版本请移步：https://github.com/eoovve/python-xray-direct
* 如需链接github部署，Fork后请先删除此README.md说明文件部署；支持Docker镜像部署又需要链接github部署的平台，只需新建项目，新建一个Dockerfile文件，里面填写FROM ghcr.io/eooce/python:latest部署即可

# 免责声明
本程序仅供学习了解, 非盈利目的，请于下载后 24 小时内删除, 不得用作任何商业用途, 文字、数据及图片均有所属版权, 如转载须注明来源。
使用本程序必循遵守部署免责声明。使用本程序必循遵守部署服务器所在地、所在国家和用户所在国家的法律法规, 程序作者不对使用者任何不当行为负责。
