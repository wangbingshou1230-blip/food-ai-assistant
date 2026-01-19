import streamlit as st
import requests
import re
import pdfplumber
import pandas as pd
import plotly.graph_objects as go
import edge_tts
import asyncio
import json
import easyocr # 新增：OCR 库
import numpy as np
from datetime import datetime
from io import BytesIO
from PIL import Image # 用于处理上传的图片

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

# --- AI 调用 (支持 R1) ---
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
            reasoning = message.get('reasoning_content', '')
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

# --- OCR 核心函数 (新!) ---
@st.cache_resource # 使用缓存，避免每次刷新都重新加载模型，这很关键！
def load_ocr_reader():
    # 加载简写中文(ch_sim)和英文(en)
    return easyocr.Reader(['ch_sim', 'en'], gpu=False) # 云端通常只有CPU

def ocr_image(uploaded_file):
    """读取图片并提取文字"""
    try:
        reader = load_ocr_reader()
        image = Image.open(uploaded_file)
        # EasyOCR 需要 numpy 数组格式
        image_np = np.array(image)
        result = reader.readtext(image_np, detail=0) # detail=0 只返回文字列表
        return " ".join(result)
    except Exception as e:
        return f"OCR 识别失败: {e}"

# --- ELN 报告生成器 ---
def generate_eln_report(messages, project_name="未命名项目"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = f"# 🧬 FoodMaster ELN 实验记录\n**项目**: {project_name}\n**时间**: {timestamp}\n---\n\n"
    for msg in messages:
        if msg["role"] == "user": report += f"## 🙋‍♂️ 提问\n{msg['content']}\n\n"
        elif msg["role"] == "assistant": report += f"## 🤖 回答\n{msg['content']}\n\n---\n"
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
    ["🔬 R&D 研发与合规 (Visual版)", "🎬 自媒体内容矩阵", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: R&D 研发 (集成 Vision)
# ==================================================
if app_mode == "🔬 R&D 研发与合规 (Visual版)":
    st.title("🔬 智能研发与法规助手")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 大脑配置")
    model_choice = st.sidebar.radio("选择模型", ["🚀 V3 极速版", "🧠 R1 深度思考"], index=0)
    current_model = "reasoner" if "R1" in model_choice else "chat"

    if "messages_law" not in st.session_state:
        st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
    
    # ELN 导出
    st.sidebar.markdown("---")
    if len(st.session_state["messages_law"]) > 1:
        report = generate_eln_report(st.session_state["messages_law"])
        st.sidebar.download_button("📥 导出实验报告", report, file_name="ELN.md")

    # 新增 Tab 4: 视觉配料分析
    tab1, tab2, tab4, tab3 = st.tabs(["💬 法规对话", "📄 文档Chat", "📸 视觉配料分析 (OCR)", "📊 新品研发"])

    # --- Tab 1: 法规对话 ---
    with tab1:
        for msg in st.session_state["messages_law"]:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    if "reasoning" in msg:
                        with st.expander("🧠 思维链"): st.markdown(msg["reasoning"])
                    st.markdown(msg["content"])
        
        if prompt := st.chat_input("输入问题..."):
            st.session_state["messages_law"].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("AI 思考中..."):
                    r, a = call_deepseek_advanced(st.session_state["messages_law"], current_model)
                if r: 
                    with st.expander("🧠 思维链"): st.markdown(r)
                st.markdown(a)
                st.session_state["messages_law"].append({"role": "assistant", "content": a, "reasoning": r})
            
    # --- Tab 4: 视觉配料分析 (核心新功能) ---
    with tab4:
        st.subheader("📸 视觉配料表分析 (AI Vision)")
        st.info("场景：上传食品包装/配料表照片，AI 自动提取文字并分析潜在风险。")
        
        img_file = st.file_uploader("上传图片 (JPG/PNG)", type=["jpg", "png", "jpeg"])
        
        if img_file:
            # 显示图片
            st.image(img_file, caption="上传的图片", width=300)
            
            if st.button("👁️ 开始识别并分析"):
                with st.spinner("🔍 正在进行 OCR 文字提取 (首次运行可能较慢)..."):
                    # 1. 提取文字
                    extracted_text = ocr_image(img_file)
                
                if extracted_text and "失败" not in extracted_text:
                    st.success("✅ 文字提取成功！")
                    with st.expander("查看提取到的原始文字"):
                        st.code(extracted_text)
                    
                    # 2. 交给 AI 分析
                    with st.spinner("🧠 R1 正在深度分析配料表..."):
                        sys_prompt = """
                        你是一名食品安全专家。用户会提供一段从食品包装上识别出的文字（可能包含乱码）。
                        请做以下分析：
                        1. 【整理】：修正OCR识别错误的食品添加剂名称。
                        2. 【风险】：指出是否含有致敏原、反式脂肪酸或受争议的添加剂。
                        3. 【评价】：基于配料表判断该产品的加工加工程度（清洁标签程度）。
                        """
                        # 这里强制使用 R1 进行深度推理，因为分析配料表需要逻辑
                        r, a = call_deepseek_advanced([
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": f"识别到的配料表内容：{extracted_text}"}
                        ], model_type="reasoner")
                        
                        if r:
                            with st.expander("🧠 AI 分析逻辑"): st.markdown(r)
                        st.markdown("### 🥗 配料表深度分析报告")
                        st.markdown(a)
                        
                        # 自动存入对话历史，方便导出 ELN
                        st.session_state["messages_law"].append({
                            "role": "user", 
                            "content": f"[图片分析] 配料表内容：{extracted_text}"
                        })
                        st.session_state["messages_law"].append({
                            "role": "assistant", 
                            "content": a,
                            "reasoning": r
                        })
                else:
                    st.error(extracted_text)

    # --- Tab 2: 文档对话 ---
    with tab2:
        st.subheader("📄 文档对话")
        uploaded_files = st.file_uploader("上传PDF", type="pdf", accept_multiple_files=True)
        if uploaded_files and st.button("读取"):
            c = ""
            for f in uploaded_files: c += f"\n--- {f.name} ---\n{extract_text_from_pdf(f)}\n"
            st.session_state["pdf_context"] = c
            st.session_state["messages_doc"] = [{"role":"system","content":f"内容:\n{c[:8000]}"}]
            st.success("读取完成")
        
        if "messages_doc" in st.session_state:
            for m in st.session_state["messages_doc"]:
                if m["role"]!="system":
                    with st.chat_message(m["role"]): st.markdown(m["content"])
            if p:=st.chat_input("问文档", key="doc_chat"):
                st.session_state["messages_doc"].append({"role":"user","content":p})
                with st.chat_message("user"): st.markdown(p)
                r, a = call_deepseek_advanced(st.session_state["messages_doc"], current_model)
                with st.chat_message("assistant"): st.markdown(a)
                st.session_state["messages_doc"].append({"role":"assistant","content":a})

    # --- Tab 3: 新品研发 ---
    with tab3:
        st.subheader("💡 新品概念")
        c1,c2=st.columns(2)
        with c1: base=st.text_input("基底","0糖酸奶")
        with c2: user=st.text_input("人群","减脂党")
        trend=st.selectbox("趋势",["药食同源","0糖"])
        if st.button("生成"):
            col_t, col_c = st.columns([3, 2])
            with col_t: st.markdown(call_deepseek_once("生成概念书", f"{base} {user} {trend}"))
            with col_c: st.plotly_chart(plot_sensory_radar(base, trend))

# ==================================================
# 模块 2: 自媒体
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵":
    st.title("🎬 自动化内容生产工厂")
    tab_script, tab_voice = st.tabs(["📝 脚本生成", "🎙️ AI配音"])
    with tab_script:
        col_h, col_g = st.columns([1,2])
        with col_h:
            if st.button("刷新"): st.cache_data.clear()
            hot=get_realtime_news()
            sel=st.radio("热点",hot,index=None)
            if sel: st.session_state['sel']=sel
        with col_g:
            top=st.text_input("选题",st.session_state.get('sel',''))
            if st.button("生成脚本"):
                st.markdown(call_deepseek_once(f"写脚本，选题：{top}",""))
    with tab_voice:
        txt=st.text_area("文案")
        if st.button("生成语音"):
            try:
                mp3=asyncio.run(generate_speech(txt,"zh-CN-YunxiNeural"))
                st.audio(mp3)
            except: st.error("失败")

# ==================================================
# 模块 3: 云端看板
# ==================================================
elif app_mode == "⚙️ 云端数据看板":
    st.title("⚙️ 自动化系统监控")
    st.info("daily_task.py 每日 08:00 运行")
    if st.button("测试推送"):
        if "BARK_SERVER" in st.secrets:
            requests.get(f"{st.secrets['BARK_SERVER']}/{st.secrets['BARK_DEVICE_KEY']}/测试")
            st.success("已发送")