import sys
import os
import subprocess
import http.server
import socketserver
import threading

# 定义端口
port = int(os.getenv('PORT', 3000))

# http路由
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
httpd = socketserver.TCPServer(('', port), MyHandler)
server_thread = threading.Thread(target=httpd.serve_forever)
server_thread.daemon = True
server_thread.start()

# 定义要执行的Shell命令并赋权
shell_command = "chmod +x start.sh && ./start.sh"

# 执行shell文件
try:
    completed_process = subprocess.run(['bash', '-c', shell_command], stdout=sys.stdout, stderr=subprocess.PIPE, text=True, check=True)

    print("App is running")
    print("Thank you for using this script,enjoy!")

except subprocess.CalledProcessError as e:
    print(f"Error: {e.returncode}")
    print("Standard Output:")
    print(e.stdout)
    print("Standard Error:")
    print(e.stderr)
    sys.exit(1)

server_thread.join()
