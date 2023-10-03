import sys
import subprocess
import http.server
import socketserver

port = 3000

subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])

shell_command = "chmod +x start.sh && ./start.sh" 
try:
    completed_process = subprocess.run(['bash', '-c', shell_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    print("Command executed successfully.")
except subprocess.CalledProcessError as e:
    print(f"Error: {e.returncode}")
    print(e.stdout)
    print(e.stderr)

class MyHandler(http.server.SimpleHTTPRequestHandler):

  def do_GET(self):
    if self.path == '/':
      self.send_response(200)
      self.end_headers()
      self.wfile.write(b'Hello, world')
    elif self.path == '/list':
      try:
        with open("./list.txt", 'rb') as file:
          content = file.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(content)
      except FileNotFoundError:
        self.send_response(500)
        self.end_headers()
        self.wfile.write(b'Error reading file')
    elif self.path == '/sub':
      try:
        with open("./sub.txt", 'rb') as file:
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
  print(f'Server is running on port:{port}')
  httpd.serve_forever()
