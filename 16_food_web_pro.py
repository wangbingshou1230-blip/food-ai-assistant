import streamlit as st
import requests
import re
import pdfplumber
import pandas as pd
import plotly.graph_objects as go
import edge_tts
import asyncio
import json
import easyocr
import numpy as np
import sqlite3
from datetime import datetime
from io import BytesIO
from PIL import Image

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
#  数据库核心函数 (SQLite)
# ==================================================
DB_FILE = "food_master.db"

def init_db():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, title TEXT, content TEXT, timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(record_type, title, content):
    """保存记录"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO records (type, title, content, timestamp) VALUES (?, ?, ?, ?)",
              (record_type, title, content, t))
    conn.commit()
    conn.close()
    st.sidebar.success(f"✅ 已归档: {title[:10]}...")

def get_history(record_type=None):
    """获取历史"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if record_type:
        c.execute("SELECT * FROM records WHERE type=? ORDER BY id DESC LIMIT 20", (record_type,))
    else:
        c.execute("SELECT * FROM records ORDER BY id DESC LIMIT 20")
    data = c.fetchall()
    conn.close()
    return data

init_db()

# ==================================================
#  配置与工具函数
# ==================================================

if "DEEPSEEK_API_KEY" not in st.secrets:
    st.error("⚠️ 配置缺失：请在 Secrets 中添加 DEEPSEEK_API_KEY")
    st.stop()
API_KEY = st.secrets["DEEPSEEK_API_KEY"]

def call_deepseek_advanced(messages, model_type="chat"):
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    model_name = "deepseek-reasoner" if model_type == "reasoner" else "deepseek-chat"
    try:
        response = requests.post(url, headers=headers, json={
            "model": model_name, "messages": messages, "stream": False
        })
        if response.status_code == 200:
            res = response.json()['choices'][0]['message']
            return res.get('reasoning_content', ''), res.get('content', '')
        return None, f"Error: {response.status_code}"
    except Exception as e: return None, str(e)

def call_deepseek_once(sys, user):
    _, c = call_deepseek_advanced([{"role":"system","content":sys},{"role":"user","content":user}],"chat")
    return c

async def generate_speech(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    mp3_fp = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": mp3_fp.write(chunk["data"])
    mp3_fp.seek(0)
    return mp3_fp

@st.cache_resource
def load_ocr(): return easyocr.Reader(['ch_sim','en'], gpu=False)

def ocr_image(file):
    try:
        reader = load_ocr()
        img = np.array(Image.open(file))
        return " ".join(reader.readtext(img, detail=0))
    except Exception as e: return f"Error: {e}"

def generate_eln(messages):
    t = datetime.now().strftime("%Y-%m-%d %H:%M")
    rpt = f"# ELN Report\nTime: {t}\n\n"
    for m in messages:
        if m['role']!='system': rpt += f"## {m['role']}\n{m['content']}\n\n"
    return rpt

# 恢复完整的雷达图逻辑
def plot_sensory_radar(product_name, trend):
    categories = ['甜度', '酸度', '苦度', '咸度', '鲜度']
    values = [3, 2, 1, 1, 2] # 默认
    if "酸奶" in product_name: values = [3, 4, 1, 0, 2]
    elif "咖啡" in product_name: values = [2, 3, 5, 0, 1]
    elif "茶" in product_name: values = [1, 2, 4, 0, 3]
    
    if "0糖" in trend: values[0] = 1 # 降甜
    if "高蛋白" in trend: values[4] += 1 # 提鲜/厚度
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name=product_name, line_color='#FF4B4B'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, margin=dict(t=20, b=20, l=40, r=40))
    return fig

def extract_text_from_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages[:5]: text += page.extract_text() + "\n"
            return text
    except: return ""

# --- 侧边栏 ---
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")

