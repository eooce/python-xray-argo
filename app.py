import subprocess
import sys

# 升级pip到最新版本
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])

# 赋权并执行
shell_command = "chmod +x start.sh && ./start.sh" 

try:
    completed_process = subprocess.run(['bash', '-c', shell_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    print("Server is running")
except subprocess.CalledProcessError as e:
    print(f"Error: {e.returncode}")
    print(e.stdout)
    print(e.stderr)
