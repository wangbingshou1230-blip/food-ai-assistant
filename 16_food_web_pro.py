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
from datetime import datetime
from io import BytesIO
from PIL import Image
from supabase import create_client, Client

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
#  云端数据库核心函数 (Supabase) - 核心升级点
# ==================================================
# 从 Secrets 获取配置
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("⚠️ 配置缺失：请在 Secrets 中配置 SUPABASE_URL 和 SUPABASE_KEY")
    st.stop()

# 初始化客户端 (使用 @st.cache_resource 避免重复连接)
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

def save_to_db(record_type, title, content):
    """保存数据到 Supabase Cloud"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        data = {
            "type": record_type,
            "title": title,
            "content": content,
            "timestamp": current_time
        }
        # 插入数据
        supabase.table("records").insert(data).execute()
        st.sidebar.success(f"☁️ 已云端归档: {title[:10]}...")
    except Exception as e:
        st.sidebar.error(f"保存失败: {e}")

def get_history(record_type=None):
    """从 Supabase Cloud 拉取数据"""
    try:
        query = supabase.table("records").select("*").order("id", desc=True).limit(20)
        
        if record_type:
            query = query.eq("type", record_type)
            
        response = query.execute()
        return response.data # 返回的是列表字典 [{'id':1, 'title':'...'}, ...]
    except Exception as e:
        st.error(f"读取失败: {e}")
        return []

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

def plot_nutrition_pie(data):
    fig = go.Figure(data=[go.Pie(labels=list(data.keys()), values=list(data.values()), hole=.3)])
    fig.update_layout(margin=dict(t=20,b=20,l=20,r=20))
    return fig

def plot_radar(name, trend):
    vals=[3,2,1,1,2]
    if "酸奶" in name: vals=[3,4,1,0,2]
    elif "咖啡" in name: vals=[2,3,5,0,1]
    if "0糖" in trend: vals[0] = 1
    if "高蛋白" in trend: vals[4] += 1
    fig = go.Figure(go.Scatterpolar(r=vals, theta=['甜','酸','苦','咸','鲜'], fill='toself', name=name))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0,5])), margin=dict(t=20,b=20,l=30,r=30))
    return fig

# ==================================================
#  主界面逻辑
# ==================================================
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的云端解决方案")
app_mode = st.sidebar.selectbox("工作模式", ["🔬 R&D 研发中心", "🎬 自媒体工厂", "🗄️ 云端档案库 (Supabase)", "⚙️ 云端监控"])

# --------------------------------------------------
#  MODE 1: R&D 研发中心
# --------------------------------------------------
if app_mode == "🔬 R&D 研发中心":
    st.title("🔬 智能研发与法规助手")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 大脑配置")
    model_choice = st.sidebar.radio("模型", ["🚀 V3 极速版", "🧠 R1 深度思考"], 0)
    current_model = "reasoner" if "R1" in model_choice else "chat"

    strict_prompt = """
    你是一名严谨的食品法规合规专家。核心原则：【依据事实，拒绝幻觉】。
    1. 引用标准：必须明确引用具体标准号。
    2. 保守回答：不确定请回答“需核实”，严禁编造。
    3. 数据敏感：限量必须精确。
    4. 思考过程：先逻辑分析，再给结论。
    """
    if "msg_law" not in st.session_state:
        st.session_state["msg_law"] = [{"role": "system", "content": strict_prompt}]

    if len(st.session_state["msg_law"]) > 1:
        st.sidebar.markdown("---")
        report = generate_eln(st.session_state["msg_law"])
        st.sidebar.download_button("📥 导出 MD", report, "ELN.md")
        if st.sidebar.button("💾 云端归档"):
            q = next((m['content'] for m in st.session_state["msg_law"] if m['role']=='user'), "记录")
            save_to_db("ELN", f"对话: {q[:10]}", report)

    tabs = st.tabs(["💬 法规对话", "🧪 智能配方", "📸 视觉分析", "📄 文档Chat", "📊 新品概念"])

    # Tab 1: 法规
    with tabs[0]:
        for m in st.session_state["msg_law"]:
            if m['role']!='system':
                with st.chat_message(m['role']):
                    if "reasoning" in m: st.expander("🧠 思维链").markdown(m["reasoning"])
                    st.markdown(m['content'])
                    if m['role'] == 'assistant':
                        st.caption("🛡️ 核实链接：")
                        c1, c2 = st.columns(2)
                        with c1: st.link_button("🔗 食品伙伴网", "http://www.foodmate.net/standards/")
                        with c2: st.link_button("🔗 卫健委", "https://ssp.nhc.gov.cn/database/standards/list.html")

        if p:=st.chat_input("输入合规问题"):
            st.session_state["msg_law"].append({"role":"user","content":p})
            with st.chat_message("user"): st.markdown(p)
            with st.chat_message("assistant"):
                with st.spinner("AI 正在云端思考..."):
                    r, a = call_deepseek_advanced(st.session_state["msg_law"], current_model)
                if r: st.expander("🧠 思维链").markdown(r)
                st.markdown(a)
                st.caption("🛡️ 核实链接：")
                c1, c2 = st.columns(2)
                with c1: st.link_button("🔗 食品伙伴网", f"http://www.foodmate.net/search.php?kw={p}")
                with c2: st.link_button("🔗 卫健委", "https://ssp.nhc.gov.cn/database/standards/list.html")
                st.session_state["msg_law"].append({"role":"assistant","content":a,"reasoning":r})

    # Tab 2: 配方
    with tabs[1]:
        st.subheader("🧪 智能配方计算器")
        txt = st.text_area("输入配方 (如: 生牛乳85%, 白砂糖10%, 浓缩乳清蛋白4%, 果胶0.8%, 山梨酸钾0.2%)", height=100)
        if st.button("🧮 计算"):
            with st.spinner("R1 拆解中..."):
                sys = "你是一名配方工程师。提取原料百分比，计算营养成分，进行GB2760预警。"
                r, a = call_deepseek_advanced([{"role":"system","content":sys},{"role":"user","content":txt}], "reasoner")
            c1, c2 = st.columns([3, 2])
            with c1:
                if r: st.expander("计算逻辑").markdown(r)
                st.markdown(a)
            with c2:
                st.plotly_chart(plot_nutrition_pie({"碳水":12,"蛋白":3.5,"脂肪":4,"水":80.5}))
            if st.button("💾 云端保存配方"): save_to_db("FORMULA", f"配方: {txt[:10]}", a)

    # Tab 3: OCR
    with tabs[2]:
        st.subheader("📸 配料表扫描")
        f = st.file_uploader("传图", ["jpg","png"])
        if f and st.button("识别"):
            txt = ocr_image(f)
            st.code(txt)
            with st.spinner("评估中..."):
                r, a = call_deepseek_advanced([{"role":"user","content":f"分析风险:{txt}"}], "reasoner")
            st.markdown(a)
            st.session_state["msg_law"].append({"role":"user","content":f"[OCR]{txt}"})
            st.session_state["msg_law"].append({"role":"assistant","content":a})

    # Tab 4: 文档
    with tabs[3]:
        st.subheader("📄 文档问答")
        fs = st.file_uploader("上传PDF", "pdf", True)
        if fs and st.button("读取"):
            st.session_state["doc_c"] = extract_pdf(fs)
            st.session_state["doc_m"] = [{"role":"system","content":f"基于:\n{st.session_state['doc_c'][:8000]}"}]
            st.success("OK")
        if "doc_m" in st.session_state:
            for m in st.session_state["doc_m"]:
                if m['role']!='system': st.chat_message(m['role']).markdown(m['content'])
            if p:=st.chat_input("问文档", key="doc"):
                st.session_state["doc_m"].append({"role":"user","content":p})
                st.chat_message("user").markdown(p)
                r, a = call_deepseek_advanced(st.session_state["doc_m"], current_model)
                st.chat_message("assistant").markdown(a)
                st.session_state["doc_m"].append({"role":"assistant","content":a})

    # Tab 5: 新品 (🔥 满血恢复)
    with tabs[4]:
        st.subheader("💡 概念生成")
        c1,c2 = st.columns(2)
        with c1: base_product = st.text_input("基底产品", "0糖酸奶")
        with c2: target_user = st.text_input("目标人群", "减脂打工人")
        
        # 选项完全恢复
        trend = st.selectbox("结合趋势", ["药食同源", "0糖0卡", "高蛋白", "助眠/解压", "清洁标签"])
        
        if st.button("生成概念"):
            # Prompt 完整恢复
            prompt = f"生成食品新品概念书，Markdown格式，包含卖点、配料、风味、包装建议。基底：{base_product}，人群：{target_user}，趋势：{trend}"
            res = call_deepseek_once(prompt, "")
            st.markdown(res)
            if st.button("💾 云端保存"): save_to_db("IDEA",f"概念:{base_product}",res)
            st.plotly_chart(plot_radar(base_product,trend))

# --------------------------------------------------
#  MODE 2: 自媒体工厂
# --------------------------------------------------
elif app_mode == "🎬 自媒体工厂":
    st.title("🎬 自动化内容工厂")
    t1, t2 = st.tabs(["📝 脚本", "🎙️ 配音"])
    with t1:
        c1,c2=st.columns([1,2])
        with c1:
            if st.button("刷新热搜"): st.cache_data.clear()
            try:
                hot = requests.get("https://top.baidu.com/board?tab=realtime", headers={"UA":"Mozilla/5.0"}).text
                ts = [t.strip() for t in re.findall(r'ellipsis">(.*?)</div>', hot) if len(t)>4][:10]
                sel = st.radio("热点", ts, index=None)
            except: sel=None
        with c2:
            top = st.text_input("选题", sel if sel else "")
            
            # 🔥 选项完全恢复
            c_type, c_style = st.columns(2)
            with c_type:
                script_type = st.selectbox("类型", ["辟谣粉碎机", "红黑榜测评", "行业内幕揭秘", "热点吃瓜解读"])
            with c_style:
                visual_style = st.selectbox("风格", ["实拍生活风", "宫崎骏动漫", "赛博朋克风", "微距美食"])
            
            if st.button("生成脚本"):
                # Prompt 完整恢复
                p = f"我是食品科普博主。选题：{top}。类型：{script_type}。风格：{visual_style}。请输出Markdown分镜表格。"
                s = call_deepseek_once(p, "")
                st.session_state["scr"] = s
                st.rerun()
            if "scr" in st.session_state:
                st.markdown(st.session_state["scr"])
                if st.button("💾 云端存脚本"): save_to_db("SCRIPT",top,st.session_state["scr"])

    with t2:
        txt=st.text_area("文案")
        v=st.selectbox("音色",["zh-CN-YunxiNeural (男声)","zh-CN-XiaoxiaoNeural (女声)","zh-CN-YunjianNeural (新闻)"])
        if st.button("生成语音"):
            try: st.audio(asyncio.run(generate_speech(txt,v.split(" ")[0])))
            except: st.error("Error")

# --------------------------------------------------
#  MODE 3: 云端档案库 (Supabase)
# --------------------------------------------------
elif app_mode == "🗄️ 云端档案库 (Supabase)":
    st.title("🗄️ 研发与创作档案 (Cloud)")
    st.caption("数据存储于 Supabase PostgreSQL 数据库，永不丢失。")
    
    filter_type = st.radio("筛选", ["全部","ELN","FORMULA","SCRIPT","IDEA"], horizontal=True)
    t = None if filter_type=="全部" else filter_type
    
    # 获取数据 (Supabase 返回的是字典列表)
    recs = get_history(t)
    
    if not recs:
        st.info("☁️ 云端数据库暂无数据，请去其他模块生成并保存。")
    else:
        for r in recs:
            # r 是字典: {'id': 1, 'type': 'ELN', 'timestamp': '...', ...}
            with st.expander(f"{r['timestamp']} | [{r['type']}] {r['title']}"):
                st.markdown(r['content'])
                st.download_button("导出MD", r['content'], f"{r['type']}_{r['id']}.md")

# --------------------------------------------------
#  MODE 4: 云端监控
# --------------------------------------------------
elif app_mode == "⚙️ 云端监控":
    st.title("⚙️ 监控")
    if st.button("测试推送") and "BARK_SERVER" in st.secrets:
        requests.get(f"{st.secrets['BARK_SERVER']}/{st.secrets['BARK_DEVICE_KEY']}/测试")
        st.success("Sent")