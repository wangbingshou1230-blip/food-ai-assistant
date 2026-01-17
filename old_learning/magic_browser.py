import time
import pandas as pd # 引入强大的表格库
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# ================== ⚙️ 配置机器人 (不变) ==================
def start_browser():
    print("🤖 正在启动自动化浏览器...")
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") 
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# ================== 🕸️ 执行任务 (升级版) ==================
def search_food_news(keyword):
    driver = start_browser()
    news_list = [] # 创建一个空列表，用来装新闻
    
    try:
        print(f"🔍 正在搜索关键词: {keyword}")
        driver.get(f"https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&word={keyword}")
        time.sleep(3)
        
        print("⬇️ 正在模拟滚动页面...")
        for i in range(3):
            driver.execute_script("window.scrollBy(0, 500);") 
            time.sleep(1)
        
        print("📝 正在提取新闻...")
        titles = driver.find_elements(By.CSS_SELECTOR, "h3")
        
        # --- 核心修改：把数据存进列表 ---
        for title in titles[:10]: # 抓前10条
            text = title.text.replace("\n", " ")
            link = title.find_element(By.TAG_NAME, "a").get_attribute("href") # 顺便把链接也抓下来
            
            # 把每一条新闻打包成一个字典
            news_item = {
                "标题": text,
                "链接": link,
                "来源": "百度新闻"
            }
            news_list.append(news_item)
            print(f"✅ 已捕获: {text[:20]}...")
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        
    finally:
        print("\n✅ 抓取结束，正在关闭浏览器...")
        driver.quit()
        
        # --- 核心修改：保存为 Excel ---
        if news_list:
            df = pd.DataFrame(news_list)
            file_name = f"{keyword}_新闻.xlsx"
            df.to_excel(file_name, index=False)
            print(f"\n🎉 成功！数据已保存为: {file_name}")
            print("👉 你可以在左侧文件列表里找到它，右键下载或直接打开！")
        else:
            print("⚠️ 没有抓到数据，请检查网络。")

if __name__ == "__main__":
    search_food_news("预制菜标准") # 换个关键词试试