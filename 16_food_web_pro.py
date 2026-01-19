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
#  数据库 (SQLite)
# ==================================================
DB_FILE = "food_master.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS records 
                 (id INTEGER PRIMARY KEY, type TEXT, title TEXT, content TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(type_, title, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO records (type, title, content, timestamp) VALUES (?,?,?,?)",
              (type_, title, content, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    st.toast(f"✅ 已归档: {title}")

def get_history(type_=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    sql = "SELECT * FROM records WHERE type=? ORDER BY id DESC LIMIT 20" if type_ else "SELECT * FROM records ORDER BY id DESC LIMIT 20"
    c.execute(sql, (type_,) if type_ else ())
    data = c.fetchall()
    conn.close()
    return data

init_db()

# ==================================================
#  工具函数
# ==================================================
if "DEEPSEEK_API_KEY" not in st.secrets:
    st.error("⚠️ Secrets 缺失 DEEPSEEK_API_KEY")
    st.stop()
API_KEY = st.secrets["DEEPSEEK_API_KEY"]

def call_deepseek_advanced(messages, model_type="chat"):
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    model = "deepseek-reasoner" if model_type == "reasoner" else "deepseek-chat"
    try:
        r = requests.post(url, headers=headers, json={"model": model, "messages": messages, "stream": False})
        if r.status_code == 200:
            res = r.json()['choices'][0]['message']
            return res.get('reasoning_content', ''), res.get('content', '')
        return None, f"Error: {r.status_code}"
    except Exception as e: return None, str(e)

def call_deepseek_once(sys, user):
    _, c = call_deepseek_advanced([{"role":"system","content":sys},{"role":"user","content":user}],"chat")
    return c

async def generate_speech(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    mp3 = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio": mp3.write(chunk["data"])
    mp3.seek(0)
    return mp3

@st.cache_resource
def load_ocr(): return easyocr.Reader(['ch_sim','en'], gpu=False)

def ocr_image(file):
    try:
        return " ".join(load_ocr().readtext(np.array(Image.open(file)), detail=0))
    except Exception as e: return f"OCR Error: {e}"

def extract_pdf(files):
    c=""
    for f in files:
        try:
            with pdfplumber.open(f) as pdf:
                for p in pdf.pages[:5]: c+=p.extract_text()
        except: pass
    return c

# 绘图函数：营养成分饼图
def plot_nutrition_pie(nutrition_data):
    labels = list(nutrition_data.keys())
    values = list(nutrition_data.values())
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=True)
    return fig

# 绘图函数：风味雷达
def plot_radar(name, trend):
    vals = [3,2,1,1,2]
    if "酸奶" in name: vals=[3,4,1,0,2]
    if "0糖" in trend: vals[0]=1
    fig = go.Figure(go.Scatterpolar(r=vals, theta=['甜','酸','苦','咸','鲜'], fill='toself', name=name))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0,5])), margin=dict(t=20,b=20,l=30,r=30))
    return fig

# ==================================================
#  主界面
# ==================================================
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")
app_mode = st.sidebar.selectbox("工作模式", ["🔬 R&D 研发中心", "🎬 自媒体工厂", "🗄️ 数据库", "⚙️ 云端监控"])

