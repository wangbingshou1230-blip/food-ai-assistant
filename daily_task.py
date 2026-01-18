import requests
import os
from datetime import datetime

# --- 配置区域 (从 GitHub Secrets 自动读取) ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
BARK_SERVER = os.getenv("BARK_SERVER")
BARK_DEVICE_KEY = os.getenv("BARK_DEVICE_KEY")

# --- 功能 1: 百度新闻爬虫 ---
def get_baidu_news():
    print("正在获取百度热搜...")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    return [
        f"【热点】食品安全新国标解读 (时间: {current_time})",
        "【趋势】功能性食品在减脂期的应用",
        "【科技】AI 如何赋能食品溯源体系"
    ]

# --- 功能 2: DeepSeek 智能锐评 ---
def process_with_deepseek(news_list):
    if not DEEPSEEK_API_KEY:
        return "错误：未配置 DeepSeek API Key"

    print("正在调用 DeepSeek...")
    news_text = "\n".join(news_list)
    prompt = (
        f"我是一名食品加工与安全的硕士，也是自媒体人。\n"
        f"请从下面新闻中选一条最值得讨论的，写一段100字以内的专业微头条，要求有深度且通俗：\n\n"
        f"{news_text}"
    )

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个食品科学领域的专业助手。"},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"DeepSeek 调用失败: {response.status_code}"
    except Exception as e:
        return f"请求异常: {e}"

# --- 功能 3: Bark 推送 (适配拆分版) ---
def send_bark_notification(title, content):
    # 这里的检查逻辑是关键！必须检查 SERVER 和 KEY
    if not BARK_SERVER or not BARK_DEVICE_KEY:
        print("警告：Bark 配置不完整，跳过推送")
        return

    print("正在构建 Bark 推送...")
    clean_server = BARK_SERVER.rstrip('/')
    target_url = f"{clean_server}/{BARK_DEVICE_KEY}/{title}/{content}"
    
    try:
        requests.get(target_url)
        print("Bark 推送成功！")
    except Exception as e:
        print(f"Bark 推送失败: {e}")

if __name__ == "__main__":
    print(">>> 自动化任务开始")
    news = get_baidu_news()
    comment = process_with_deepseek(news)
    today = datetime.now().strftime("%m-%d")
    send_bark_notification(f"食品科研日报-{today}", comment)
    print(">>> 自动化任务结束")