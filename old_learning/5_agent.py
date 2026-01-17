import requests
from bs4 import BeautifulSoup
import csv
import datetime
import json
import os

# ==================== 配置中心 ====================
# 1. 你的 DeepSeek 密钥
API_KEY = "sk-44104f41c16f42748973c225aff64f0f"  # <--- 【请务必替换为你刚才充值过的密钥】
# 2. 你想监控的关键词
SEARCH_KEYWORD = "食品行业 AI 应用"  # <--- 可以随时改这个词，比如“食品行业 AI 转型”
# ================================================

def step1_crawl_data():
    """第一步：去必应抓取数据"""
    print(f"\n🚀 启动阶段一：正在全网搜索 '{SEARCH_KEYWORD}' ...")
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    url = f"https://cn.bing.com/search?q={SEARCH_KEYWORD}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = soup.find_all('h2')
        
        data = []
        for tag in results:
            link = tag.find('a')
            if link:
                title = link.get_text()
                href = link.get('href')
                data.append(f"标题：{title} | 链接：{href}")
        
        # 保存到临时文件
        if data:
            filename = "latest_data.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(data))
            print(f"✅ 抓取成功：找到 {len(data)} 条信息，已缓存。")
            return filename
        else:
            print("❌ 抓取失败：未找到内容（可能是反爬虫拦截）。")
            return None
            
    except Exception as e:
        print(f"❌ 抓取阶段出错：{e}")
        return None

def step2_analyze_data(filename):
    """第二步：调用 DeepSeek 分析"""
    print(f"\n🧠 启动阶段二：正在调用 DeepSeek 大脑进行分析 ...")
    
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    
    # 指令：让 AI 扮演毒舌的职业顾问
    prompt = """
    你是一个犀利的职业规划顾问。用户想转行做 AI。
    请分析下面抓取到的搜索结果：
    1. 挑出最有价值的 2 条信息（招聘或文章）。
    2. 只要干货，不要废话。
    3. 如果看起来都是垃圾广告，请直接吐槽。
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ]
    }
    
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload))
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        else:
            return f"API 调用失败：{resp.text}"
    except Exception as e:
        return f"分析阶段出错：{e}"

def main():
    print("==="*10 + " 自动化 Agent 启动 " + "==="*10)
    
    # 顺序执行
    data_file = step1_crawl_data()
    
    if data_file:
        report = step2_analyze_data(data_file)
        
        print("\n" + "==="*10 + " 最终分析报告 " + "==="*10)
        print(report)
        print("==="*30)
        
        # 这里以后可以加：发送邮件给我的功能
    
    print("\n✅ 任务结束。")

if __name__ == "__main__":
    main()