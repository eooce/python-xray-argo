import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def check_streamlit_app():
    # --- 1. 配置 ---
    cookie_str = os.getenv('STREAMLIT_COOKIE')
    project_url = os.getenv('PROJECT_URL')
    dashboard_url = "https://share.streamlit.io/"

    if not cookie_str or not project_url:
        print("错误：请确保 STREAMLIT_COOKIE 和 PROJECT_URL 环境变量都已设置。")
        sys.exit(1)

    # --- 2. 设置 Selenium WebDriver ---
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.binary_location = "/usr/bin/chromium-browser"
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("WebDriver 启动成功。")

        # --- 3. 添加 Cookie 并访问仪表板 ---
        print(f"步骤 1: 正在访问仪表板 URL: {dashboard_url}")
        driver.get(dashboard_url)

        print("正在添加 Cookie...")
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                name, value = part.split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.streamlit.io'})
        
        print("刷新页面以应用登录状态...")
        driver.get(dashboard_url)
        time.sleep(10) 

        # --- 4. 验证项目链接 ---
        print(f"步骤 2: 在仪表板上等待并验证项目链接: {project_url}")
        try:
            wait = WebDriverWait(driver, 60)
            print(f"仪表板页面标题是: '{driver.title}'")
            print("正在等待项目列表容器(tbody)加载...")
            list_container_locator = (By.TAG_NAME, "tbody")
            wait.until(EC.presence_of_element_located(list_container_locator))
            print("项目列表容器加载成功。")

            print("正在验证具体的项目链接...")
            link_locator = (By.CSS_SELECTOR, f"a[href='{project_url}']")
            wait.until(EC.presence_of_element_located(link_locator))
            print("项目链接验证成功。")

        except Exception as e:
            print(f"失败。在60秒内未能于仪表板页面上找到项目链接 '{project_url}'。")
            driver.save_screenshot('debug_screenshot.png')
            with open('debug_page_source.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("已保存 debug_screenshot.png 和 debug_page_source.html 以供分析。")
            raise e

        # --- 5. 访问项目 URL 并验证关键词 ---
        print(f"步骤 3: 正在访问项目 URL: {project_url}")
        driver.get(project_url)
        time.sleep(15)

        page_content = driver.page_source
        keyword = "stop"

        if keyword in page_content:
            print(f"成功！在项目页面上找到了关键词 '{keyword}'。")
            sys.exit(0)
        else:
            print(f"失败。未能在项目页面上找到关键词 '{keyword}'。")
            sys.exit(1)

    except Exception as e:
        print(f"脚本执行过程中发生错误: {e}")
        sys.exit(1)
    finally:
        if driver:
            driver.quit()
            print("WebDriver 已关闭。")

if __name__ == "__main__":
    check_streamlit_app()
