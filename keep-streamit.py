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
    base_domain_url = "https://streamlit.io/"
    
    if not project_url:
        print("错误：PROJECT_URL 环境变量未设置。")
        sys.exit(1)
    if not cookie_str:
        print("错误：STREAMLIT_COOKIE 环境变量未设置。")
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

        # --- 3. 登录并找到项目链接 ---
        print(f"步骤 1: 正在访问主域名 {base_domain_url} 以设置 Cookie。")
        driver.get(base_domain_url)
        
        print("正在添加 Cookie...")
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                name, value = part.split('=', 1)
                driver.add_cookie({'name': name, 'value': value, 'domain': '.streamlit.io'})
        
        print(f"Cookie 设置完毕，正在跳转到仪表板 URL: {dashboard_url}")
        driver.get(dashboard_url)
        time.sleep(5) 

        print(f"步骤 2: 在仪表板上等待并验证项目链接: {project_url}")
        wait = WebDriverWait(driver, 60)
        print(f"仪表板页面标题是: '{driver.title}'")
        if "Sign in" in driver.title:
            raise Exception("登录失败，页面仍然在 Sign in 页面。请检查 Cookie 是否过期。")

        print("正在等待项目列表容器(tbody)加载...")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
        print("项目列表容器加载成功。")

        print("正在验证具体的项目链接...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"a[href='{project_url}']")))
        print("项目链接验证成功。")
        
        # --- 4. 用浏览器访问项目 URL 并验证页面元素---
        print(f"步骤 3: 正在使用浏览器访问项目 URL: {project_url}")
        driver.get(project_url)

        print("正在验证项目页面是否加载成功...")
        try:
            app_container_locator = (By.CSS_SELECTOR, 'div[data-testid="stAppViewContainer"]')
            wait.until(EC.presence_of_element_located(app_container_locator))
            print("成功！项目页面已成功加载。脚本执行完毕。")
            sys.exit(0)
        except Exception:
            print("失败。访问项目页面后，未能找到应用加载成功的标志。")
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
