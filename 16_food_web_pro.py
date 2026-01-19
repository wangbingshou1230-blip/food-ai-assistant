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
    st.sidebar.success(f"✅ 已归档: {title[:10]}...")

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
#  配置与工具函数
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

def generate_eln(messages):
    t = datetime.now().strftime("%Y-%m-%d %H:%M")
    rpt = f"# ELN Report\nTime: {t}\n\n"
    for m in messages:
        if m['role']!='system': rpt += f"## {m['role']}\n{m['content']}\n\n"
    return rpt

# --- 图表函数 ---
def plot_nutrition_pie(data):
    fig = go.Figure(data=[go.Pie(labels=list(data.keys()), values=list(data.values()), hole=.3)])
    fig.update_layout(margin=dict(t=20,b=20,l=20,r=20))
    return fig

def plot_radar(name, trend):
    vals=[3,2,1,1,2]
    # 模拟逻辑
    if "酸奶" in name: vals=[3,4,1,0,2]
    elif "咖啡" in name: vals=[2,3,5,0,1]
    
    # 趋势微调
    if "0糖" in trend: vals[0] = 1
    if "高蛋白" in trend: vals[4] += 1
    
    fig = go.Figure(go.Scatterpolar(r=vals, theta=['甜','酸','苦','咸','鲜'], fill='toself', name=name))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0,5])), margin=dict(t=20,b=20,l=30,r=30))
    return fig

# ==================================================
#  主界面逻辑
# ==================================================
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")
app_mode = st.sidebar.selectbox("工作模式", ["🔬 R&D 研发中心", "🎬 自媒体工厂", "🗄️ 数据库", "⚙️ 云端监控"])

