import requests
import re
import os
import json
from datetime import datetime

# --- 配置区 (从 GitHub Secrets 获取) ---
# 必须在 GitHub 仓库 Settings -> Secrets -> Actions 中配置这些
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
BARK_SERVER = os.environ.get("BARK_SERVER")
BARK_KEY = os.environ.get("BARK_DEVICE_KEY")

def get_baidu_hot():
    """抓取百度实时热搜列表"""
    print("正在抓取百度热搜...")
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=headers)
        # 正则提取标题
        titles = re.findall(r'class="c-single-text-ellipsis">(.*?)</div>', resp.text)
        # 只要前 15 条，给 AI 去筛选
        clean_titles = [t.strip() for t in titles if len(t) > 2][:15]
        return clean_titles
    except Exception as e:
        print(f"抓取失败: {e}")
        return []

def ai_analyze_news(news_list):
    """用 DeepSeek 进行筛选和点评"""
    if not DEEPSEEK_API_KEY:
        return "⚠️ GitHub Secrets 未配置 DeepSeek Key，无法进行 AI 分析。"
    
    print("正在调用 DeepSeek 进行分析...")
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    # 构造 Prompt：让 AI 做食品情报员
    news_text = "\n".join([f"- {t}" for t in news_list])
    system_prompt = """
    你是一名【食品行业情报分析师】。
    请从给定的热搜列表中，筛选出【可能与食品、健康、餐饮、农业、消费】相关的 1-3 条新闻。
    
    如果没有直接相关的，就选最热门的一条社会新闻。
    
    请输出一份【简报】，格式如下：
    📅 **今日食安/热点情报**
    1. **[标题]**
       💡 *AI微评*：用一句话犀利点评或分析对食品人的启示。
    (如果没有更多相关新闻，只列1条即可)
    """
    
    try:
        resp = requests.post(url, headers=headers, json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"今日热搜列表：\n{news_text}"}
            ],
            "stream": False
        })
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        else:
            return f"AI 思考失败: {resp.text}"
    except Exception as e:
        return f"AI 请求异常: {e}"

def send_bark(title, content):
    """发送 Bark 推送"""
    if not BARK_SERVER or not BARK_KEY:
        print("Bark 配置缺失，跳过推送")
        return
    
    print("正在发送推送...")
    # Bark 的 URL 只能通过 GET 传参，内容需要简单处理一下
    # 为了防止太长，DeepSeek 输出的内容如果太长可能会被截断，这里不作特殊处理，Bark会自动折叠
    base_url = BARK_SERVER.rstrip("/")
    
    # 组合 URL: server/key/title/content
    # 注意：Bark 也可以用 POST 发送，这里为了兼容旧代码用 GET，但更稳妥是用 POST
    # 这里我们切换为 POST 方法以支持长文本
    push_url = f"{base_url}/{BARK_KEY}"
    payload = {
        "title": title,
        "body": content,
        "group": "FoodMaster情报",
        "icon": "https://cdn-icons-png.flaticon.com/512/2921/2921822.png" # 一个好看的烧瓶图标
    }
    
    try:
        requests.post(push_url, data=payload)
        print("推送成功！")
    except Exception as e:
        print(f"推送失败: {e}")

def main():
    # 1. 抓取
    hot_list = get_baidu_hot()
    if not hot_list:
        send_bark("运行报错", "未能抓取到热搜数据")
        return

    # 2. AI 分析
    ai_report = ai_analyze_news(hot_list)
    print("AI 简报内容：")
    print(ai_report)

    # 3. 推送
    # 标题用当天的日期
    date_str = datetime.now().strftime("%m-%d")
    send_bark(f"早报 {date_str}", ai_report)

if __name__ == "__main__":
    main()