import streamlit as st
import requests
import re
import pdfplumber
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="FoodMaster 智能工作台",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 🔐 登录验证 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 FoodMaster Pro 登录")
        st.markdown("---")
        password = st.text_input("请输入访问密码", type="password")
        if st.button("🚀 登录系统"):
            correct_password = st.secrets.get("APP_PASSWORD", "123456")
            if password == correct_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ 密码错误")
    return False

if not check_password():
    st.stop()

# ==================================================
#  配置与工具函数
# ==================================================

if "DEEPSEEK_API_KEY" not in st.secrets:
    st.error("⚠️ 配置缺失：请在 Secrets 中添加 DEEPSEEK_API_KEY")
    st.stop()
API_KEY = st.secrets["DEEPSEEK_API_KEY"]

# --- 升级版 AI 调用：支持历史上下文 ---
def call_deepseek_chat(messages):
    """
    messages: list of dict, e.g. [{"role": "user", "content": "hi"}, ...]
    """
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    try:
        with st.spinner("AI 正在思考..."):
            response = requests.post(url, headers=headers, json={
                "model": "deepseek-chat",
                "messages": messages, # 直接发送完整的历史记录
                "stream": False
            })
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"请求异常: {e}"

# 单次调用（用于非对话场景，如写脚本）
def call_deepseek_once(system_prompt, user_input):
    return call_deepseek_chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ])

@st.cache_data(ttl=3600)
def get_realtime_news():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=headers)
        titles = re.findall(r'class="c-single-text-ellipsis">(.*?)</div>', resp.text)
        return [t.strip() for t in titles if len(t) > 4][:10]
    except Exception as e:
        return [f"抓取异常: {e}"]

def extract_text_from_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages[:5]: 
                text += page.extract_text() + "\n"
            return text
    except:
        return ""

def plot_sensory_radar(product_name, trend):
    categories = ['甜度', '酸度', '苦度', '咸度', '鲜度']
    if "酸奶" in product_name: values = [3, 4, 1, 0, 2]
    elif "咖啡" in product_name: values = [2, 3, 5, 0, 1]
    elif "茶" in product_name: values = [1, 2, 4, 0, 3]
    elif "麻辣" in product_name: values = [1, 1, 1, 4, 5]
    else: values = [3, 2, 1, 1, 2]
    
    if "0糖" in trend: values[0] = 1
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself', name=product_name, line_color='#FF4B4B'
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, margin=dict(t=20, b=20, l=40, r=40))
    return fig

# --- 侧边栏 ---
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")

