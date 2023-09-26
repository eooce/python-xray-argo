import subprocess
import sys

# 升级pip到最新版本
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'])

# 定义要执行的Shell命令并赋权）
shell_command = "chmod +x start.sh && ./start.sh" 

# 执行shell文件
try:
    completed_process = subprocess.run(['bash', '-c', shell_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    print("Server is running")
except subprocess.CalledProcessError as e:
    print(f"Error: {e.returncode}")
    print(e.stdout)
    print(e.stderr)