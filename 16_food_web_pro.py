import streamlit as st
import pandas as pd
import os
import json
import requests
import pdfplumber  # 用于读取 PDF
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ================= ⚙️ 1. 全局配置 =================
st.set_page_config(
    page_title="FoodAI 全能助手", 
    page_icon="🍔", 
    layout="wide"
)

# 字体配置：适配云端 (根目录) 和 本地 (C盘)
# 优先使用根目录下的 simhei.ttf (为了云端词云不乱码)
FONT_PATH = "simhei.ttf" 

# ================= 🔐 2. 核心工具：智能密钥获取 =================
def get_api_key():
    """
    双重保险：
    1. 优先去 Streamlit Cloud 的 Secrets 里找 (云端模式)
    2. 找不到再去本地 config.json 里找 (本地开发模式)
    """
    # A. 云端模式
    if "deepseek_api_key" in st.secrets:
        return st.secrets["deepseek_api_key"]
    
    # B. 本地模式
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                return json.load(f).get("deepseek_api_key")
    except Exception:
        pass
    
    return None

def get_deepseek_response(messages):
    """调用 DeepSeek API 的通用函数"""
    api_key = get_api_key()
    
    if not api_key:
        return "❌ 严重错误：未找到 API Key！请在 Streamlit Secrets 或本地 config.json 中配置。"

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-chat", 
                "messages": messages,
                "stream": False
            }
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"❌ API 返回报错: {response.text}"
    except Exception as e:
        return f"❌ 网络请求失败: {e}"

# ================= 🤖 3. 功能模块 A：智能问答 =================
def page_chat():
    st.title("🤖 食品安全 AI 专家")
    st.caption("基于 DeepSeek-V3 · 你的私人科研顾问")

    # 初始化历史记录 (这是上下文记忆的关键)
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 1. 渲染历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 2. 处理新输入
    if prompt := st.chat_input("请输入你的问题，例如：亚硝酸盐超标怎么办？"):
        # 显示用户问题
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # 调用 AI
        with st.chat_message("assistant"):
            with st.spinner("DeepSeek 正在思考..."):
                reply = get_deepseek_response(st.session_state.messages)
                st.write(reply)
                # 记录 AI 回答
                st.session_state.messages.append({"role": "assistant", "content": reply})

# ================= 📄 4. 功能模块 B：文档分析 (RAG) =================
def read_pdf(file):
    """使用 pdfplumber 提取文本"""
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        st.error(f"解析 PDF 失败: {e}")
    return text

def page_doc_analysis():
    st.title("📄 论文/文档深度分析")
    st.caption("上传 PDF，让 AI 帮你读文献、写综述。")

    uploaded_file = st.file_uploader("📂 请上传 PDF 文档", type=["pdf"])
    
    if uploaded_file:
        # 1. 读取内容
        with st.spinner("正在提取文本..."):
            doc_text = read_pdf(uploaded_file)
        
        if len(doc_text) > 10:
            st.success(f"✅ 读取成功！文档长度: {len(doc_text)} 字")
            
            # 2. 预览 (只看前 800 字)
            with st.expander("👀 点击查看文档开头内容"):
                st.text(doc_text[:800] + "......")

            # 3. 提问区
            user_q = st.text_input("👇 关于这篇文档，你想问什么？", placeholder="例如：这篇文章的核心结论是什么？")
            
            if user_q and st.button("🚀 提交问题"):
                with st.spinner("AI 正在阅读并分析..."):
                    # 构造 RAG Prompt
                    # 注意：如果文档太长，截取前 10000 字防止超长
                    context = doc_text[:10000] 
                    messages = [
                        {"role": "system", "content": "你是一个专业的学术助手。请务必基于下方的【文档内容】来回答用户的问题。如果文档里没有提到，请直接说不知道。"},
                        {"role": "user", "content": f"【文档内容】：\n{context}\n\n【用户问题】：{user_q}"}
                    ]
                    answer = get_deepseek_response(messages)
                    st.markdown("### 💡 分析结果")
                    st.write(answer)
        else:
            st.warning("⚠️ 文档内容为空或无法识别，请检查 PDF 是否为扫描件。")

# ================= 📊 5. 功能模块 C：舆情词云 =================
def draw_word_cloud(text_data):
    """生成词云图"""
    if not os.path.exists(FONT_PATH):
        st.error(f"❌ 严重错误：在根目录下找不到字体文件 {FONT_PATH}！请务必上传。")
        return None

    try:
        wc = WordCloud(
            font_path=FONT_PATH,      # 必须指定中文字体
            width=800, height=400,
            background_color='white',
            max_words=80
        ).generate(text_data)
        
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off')
        return plt
    except Exception as e:
        st.error(f"生成词云失败: {e}")
        return None

def page_data_viz():
    st.title("📊 舆情热词可视化")
    
    folder = "output_files"
    if not os.path.exists(folder):
        st.warning("⚠️ 暂无数据。请先运行本地爬虫脚本抓取新闻。")
        return

    # 找 Excel 文件
    files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]
    
    if not files:
        st.info("📂 output_files 文件夹是空的，快去抓点新闻吧！")
        return

    # 选择文件
    selected_file = st.selectbox("📂 选择要分析的数据源:", files)
    
    if selected_file:
        file_path = os.path.join(folder, selected_file)
        try:
            df = pd.read_excel(file_path)
            if "标题" in df.columns:
                st.success(f"✅ 加载数据: {len(df)} 条")
                
                if st.button("🎨 生成今日热点词云"):
                    # 拼接所有标题
                    text = " ".join(df["标题"].astype(str).tolist())
                    fig = draw_word_cloud(text)
                    if fig:
                        st.pyplot(fig)
            else:
                st.error("❌ Excel 格式错误：找不到 '标题' 这一列。")
        except Exception as e:
            st.error(f"读取文件失败: {e}")

# ================= 🔗 6. 主程序导航 =================
def main():
    # 侧边栏图片 (防止报错，先检查是否存在)
    if os.path.exists("background.jpg"):
        st.sidebar.image("background.jpg", use_container_width=True)
    
    st.sidebar.title("🍔 FoodAI 导航")
    
    page = st.sidebar.radio(
        "请选择功能模块:", 
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