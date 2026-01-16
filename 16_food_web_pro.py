import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import PyPDF2
import matplotlib.pyplot as plt
import os

# 1. 基础配置
st.set_page_config(page_title="FoodAI 科研中台 Pro", page_icon="🧬", layout="wide")

# ================= 🔐 安全登录模块 =================
def check_password():
    """检查密码是否正确"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True # 已登录

    # 显示输入框
    st.markdown("### 🔒 请输入访问密码")
    pwd = st.text_input("Password", type="password")
    
    # 验证逻辑 (这里我们把密码设为 123456，你也可以去 secrets 里改)
    if st.button("登录"):
        if pwd == st.secrets.get("app_password", "123456"): # 优先读取云端配置的密码
            st.session_state.password_correct = True
            st.rerun() # 刷新页面进入系统
        else:
            st.error("❌ 密码错误")
    return False

# 如果没登录，就停止运行下面的代码
if not check_password():
    st.stop()
# ================================================

# ... (以下是原来的所有功能代码，保持不变) ...

# 加载配置
def load_config():
    if os.path.exists("config.json"):
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    elif hasattr(st, "secrets"):
        return st.secrets
    return {}

CONFIG = load_config()
API_KEY = CONFIG.get("deepseek_api_key", "")
PROXY_URL = CONFIG.get("proxy_url", "")

# 侧边栏
with st.sidebar:
    st.title("🎛️ 控制台")
    st.success(f"✅ 已安全登录") # 登录成功提示
    page = st.radio("功能导航", ["📢 行业情报监测", "📄 文献智能阅读", "📈 实验数据分析"])

# --- 后面所有的函数和页面逻辑(search_bing, ask_deepseek等)全部照搬原来的 ---
# (请把之前代码里 check_password 之后的部分全部粘贴在这里)
# ...
def search_bing(q):
    """真·爬虫模块"""
    headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" }
    try:
        r = requests.get(f"https://cn.bing.com/search?q={q}", headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = []
        for item in soup.select('li.b_algo h2 a'):
            results.append(f"- {item.get_text()} ({item.get('href')})")
        return "\n".join(results[:8]) if results else "未找到有效搜索结果"
    except Exception as e: return f"搜索出错: {e}"

def ask_deepseek(system_prompt, user_content):
    """真·AI模块"""
    if not API_KEY: return "❌ 请先配置 API Key"
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }
        # 如果有配置代理，使用代理
        proxies = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None
        
        resp = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, proxies=proxies, timeout=12030)
        return resp.json()['choices'][0]['message']['content']
    except Exception as e: return f"AI 调用出错: {e}"

def extract_pdf_text(uploaded_file):
    """PDF 解析模块"""
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        return "".join([p.extract_text() for p in reader.pages])
    except: return ""

# ================= 2. 页面逻辑 =================

# --- 模块 A: 情报监测 ---
if page == "📢 行业情报监测":
    st.title("📢 行业情报监测中心")
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        keyword = st.text_input("请输入监测关键词", "非热杀菌技术")
    with col2:
        st.write("") # 占位
        st.write("") 
        start_btn = st.button("🚀 开始全网扫描", type="primary", use_container_width=True)

    if start_btn:
        with st.status("正在执行自动化任务...", expanded=True) as status:
            st.write("🕵️ 正在潜入 Bing 搜索最新情报...")
            search_data = search_bing(keyword)
            st.code(search_data[:200] + "...", language="text") # 展示一部分抓取结果
            
            st.write("🧠 正在唤醒 DeepSeek 大脑进行分析...")
            report = ask_deepseek("你是一位食品行业情报分析专家，请根据搜索结果撰写简报。", f"关键词：{keyword}\n搜索结果：\n{search_data}")
            
            status.update(label="✅ 分析完成！", state="complete", expanded=False)
        
        st.subheader("📝 AI 分析报告")
        st.markdown(report)
        st.download_button("💾 下载报告", report, file_name=f"{keyword}_report.md")

# --- 模块 B: 文献阅读 ---
elif page == "📄 文献智能阅读":
    st.title("📄 文献智能阅读助手")
    st.markdown("---")
    
    uploaded_pdf = st.file_uploader("拖入 PDF 文献 (支持点击上传)", type="pdf")
    
    if uploaded_pdf:
        with st.spinner("正在提取文本..."):
            text = extract_pdf_text(uploaded_pdf)
            st.success(f"已加载: {uploaded_pdf.name} (共 {len(text)} 字)")
        
        question = st.text_input("💡 针对这篇论文，你想问什么？", "这篇论文的核心创新点是什么？")
        
        if st.button("🧠 深度阅读"):
            with st.spinner("AI 正在阅读论文..."):
                answer = ask_deepseek("你是一位严谨的科研助手。请根据下文回答问题。", f"问题：{question}\n原文片段：\n{text[:20000]}")
                st.markdown("### 🎓 回答：")
                st.markdown(answer)

# --- 模块 C: 数据分析 ---
elif page == "📈 实验数据分析":
    st.title("📈 实验数据自动化分析")
    st.info("支持批量上传多个 Excel (.xlsx) 文件，自动合并并计算 Mean ± SD")
    st.markdown("---")
    
    # 支持多文件上传
    uploaded_files = st.file_uploader("请选择实验数据文件 (可多选)", type="xlsx", accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("⚡ 开始批量处理"):
            all_data = []
            for f in uploaded_files:
                df = pd.read_excel(f)
                all_data.append(df)
            
            # 合并数据
            big_df = pd.concat(all_data, ignore_index=True)
            
            # 计算统计量
            summary = big_df.groupby("时间 (h)")["pH值"].agg(["mean", "std"])
            
            # 展示两列：左边表格，右边图表
            c1, c2 = st.columns([1, 2])
            
            with c1:
                st.subheader("📋 统计数据")
                st.dataframe(summary)
            
            with c2:
                st.subheader("📊 科研绘图 (带误差带)")
                # 用 Matplotlib 画图 (为了那个漂亮的误差带)
                fig, ax = plt.subplots(figsize=(8, 5))
                plt.rcParams['font.sans-serif'] = ['SimHei'] # 解决中文乱码
                plt.rcParams['axes.unicode_minus'] = False
                
                ax.plot(summary.index, summary["mean"], color="#FF4B4B", label="pH 平均值", linewidth=2)
                ax.fill_between(summary.index, 
                                summary["mean"] - summary["std"], 
                                summary["mean"] + summary["std"], 
                                color="#FF4B4B", alpha=0.2, label="误差范围 (±SD)")
                ax.set_xlabel("时间 (h)")
                ax.set_ylabel("pH 值")
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.5)
                
                # 🔥 关键：把 Matplotlib 图表显示在网页上
                st.pyplot(fig)