# --------------------------------------------------
#  MODE 1: R&D 研发中心
# --------------------------------------------------
if app_mode == "🔬 R&D 研发中心":
    st.title("🔬 智能研发与法规助手")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 大脑配置")
    model_choice = st.sidebar.radio("模型", ["🚀 V3 极速版", "🧠 R1 深度思考"], 0)
    current_model = "reasoner" if "R1" in model_choice else "chat"

    # 防幻觉 Prompt
    strict_prompt = """
    你是一名严谨的食品法规合规专家。核心原则：【依据事实，拒绝幻觉】。
    1. 引用标准：回答合规问题时，必须明确引用具体标准号（如 GB 2760-2024）。
    2. 保守回答：若不确定最新数值，请直接回答“需核实最新标准”，严禁编造。
    3. 数据敏感：添加剂限量必须精确，不能模糊。
    4. 思考过程：请先进行逻辑分析，再给出结论。
    """
    
    if "msg_law" not in st.session_state:
        st.session_state["msg_law"] = [{"role": "system", "content": strict_prompt}]

    # 侧边栏保存
    if len(st.session_state["msg_law"]) > 1:
        st.sidebar.markdown("---")
        report = generate_eln(st.session_state["msg_law"])
        st.sidebar.download_button("📥 导出 MD 报告", report, "ELN.md")
        if st.sidebar.button("💾 归档对话"):
            q = next((m['content'] for m in st.session_state["msg_law"] if m['role']=='user'), "记录")
            save_to_db("ELN", f"对话: {q[:10]}", report)

    # 5大功能区
    tabs = st.tabs(["💬 法规对话", "🧪 智能配方", "📸 视觉分析", "📄 文档Chat", "📊 新品概念"])

    # --- Tab 1: 法规对话 ---
    with tabs[0]:
        for m in st.session_state["msg_law"]:
            if m['role']!='system':
                with st.chat_message(m['role']):
                    if "reasoning" in m: st.expander("🧠 深度思考链").markdown(m["reasoning"])
                    st.markdown(m['content'])
                    if m['role'] == 'assistant':
                        st.caption("🛡️ 人工核实链接：")
                        c1, c2 = st.columns(2)
                        with c1: st.link_button("🔗 食品伙伴网", "http://www.foodmate.net/standards/")
                        with c2: st.link_button("🔗 卫健委", "https://ssp.nhc.gov.cn/database/standards/list.html")

        if p:=st.chat_input("输入合规问题"):
            st.session_state["msg_law"].append({"role":"user","content":p})
            with st.chat_message("user"): st.markdown(p)
            with st.chat_message("assistant"):
                with st.spinner("AI 正在严谨检索与推理..."):
                    r, a = call_deepseek_advanced(st.session_state["msg_law"], current_model)
                if r: st.expander("🧠 深度思考链").markdown(r)
                st.markdown(a)
                st.caption("🛡️ 人工核实链接：")
                c1, c2 = st.columns(2)
                with c1: st.link_button("🔗 食品伙伴网", f"http://www.foodmate.net/search.php?kw={p}")
                with c2: st.link_button("🔗 卫健委", "https://ssp.nhc.gov.cn/database/standards/list.html")
                st.session_state["msg_law"].append({"role":"assistant","content":a,"reasoning":r})

    # --- Tab 2: 智能配方 ---
    with tabs[1]:
        st.subheader("🧪 智能配方计算器")
        txt = st.text_area("输入配方 (如: 生牛乳90%, 白砂糖10%)", height=100)
        if st.button("🧮 计算与评估"):
            with st.spinner("R1 正在逆向拆解配方..."):
                sys = "你是一名配方工程师。请提取原料百分比，计算营养成分(蛋/脂/碳)，并进行GB2760合规预警。"
                r, a = call_deepseek_advanced([{"role":"system","content":sys},{"role":"user","content":txt}], "reasoner")
            c1, c2 = st.columns([3, 2])
            with c1:
                if r: st.expander("计算逻辑").markdown(r)
                st.markdown(a)
            with c2:
                st.markdown("### 📊 预估营养分布")
                st.plotly_chart(plot_nutrition_pie({"碳水":12,"蛋白":3.5,"脂肪":4,"水":80.5}))
            if st.button("💾 保存配方"): save_to_db("FORMULA", f"配方: {txt[:10]}", a)

    # --- Tab 3: 视觉分析 ---
    with tabs[2]:
        st.subheader("📸 配料表风险扫描 (OCR)")
        f = st.file_uploader("上传图片", ["jpg","png"])
        if f and st.button("👁️ 识别"):
            txt = ocr_image(f)
            st.code(txt)
            with st.spinner("R1 风险评估中..."):
                r, a = call_deepseek_advanced([{"role":"user","content":f"分析配料表风险:{txt}"}], "reasoner")
            st.markdown(a)
            st.session_state["msg_law"].append({"role":"user","content":f"[OCR]{txt}"})
            st.session_state["msg_law"].append({"role":"assistant","content":a})

    # --- Tab 4: 文档 Chat ---
    with tabs[3]:
        st.subheader("📄 文档深度问答")
        fs = st.file_uploader("上传PDF", "pdf", True)
        if fs and st.button("📥 读取"):
            st.session_state["doc_c"] = extract_pdf(fs)
            st.session_state["doc_m"] = [{"role":"system","content":f"严格基于以下内容回答:\n{st.session_state['doc_c'][:8000]}"}]
            st.success("读取完成")
        if "doc_m" in st.session_state:
            for m in st.session_state["doc_m"]:
                if m['role']!='system': st.chat_message(m['role']).markdown(m['content'])
            if p:=st.chat_input("基于文档提问", key="doc"):
                st.session_state["doc_m"].append({"role":"user","content":p})
                st.chat_message("user").markdown(p)
                r, a = call_deepseek_advanced(st.session_state["doc_m"], current_model)
                st.chat_message("assistant").markdown(a)
                st.session_state["doc_m"].append({"role":"assistant","content":a})

    # --- Tab 5: 新品概念 (🔥 选项已完全恢复) ---
    with tabs[4]:
        st.subheader("💡 新品概念生成器")
        col1, col2 = st.columns(2)
        with col1: base_product = st.text_input("基底产品", "0糖酸奶")
        with col2: target_user = st.text_input("目标人群", "减脂打工人")
        trend = st.selectbox("结合趋势", ["药食同源", "0糖0卡", "高蛋白", "助眠/解压", "清洁标签"])
        
        if st.button("🧪 生成概念书"):
            sys = "生成食品新品概念书，Markdown格式，包含卖点、配料、风味、包装建议。"
            req = f"基底：{base_product}，人群：{target_user}，趋势：{trend}"
            c_t, c_c = st.columns([3, 2])
            with c_t:
                res = call_deepseek_once(sys, req)
                st.markdown(res)
                if st.button("💾 保存概念"): save_to_db("IDEA", f"概念: {base_product}", res)
            with c_c:
                st.plotly_chart(plot_radar(base_product, trend), use_container_width=True)

