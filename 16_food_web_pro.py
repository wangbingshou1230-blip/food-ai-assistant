import streamlit as st
import pandas as pd
import os
import json
import requests
import pdfplumber
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter

# ================= ⚙️ 1. 全局配置 =================
st.set_page_config(
    page_title="FoodAI 全能工作台", 
    page_icon="📡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 字体路径 (适配云端和本地)
FONT_PATH = "simhei.ttf"

# ================= 🔐 2. 核心：适配你的 Secrets 配置 =================
def get_config(key_name):
    """
    精准读取你的配置：
    1. 优先读取 Streamlit Secrets (云端)
    2. 其次读取本地 config.json (本地)
    """
    # A. 云端模式 (匹配你截图中的变量名)
    if key_name in st.secrets:
        return st.secrets[key_name]
    
    # B. 本地模式
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                # 本地 config.json 的键名可能不同，这里做个兼容映射
                mapping = {
                    "deepseek_api_key": "deepseek_api_key",
                    "bark_device_key": "bark_key", # 假设本地json里叫bark_key
                    "app_password": "password"     # 假设本地json里叫password
                }
                return config.get(mapping.get(key_name, key_name))
    except:
        pass
    return None

# ================= 🛡️ 3. 安全门禁 (适配 app_password) =================
def check_password():
    """密码验证，对接你的 'app_password'"""
    if st.session_state.get("password_correct", False):
        return True

    st.header("🔒 FoodAI 系统登录")
    password = st.text_input("请输入访问密码", type="password")
    
    if st.button("登录"):
        # 🔥 关键修正：直接读取你 Secrets 里的 'app_password'
        correct_password = get_config("app_password")
        
        # 如果没配置，兜底用 123456，防止死锁
        if not correct_password:
            correct_password = "123456" 
            
        if password == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 密码错误")
    return False

# ================= 📡 4. Bark 推送 (适配 bark_device_key) =================
def send_bark(title, content):
    """
    发送 Bark 通知
    🔥 关键修正：读取 'bark_device_key' 和 'bark_server'
    """
    device_key = get_config("bark_device_key")
    server = get_config("bark_server")
    
    # 如果没配置 server，默认用官方的
    if not server: 
        server = "https://api.day.app"
    
    # 去掉 server 结尾可能的 /
    server = server.rstrip("/")

    if not device_key:
        return False, "⚠️ 未检测到 bark_device_key，无法推送"
    
    # 构造 URL: https://api.day.app/你的Key/标题/内容
    url = f"{server}/{device_key}/{title}/{content}"
    
    try:
        res = requests.get(url)
        if res.status_code == 200:
            return True, "✅ 推送成功"
        else:
            return False, f"❌ 推送失败: {res.text}"
    except Exception as e:
        return False, f"❌ 网络错误: {e}"

# ================= 🧠 5. AI 引擎 (适配 deepseek_api_key) =================
def get_deepseek_response(messages):
    api_key = get_config("deepseek_api_key")
    
    if not api_key:
        return "❌ 错误：未找到 deepseek_api_key，请检查 Secrets。"

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "deepseek-chat", "messages": messages, "stream": False}
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"❌ API 报错: {response.text}"
    except Exception as e:
        return f"❌ 请求失败: {e}"

# ================= 🧩 6. 功能页面组装 =================

def page_chat():
    st.title("🤖 智能问答")
    st.caption("支持 DeepSeek 对话 & Bark 远程推送")

    # --- Bark 测试区 ---
    with st.expander("📡 测试手机推送"):
        col1, col2 = st.columns([3, 1])
        with col1:
            test_msg = st.text_input("输入测试内容", value="系统连接正常")
        with col2:
            if st.button("🚀 发送"):
                success, msg = send_bark("FoodAI测试", test_msg)
                if success:
                    st.toast(msg, icon="✅")
                else:
                    st.error(msg)
    # -------------------

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("请输入问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                reply = get_deepseek_response(st.session_state.messages)
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                
                # 长文本推送按钮
                if len(reply) > 100:
                    if st.button("📲 推送回答摘要到手机"):
                        send_bark("AI回答", reply[:100] + "...")
                        st.success("已推送")

def page_doc_analysis():
    st.title("📄 文档深度分析")
    uploaded_file = st.file_uploader("上传 PDF", type=["pdf"])
    
    if uploaded_file:
        text = ""
        with st.spinner("解析 PDF 中..."):
            try:
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text: text += page_text + "\n"
                
                st.success(f"✅ 解析成功，共 {len(text)} 字")
                
                user_q = st.text_input("关于文档你想问什么？")
                if user_q and st.button("分析"):
                    with st.spinner("AI 阅读中..."):
                        context = text[:15000]
                        messages = [
                            {"role": "system", "content": "你是一个学术助手。"},
                            {"role": "user", "content": f"文档：\n{context}\n\n问题：{user_q}"}
                        ]
                        answer = get_deepseek_response(messages)
                        st.markdown("### 💡 分析结果")
                        st.write(answer)
                        
                        # 自动推送结果
                        send_bark("文档分析完成", f"关于{user_q}的分析已完成。")
            except Exception as e:
                st.error(f"解析失败: {e}")

def page_data_viz():
    st.title("📊 舆情数据看板")
    
    folder = "output_files"
    if not os.path.exists(folder):
        st.warning("⚠️ output_files 文件夹不存在")
        return

    files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]
    if not files:
        st.info("📂 暂无数据文件")
        return

    selected = st.selectbox("选择数据源:", files)
    if selected:
        try:
            df = pd.read_excel(os.path.join(folder, selected))
            if "标题" in df.columns:
                st.success(f"✅ 加载 {len(df)} 条数据")
                
                tab1, tab2 = st.tabs