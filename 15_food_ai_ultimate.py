import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
import threading
import requests
from bs4 import BeautifulSoup
import json
import PyPDF2 
import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
# 👇 核心技术：把 Matplotlib 图表嵌入 Tkinter 的专用工具
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import json # 👈 记得确保顶部有这行引入
import sys

# ================= 配置中心 (升级版: 读取 config.json) =================
def load_config():
    config_path = "config.json"
    # 检查文件是否存在
    if not os.path.exists(config_path):
        messagebox.showerror("错误", f"找不到配置文件 {config_path}！\n请确保它和程序在同一个文件夹下。")
        sys.exit()
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        messagebox.showerror("配置错误", f"读取 config.json 失败：\n{e}")
        sys.exit()

# 1. 加载配置到变量
CONFIG = load_config()
API_KEY = CONFIG.get("deepseek_api_key", "")
BARK_SERVER = CONFIG.get("bark_server", "https://api.day.app")
BARK_KEY = CONFIG.get("bark_device_key", "")
PROXY_URL = CONFIG.get("proxy_url", "")

# 2. 简单的安全检查
if not API_KEY or "sk-" not in API_KEY:
    print("⚠️ 警告: DeepSeek Key 似乎未正确配置，请检查 config.json")
# ================================================================

class ResearchAgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("食品 AI 全能科研工作台 v3.0 (终极合体版)")
        self.root.geometry("1100x800") # 窗口必须够大，才能放下图表
        
        # --- 1. 创建选项卡管理器 ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # --- 2. 初始化三个功能区 ---
        # Tab 1: 情报 (已完成)
        self.tab_news = tk.Frame(self.notebook)
        self.notebook.add(self.tab_news, text="🕵️ 行业情报监测")
        self.setup_news_tab()
        
        # Tab 2: 文献 (已完成)
        self.tab_paper = tk.Frame(self.notebook)
        self.notebook.add(self.tab_paper, text="🎓 文献智能阅读")
        self.setup_paper_tab()

        # Tab 3: 数据 (🔥 新增功能)
        self.tab_data = tk.Frame(self.notebook)
        self.notebook.add(self.tab_data, text="📊 实验数据分析")
        self.setup_data_tab()
        
        # --- 3. 公共日志区 ---
        tk.Label(root, text="--- 系统运行日志 ---", fg="gray").pack()
        self.log_area = scrolledtext.ScrolledText(root, width=120, height=8, font=("Consolas", 9))
        self.log_area.pack(padx=10, pady=5)
        self.log("✅ 系统全模块加载完毕！等待指令...")

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    # ================= Tab 1: 行业情报 (保持不变) =================
    def setup_news_tab(self):
        frame = tk.Frame(self.tab_news)
        frame.pack(pady=20)
        tk.Label(frame, text="关键词：", font=("微软雅黑", 12)).grid(row=0, column=0)
        self.entry_news = tk.Entry(frame, width=30)
        self.entry_news.insert(0, "非热杀菌技术")
        self.entry_news.grid(row=0, column=1, padx=10)
        tk.Button(frame, text="🚀 开始监测", command=lambda: threading.Thread(target=self.run_news_task).start(), bg="#0078d7", fg="white").grid(row=0, column=2)

    def run_news_task(self):
        keyword = self.entry_news.get()
        self.log(f"--- [情报] 正在搜索: {keyword} ---")
        data = self.search_bing(keyword)
        if data:
            self.log("✅ 搜索完成，正在 AI 分析...")
            res = self.ask_deepseek("news", data)
            self.log(f"🤖 分析报告：\n{res}")
            self.send_bark(res)

    # ================= Tab 2: 文献阅读 (保持不变) =================
    def setup_paper_tab(self):
        frame = tk.Frame(self.tab_paper)
        frame.pack(pady=20)
        tk.Button(frame, text="📂 选择 PDF", command=self.select_pdf).grid(row=0, column=0)
        self.lbl_pdf = tk.Label(frame, text="[未选择]", fg="red")
        self.lbl_pdf.grid(row=0, column=1, padx=10)
        tk.Label(frame, text="提问：").grid(row=1, column=0, pady=10)
        self.entry_q = tk.Entry(frame, width=40)
        self.entry_q.insert(0, "总结核心创新点")
        self.entry_q.grid(row=1, column=1)
        tk.Button(frame, text="🧠 深度阅读", command=lambda: threading.Thread(target=self.run_paper_task).start(), bg="green", fg="white").grid(row=2, column=0, columnspan=2, pady=10)
        self.pdf_text_cache = ""

    def select_pdf(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f: 
            self.pdf_path = f
            self.lbl_pdf.config(text=os.path.basename(f), fg="green")
            self.log(f"📂 加载 PDF: {f}")

    def run_paper_task(self):
        if not self.pdf_text_cache:
            self.log("📖 正在解析 PDF...")
            self.pdf_text_cache = self.extract_pdf(self.pdf_path)
        q = self.entry_q.get()
        context = self.pdf_text_cache[:20000]
        self.log(f"❓ 提问: {q}")
        res = self.ask_deepseek("paper", f"问题：{q}\n原文：\n{context}")
        self.log(f"🎓 回答：\n{res}")

    # ================= Tab 3: 数据分析 (🔥 全新代码) =================
    def setup_data_tab(self):
        # 顶部控制区
        frame_top = tk.Frame(self.tab_data)
        frame_top.pack(pady=10)
        
        tk.Button(frame_top, text="📂 选择数据文件夹 (包含多个xlsx)", command=self.select_folder, width=30).grid(row=0, column=0, padx=5)
        self.lbl_folder = tk.Label(frame_top, text="[未选择文件夹]", fg="red")
        self.lbl_folder.grid(row=0, column=1, padx=5)
        
        tk.Button(frame_top, text="⚡ 一键批量分析 & 绘图", command=self.run_data_analysis, 
                  bg="#d9534f", fg="white", font=("微软雅黑", 10, "bold")).grid(row=0, column=2, padx=15)

        # 底部绘图区 (用一个 Frame 来装 Matplotlib 的图)
        self.plot_frame = tk.Frame(self.tab_data, bg="white", bd=2, relief="sunken")
        self.plot_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # 预留一个变量存画布，防止重复画图重叠
        self.canvas = None

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.data_folder = folder
            self.lbl_folder.config(text=os.path.basename(folder), fg="blue")
            self.log(f"📂 已选中数据池：{folder}")

    def run_data_analysis(self):
        if not hasattr(self, 'data_folder'):
            messagebox.showwarning("提示", "请先选择包含 Excel 文件的文件夹！")
            return
            
        self.log("🧮 正在启动 Pandas 内核处理数据...")
        
        try:
            # 1. 寻找文件
            file_list = glob.glob(os.path.join(self.data_folder, "*.xlsx"))
            if not file_list:
                self.log("❌ 该文件夹下没有 .xlsx 文件！")
                return
            
            self.log(f"ℹ️ 发现 {len(file_list)} 个实验文件，开始合并...")
            
            # 2. 批量读取合并
            all_data = []
            for f in file_list:
                df = pd.read_excel(f)
                all_data.append(df)
            big_df = pd.concat(all_data, ignore_index=True)
            
            # 3. 计算统计量
            summary = big_df.groupby("时间 (h)")["pH值"].agg(["mean", "std"])
            self.log("✅ 数据计算完毕！准备绘图...")
            
            # 4. 嵌入式绘图 (难点！)
            self.draw_plot_in_gui(summary)
            
        except Exception as e:
            self.log(f"❌ 分析出错: {e}")

    def draw_plot_in_gui(self, summary):
        """核心技术：把 Matplotlib 画在 Tkinter 里面"""
        
        # 如果之前画过图，先清除掉，不然会重叠
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
            plt.close('all') # 关闭后台的 plot 避免内存泄漏

        # 1. 创建 Matplotlib 图形对象 (Figure)
        fig = plt.Figure(figsize=(8, 5), dpi=100)
        ax = fig.add_subplot(111) # 添加一个子图
        
        # 2. 正常画图 (用 ax.plot 而不是 plt.plot)
        # 设置字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 绘制
        ax.plot(summary.index, summary["mean"], color="red", label="pH 平均值")
        ax.fill_between(summary.index, 
                        summary["mean"] - summary["std"], 
                        summary["mean"] + summary["std"], 
                        color="red", alpha=0.2, label="误差范围")
        
        ax.set_title("批量实验数据分析报告", fontsize=12)
        ax.set_xlabel("时间 (h)")
        ax.set_ylabel("pH 值")
        ax.grid(True, linestyle='--')
        ax.legend()

        # 3. 关键一步：把 Figure 放入 Tkinter Canvas
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        
        self.log("🎉 图表绘制成功！已展示在下方面板。")

    # ================= 辅助函数 (保持原样) =================
    def extract_pdf(self, path):
        try:
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return "".join([p.extract_text() for p in reader.pages if p.extract_text()])
        except: return ""

    def search_bing(self, q):
        """
        升级版爬虫：
        1. 使用完整 User-Agent 防止被 Bing 拦截。
        2. 使用 li.b_algo 定位符，精准剔除广告。
        3. 增加调试打印，让你看到到底抓了什么。
        """
        try:
            # 伪装成最新的 Chrome 浏览器
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            # 打印一下，看看是不是真的去搜了
            self.log(f"🕵️ 正在潜入 Bing 搜索：{q} ...")
            
            # 发送请求
            r = requests.get(f"https://cn.bing.com/search?q={q}", headers=headers, timeout=10)
            r.encoding = 'utf-8' # 防止中文乱码
            
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # 🟢 关键修改：只提取 'li.b_algo' (正文结果) 下面的标题
            # 之前的写法太宽泛，容易抓到侧边栏广告
            results = []
            for item in soup.select('li.b_algo h2 a'):
                title = item.get_text()
                link = item.get('href')
                results.append(f"- {title} ({link})")
            
            # 如果没抓到正文，可能还是被拦截了，打印源码长度看看
            if not results:
                self.log("⚠️ 警告：未找到有效搜索结果，可能被 Bing 拦截或网络卡顿。")
                # 备用方案：抓所有 h2，但可能含杂质
                results = [t.get_text() for t in soup.select('h2 a')[:5]]
            
            # 提取前 8 条
            final_data = "\n".join(results[:8])
            self.log(f"✅ 抓取成功！获取到 {len(results)} 条线索。")
            return final_data

        except Exception as e:
            self.log(f"❌ 爬虫报错: {e}")
            return None

    def ask_deepseek(self, type, content):
        sys = "你是一位严谨的食品科研专家。" if type == "paper" else "你是一位情报分析师。"
        try:
            resp = requests.post("https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={"model": "deepseek-chat", "messages": [{"role": "system", "content": sys}, {"role": "user", "content": content}]})
            return resp.json()['choices'][0]['message']['content']
        except Exception as e: return str(e)

    def send_bark(self, text):
        """
        修复版：增加字数自动截断功能，防止 413 报错
        """
        # 1. 检查字数，如果太长就截断 (保留前 500 字)
        limit = 500
        if len(text) > limit:
            display_text = text[:limit] + "\n\n(......内容过长，请在电脑端查看完整报告)"
            self.log(f"✂️ 内容过长({len(text)}字)，已自动截取前 {limit} 字推送。")
        else:
            display_text = text
            self.log(f"📲 正在尝试推送 Bark... (字数: {len(text)})")
        
        try:
            payload = {
                "device_key": BARK_KEY,
                "title": "食品AI情报 (简报)",
                "body": display_text, # 发送截断后的内容
                "icon": "https://cdn-icons-png.flaticon.com/512/3076/3076416.png"
            }
            
            resp = requests.post(f"{BARK_SERVER}/push", json=payload, timeout=5)
            
            if resp.status_code == 200:
                self.log("✅ Bark 推送成功！")
            else:
                self.log(f"❌ 推送仍被拒绝: {resp.status_code} - {resp.text}")
                
        except Exception as e:
            self.log(f"❌ 推送网络报错: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ResearchAgentGUI(root)
    root.mainloop()