# --------------------------------------------------
#  MODE 2: 自媒体工厂 (🔥 选项已完全恢复)
# --------------------------------------------------
elif app_mode == "🎬 自媒体工厂":
    st.title("🎬 自动化内容工厂")
    t1, t2 = st.tabs(["📝 脚本", "🎙️ 配音"])
    
    # --- Tab 1: 脚本生成 ---
    with t1:
        col_h, col_g = st.columns([1,2])
        with col_h:
            if st.button("🔄 刷新热搜"): st.cache_data.clear()
            try:
                hot = requests.get("https://top.baidu.com/board?tab=realtime", headers={"UA":"Mozilla/5.0"}).text
                ts = [t.strip() for t in re.findall(r'ellipsis">(.*?)</div>', hot) if len(t)>4][:10]
                sel = st.radio("选取热点", ts, index=None)
            except: sel=None
            
        with col_g:
            # 恢复完整的输入区
            top = st.text_input("选题", sel if sel else "")
            c1, c2 = st.columns(2)
            with c1: 
                script_type = st.selectbox("类型", ["辟谣粉碎机", "红黑榜测评", "行业内幕揭秘", "热点吃瓜解读"])
            with c2: 
                visual_style = st.selectbox("风格", ["实拍生活风", "宫崎骏动漫", "赛博朋克风", "微距美食"])
            
            if st.button("🚀 生成脚本"):
                # 恢复完整的 Prompt 逻辑
                prompt = f"我是食品科普博主。选题：{top}。类型：{script_type}。风格：{visual_style}。请输出Markdown分镜表格。"
                s = call_deepseek_once(prompt, "")
                st.session_state["scr"] = s
                st.rerun()
                
            if "scr" in st.session_state:
                st.markdown(st.session_state["scr"])
                if st.button("💾 存脚本"): save_to_db("SCRIPT", top, st.session_state["scr"])

    # --- Tab 2: 配音 ---
    with t2:
        st.subheader("🎙️ TTS 配音室")
        txt = st.text_area("粘贴文案")
        voice = st.selectbox("音色", ["zh-CN-YunxiNeural (男声-稳重)", "zh-CN-XiaoxiaoNeural (女声-亲切)", "zh-CN-YunjianNeural (男声-新闻)"])
        if st.button("🎧 生成"):
            try: st.audio(asyncio.run(generate_speech(txt, voice.split(" ")[0])))
            except: st.error("生成失败，请检查网络")

# --------------------------------------------------
#  MODE 3: 数据库
# --------------------------------------------------
elif app_mode == "🗄️ 数据库":
    st.title("🗄️ 研发档案")
    type_ = st.radio("筛选", ["全部","ELN","FORMULA","SCRIPT","IDEA"], horizontal=True)
    t = None if type_=="全部" else type_
    for r in get_history(t):
        with st.expander(f"{r[4]} | [{r[1]}] {r[2]}"): 
            st.markdown(r[3])
            st.download_button("导出MD", r[3], f"{r[1]}.md")

# --------------------------------------------------
#  MODE 4: 云端监控
# --------------------------------------------------
elif app_mode == "⚙️ 云端监控":
    st.title("⚙️ 监控")
    if st.button("测试推送") and "BARK_SERVER" in st.secrets:
        requests.get(f"{st.secrets['BARK_SERVER']}/{st.secrets['BARK_DEVICE_KEY']}/测试")
        st.success("Sent")