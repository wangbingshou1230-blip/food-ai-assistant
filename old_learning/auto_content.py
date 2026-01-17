import pandas as pd
import json
import requests

# ================= ⚙️ 配置中心 =================
# 1. 读取我们安全的 API Key
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    API_KEY = config["deepseek_api_key"]
except Exception as e:
    print("❌ 没找到 config.json，请确认你配置了密钥！")
    exit()

# 2. 指定要读取的数据文件 (刚才爬下来的那个)
DATA_FILE = "预制菜标准_新闻.xlsx"

# ================= 🧠 大脑逻辑 =================
def generate_script():
    print(f"📂 正在读取数据文件: {DATA_FILE}...")
    try:
        # 读取 Excel
        df = pd.read_excel(DATA_FILE)
        # 提取前 5 个标题，拼成一个字符串
        titles = df["标题"].head(5).tolist()
        titles_text = "\n".join([f"- {t}" for t in titles])
        print(f"✅ 读取成功！获取到 {len(titles)} 条热点素材。")
        
    except Exception as e:
        print(f"❌ 读取 Excel 失败: {e}")
        return

    # 准备给 AI 的指令 (Prompt)
    prompt = f"""
    你是一个专业的食品安全科普博主。
    以下是今天关于“预制菜”的最新热点新闻标题：
    {titles_text}

    请根据这些热点，写一个 300 字以内的抖音短视频脚本。
    要求：
    1. 风格：犀利、客观、接地气。
    2. 开头：用一句反问或金句抓住眼球。
    3. 中间：结合新闻标题里的信息进行分析（不需要罗列所有新闻，挑重点）。
    4. 结尾：给出一个让观众安心或避雷的建议，并引导点赞关注。
    5. 只要文案内容，不要写“镜头1、镜头2”这种格式。
    """

    print("🧠 正在让 DeepSeek 思考文案 (请稍等)...")
    
    # 调用 DeepSeek API
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            script_content = result['choices'][0]['message']['content']
            
            print("\n" + "="*20 + " 📝 生成的爆款文案 " + "="*20)
            print(script_content)
            print("="*55)
            
            # (可选) 把文案保存到文件
            with open("今日脚本.txt", "w", encoding="utf-8") as f:
                f.write(script_content)
            print("✅ 文案已保存为 '今日脚本.txt'")
            
        else:
            print(f"❌ API 调用失败: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ 网络请求出错: {e}")

if __name__ == "__main__":
    generate_script()