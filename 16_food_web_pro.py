import streamlit as st
import requests
import re
import pdfplumber
import pandas as pd
import plotly.graph_objects as go
import edge_tts
import asyncio
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

# --- AI 调用 ---
def call_deepseek_chat(messages):
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    try:
        with st.spinner("AI 正在思考..."):
            response = requests.post(url, headers=headers, json={
                "model": "deepseek-chat",
                "messages": messages,
                "stream": False
            })
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"请求异常: {e}"

def call_deepseek_once(system_prompt, user_input):
    return call_deepseek_chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ])

# --- 语音合成 (TTS) 工具函数 (新!) ---
async def generate_speech(text, voice):
    """异步生成语音"""
    communicate = edge_tts.Communicate(text, voice)
    # 将音频数据写入内存 BytesIO，避免产生临时文件
    mp3_fp = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_fp.write(chunk["data"])
    mp3_fp.seek(0)
    return mp3_fp

# --- 其他工具 ---
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
# 模块 1: R&D 研发 (保持 v3.0 不变)
# ==================================================
if app_mode == "🔬 R&D 研发与合规 (对话版)":
    st.title("🔬 智能研发与法规助手")
    
    if "messages_law" not in st.session_state:
        st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
    
    tab1, tab2, tab3 = st.tabs(["💬 法规智能对话", "📄 智能文档 Chat", "📊 新品研发可视化"])

    with tab1:
        for msg in st.session_state["messages_law"]:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        if prompt := st.chat_input("输入合规问题..."):
            st.session_state["messages_law"].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            response = call_deepseek_chat(st.session_state["messages_law"])
            st.session_state["messages_law"].append({"role": "assistant", "content": response})
            with st.chat_message("assistant"): st.markdown(response)
        
        if st.button("🗑️ 清空对话"):
            st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
            st.rerun()

    with tab2:
        st.subheader("📄 智能文档对话")
        uploaded_files = st.file_uploader("上传 PDF", type="pdf", accept_multiple_files=True)
        if "messages_doc" not in st.session_state: st.session_state["messages_doc"] = []
        if "pdf_context" not in st.session_state: st.session_state["pdf_context"] = ""

        if uploaded_files:
            if st.button("📥 读取文档"):
                content = ""
                for file in uploaded_files: content += f"\n--- {file.name} ---\n{extract_text_from_pdf(file)}\n"
                st.session_state["pdf_context"] = content
                st.success("读取完毕")
                st.session_state["messages_doc"] = [{"role": "system", "content": f"基于以下内容回答:\n{content[:8000]}"}]

        if st.session_state["pdf_context"]:
            for msg in st.session_state["messages_doc"]:
                if msg["role"] != "system":
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
            if prompt := st.chat_input("提问文档..."):
                st.session_state["messages_doc"].append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                response = call_deepseek_chat(st.session_state["messages_doc"])
                st.session_state["messages_doc"].append({"role": "assistant", "content": response})
                with st.chat_message("assistant"): st.markdown(response)

    with tab3:
        st.subheader("💡 新品概念生成")
        c1, c2 = st.columns(2)
        with c1: base_product = st.text_input("基底", "0糖酸奶")
        with c2: target_user = st.text_input("人群", "减脂党")
        trend = st.selectbox("趋势", ["药食同源", "0糖0卡", "高蛋白", "清洁标签"])
        if st.button("生成"):
            col_text, col_chart = st.columns([3, 2])
            with col_text: st.markdown(call_deepseek_once("生成新品概念书", f"{base_product} {target_user} {trend}"))
            with col_chart: st.plotly_chart(plot_sensory_radar(base_product, trend))

# ==================================================
# 模块 2: 自媒体内容矩阵 (新增 TTS 配音室)
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵":
    st.title("🎬 自动化内容生产工厂")
    
    # 将原来的布局拆分为 Tabs，加入配音功能
    tab_script, tab_voice = st.tabs(["📝 智能脚本生成", "🎙️ AI 配音室 (TTS)"])

    # --- Tab 1: 脚本生成 (原来的功能) ---
    with tab_script:
        col_hot, col_gen = st.columns([1, 2])
        with col_hot:
            if st.button("🔄 刷新热搜"): st.cache_data.clear()
            hot_list = get_realtime_news()
            selected_hot = st.radio("选择热点：", hot_list, index=None)
            if selected_hot: st.session_state['selected_topic'] = selected_hot

        with col_gen:
            topic = st.text_input("选题", value=st.session_state.get('selected_topic', ''))
            c1, c2 = st.columns(2)
            with c1: type_ = st.selectbox("类型", ["辟谣", "测评", "揭秘"])
            with c2: style = st.selectbox("风格", ["实拍", "动漫", "赛博"])
            
            if st.button("🚀 生成分镜脚本"):
                if topic:
                    # 提示用户复制文案
                    st.info("💡 提示：生成后，请复制表格中的'口播文案'到【AI 配音室】生成语音。")
                    prompt = f"我是科普博主。选题：{topic}。类型：{type_}。风格：{style}。输出Markdown分镜表。"
                    st.markdown(call_deepseek_once(prompt, topic))

    # --- Tab 2: AI 配音室 (新功能) ---
    with tab_voice:
        st.subheader("🎙️ 文字转语音 (Text to Speech)")
        st.caption("基于 Edge-TTS 技术，免费生成高质量 AI 语音，无需录音设备。")
        
        text_input = st.text_area("在此粘贴要朗读的文案", height=150, placeholder="例如：各位同学大家好，我是你们的食品学长...")
        
        # 声音选择 (挑选了几个好听的中文音色)
        voice_option = st.selectbox("选择音色", [
            "zh-CN-XiaoxiaoNeural (女声-温暖亲切)",
            "zh-CN-YunxiNeural (男声-稳重活泼)",
            "zh-CN-YunjianNeural (男声-新闻播音)",
            "zh-CN-XiaoyiNeural (女声-气场全开)"
        ])
        
        # 提取 voice id
        voice_id = voice_option.split(" ")[0]
        
        if st.button("🎧 开始生成语音"):
            if text_input:
                with st.spinner("AI 正在录音棚里朗读..."):
                    # 运行异步生成
                    try:
                        mp3_audio = asyncio.run(generate_speech(text_input, voice_id))
                        st.success("✅ 生成成功！点击下方播放或下载")
                        st.audio(mp3_audio, format="audio/mp3")
                    except Exception as e:
                        st.error(f"生成失败: {e}")
            else:
                st.warning("请先粘贴文案！")

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