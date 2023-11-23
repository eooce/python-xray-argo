import sys
import subprocess
import http.server
import socketserver

# 定义端口
port = 3000

# 升级pip到最新版本
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])

# 定义要执行的Shell命令并赋权
shell_command = "chmod +x start.sh && ./start.sh" 

# 执行shell文件
try:
    completed_process = subprocess.run(['bash', '-c', shell_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    print("Command executed successfully.")

except subprocess.CalledProcessError as e:
    print(f"Error: {e.returncode}")
    print(e.stdout)
    print(e.stderr)
    sys.exit(1)

# sub订阅路由
class MyHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Hello, world')
        elif self.path == '/sub':
            try:
                with open("./temp/sub.txt", 'rb') as file:
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

with socketserver.TCPServer(('', port), MyHandler) as httpd:
    print(f'Server is running on port {port}')
    httpd.serve_forever()
