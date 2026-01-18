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
#  配置与核心工具函数
# ==================================================

if "DEEPSEEK_API_KEY" not in st.secrets:
    st.error("⚠️ 配置缺失：请在 Secrets 中添加 DEEPSEEK_API_KEY")
    st.stop()
API_KEY = st.secrets["DEEPSEEK_API_KEY"]

# --- 核心 AI 调用 (支持 R1 思维链) ---
def call_deepseek_advanced(messages, model_type="chat"):
    """
    model_type: "chat" (V3极速版) or "reasoner" (R1深度思考版)
    返回: (thinking_content, answer_content)
    """
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    
    # 映射模型名称
    model_name = "deepseek-reasoner" if model_type == "reasoner" else "deepseek-chat"
    
    try:
        # Streamlit 的 Spinner 只能在这里显示简单的加载
        # 具体的思考过程展示在 UI 层处理
        response = requests.post(url, headers=headers, json={
            "model": model_name,
            "messages": messages,
            "stream": False
        })
        
        if response.status_code == 200:
            res_json = response.json()
            message = res_json['choices'][0]['message']
            
            # 提取内容
            content = message.get('content', '')
            # 提取思维链 (只有 reasoner 模式才有)
            reasoning = message.get('reasoning_content', '')
            
            return reasoning, content
        else:
            return None, f"Error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return None, f"请求异常: {e}"

# 简易调用包装 (非对话模式用)
def call_deepseek_once(system_prompt, user_input):
    _, content = call_deepseek_advanced([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ], model_type="chat") # 默认用V3
    return content

