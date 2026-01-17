import streamlit as st
import pandas as pd
import os
import json
import requests
import pdfplumber # 用于读取 PDF
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ================= ⚙️ 全局配置 =================
st.set_page_config(page_title="FoodAI 全能助手", page_icon="🍔", layout="wide")

# 字体路径 (确保 simhei.ttf 在根目录)
FONT_PATH = "simhei.ttf"
CONFIG_FILE = "config.json"

# ================= 🧹 工具函数 =================

def get_deepseek_response(messages):
    """调用 DeepSeek API"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            api_key = json.load(f)["deepseek_api_key"]
            
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "deepseek-chat", "messages": messages}
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"❌ API 报错: {response.text}"
    except Exception as e:
        return f"❌ 调用失败: {e}"

def read_pdf(file):
    """读取 PDF 文本"""
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def draw_word_cloud(text_data):
    """绘制词云"""
    try:
        wc = WordCloud(
            font_path=FONT_PATH,
            width=800, height=400,
            background_color='white',
            max_words=100
        ).generate(text_data)
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        return plt
    except Exception as e:
        st.error(f"❌ 词云生成失败 (可能是字体缺失): {e}")
        return None

# ================= 🏠 页面 1: AI 智能问答 =================
def page_chat():
    st.title("🤖 食品安全 AI 专家")
    st.caption("有问题？尽管问 DeepSeek。")

    # 初始化历史记录
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 处理用户输入
    if prompt := st.chat_input("请输入你的问题..."):
        # 1. 显示用户问题
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # 2. 调用 AI
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                reply = get_deepseek_response(st.session_state.messages)
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

# ================= 📄 页面 2: 文档分析 (RAG) =================
def page_doc_analysis():
    st.title("📄 论文/文档分析助手")
    st.caption("上传 PDF，AI 帮你读。")

    uploaded_file = st.file_uploader("上传 PDF 文档", type=["pdf"])
    
    if uploaded_file:
        # 1. 提取文本
        with st.spinner("正在读取文档..."):
            doc_text = read_pdf(uploaded_file)
            st.success(f"文档读取成功！共 {len(doc_text)} 字。")
            
        # 2. 预览内容
        with st.expander("👀 查看文档内容预览"):
            st.text(doc_text[:1000] + "...")

        # 3. 针对文档提问
        user_q = st.text_input("关于这篇文档，你想问什么？")
        if user_q and st.button("🚀 提问"):
            with st.spinner("AI 正在分析..."):
                # 构造 Prompt
                messages = [
                    {"role": "system", "content": "你是一个学术助手。请基于以下文档内容回答用户问题。"},
                    {"role": "user", "content": f"文档内容：\n{doc_text[:3000]}...\n\n用户问题：{user_q}"}
                ]
                answer = get_deepseek_response(messages)
                st.write("### 💡 AI 回答：")
                st.write(answer)

# ================= 📊 页面 3: 舆情词云 (新功能) =================
def page_data_viz():
    st.title("📊 舆情热词分析")
    st.caption("可视化你的爬虫数据。")

    folder = "output_files"
    if not os.path.exists(folder):
        st.warning("⚠️ 没找到 output_files 文件夹，请先运行本地爬虫脚本。")
        return

    files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]
    
    if not files:
        st.info("📂 output_files 文件夹里没有 Excel 文件。")
        return

    selected = st.selectbox("选择数据文件:", files)
    if selected:
        path = os.path.join(folder, selected)
        df = pd.read_excel(path)
        
        if "标题" in df.columns:
            text = " ".join(df["标题"].astype(str).tolist())
            if st.button("🎨 生成词云"):
                fig = draw_word_cloud(text)
                if fig: st.pyplot(fig)
        else:
            st.error("❌ Excel 中找不到 '标题' 列。")

# ================= 🔗 导航栏逻辑 =================
def main():
    st.sidebar.image("background.jpg", use_container_width=True)
    st.sidebar.title("🍔 FoodAI 导航")
    
    # 侧边栏菜单
    page = st.sidebar.radio(
        "功能选择", 
        ["🤖 AI 智能问答", "📄 文档分析助手", "📊 舆情热词分析"]
    )

    if page == "🤖 AI 智能问答":
        page_chat()
    elif page == "📄 文档分析助手":
        page_doc_analysis()
    elif page == "📊 舆情热词分析":
        page_data_viz()

if __name__ == "__main__":
    main()