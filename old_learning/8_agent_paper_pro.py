import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
import threading
import requests
from bs4 import BeautifulSoup
import json
import PyPDF2 # 👈 核心库：用来读 PDF
import os

# ================= 配置中心 (请填入你的密钥) =================
API_KEY = "sk-44104f41c16f42748973c225aff64f0f"  # DeepSeek 密钥
BARK_SERVER = "https://api.day.app"            # Bark 服务器
BARK_KEY = "JQAghdJVVjub7Y4rvwVPVD"            # 你的 Bark Key
# ==========================================================

class ResearchAgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("食品 AI 全能科研助手 v2.0 (学术严谨版)")
        self.root.geometry("750x650") # 窗口大一点，方便看论文
        
        # --- 创建选项卡 (Tab) ---
        # 这里的 notebook 就是“标签页管理器”
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Tab 1: 情报监测 (原来的搜新闻功能)
        self.tab_news = tk.Frame(self.notebook)
        self.notebook.add(self.tab_news, text="🕵️ 行业情报监测")
        self.setup_news_tab()
        
        # Tab 2: 文献阅读 (你没做过的 RAG 功能)
        self.tab_paper = tk.Frame(self.notebook)
        self.notebook.add(self.tab_paper, text="🎓 文献智能阅读")
        self.setup_paper_tab()
        
        # 公共日志区 (放在最下面，显示运行状态)
        tk.Label(root, text="--- 系统运行日志 ---", fg="gray").pack()
        self.log_area = scrolledtext.ScrolledText(root, width=90, height=12, font=("Consolas", 9))
        self.log_area.pack(padx=10, pady=5)
        self.log("✅ 系统已启动！请在上方选择【情报监测】或【文献阅读】...")

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    # ================= Tab 1: 行业情报 (逻辑) =================
    def setup_news_tab(self):
        frame = tk.Frame(self.tab_news)
        frame.pack(pady=20)
        
        tk.Label(frame, text="输入关键词：", font=("微软雅黑", 12)).grid(row=0, column=0)
        self.entry_news = tk.Entry(frame, width=35, font=("微软雅黑", 10))
        self.entry_news.insert(0, "非热杀菌技术在食品中的应用") # 换个学术点的默认词
        self.entry_news.grid(row=0, column=1, padx=10)
        
        tk.Button(frame, text="开始调研并推送", command=self.start_news_thread,
                  bg="#0078d7", fg="white", font=("微软雅黑", 10, "bold")).grid(row=0, column=2)
        
        tk.Label(frame, text="(注：将搜索前 15 条学术/行业资讯)", fg="gray", font=("微软雅黑", 8)).grid(row=1, column=1, sticky="w")

    def start_news_thread(self):
        threading.Thread(target=self.run_news_task).start()

    def run_news_task(self):
        keyword = self.entry_news.get()
        self.log(f"\n--- [情报模式] 启动：{keyword} ---")
        
        # 1. 搜索 (已升级为 15 条)
        self.log("🕵️ 正在去必应检索文献与资讯 (Top 15)...")
        search_data = self.search_bing(keyword)
        if not search_data: return
        
        # 2. 分析 (已升级为严谨人设)
        self.log("🧠 DeepSeek 正在进行学术综述分析...")
        ai_res = self.ask_deepseek(prompt_type="news", content=search_data)
        if not ai_res: return
        
        self.log(f"🤖 分析结果：\n{ai_res}")
        
        # 3. 推送
        self.log("📲 正在同步至手机终端...")
        self.send_bark(ai_res)
        self.log("✅ 任务闭环完成！")

    # ================= Tab 2: 文献阅读 (这就是你之前没做的！) =================
    def setup_paper_tab(self):
        frame = tk.Frame(self.tab_paper)
        frame.pack(pady=20)
        
        # 1. 文件选择区
        self.btn_file = tk.Button(frame, text="📂 选择本地 PDF", command=self.select_pdf,
                                  font=("微软雅黑", 10), width=15)
        self.btn_file.grid(row=0, column=0, padx=5, pady=5)
        
        self.lbl_filename = tk.Label(frame, text="[未选择文件]", fg="red")
        self.lbl_filename.grid(row=0, column=1, padx=5, sticky="w")
        
        # 2. 提问区
        tk.Label(frame, text="学术提问：", font=("微软雅黑", 12)).grid(row=1, column=0, pady=10)
        self.entry_question = tk.Entry(frame, width=45, font=("微软雅黑", 10))
        self.entry_question.insert(0, "请总结这篇论文的核心创新点和实验结论")
        self.entry_question.grid(row=1, column=1, pady=10)
        
        # 3. 执行按钮
        tk.Button(frame, text="🧠 AI 深度阅读", command=self.start_paper_thread,
                  bg="#28a745", fg="white", font=("微软雅黑", 10, "bold"), width=20).grid(row=2, column=0, columnspan=2, pady=15)
        
        self.pdf_text_cache = "" # 缓存变量：用来存读出来的文字

    def select_pdf(self):
        """弹出窗口让你选文件"""
        filename = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filename:
            self.pdf_path = filename
            # 显示文件名
            self.lbl_filename.config(text=os.path.basename(filename), fg="green")
            self.log(f"📂 已加载本地文件：{filename}")
            self.pdf_text_cache = "" # 换文件了，清空缓存

    def start_paper_thread(self):
        if not hasattr(self, 'pdf_path'):
            messagebox.showwarning("提示", "请先选择一个 PDF 文件！")
            return
        threading.Thread(target=self.run_paper_task).start()

    def run_paper_task(self):
        # 1. 第一次读这个文件时，需要解析
        if not self.pdf_text_cache: 
            self.log("📖 正在解析 PDF 文本 (PyPDF2)...")
            text = self.extract_pdf(self.pdf_path)
            if not text: 
                self.log("❌ PDF 读取失败，可能是扫描件或加密文件。")
                return
            self.pdf_text_cache = text 
            self.log(f"✅ 解析成功！文档长度：{len(text)} 字符。")
        
        # 2. 准备发给 DeepSeek
        question = self.entry_question.get()
        self.log(f"❓ 向 AI 提问：{question}")
        
        # 截取前 25000 字防止超长 (DeepSeek V3 其实支持很长，但保守一点)
        context = self.pdf_text_cache[:25000]
        full_input = f"用户问题：{question}\n\n【待分析论文内容】：\n{context}..."
        
        # 3. 调用 AI
        ai_res = self.ask_deepseek(prompt_type="paper", content=full_input)
        
        if ai_res:
            self.log("\n" + "="*40)
            self.log(f"🎓 论文阅读报告：\n{ai_res}")
            self.log("="*40)
            # 论文阅读结果太长，通常不发手机，直接在屏幕看

    # ================= 核心工具函数 (已升级) =================
    def extract_pdf(self, path):
        """RAG 的核心：把 PDF 变成 AI 能读懂的文字"""
        try:
            with open(path, 'rb') as f: # 打开本地文件
                reader = PyPDF2.PdfReader(f)
                text = ""
                # 遍历每一页
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted: text += extracted + "\n"
            return text
        except Exception as e:
            self.log(f"❌ 读取错误: {e}")
            return None

    def search_bing(self, keyword):
        """抓取逻辑：已升级为 15 条"""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
        try:
            resp = requests.get(f"https://cn.bing.com/search?q={keyword}", headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 🟢 修改点：[:15] 获取前15条
            results = [f"- {t.find('a').get_text()} ({t.find('a').get('href')})" for t in soup.find_all('h2')[:15] if t.find('a')]
            return "\n".join(results) if results else None
        except Exception as e:
            self.log(f"❌ 搜索错误: {e}")
            return None

    def ask_deepseek(self, prompt_type, content):
        """AI 接口：已升级为学术严谨版"""
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
        
        # 🟢 修改点：严谨的 System Prompt
        if prompt_type == "news":
            sys_prompt = """
            你是一位食品科学领域的资深研究员。请阅读以下搜索结果，撰写一份严谨的行业情报简报。
            要求：1. 剔除营销广告。2. 重点关注技术创新、法规变更、学术动态。3. 语言专业、客观，禁止使用网络用语。
            """
        else: # paper
            sys_prompt = """
            你是一位食品加工与安全专业的学术导师。请阅读用户提供的论文内容，用专业、准确的学术语言回答问题。
            要求：1. 引用论文中的数据或实验设计作为支撑。2. 逻辑清晰，条理分明。
            """

        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": content}
                ]
            }
            resp = requests.post(url, headers=headers, data=json.dumps(payload))
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            self.log(f"❌ AI 报错: {resp.text}")
            return None
        except Exception as e:
            self.log(f"❌ 网络错误: {e}")
            return None

    def send_bark(self, content):
        """推送逻辑"""
        try:
            requests.post(f"{BARK_SERVER}/push", 
                          json={"device_key": BARK_KEY, "title": "AI学术汇报", "body": content, "group": "FoodAI", "icon": "https://cdn-icons-png.flaticon.com/512/3076/3076416.png"})
        except: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = ResearchAgentGUI(root)
    root.mainloop()