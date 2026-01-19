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
import sqlite3 # 新增：数据库标准库
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
#  数据库核心函数 (SQLite) - 新增模块
# ==================================================
DB_FILE = "food_master.db"

def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 创建一个通用的记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,      -- 类型: ELN / SCRIPT
            title TEXT,     -- 标题
            content TEXT,   -- 内容详情
            timestamp TEXT  -- 时间
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(record_type, title, content):
    """保存一条记录"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO records (type, title, content, timestamp) VALUES (?, ?, ?, ?)",
              (record_type, title, content, timestamp))
    conn.commit()
    conn.close()
    st.success(f"✅ 已归档: {title}")

def get_history(record_type=None):
    """获取历史记录"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if record_type:
        c.execute("SELECT * FROM records WHERE type=? ORDER BY id DESC LIMIT 20", (record_type,))
    else:
        c.execute("SELECT * FROM records ORDER BY id DESC LIMIT 20")
    data = c.fetchall()
    conn.close()
    return data

# 初始化数据库
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

# --- 侧边栏 ---
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")

# 新增 "历史档案库" 模式
app_mode = st.sidebar.selectbox(
    "选择工作模式",
    ["🔬 R&D 研发与合规", "🎬 自媒体内容矩阵", "🗄️ 历史档案库 (Database)", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: R&D 研发 (含数据库保存)
# ==================================================
if app_mode == "🔬 R&D 研发与合规":
    st.title("🔬 智能研发与法规助手")
    
    st.sidebar.subheader("🧠 配置")
    model_choice = st.sidebar.radio("模型", ["🚀 V3", "🧠 R1"], 0)
    current_model = "reasoner" if "R1" in model_choice else "chat"

    if "messages_law" not in st.session_state:
        st.session_state["messages_law"] = [{"role": "system", "content": "你是一名资深的食品法规专员。"}]
    
    # 侧边栏：保存与导出
    st.sidebar.markdown("---")
    if len(st.session_state["messages_law"]) > 1:
        report = generate_eln(st.session_state["messages_law"])
        # 1. 下载文件
        st.sidebar.download_button("📥 下载 ELN 文件", report, "ELN.md")
        # 2. 保存到数据库 (新功能)
        if st.sidebar.button("💾 归档到数据库"):
            # 提取第一个问题的缩写作为标题
            first_q = next((m['content'] for m in st.session_state["messages_law"] if m['role']=='user'), "未命名记录")
            title = f"R&D: {first_q[:15]}..."
            save_to_db("ELN", title, report)

    tab1, tab4, tab2, tab3 = st.tabs(["💬 对话", "📸 视觉分析", "📄 文档", "📊 新品"])

    with tab1: # 对话
        for m in st.session_state["messages_law"]:
            if m["role"]!="system":
                with st.chat_message(m["role"]):
                    if "reasoning" in m: st.expander("思维链").markdown(m["reasoning"])
                    st.markdown(m["content"])
        if p:=st.chat_input("输入问题..."):
            st.session_state["messages_law"].append({"role":"user","content":p})
            with st.chat_message("user"): st.markdown(p)
            with st.chat_message("assistant"):
                with st.spinner("AI Thinking..."):
                    r, a = call_deepseek_advanced(st.session_state["messages_law"], current_model)
                if r: st.expander("思维链").markdown(r)
                st.markdown(a)
                st.session_state["messages_law"].append({"role":"assistant","content":a,"reasoning":r})

    with tab4: # 视觉
        st.subheader("📸 配料表分析")
        f = st.file_uploader("传图", ["jpg","png"])
        if f and st.button("开始识别"):
            with st.spinner("OCR识别中..."):
                txt = ocr_image(f)
            st.code(txt)
            with st.spinner("R1分析中..."):
                r, a = call_deepseek_advanced([{"role":"user","content":f"分析配料表风险:{txt}"}], "reasoner")
            st.markdown(a)
            # 自动存入对话以便保存
            st.session_state["messages_law"].append({"role":"user","content":f"[OCR] {txt}"})
            st.session_state["messages_law"].append({"role":"assistant","content":a,"reasoning":r})

    with tab2: # 文档 (略简写保持功能)
        st.subheader("📄 文档")
        fs = st.file_uploader("传PDF", "pdf", True)
        if fs and st.button("读取"):
            c=""
            for f in fs: 
                try:
                    with pdfplumber.open(f) as pdf:
                        for p in pdf.pages[:3]: c+=p.extract_text()
                except: pass
            st.session_state["doc_c"] = c
            st.success("OK")
        if "doc_c" in st.session_state and (p:=st.chat_input("问文档", key="doc")):
            st.write(f"问: {p}")
            st.markdown(call_deepseek_once(f"基于:{st.session_state['doc_c'][:5000]}", p))

    with tab3: # 新品
        b = st.text_input("基底", "酸奶")
        if st.button("生成"):
            st.markdown(call_deepseek_once("生成概念书", b))
            st.plotly_chart(go.Figure(go.Scatterpolar(r=[4,3,2,1,5], theta=['A','B','C','D','E'])))

# ==================================================
# 模块 2: 自媒体 (含数据库保存)
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵":
    st.title("🎬 内容工厂")
    t1, t2 = st.tabs(["📝 脚本", "🎙️ 配音"])
    
    with t1:
        topic = st.text_input("选题")
        if st.button("生成脚本"):
            script = call_deepseek_once(f"写分镜脚本:{topic}", "")
            st.session_state["last_script"] = script
            st.markdown(script)
        
        # 数据库保存按钮
        if "last_script" in st.session_state:
            if st.button("💾 保存脚本到数据库"):
                save_to_db("SCRIPT", f"脚本: {topic}", st.session_state["last_script"])

    with t2:
        txt = st.text_area("文案")
        if st.button("生成语音"):
            try:
                mp3 = asyncio.run(generate_speech(txt, "zh-CN-YunxiNeural"))
                st.audio(mp3)
            except: st.error("Error")

# ==================================================
# 模块 3: 历史档案库 (新功能!)
# ==================================================
elif app_mode == "🗄️ 历史档案库 (Database)":
    st.title("🗄️ 数字化研发档案")
    st.markdown("这里存储了所有归档的 **实验记录 (ELN)** 和 **自媒体脚本**。")
    
    # 筛选器
    filter_type = st.radio("筛选类型", ["全部", "ELN (实验记录)", "SCRIPT (脚本)"], horizontal=True)
    type_map = {"全部": None, "ELN (实验记录)": "ELN", "SCRIPT (脚本)": "SCRIPT"}
    
    # 获取数据
    records = get_history(type_map[filter_type])
    
    if not records:
        st.info("暂无存档记录。请去 R&D 或 自媒体模块 生成并保存。")
    else:
        for rec in records:
            # rec结构: (id, type, title, content, timestamp)
            r_id, r_type, r_title, r_content, r_time = rec
            
            with st.expander(f"{r_time} | [{r_type}] {r_title}"):
                st.caption(f"记录ID: {r_id}")
                st.markdown(r_content)
                st.download_button(
                    f"📥 导出此记录", 
                    r_content, 
                    file_name=f"{r_type}_{r_time}.md"
                )

# ==================================================
# 模块 4: 云端看板
# ==================================================
elif app_mode == "⚙️ 云端数据看板":
    st.title("⚙️ 监控")
    st.info("daily_task.py 运行正常")