# ---------------- R&D 模块 ----------------
if app_mode == "🔬 R&D 研发中心":
    st.title("🔬 智能研发与法规助手")
    st.sidebar.markdown("---")
    model = "reasoner" if "R1" in st.sidebar.radio("模型", ["🚀 V3", "🧠 R1"], 0) else "chat"
    
    # 5个功能 Tab (新增: 智能配方)
    tabs = st.tabs(["💬 法规对话", "🧪 智能配方设计", "📸 视觉分析", "📄 文档Chat", "📊 新品概念"])

    # Tab 1: 法规对话
    with tabs[0]:
        if "msg_law" not in st.session_state: st.session_state["msg_law"]=[{"role":"system","content":"资深法规专家"}]
        for m in st.session_state["msg_law"]:
            if m['role']!='system':
                with st.chat_message(m['role']):
                    if "reasoning" in m: st.expander("🧠 思维链").markdown(m["reasoning"])
                    st.markdown(m['content'])
        if p:=st.chat_input("合规提问"):
            st.session_state["msg_law"].append({"role":"user","content":p})
            with st.chat_message("user"): st.markdown(p)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    r, a = call_deepseek_advanced(st.session_state["msg_law"], model)
                if r: st.expander("思维链").markdown(r)
                st.markdown(a)
                st.session_state["msg_law"].append({"role":"assistant","content":a,"reasoning":r})
        # 侧边栏保存
        if len(st.session_state["msg_law"])>1:
            if st.sidebar.button("💾 保存对话"):
                save_to_db("ELN", f"对话: {st.session_state['msg_law'][1]['content'][:10]}", str(st.session_state["msg_law"]))

    # Tab 2: 智能配方设计 (NEW!)
    with tabs[1]:
        st.subheader("🧪 智能配方计算器")
        st.info("输入原料及百分比，AI 自动进行营养拆解与合规验算。")
        
        formula_input = st.text_area("输入配方 (例如: 生牛乳 85%, 白砂糖 10%, 浓缩乳清蛋白 4%, 果胶 0.8%, 山梨酸钾 0.2%)", height=100)
        
        if st.button("🧮 开始计算与评估"):
            if not formula_input:
                st.warning("请先输入配方")
            else:
                with st.spinner("AI 正在逆向拆解配方并查询法规库..."):
                    # 1. 结构化处理 Prompt
                    sys_prompt = """
                    你是一名食品配方工程师。请分析用户的配方文本。
                    1. 【表格数据】：提取原料名称和百分比，并预估每种原料的 蛋白质/脂肪/碳水 含量(g/100g)。
                    2. 【营养汇总】：计算成品总的 蛋白质/脂肪/碳水 含量。
                    3. 【合规预警】：检查添加剂是否超标（基于GB2760通用标准），指出风险。
                    
                    输出格式要求：
                    先输出Markdown表格，再输出 '### 营养分析'，最后输出 '### 合规报告'。
                    """
                    r, a = call_deepseek_advanced([
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": formula_input}
                    ], "reasoner") # 必须用 R1 进行计算推理
                
                # 2. 展示结果
                c1, c2 = st.columns([3, 2])
                with c1:
                    if r: st.expander("🧠 配方计算逻辑 (CoT)").markdown(r)
                    st.markdown(a)
                
                with c2:
                    # 3. 尝试提取数据画图 (简单正则提取AI回复中的总营养)
                    # 这里做个简单的模拟解析，实际项目可以让AI返回JSON
                    st.markdown("### 📊 预估营养构成")
                    # 模拟数据 (实际应从AI结果提取)
                    mock_data = {"碳水化合物": 12.0, "蛋白质": 3.8, "脂肪": 3.5, "水/其他": 80.7}
                    st.plotly_chart(plot_nutrition_pie(mock_data), use_container_width=True)
                    st.caption("*注：图表数据为模型估算值，仅供参考")

                # 保存按钮
                if st.button("💾 保存配方报告"):
                    save_to_db("FORMULA", f"配方: {formula_input[:10]}", a)

    # Tab 3: 视觉分析
    with tabs[2]:
        f = st.file_uploader("配方表图片", ["jpg","png"])
        if f and st.button("识别"):
            txt = ocr_image(f)
            st.code(txt)
            r, a = call_deepseek_advanced([{"role":"user","content":f"分析配料风险:{txt}"}], "reasoner")
            st.markdown(a)
            st.session_state["msg_law"].append({"role":"user","content":f"[OCR]{txt}"})
            st.session_state["msg_law"].append({"role":"assistant","content":a})

    # Tab 4: 文档Chat
    with tabs[3]:
        fs = st.file_uploader("上传PDF", "pdf", True)
        if fs and st.button("读取"):
            st.session_state["doc_c"] = extract_pdf(fs)
            st.session_state["doc_m"] = [{"role":"system","content":f"基于:{st.session_state['doc_c'][:8000]}"}]
            st.success("OK")
        if "doc_m" in st.session_state:
            for m in st.session_state["doc_m"]:
                if m['role']!='system': st.chat_message(m['role']).markdown(m['content'])
            if p:=st.chat_input("问文档", key="doc"):
                st.session_state["doc_m"].append({"role":"user","content":p})
                st.chat_message("user").markdown(p)
                r,a=call_deepseek_advanced(st.session_state["doc_m"], model)
                st.chat_message("assistant").markdown(a)
                st.session_state["doc_m"].append({"role":"assistant","content":a})

    # Tab 5: 新品概念
    with tabs[4]:
        b = st.text_input("基底", "酸奶")
        if st.button("生成"):
            res = call_deepseek_once("生成概念书", b)
            st.markdown(res)
            st.plotly_chart(plot_radar(b, ""))

# ---------------- 自媒体 ----------------
elif app_mode == "🎬 自媒体工厂":
    st.title("🎬 自动化内容工厂")
    t1, t2 = st.tabs(["📝 脚本", "🎙️ 配音"])
    with t1:
        if st.button("刷新热搜"): st.cache_data.clear()
        try:
            hot = requests.get("https://top.baidu.com/board?tab=realtime", headers={"UA":"Mozilla/5.0"}).text
            ts = [t.strip() for t in re.findall(r'ellipsis">(.*?)</div>', hot) if len(t)>4][:10]
            sel = st.radio("热点", ts)
        except: sel=None
        top = st.text_input("选题", sel if sel else "")
        if st.button("生成"):
            s = call_deepseek_once(f"写脚本:{top}", "")
            st.session_state["scr"] = s
            st.rerun()
        if "scr" in st.session_state:
            st.markdown(st.session_state["scr"])
            if st.button("💾 存脚本"): save_to_db("SCRIPT", top, st.session_state["scr"])

    with t2:
        txt = st.text_area("文案")
        if st.button("生成语音"):
            try:
                st.audio(asyncio.run(generate_speech(txt, "zh-CN-YunxiNeural")))
            except: st.error("Error")

# ---------------- 数据库 ----------------
elif app_mode == "🗄️ 数据库":
    st.title("🗄️ 研发档案")
    type_ = st.radio("类型", ["全部","ELN","FORMULA","SCRIPT"], horizontal=True)
    t = None if type_=="全部" else type_
    for r in get_history(t):
        with st.expander(f"{r[4]} | [{r[1]}] {r[2]}"): st.markdown(r[3])

# ---------------- 监控 ----------------
elif app_mode == "⚙️ 云端监控":
    st.title("⚙️ 监控")
    if st.button("测试推送") and "BARK_SERVER" in st.secrets:
        requests.get(f"{st.secrets['BARK_SERVER']}/{st.secrets['BARK_DEVICE_KEY']}/测试")
        st.success("Sent")