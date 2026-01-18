import streamlit as st
import requests
import re
import pdfplumber
import pandas as pd
import plotly.graph_objects as go
import edge_tts
import asyncio
import json
from datetime import datetime
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

# --- AI 调用 (支持 R1 思维链) ---
def call_deepseek_advanced(messages, model_type="chat"):
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    model_name = "deepseek-reasoner" if model_type == "reasoner" else "deepseek-chat"
    
    try:
        response = requests.post(url, headers=headers, json={
            "model": model_name,
            "messages": messages,
            "stream": False
        })
        if response.status_code == 200:
            res_json = response.json()
            message = res_json['choices'][0]['message']
            content = message.get('content', '')
            reasoning = message.get('reasoning_content', '') # 获取思维链
            return reasoning, content
        else:
            return None, f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return None, f"请求异常: {e}"

def call_deepseek_once(system_prompt, user_input):
    _, content = call_deepseek_advanced([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ], model_type="chat")
    return content

# --- TTS ---
async def generate_speech(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    mp3_fp = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_fp.write(chunk["data"])
    mp3_fp.seek(0)
    return mp3_fp

# --- ELN 报告生成器 (新!) ---
def generate_eln_report(messages, project_name="未命名项目"):
    """将对话记录转换为格式化的 Markdown 实验报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"# 🧬 FoodMaster ELN 实验记录\n"
    report += f"**项目名称**: {project_name}\n"
    report += f"**记录时间**: {timestamp}\n"
    report += f"**记录人**: FoodMaster Pro User\n"
    report += "---\n\n"
    
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        if role == "system":
            continue
        elif role == "user":
            report += f"## 🙋‍♂️ 提问/指令\n{content}\n\n"
        elif role == "assistant":
            # 尝试从 session state 找对应的思维链 (这里简化处理，直接输出回答)
            # 如果要保存思维链，需要在 chat loop 里把思维链也存进 messages 或者单独的结构
            # 这里我们假设 content 包含了回答
            report += f"## 🤖 AI 分析结论\n{content}\n\n"
            report += "---\n"
            
    return report

# --- 其他辅助 ---
@st.cache_data(ttl=3600)
def get_realtime_news():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=headers)
        titles = re.findall(r'class="c-single-text-ellipsis">(.*?)</div>', resp.text)
        return [t.strip() for t in titles if len(t) > 4][:10]
    except: return ["暂无热点"]

def extract_text_from_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages[:5]: text += page.extract_text() + "\n"
            return text
    except: return ""

def plot_sensory_radar(product_name, trend):
    categories = ['甜度', '酸度', '苦度', '咸度', '鲜度']
    values = [3, 2, 1, 1, 2]
    if "酸奶" in product_name: values = [3, 4, 1, 0, 2]
    elif "咖啡" in product_name: values = [2, 3, 5, 0, 1]
    if "0糖" in trend: values[0] = 1
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name=product_name, line_color='#FF4B4B'))
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
# 模块 1: R&D 研发 (含 ELN 导出)
# ==================================================
if app_mode == "🔬 R&D 研发与合规 (R1推理版)":
    st.title("🔬 智能研发与法规助手")
    
    # 侧边栏配置
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 大脑配置")
    model_choice = st.sidebar.radio("选择模型", ["🚀 V3 极速版", "🧠 R1 深度思考"], index=0)
    current_model = "reasoner" if "R1" in model_choice else "chat"

    if "messages_law" not in st.session_state:
        st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
    
    # --- ELN 导出区 (侧边栏) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("📂 电子实验记录 (ELN)")
    if len(st.session_state["messages_law"]) > 1:
        st.sidebar.info(f"当前已记录 {len(st.session_state['messages_law'])-1} 条对话")
        report_content = generate_eln_report(st.session_state["messages_law"], project_name="法规合规性审查项目")
        st.sidebar.download_button(
            label="📥 导出实验报告 (.md)",
            data=report_content,
            file_name=f"ELN_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown"
        )
    else:
        st.sidebar.caption("暂无对话记录可导出")

    tab1, tab2, tab3 = st.tabs(["💬 法规智能对话", "📄 智能文档 Chat", "📊 新品研发可视化"])

    with tab1:
        for msg in st.session_state["messages_law"]:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]): 
                    # 如果有思维链字段（这是我们自己加的标记），可以用 expander 显示
                    if "reasoning" in msg:
                        with st.expander("🧠 查看历史思维链"):
                            st.markdown(msg["reasoning"])
                    st.markdown(msg["content"])
        
        if prompt := st.chat_input("输入合规问题..."):
            st.session_state["messages_law"].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant"):
                status = "AI 思考中..." if current_model == "chat" else "R1 深度推理中..."
                with st.spinner(status):
                    reasoning, answer = call_deepseek_advanced(st.session_state["messages_law"], model_type=current_model)
                
                # 记录思维链到历史（为了导出时能看到，虽然generate_eln_report目前还没完美解析它，但我们可以先存着）
                msg_data = {"role": "assistant", "content": answer}
                
                if reasoning:
                    with st.expander("🧠 深度思考过程"): st.markdown(reasoning)
                    msg_data["reasoning"] = reasoning # 把思维链存入消息对象
                
                st.markdown(answer)
                st.session_state["messages_law"].append(msg_data)

        if st.button("🗑️ 清空对话"):
            st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
            st.rerun()

    with tab2: # 文档对话 (简化版)
        st.subheader("📄 智能文档对话")
        uploaded_files = st.file_uploader("上传 PDF", type="pdf", accept_multiple_files=True)
        if "pdf_context" not in st.session_state: st.session_state["pdf_context"] = ""
        if "messages_doc" not in st.session_state: st.session_state["messages_doc"] = []

        if uploaded_files and st.button("📥 读取"):
            content = ""
            for f in uploaded_files: content += f"\n--- {f.name} ---\n{extract_text_from_pdf(f)}\n"
            st.session_state["pdf_context"] = content
            st.session_state["messages_doc"] = [{"role": "system", "content": f"基于内容回答:\n{content[:8000]}"}]
            st.success("读取完成")

        if st.session_state["pdf_context"]:
            for m in st.session_state["messages_doc"]:
                if m["role"]!="system":
                    with st.chat_message(m["role"]): st.markdown(m["content"])
            if p := st.chat_input("问文档..."):
                st.session_state["messages_doc"].append({"role":"user", "content":p})
                with st.chat_message("user"): st.markdown(p)
                # 这里也可以用 R1
                r, a = call_deepseek_advanced(st.session_state["messages_doc"], model_type=current_model)
                with st.chat_message("assistant"):
                    if r: 
                        with st.expander("逻辑"): st.markdown(r)
                    st.markdown(a)
                st.session_state["messages_doc"].append({"role":"assistant", "content":a})

    with tab3: # 新品研发
        st.subheader("💡 新品概念生成")
        c1, c2 = st.columns(2)
        with c1: base = st.text_input("基底", "0糖酸奶")
        with c2: user = st.text_input("人群", "减脂党")
        trend = st.selectbox("趋势", ["药食同源", "0糖0卡"])
        if st.button("生成"):
            col_t, col_c = st.columns([3, 2])
            with col_t: st.markdown(call_deepseek_once("生成概念书", f"{base} {user} {trend}"))
            with col_c: st.plotly_chart(plot_sensory_radar(base, trend))

# ==================================================
# 模块 2: 自媒体 (含脚本导出)
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵":
    st.title("🎬 自动化内容生产工厂")
    tab_script, tab_voice = st.tabs(["📝 智能脚本生成", "🎙️ AI 配音室 (TTS)"])

    with tab_script:
        col_hot, col_gen = st.columns([1, 2])
        with col_hot:
            if st.button("🔄 刷新"): st.cache_data.clear()
            hot_list = get_realtime_news()
            sel = st.radio("热点", hot_list, index=None)
            if sel: st.session_state['sel_topic'] = sel

        with col_gen:
            topic = st.text_input("选题", value=st.session_state.get('sel_topic', ''))
            c1, c2 = st.columns(2)
            with c1: type_ = st.selectbox("类型", ["辟谣", "测评"])
            with c2: style = st.selectbox("风格", ["实拍", "动漫"])
            
            # 使用 session_state 存储生成的脚本，防止刷新消失
            if "generated_script" not in st.session_state:
                st.session_state["generated_script"] = ""

            if st.button("🚀 生成分镜脚本"):
                if topic:
                    prompt = f"我是科普博主。选题：{topic}。类型：{type_}。风格：{style}。输出Markdown分镜表。"
                    script = call_deepseek_once(prompt, topic)
                    st.session_state["generated_script"] = script
                    st.rerun() # 刷新页面以显示下载按钮

            if st.session_state["generated_script"]:
                st.markdown(st.session_state["generated_script"])
                st.download_button(
                    label="📥 下载脚本文件 (.md)",
                    data=st.session_state["generated_script"],
                    file_name=f"Script_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )

    with tab_voice:
        st.subheader("🎙️ AI 配音室")
        txt = st.text_area("粘贴文案", height=150)
        voice = st.selectbox("音色", ["zh-CN-YunxiNeural (男)", "zh-CN-XiaoxiaoNeural (女)"])
        if st.button("🎧 生成"):
            if txt:
                try:
                    mp3 = asyncio.run(generate_speech(txt, voice.split(" ")[0]))
                    st.audio(mp3)
                    st.success("生成成功")
                except: st.error("失败")

# ==================================================
# 模块 3: 云端看板
# ==================================================
elif app_mode == "⚙️ 云端数据看板":
    st.title("⚙️ 自动化系统监控")
    st.info("云端任务：daily_task.py 正在 GitHub 服务器上每日 08:00 运行")
    if st.button("📲 测试推送"):
        if "BARK_SERVER" in st.secrets:
            try:
                requests.get(f"{st.secrets['BARK_SERVER']}/{st.secrets['BARK_DEVICE_KEY']}/测试/网页端指令")
                st.success("✅ 推送成功")
            except: st.error("失败")