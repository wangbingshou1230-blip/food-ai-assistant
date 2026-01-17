import streamlit as st
import pandas as pd
import os
import json
import requests
import pdfplumber
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter # 用于统计词频

# ================= ⚙️ 1. 全局配置与字体 =================
st.set_page_config(
    page_title="FoodAI 全能工作台", 
    page_icon="🛡️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 字体路径 (适配云端和本地)
FONT_PATH = "simhei.ttf"

# ================= 🔐 2. 安全门神：密码登录系统 =================
def check_password():
    """返回 True 如果密码正确，否则返回 False"""
    
    # 如果已经登录成功，直接放行
    if st.session_state.get("password_correct", False):
        return True

    # 显示登录框
    st.header("🔒 FoodAI 内部系统登录")
    password = st.text_input("请输入访问密码", type="password")
    
    if st.button("登录"):
        # 优先从 Secrets 读取密码，如果没有配置，默认密码是 123456
        # 你可以在 Streamlit Secrets 里配置 [passwords] main = "你的密码"
        correct_password = st.secrets.get("passwords", {}).get("main", "123456")
        
        if password == correct_password:
            st.session_state["password_correct"] = True
            st.rerun() # 刷新页面进入系统
        else:
            st.error("❌ 密码错误")
            
    return False

# ================= 🔑 3. 核心工具：双重密钥获取 =================
def get_api_key():
    """双重保险：优先云端 Secrets，其次本地 config.json"""
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
    """调用 DeepSeek API"""
    api_key = get_api_key()
    if not api_key:
        return "❌ 未找到 API Key！请配置 Secrets 或 config.json。"

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

# ================= 🤖 4. 模块 A：AI 智能问答 =================
def page_chat():
    st.title("🤖 食品安全 AI 专家")
    st.caption("基于 DeepSeek-V3 · 你的私人科研顾问")

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
            with st.spinner("AI 思考中..."):
                reply = get_deepseek_response(st.session_state.messages)
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

# ================= 📄 5. 模块 B：文档深度分析 (RAG) =================
def page_doc_analysis():
    st.title("📄 文献/文档智能分析")
    uploaded_file = st.file_uploader("上传 PDF 文档", type=["pdf"])
    
    if uploaded_file:
        text = ""
        with st.spinner("正在解析 PDF..."):
            try:
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                st.success(f"✅ 解析成功，共 {len(text)} 字")
                
                with st.expander("👀 查看文档预览"):
                    st.text(text[:1000] + "...")
                    
                user_q = st.text_input("针对此文档提问：")
                if user_q and st.button("分析"):
                    with st.spinner("AI 正在阅读..."):
                        # 防止 token 超出，截取前 1.5万字
                        context = text[:15000]
                        messages = [
                            {"role": "system", "content": "你是一个学术助手。必须基于以下文档内容回答问题。"},
                            {"role": "user", "content": f"文档内容：\n{context}\n\n问题：{user_q}"}
                        ]
                        answer = get_deepseek_response(messages)
                        st.markdown("### 💡 分析结果")
                        st.write(answer)
            except Exception as e:
                st.error(f"PDF 解析失败: {e}")

# ================= 📊 6. 模块 C：数据分析 (词云 + 图表) =================
def page_data_viz():
    st.title("📊 舆情与数据分析看板")
    
    folder = "output_files"
    if not os.path.exists(folder):
        st.warning("⚠️ 本地没有 output_files 文件夹，请先运行爬虫脚本。")
        return

    files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]
    if not files:
        st.info("📂 暂无数据文件。")
        return

    selected_file = st.selectbox("📂 选择数据源:", files)
    
    if selected_file:
        file_path = os.path.join(folder, selected_file)
        try:
            df = pd.read_excel(file_path)
            if "标题" not in df.columns:
                st.error("❌ 数据格式错误：缺少 '标题' 列")
                return
                
            st.success(f"✅ 加载 {len(df)} 条数据")
            
            # --- 核心修复：数据分析不只是词云 ---
            tab1, tab2 = st.tabs(["☁️ 词云视图", "📈 频次统计"])
            
            # 准备文本数据
            all_text = " ".join(df["标题"].astype(str).tolist())
            
            with tab1:
                if st.button("生成词云"):
                    if not os.path.exists(FONT_PATH):
                        st.error("❌ 缺少 simhei.ttf 字体文件")
                    else:
                        wc = WordCloud(font_path=FONT_PATH, width=800, height=400, background_color='white').generate(all_text)
                        plt.figure(figsize=(10, 5))
                        plt.imshow(wc, interpolation='bilinear')
                        plt.axis('off')
                        st.pyplot(plt)
            
            with tab2:
                # 简单的分词逻辑（按空格分割，实际中文分词通常用 jieba，但这里为了环境简单，假设标题里有空格或直接统计字/词）
                # 这里做一个简单的 Top 20 词频统计（按空格切分模拟，如果标题是整句，这里统计的可能不准，但演示了图表功能）
                st.caption("这里展示标题中出现频率最高的关键词（示例算法）")
                # 为了让图表有内容，我们简单按字/词切分
                words = [w for w in all_text.split() if len(w) > 1] 
                if words:
                    count_data = pd.DataFrame(Counter(words).most_common(20), columns=["词语", "频次"])
                    st.bar_chart(count_data.set_index("词语"))
                else:
                    st.warning("数据太少，无法生成统计图。")

        except Exception as e:
            st.error(f"读取失败: {e}")

# ================= 🚀 7. 主程序入口 =================
def main():
    # 🛑 只有密码验证通过，才显示下面的内容
    if not check_password():
        return  # 如果没登录，直接结束，不渲染侧边栏和功能区

    # 登录成功后显示的内容
    if os.path.exists("background.jpg"):
        st.sidebar.image("background.jpg", use_container_width=True)
    
    st.sidebar.title("🍔 FoodAI 系统")
    st.sidebar.success("✅ 已安全登录")
    
    page = st.sidebar.radio("功能导航", ["🤖 智能问答", "📄 文档分析", "📊 数据看板"])
    
    if page == "🤖 智能问答":
        page_chat()
    elif page == "📄 文档分析":
        page_doc_analysis()
    elif page == "📊 数据看板":
        page_data_viz()

if __name__ == "__main__":
    main()