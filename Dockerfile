FROM python:3.11.5

# 设置工作目录
WORKDIR /app

# 将应用程序文件复制到容器中
COPY . .

# EXPOSE 7860

# 安装应用程序的依赖
RUN pip install

# 设置默认的命令，即启动应用程序
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "7860"]