app_mode = st.sidebar.selectbox(
    "选择工作模式",
    ["🔬 R&D 研发与合规", "🎬 自媒体内容矩阵", "🗄️ 历史档案库 (Database)", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: R&D 研发 (全功能恢复版)
# ==================================================
if app_mode == "🔬 R&D 研发与合规":
    st.title("🔬 智能研发与法规助手")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 大脑配置")
    model_choice = st.sidebar.radio("模型选择", ["🚀 V3 极速版", "🧠 R1 深度思考"], 0)
    current_model = "reasoner" if "R1" in model_choice else "chat"

    if "messages_law" not in st.session_state:
        st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
    
    # 侧边栏：保存与导出
    st.sidebar.markdown("---")
    if len(st.session_state["messages_law"]) > 1:
        report = generate_eln(st.session_state["messages_law"])
        c1, c2 = st.sidebar.columns(2)
        with c1: st.download_button("📥 导出MD", report, "ELN.md")
        with c2: 
            if st.button("💾 存入库"):
                first_q = next((m['content'] for m in st.session_state["messages_law"] if m['role']=='user'), "记录")
                save_to_db("ELN", f"R&D: {first_q[:10]}", report)

    # 恢复完整的四个 Tab
    tab1, tab4, tab2, tab3 = st.tabs(["💬 法规智能对话", "📸 视觉配料分析", "📄 智能文档 Chat", "📊 新品研发可视化"])

    # --- Tab 1: 法规对话 ---
    with tab1:
        st.caption(f"当前模式: {model_choice}")
        for m in st.session_state["messages_law"]:
            if m["role"]!="system":
                with st.chat_message(m["role"]):
                    if "reasoning" in m: st.expander("🧠 思维链").markdown(m["reasoning"])
                    st.markdown(m["content"])
        if p:=st.chat_input("输入合规问题..."):
            st.session_state["messages_law"].append({"role":"user","content":p})
            with st.chat_message("user"): st.markdown(p)
            with st.chat_message("assistant"):
                with st.spinner("AI 思考中..."):
                    r, a = call_deepseek_advanced(st.session_state["messages_law"], current_model)
                if r: st.expander("🧠 思维链").markdown(r)
                st.markdown(a)
                st.session_state["messages_law"].append({"role":"assistant","content":a,"reasoning":r})

    # --- Tab 4: 视觉分析 (EasyOCR) ---
    with tab4:
        st.subheader("📸 配料表风险扫描")
        f = st.file_uploader("上传配料表图片", ["jpg","png"])
        if f:
            st.image(f, width=300)
            if st.button("👁️ 开始识别并分析"):
                with st.spinner("OCR 识别中..."):
                    txt = ocr_image(f)
                st.code(txt)
                
                with st.spinner("R1 深度评估中..."):
                    prompt = f"分析以下食品配料表，指出添加剂风险和清洁标签程度：\n{txt}"
                    r, a = call_deepseek_advanced([{"role":"user","content":prompt}], "reasoner")
                
                if r: st.expander("🧠 分析逻辑").markdown(r)
                st.markdown(a)
                # 存入历史以便归档
                st.session_state["messages_law"].append({"role":"user","content":f"[OCR] {txt}"})
                st.session_state["messages_law"].append({"role":"assistant","content":a,"reasoning":r})

    # --- Tab 2: 文档对话 (恢复完整逻辑) ---
    with tab2:
        st.subheader("📄 文档深度问答")
        fs = st.file_uploader("上传 PDF (支持多选)", "pdf", True)
        if fs and st.button("📥 读取文档"):
            c=""
            for f in fs: 
                c += f"\n--- {f.name} ---\n{extract_text_from_pdf(f)}\n"
            st.session_state["doc_c"] = c
            st.session_state["doc_msgs"] = [{"role":"system","content":f"基于内容回答:\n{c[:8000]}"}]
            st.success(f"已读取 {len(fs)} 个文件")
            
        if "doc_msgs" in st.session_state:
            for m in st.session_state["doc_msgs"]:
                if m["role"]!="system":
                    with st.chat_message(m["role"]): st.markdown(m["content"])
            if p:=st.chat_input("问文档...", key="doc_input"):
                st.session_state["doc_msgs"].append({"role":"user","content":p})
                with st.chat_message("user"): st.markdown(p)
                r, a = call_deepseek_advanced(st.session_state["doc_msgs"], current_model)
                with st.chat_message("assistant"):
                    if r: st.expander("逻辑").markdown(r)
                    st.markdown(a)
                st.session_state["doc_msgs"].append({"role":"assistant","content":a})

    # --- Tab 3: 新品研发 (恢复完整表单与图表) ---
    with tab3:
        st.subheader("💡 新品概念生成器")
        c1, c2 = st.columns(2)
        with c1: base = st.text_input("基底产品", "0糖酸奶")
        with c2: user = st.text_input("目标人群", "减脂打工人")
        trend = st.selectbox("结合趋势", ["药食同源", "0糖0卡", "高蛋白", "助眠/解压", "清洁标签"])
        
        if st.button("🧪 生成概念书 & 风味雷达"):
            sys = "生成食品新品概念书，Markdown格式，包含卖点、配料、风味、包装建议。"
            req = f"基底：{base}，人群：{user}，趋势：{trend}"
            
            col_t, col_c = st.columns([3, 2])
            with col_t:
                res = call_deepseek_once(sys, req)
                st.markdown(res)
                # 自动保存到 DB 的快捷按钮
                if st.button("💾 保存此概念"):
                    save_to_db("IDEA", f"概念: {base} x {trend}", res)
            
            with col_c:
                st.markdown("#### 🧬 预估风味轮廓")
                st.plotly_chart(plot_sensory_radar(base, trend), use_container_width=True)

# ==================================================
# 模块 2: 自媒体内容矩阵
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵":
    st.title("🎬 自动化内容工厂")
    t1, t2 = st.tabs(["📝 智能脚本", "🎙️ AI 配音"])
    
    with t1:
        st.caption("从热点到脚本")
        col_h, col_g = st.columns([1,2])
        with col_h:
            if st.button("🔄 刷新热搜"): st.cache_data.clear()
            hot = requests.get("https://top.baidu.com/board?tab=realtime", headers={"User-Agent":"Mozilla/5.0"}).text
            titles = re.findall(r'class="c-single-text-ellipsis">(.*?)</div>', hot)
            clean_t = [t.strip() for t in titles if len(t)>4][:10]
            sel = st.radio("选取热点", clean_t, index=None)
            if sel: st.session_state['sel_topic'] = sel
            
        with col_g:
            topic = st.text_input("选题", st.session_state.get('sel_topic',''))
            c1, c2 = st.columns(2)
            with c1: type_ = st.selectbox("类型", ["辟谣", "测评", "揭秘"])
            with c2: style = st.selectbox("风格", ["实拍", "动漫", "赛博"])
            
            if st.button("🚀 生成脚本"):
                s = call_deepseek_once(f"写分镜脚本,类型{type_},风格{style}", topic)
                st.session_state["last_script"] = s
                st.rerun()
            
            if "last_script" in st.session_state:
                st.markdown(st.session_state["last_script"])
                if st.button("💾 保存脚本到数据库"):
                    save_to_db("SCRIPT", f"脚本: {topic}", st.session_state["last_script"])

    with t2:
        st.subheader("🎙️ TTS 配音室")
        txt = st.text_area("粘贴文案")
        voice = st.selectbox("音色", ["zh-CN-YunxiNeural (男)", "zh-CN-XiaoxiaoNeural (女)"])
        if st.button("🎧 生成"):
            try:
                mp3 = asyncio.run(generate_speech(txt, voice.split(" ")[0]))
                st.audio(mp3)
                st.success("生成成功")
            except: st.error("生成失败")

# ==================================================
# 模块 3: 历史档案库
# ==================================================
elif app_mode == "🗄️ 历史档案库 (Database)":
    st.title("🗄️ 研发与创作档案")
    filter_type = st.radio("筛选", ["全部", "ELN", "SCRIPT", "IDEA"], horizontal=True)
    t_map = {"全部":None, "ELN":"ELN", "SCRIPT":"SCRIPT", "IDEA":"IDEA"}
    
    recs = get_history(t_map[filter_type])
    if not recs: st.info("暂无记录")
    for r in recs:
        with st.expander(f"{r[4]} | [{r[1]}] {r[2]}"):
            st.markdown(r[3])
            st.download_button("导出", r[3], f"{r[1]}_{r[0]}.md")

# ==================================================
# 模块 4: 云端看板
# ==================================================
elif app_mode == "⚙️ 云端数据看板":
    st.title("⚙️ 系统监控")
    st.info("daily_task.py 运行正常")
    if st.button("测试推送"):
        if "BARK_SERVER" in st.secrets:
            requests.get(f"{st.secrets['BARK_SERVER']}/{st.secrets['BARK_DEVICE_KEY']}/测试")
            st.success("Sent")