app_mode = st.sidebar.selectbox(
    "选择工作模式",
    ["🔬 R&D 研发与合规 (对话版)", "🎬 自媒体内容矩阵", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: R&D 研发 (Chat 升级版)
# ==================================================
if app_mode == "🔬 R&D 研发与合规 (对话版)":
    st.title("🔬 智能研发与法规助手")
    
    # 使用 session_state 初始化聊天记录
    if "messages_law" not in st.session_state:
        st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。请基于GB2760/GB7718等标准严谨回答。"}]
    
    tab1, tab2, tab3 = st.tabs(["💬 法规智能对话", "📄 智能文档 Chat", "📊 新品研发可视化"])

    # --- Tab 1: 类似 ChatGPT 的法规对话 ---
    with tab1:
        st.info("场景：连续追问合规细节 (具备上下文记忆)")
        
        # 1. 渲染历史聊天记录
        for msg in st.session_state["messages_law"]:
            if msg["role"] != "system": # 不显示系统提示词
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        # 2. 接收新输入
        if prompt := st.chat_input("输入问题 (例如：酸奶能加山梨酸钾吗？)"):
            # 显示用户输入
            st.session_state["messages_law"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # 调用 AI (传入完整历史)
            response = call_deepseek_chat(st.session_state["messages_law"])
            
            # 显示 AI 回答
            st.session_state["messages_law"].append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
                
        # 清空按钮
        if st.button("🗑️ 清空法规对话"):
            st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
            st.rerun()

    # --- Tab 2: 文档对话 (RAG Chat) ---
    with tab2:
        st.subheader("📄 智能文档对话")
        uploaded_files = st.file_uploader("上传 PDF (支持多选)", type="pdf", accept_multiple_files=True)
        
        # 初始化文档聊天记录
        if "messages_doc" not in st.session_state:
            st.session_state["messages_doc"] = []
        if "pdf_context" not in st.session_state:
            st.session_state["pdf_context"] = ""

        if uploaded_files:
            # 读取文件逻辑
            if st.button("📥 读取文档"):
                content = ""
                for file in uploaded_files:
                    content += f"\n--- {file.name} ---\n{extract_text_from_pdf(file)}\n"
                st.session_state["pdf_context"] = content
                st.success(f"已读取 {len(uploaded_files)} 个文件，现在可以开始对话了！")
                # 设置 AI 的系统人设（包含文档内容）
                sys_prompt = f"你是一个文档助手。请完全基于以下内容回答：\n{content[:8000]}..."
                st.session_state["messages_doc"] = [{"role": "system", "content": sys_prompt}]

        # 如果已经读取了文档，显示聊天界面
        if st.session_state["pdf_context"]:
            for msg in st.session_state["messages_doc"]:
                if msg["role"] != "system":
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
            
            if prompt := st.chat_input("基于文档提问..."):
                st.session_state["messages_doc"].append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                response = call_deepseek_chat(st.session_state["messages_doc"])
                
                st.session_state["messages_doc"].append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.markdown(response)
        
        else:
            st.info("请先上传并读取文档。")

    # --- Tab 3: 新品研发 (保留表单模式，适合单次生成) ---
    with tab3:
        st.subheader("💡 新品概念生成 & 风味模拟")
        c1, c2 = st.columns(2)
        with c1: base_product = st.text_input("基底产品", "0糖酸奶")
        with c2: target_user = st.text_input("目标人群", "减脂党")
        trend = st.selectbox("结合趋势", ["药食同源", "0糖0卡", "高蛋白", "助眠/解压", "清洁标签"])
        
        if st.button("🧪 生成概念书 & 风味雷达"):
            sys_prompt = "生成食品新品概念书，Markdown格式。"
            req = f"基底：{base_product}，人群：{target_user}，趋势：{trend}"
            
            col_text, col_chart = st.columns([3, 2])
            with col_text:
                res = call_deepseek_once(sys_prompt, req)
                st.markdown(res)
            with col_chart:
                fig = plot_sensory_radar(base_product, trend)
                st.plotly_chart(fig, use_container_width=True)

# ==================================================
# 模块 2: 自媒体内容矩阵
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵":
    st.title("🎬 自动化内容生产工厂")
    col_hot, col_gen = st.columns([1, 2])
    with col_hot:
        if st.button("🔄 刷新"): st.cache_data.clear()
        hot_list = get_realtime_news()
        selected_hot = st.radio("选择热点：", hot_list, index=None)
        if selected_hot: st.session_state['selected_topic'] = selected_hot

    with col_gen:
        topic = st.text_input("选题", value=st.session_state.get('selected_topic', ''))
        c1, c2 = st.columns(2)
        with c1: type_ = st.selectbox("类型", ["辟谣", "测评", "揭秘"])
        with c2: style = st.selectbox("风格", ["实拍", "动漫", "赛博"])
        if st.button("🚀 生成脚本"):
            if topic:
                prompt = f"我是科普博主。选题：{topic}。类型：{type_}。风格：{style}。输出Markdown分镜表。"
                st.markdown(call_deepseek_once(prompt, topic))

# ==================================================
# 模块 3: 云端看板
# ==================================================
elif app_mode == "⚙️ 云端数据看板":
    st.title("⚙️ 自动化系统监控")
    st.info("云端任务：daily_task.py 正在 GitHub 服务器上每日 08:00 运行")
    if st.button("📲 发送测试推送"):
        if "BARK_SERVER" in st.secrets:
            try:
                requests.get(f"{st.secrets['BARK_SERVER']}/{st.secrets['BARK_DEVICE_KEY']}/测试/网页端指令")
                st.success("✅ 推送成功")
            except: st.error("失败")