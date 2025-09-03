import requests
import os
import sys
from bs4 import BeautifulSoup

def check_streamlit_app():
    # 从环境变量中获取配置
    cookie = os.getenv('STREAMLIT_COOKIE')
    project_url = os.getenv('PROJECT_URL')
    dashboard_url = "https://share.streamlit.io/"

    # 检查环境变量是否都已设置
    if not cookie:
        print("错误：STREAMLIT_COOKIE 环境变量未设置。")
        sys.exit(1)
    if not project_url:
        print("错误：PROJECT_URL 环境变量未设置。")
        sys.exit(1)

    # 设置请求头，模拟浏览器并包含 Cookie
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Cookie': cookie
    }

    try:
        #  访问仪表板
        print(f"步骤 1: 正在访问仪表板 URL: {dashboard_url}")
        dashboard_response = requests.get(dashboard_url, headers=headers, timeout=60)
        dashboard_response.raise_for_status()
        print("仪表板访问成功。")

        # 验证项目链接
        print(f"步骤 2: 在仪表板上验证项目链接: {project_url}")
        soup = BeautifulSoup(dashboard_response.text, 'html.parser')
        project_link = soup.find('a', href=project_url)

        if not project_link:
            print(f"失败。未能在仪表板页面上找到项目链接 '{project_url}'。")
            sys.exit(1)
        
        print("项目链接验证成功。")

        # 访问项目 URL 并验证关键词
        print(f"步骤 3: 正在访问项目 URL: {project_url}")
        project_response = requests.get(project_url, headers=headers, timeout=60)
        project_response.raise_for_status()
        
        page_content = project_response.text
        keyword = "stop"

        if keyword in page_content:
            print(f"成功！在项目页面上找到了关键词 '{keyword}'。")
            sys.exit(0) # 成功退出
        else:
            print(f"失败。未能在项目页面上找到关键词 '{keyword}'。")
            sys.exit(1) # 失败退出

    except requests.exceptions.RequestException as e:
        print(f"请求失败，发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_streamlit_app()
