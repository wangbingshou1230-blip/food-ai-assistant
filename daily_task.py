import os
import requests
import pandas as pd
import json
from datetime import datetime
from bs4 import BeautifulSoup
import time

# ================= ⚙️ 配置区 =================
# 你关心的关键词，可以是 "预制菜", "乳液凝胶", "食品安全"
KEYWORDS = ["食品安全", "预制菜"] 
OUTPUT_FOLDER = "output_files"

# ================= 🔐 密钥获取 (自动适配 GitHub Secrets) =================
def get_env_var(key_name):
    # 优先从环境变量获取 (GitHub Actions 运行时)
    val = os.environ.get(key_name)
    if not val:
        # 本地测试时，尝试读 config.json
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    return json.load(f).get(key_name)
        except:
            pass
    return val

# ================= 🕷️ 1. 爬虫模块 =================
def run_crawler():
    print("🕷️ 侦察兵启动，开始抓取新闻...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    all_news = []
    
    for kw in KEYWORDS:
        # 百度资讯搜索链接
        url = f"https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 查找新闻标题 (百度新闻结构可能会变，这里用较通用的找法)
            # 寻找所有 h3 标签，且 class 包含 news-title
            items = soup.find_all('h3', class_=lambda x: x and 'news-title' in x)
            
            for item in items:
                link = item.find('a')
                if link:
                    title = link.get_text().strip()
                    href = link['href']
                    source_span = item.parent.find('span', class_=lambda x: x and 'c-color-gray' in x)
                    source = source_span.get_text().strip() if source_span else "未知来源"
                    
                    all_news.append({
                        "关键词": kw,
                        "标题": title,
                        "来源": source,
                        "链接": href,
                        "爬取时间": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
            print(f"✅ 关键词【{kw}】抓取完成")
            time.sleep(1) # 休息一下，防止被封
        except Exception as e:
            print(f"❌ 关键词【{kw}】抓取失败: {e}")

    if not all_news:
        print("⚠️ 未抓取到任何数据")
        return None

    # 保存为 Excel
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    
    # 文件名带日期：2026-01-18_DailyNews.xlsx
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{OUTPUT_FOLDER}/{today}_DailyNews.xlsx"
    
    df = pd.DataFrame(all_news)
    df.to_excel(filename, index=False)
    print(f"💾 数据已保存: {filename}")
    return df

# ================= 🧠 2. AI 分析模块 =================
def analyze_news(df):
    print("🧠 AI 正在阅读新闻...")
    api_key = get_env_var("deepseek_api_key")
    if not api_key:
        print("❌ 缺少 DeepSeek Key，跳过分析")
        return "今日爬取完成，但未配置 AI Key，无法生成摘要。"

    # 取前 20 条标题
    titles = df["标题"].head(20).tolist()
    text_block = "\n".join(titles)

    # 构造 Prompt
    prompt = [
        {"role": "system", "content": "你是一个食品安全情报官。请根据以下新闻标题，简要总结今日舆情热点 (100字以内)。如果无特殊大事，请简报平安。"},
        {"role": "user", "content": f"今日新闻标题：\n{text_block}"}
    ]

    try:
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "deepseek-chat", "messages": prompt, "stream": False},
            timeout=30
        )
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            return f"AI 报错: {res.text}"
    except Exception as e:
        return f"请求失败: {e}"

# ================= 📡 3. Bark 推送模块 =================
def push_bark(summary):
    print("📡 准备推送...")
    device_key = get_env_var("bark_device_key")
    server = get_env_var("bark_server")
    if not server: server = "https://api.day.app"
    
    if not device_key:
        print("⚠️ 未配置 Bark Key，跳过推送")
        return

    title = "FoodAI早报"
    content = summary[:200] # 截取防止超长
    
    url = f"{server.rstrip('/')}/{device_key}/{title}/{content}"
    try:
        requests.get(url, timeout=10)
        print("✅ 推送成功")
    except Exception as e:
        print(f"❌ 推送出错: {e}")

# ================= 🚀 主流程 =================
if __name__ == "__main__":
    df = run_crawler()
    if df is not None:
        summary = analyze_news(df)
        print(f"📊 摘要: {summary}")
        push_bark(summary)
    else:
        print("💤 今日无新数据")