import os
import glob
import json
import requests
import pandas as pd  # 如果这行报错，终端运行 pip install pandas

# ================= 配置区 =================
# 【重要】请将下面的 sk-xxx 替换为你刚才申请到的 DeepSeek API Key
api_key = "sk-44104f41c16f42748973c225aff64f0f" 
# =========================================

def get_latest_csv():
    """自动寻找当前文件夹下最新的 CSV 文件"""
    list_of_files = glob.glob('*.csv') # 找所有 csv 文件
    if not list_of_files:
        return None
    # 按创建时间排序，找最新的
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def ask_deepseek(content):
    """把数据发送给 DeepSeek 进行分析"""
    url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 这是我们给 AI 的指令 (Prompt)
    system_prompt = """
    你是一名资深的职业规划师。用户是一名【食品专业硕士】，正在寻求【AI/新媒体运营】方向的工作。
    用户会给你一份从搜索引擎抓取的职位/文章列表。
    
    请你做以下 3 件事：
    1. 【筛选】：剔除掉明显的广告、培训班推销、或者完全不相关的条目。
    2. 【推荐】：挑选出 3 个最值得用户去点击的链接。
    3. 【理由】：用简短的语言解释为什么这 3 个链接对他的转行有帮助。
    
    请直接输出分析结果，不要啰嗦。
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"这是我抓取到的数据：\n{content}"}
        ],
        "stream": False
    }
    
    print("正在请求 DeepSeek 大脑进行分析，请稍等...")
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        # 检查是否成功
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"调用失败，错误代码：{response.status_code}, 信息：{response.text}"
    except Exception as e:
        return f"发生错误：{e}"

def main():
    # 1. 找到最新的数据文件
    csv_file = get_latest_csv()
    if not csv_file:
        print("错误：没找到 CSV 文件。请先运行 3.py 抓取数据！")
        return
    
    print(f"--- 正在读取文件：{csv_file} ---")
    
    # 2. 读取文件内容 (为了节省 tokens，我们只读取前 10 行做测试)
    # 这里我们不用 pandas 库也可以，直接用文件读取，防止你没装 pandas
    with open(csv_file, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    # 3. 发送给 AI
    analysis = ask_deepseek(file_content)
    
    # 4. 打印结果
    print("\n" + "="*20 + " DeepSeek 分析报告 " + "="*20 + "\n")
    print(analysis)
    print("\n" + "="*60)

if __name__ == "__main__":
    main()