# 说明

python-xray-argo是基于python环境搭建xray，引用argo隧道，集成哪吒探针搭建科学上网节点。
文件说明：app.py，start.sh为必要运行文件，swith为哪吒，server为cloudfared，web为xray。

# 部署

方式一：常规python环境，例如游戏平台玩具，只需上传app.py和start.sh两个文件即可，需授权777，start.sh文件设置哪吒参数和uuid

方式二：容器平台：文件+命令结合，需root权限，上传app.py和start.sh两个文件，运行python app.py即可。

方式三：docker部署。
