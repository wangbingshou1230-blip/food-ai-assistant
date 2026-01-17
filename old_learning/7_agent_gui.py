import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading # 这是一个防卡死的神器
import requests
from bs4 import BeautifulSoup
import json
import time

# ================= 配置中心 (请填入你的密钥) =================
API_KEY = "sk-44104f41c16f42748973c225aff64f0f"  # DeepSeek 密钥
BARK_SERVER = "https://api.day.app"            # Bark 服务器
BARK_KEY = "JQAghdJVVjub7Y4rvwVPVD"            # 你的 Bark Key
# ==========================================================

class FoodAIAgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("食品 AI 情报助手 v1.0 (Python版)")
        self.root.geometry("600x450") # 设置窗口大小
        
        # 1. 顶部：输入区
        self.label = tk.Label(root, text="请输入你想调研的主题：", font=("微软雅黑", 12))
        self.label.pack(pady=5)
        
        self.entry = tk.Entry(root, width=50, font=("微软雅黑", 10))
        self.entry.insert(0, "食品行业 AI 落地应用") # 默认文字
        self.entry.pack(pady=5)
        
        # 2. 中部：大按钮
        self.btn_start = tk.Button(root, text="开始全自动分析", command=self.start_thread, 
                                   bg="#0078d7", fg="white", font=("微软雅黑", 12, "bold"), width=20)
        self.btn_start.pack(pady=10)
        
        # 3. 底部：滚动文本框 (显示运行日志)
        self.log_area = scrolledtext.ScrolledText(root, width=70, height=18, font=("Consolas", 9))
        self.log_area.pack(pady=5)
        
        self.log("✅ 软件已启动，随时待命...")

    def log(self, message):
        """往文本框里写日志"""
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END) # 自动滚动到底部

    def start_thread(self):
        """启动一个新线程来干活，这样界面不会卡死"""
        self.btn_start.config(state=tk.DISABLED, text="正在运行中...") # 禁用按钮
        self.log_area.delete(1.0, tk.END) # 清空旧日志
        
        # 创建并启动线程
        threading.Thread(target=self.run_task).start()

    def run_task(self):
        """这是真正的后台干活逻辑 (把之前的 step1,2,3 搬过来了)"""
        keyword = self.entry.get()
        
        # --- 第一步：搜索 ---
        self.log(f"🕵️ 正在去必应搜索：{keyword} ...")
        search_result = self.step1_search_bing(keyword)
        if not search_result:
            self.finish_task("搜索失败")
            return
        self.log(f"✅ 抓取成功！获取到信息量：{len(search_result)} 字符")
        
        # --- 第二步：DeepSeek 分析 ---
        self.log("🧠 正在发送给 DeepSeek 大脑进行分析 (请稍等 5-10 秒)...")
        ai_comment = self.step2_ai_analyze(search_result)
        if not ai_comment:
            self.finish_task("AI 分析失败")
            return
        
        self.log("\n" + "="*30)
        self.log("🤖 DeepSeek 的评价：")
        self.log(ai_comment)
        self.log("="*30 + "\n")
        
        # --- 第三步：推送 ---
        self.log("📲 正在推送到手机 Bark...")
        self.step3_send_notification(ai_comment)
        
        self.finish_task("✅ 所有任务执行完毕！")

    def finish_task(self, status):
        """任务结束，恢复按钮"""
        self.log(f"\n[{status}]")
        self.btn_start.config(state=tk.NORMAL, text="开始全自动分析")

    # ================= 下面是你的核心逻辑函数 (原封不动搬过来的) =================
    
    def step1_search_bing(self, keyword):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
        url = f"https://cn.bing.com/search?q={keyword}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = [f"- {t.find('a').get_text()} ({t.find('a').get('href')})" for t in soup.find_all('h2')[:15] if t.find('a')]
            return "\n".join(results) if results else None
        except Exception as e:
            self.log(f"❌ 搜索出错: {e}")
            return None

    def step2_ai_analyze(self, data):
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
        prompt = """你是一位资深的食品科学与工程研究员。用户是该领域的硕士毕业生。
            请阅读以下搜索结果，撰写一份【严谨的行业情报简报】：
            1. 剔除无关广告和营销号内容。
            2. 提炼出核心的技术趋势、新应用场景或政策导向。
            3. 语言风格要求：学术、客观、专业（禁止使用网络流行语）。
            4. 格式要求：分点陈述，关键信息加粗。"""
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": data}]
        }
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload))
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            return None
        except Exception as e:
            self.log(f"❌ AI 出错: {e}")
            return None

    def step3_send_notification(self, content):
        url = "https://api.day.app/push"
        payload = {
            "device_key": BARK_KEY,
            "title": "AI情报助手",
            "body": content,
            "group": "FoodAI",
            "icon": "https://cdn-icons-png.flaticon.com/512/2083/2083256.png"
        }
        try:
            requests.post(url, json=payload, headers={"Content-Type": "application/json; charset=utf-8"})
            self.log("✅ 手机推送成功！")
        except Exception as e:
            self.log(f"❌ 推送失败: {e}")

# ================= 启动程序 =================
if __name__ == "__main__":
    root = tk.Tk()
    app = FoodAIAgentGUI(root)
    root.mainloop()