# --- 语音合成 ---
async def generate_speech(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    mp3_fp = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_fp.write(chunk["data"])
    mp3_fp.seek(0)
    return mp3_fp

# --- 其他辅助 ---
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
            for page in pdf.pages[:5]: text += page.extract_text() + "\n"
            return text
    except: return ""

def plot_sensory_radar(product_name, trend):
    categories = ['甜度', '酸度', '苦度', '咸度', '鲜度']
    values = [3, 2, 1, 1, 2] # Default
    if "酸奶" in product_name: values = [3, 4, 1, 0, 2]
    elif "咖啡" in product_name: values = [2, 3, 5, 0, 1]
    elif "茶" in product_name: values = [1, 2, 4, 0, 3]
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
    ["🔬 R&D 研发与合规 (R1推理版)", "🎬 自媒体内容矩阵", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: R&D 研发 (集成 R1 推理模型)
# ==================================================
if app_mode == "🔬 R&D 研发与合规 (R1推理版)":
    st.title("🔬 智能研发与法规助手")
    
    # --- 侧边栏增加模型控制 ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 大脑配置")
    model_choice = st.sidebar.radio(
        "选择思考模型",
        ["🚀 DeepSeek-V3 (极速模式)", "🧠 DeepSeek-R1 (深度思考)"],
        index=0,
        help="V3适合快速问答；R1适合复杂逻辑推理，会展示思维链。"
    )
    # 将选项转换为代码标识
    current_model = "reasoner" if "R1" in model_choice else "chat"

    # 初始化聊天记录
    if "messages_law" not in st.session_state:
        st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
    
    tab1, tab2, tab3 = st.tabs(["💬 法规智能对话", "📄 智能文档 Chat", "📊 新品研发可视化"])

    # --- Tab 1: 法规对话 ---
    with tab1:
        # 显示历史消息
        for msg in st.session_state["messages_law"]:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    # 如果历史消息里有思考过程，也显示出来（可选，这里简化只显示内容）
                    st.markdown(msg["content"])
        
        # 输入框
        if prompt := st.chat_input("输入合规问题 (试着问一些复杂的逻辑题)..."):
            # 1. 显示用户提问
            st.session_state["messages_law"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # 2. 调用 AI
            with st.chat_message("assistant"):
                status_text = "AI 正在极速响应..." if current_model == "chat" else "AI 正在深度推理 (Chain of Thought)..."
                with st.spinner(status_text):
                    reasoning, answer = call_deepseek_advanced(st.session_state["messages_law"], model_type=current_model)
                
                # 3. 如果有思考过程，使用 Expander 展示
                if reasoning:
                    with st.expander("🧠 点击查看 AI 的深度思考过程 (CoT)"):
                        st.markdown(reasoning)
                
                # 4. 显示最终答案
                st.markdown(answer)
                
                # 5. 保存到历史
                # 注意：为了节省 Token，通常只保存最终答案进历史上下文
                st.session_state["messages_law"].append({"role": "assistant", "content": answer})

        if st.button("🗑️ 清空对话"):
            st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
            st.rerun()

    # --- Tab 2: 文档对话 ---
    with tab2:
        st.subheader("📄 智能文档对话 (支持 R1 推理)")
        uploaded_files = st.file_uploader("上传 PDF", type="pdf", accept_multiple_files=True)
        if "messages_doc" not in st.session_state: st.session_state["messages_doc"] = []
        if "pdf_context" not in st.session_state: st.session_state["pdf_context"] = ""

        if uploaded_files:
            if st.button("📥 读取文档"):
                content = ""
                for file in uploaded_files: content += f"\n--- {file.name} ---\n{extract_text_from_pdf(file)}\n"
                st.session_state["pdf_context"] = content
                st.success(f"已读取 {len(uploaded_files)} 个文件")
                st.session_state["messages_doc"] = [{"role": "system", "content": f"基于以下内容回答:\n{content[:8000]}"}]

        if st.session_state["pdf_context"]:
            for msg in st.session_state["messages_doc"]:
                if msg["role"] != "system":
                    with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            if prompt := st.chat_input("提问文档..."):
                st.session_state["messages_doc"].append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                
                # 这里也复用当前的 model_choice
                with st.chat_message("assistant"):
                    with st.spinner("AI 阅读与思考中..."):
                        reasoning, answer = call_deepseek_advanced(st.session_state["messages_doc"], model_type=current_model)
                    if reasoning:
                        with st.expander("🧠 查看文档分析逻辑"):
                            st.markdown(reasoning)
                    st.markdown(answer)
                    st.session_state["messages_doc"].append({"role": "assistant", "content": answer})

    # --- Tab 3: 新品研发 ---
    with tab3:
        st.subheader("💡 新品概念生成")
        c1, c2 = st.columns(2)
        with c1: base_product = st.text_input("基底", "0糖酸奶")
        with c2: target_user = st.text_input("人群", "减脂党")
        trend = st.selectbox("趋势", ["药食同源", "0糖0卡", "高蛋白"])
        
        if st.button("生成"):
            # 概念生成不需要 R1，用 V3 即可，省钱且快
            col_text, col_chart = st.columns([3, 2])
            with col_text: 
                # 这里调用 once 默认是 chat 模型
                st.markdown(call_deepseek_once("生成概念书", f"{base_product} {target_user} {trend}"))
            with col_chart: 
                st.plotly_chart(plot_sensory_radar(base_product, trend))

# ==================================================
# 模块 2: 自媒体 (保持 V3.1)
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵":
    st.title("🎬 自动化内容生产工厂")
    tab_script, tab_voice = st.tabs(["📝 智能脚本生成", "🎙️ AI 配音室 (TTS)"])

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
                    st.info("💡 提示：请复制文案到配音室使用。")
                    prompt = f"我是科普博主。选题：{topic}。类型：{type_}。风格：{style}。输出Markdown分镜表。"
                    st.markdown(call_deepseek_once(prompt, topic))

    with tab_voice:
        st.subheader("🎙️ AI 配音室")
        text_input = st.text_area("粘贴文案", height=150)
        voice_option = st.selectbox("选择音色", ["zh-CN-YunxiNeural (男声)", "zh-CN-XiaoxiaoNeural (女声)"])
        if st.button("🎧 生成语音"):
            if text_input:
                try:
                    mp3 = asyncio.run(generate_speech(text_input, voice_option.split(" ")[0]))
                    st.audio(mp3, format="audio/mp3")
                    st.success("生成成功")
                except Exception as e: st.error(f"失败: {e}")

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