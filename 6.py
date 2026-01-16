import requests
from bs4 import BeautifulSoup
import json
import time

# ================= 配置中心 (已填入你的新Key) =================
# 1. 你的 DeepSeek 密钥 (保持不变)
API_KEY = "sk-44104f41c16f42748973c225aff64f0f" 

# 2. Bark 官方服务器地址
BARK_SERVER = "https://api.day.app"

# 3. 你的新 Bark Key (从链接里提取出来的)
BARK_KEY = "JQAghdJVVjub7Y4rvwVPVD"

# 4. 搜索关键词
SEARCH_KEYWORD = "食品行业 AI 落地应用 案例"
# ==========================================================

def step1_search_bing():
    """去必应抓取最新情报"""
    print(f"🕵️  正在全网搜索：{SEARCH_KEYWORD} ...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    url = f"https://cn.bing.com/search?q={SEARCH_KEYWORD}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        results = []
        for tag in soup.find_all('h2')[:5]:
            link = tag.find('a')
            if link:
                title = link.get_text()
                href = link.get('href')
                results.append(f"- {title} ({href})")
        
        if not results:
            print("❌ 未找到搜索结果。")
            return None
            
        print(f"✅ 成功抓取到 {len(results)} 条信息。")
        return "\n".join(results)
    except Exception as e:
        print(f"❌ 搜索出错: {e}")
        return None

def step2_ai_analyze(data):
    """让 DeepSeek 帮你读"""
    print("🧠 正在唤醒 DeepSeek 大脑进行分析...")
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    
    prompt = """
    你是一个毒舌科技评论员。用户是食品专业硕士想转行 AI。
    请阅读下面的搜索结果：
    1. 用“人话”总结这些信息里最有价值的一个趋势。
    2. 如果全是垃圾广告，请直接吐槽。
    3. 风格要幽默、简短（100字以内），适合发在手机通知栏看。
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": data}
        ]
    }
    
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload))
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        else:
            print(f"❌ AI 调用失败: {resp.text}")
            return None
    except Exception as e:
        print(f"❌ 分析出错: {e}")
        return None

def step3_send_notification(content):
    """【官方版】推送到 Bark (使用最稳的 POST 方式)"""
    print("📲 正在呼叫 Bark 官方服务器...")
    
    # 官方接口地址
    url = "https://api.day.app/push"
    
    # 打包数据
    payload = {
        "device_key": BARK_KEY,
        "title": "AI情报员汇报",
        "body": content,
        "group": "FoodAI",
        "icon": "https://cdn-icons-png.flaticon.com/512/2083/2083256.png", # 换了个可爱的机器人图标
        "level": "active" # 确保是时效性通知
    }
    
    try:
        # 发送 POST 请求 (官方服务器必须用 json 发送复杂内容)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        resp = requests.post(url, json=payload, headers=headers)
        
        if resp.status_code == 200:
            print("✅ Bark 推送成功！你的 iPhone 应该震动了！")
        else:
            print(f"❌ 推送失败，状态码: {resp.status_code}")
            print(f"❌ 错误信息: {resp.text}")

    except Exception as e:
        print(f"❌ 网络连接失败: {e}")

def main():
    print("==="*10 + " Python 智能情报员 (官方Bark版) " + "==="*10)
    
    # 1. 抓取
    raw_data = step1_search_bing()
    if not raw_data: return

    # 2. 分析
    ai_comment = step2_ai_analyze(raw_data)
    if not ai_comment: return
    
    print("\n--- AI 评价 ---\n", ai_comment, "\n---------------")

    # 3. 推送
    step3_send_notification(ai_comment)
    
    input("\n任务完成！按回车键退出...")

if __name__ == "__main__":
    main()