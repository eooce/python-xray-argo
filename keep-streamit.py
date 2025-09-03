import requests
import os
import sys

def check_streamlit_app():
    # 从环境变量中获取 Cookie
    cookie = os.getenv('STREAMLIT_COOKIE')
    if not cookie:
        print("错误：STREAMLIT_COOKIE 环境变量未设置。")
        sys.exit(1)

    # 目标 URL
    url = "https://python-xray-argo-yutian81.streamlit.app/"

    # 设置请求头，模拟浏览器并包含 Cookie
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Cookie': cookie
    }

    try:
        print(f"正在访问 URL: {url}")
        response = requests.get(url, headers=headers, timeout=60) # 设置60秒超时
        response.raise_for_status()
        page_content = response.text
        keyword = "stop"

        if keyword in page_content:
            print(f"成功！在页面上找到了关键词 '{keyword}'。")
            sys.exit(0) # 成功退出
        else:
            print(f"失败。未能在页面上找到关键词 '{keyword}'。")
            sys.exit(1) # 失败退出

    except requests.exceptions.RequestException as e:
        print(f"请求失败，发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_streamlit_app()
