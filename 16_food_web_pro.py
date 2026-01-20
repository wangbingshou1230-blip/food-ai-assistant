import streamlit as st
import requests
import re
import pdfplumber # 保留作为备用
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

# --- RAG 2.0 核心组件 (v11.0 新增) ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

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
#  云端数据库 (Supabase)
# ==================================================
supabase = None
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    @st.cache_resource
    def init_supabase():
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase = init_supabase()
except Exception as e:
    st.sidebar.warning("⚠️ Supabase 配置未生效")

def save_to_db(record_type, title, content):
    if not supabase:
        st.error("数据库未连接")
        return
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        data = {
            "type": record_type,
            "title": title,
            "content": content,
            "timestamp": current_time
        }
        supabase.table("records").insert(data).execute()
        st.sidebar.success(f"☁️ 已云端归档: {title[:10]}...")
    except Exception as e:
        st.sidebar.error(f"保存失败: {e}")

def get_history(record_type=None):
    if not supabase: return []
    try:
        query = supabase.table("records").select("*").order("id", desc=True).limit(20)
        if record_type:
            query = query.eq("type", record_type)
        response = query.execute()
        return response.data
    except Exception as e:
        return []

# ==================================================
#  RAG 2.0 向量库连接 (Pinecone)
# ==================================================
@st.cache_resource
def get_vector_store():
    """初始化向量数据库连接"""
    if "PINECONE_API_KEY" not in st.secrets:
        return None
    try:
        # 使用轻量级模型 (与 ingest.py 保持一致)
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # 连接 Pinecone
        vectorstore = PineconeVectorStore(
            index_name="food-standards", # 确保和你建库的名字一样
            embedding=embeddings,
            pinecone_api_key=st.secrets["PINECONE_API_KEY"]
        )
        return vectorstore
    except Exception as e:
        print(f"Vector Store Error: {e}")
        return None

# ==================================================
#  DeepSeek API & Tools
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

def generate_eln(messages):
    t = datetime.now().strftime("%Y-%m-%d %H:%M")
    rpt = f"# ELN Report\nTime: {t}\n\n"
    for m in messages:
        if m['role']!='system': rpt += f"## {m['role']}\n{m['content']}\n\n"
    return rpt

def plot_nutrition_pie(data_dict):
    if not data_dict: data_dict = {"碳水": 0, "蛋白": 0, "脂肪": 0}
    fig = go.Figure(data=[go.Pie(labels=list(data_dict.keys()), values=list(data_dict.values()), hole=.3)])
    fig.update_layout(margin=dict(t=20,b=20,l=20,r=20), showlegend=True)
    return fig

def plot_radar(name, trend):
    vals = [3, 2, 1, 1, 2]
    if "酸奶" in name: vals = [3, 4, 1, 0, 2]
    elif "咖啡" in name: vals = [2, 3, 5, 0, 1]
    
    if "0糖" in trend: vals[0] = max(0, vals[0]-2)
    if "高蛋白" in trend: vals[4] = min(5, vals[4]+1)
    
    fig = go.Figure(go.Scatterpolar(r=vals, theta=['甜度', '酸度', '苦度', '咸度', '鲜度'], fill='toself', name=name))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, margin=dict(t=20,b=20,l=40,r=40))
    return fig

# ==================================================
#  主界面逻辑
# ==================================================
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("v11.1 | RAG 2.0 终极融合版") # 版本号更新
app_mode = st.sidebar.selectbox("工作模式", ["🔬 R&D 研发中心", "🎬 自媒体工厂", "🗄️ 云端档案库", "⚙️ 云端监控"])

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
    1. 引用标准：必须明确引用具体标准号（如 GB 2760-2024）。
    2. 保守回答：不确定请回答“需核实”，严禁编造。
    3. 数据敏感：限量必须精确。
    4. 思考过程：先逻辑分析，再给结论。
    """
    if "msg_law" not in st.session_state:
        st.session_state["msg_law"] = [{"role": "system", "content": strict_prompt}]

    # 侧边栏保存
    if len(st.session_state["msg_law"]) > 1:
        st.sidebar.markdown("---")
        report = generate_eln(st.session_state["msg_law"])
        st.sidebar.download_button("📥 导出 MD", report, "ELN.md")
        if st.sidebar.button("💾 归档对话"):
            q = next((m['content'] for m in st.session_state["msg_law"] if m['role']=='user'), "记录")
            save_to_db("ELN", f"对话: {q[:10]}", report)

    # 5大功能区 (Tab 4 名字改为 行业大脑)
    tabs = st.tabs(["💬 法规对话", "🧪 智能配方", "📸 视觉分析", "🧠 行业大脑(RAG)", "📊 新品概念"])

    # --- Tab 1: 法规对话 ---
    with tabs[0]:
        for m in st.session_state["msg_law"]:
            if m['role']!='system':
                with st.chat_message(m['role']):
                    if "reasoning" in m: st.expander("🧠 思维链 (CoT)").markdown(m["reasoning"])
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
                with st.spinner("AI 正在检索法规库与逻辑推理中..."):
                    r, a = call_deepseek_advanced(st.session_state["msg_law"], current_model)
                if r: st.expander("🧠 思维链 (CoT)").markdown(r)
                st.markdown(a)
                st.session_state["msg_law"].append({"role":"assistant","content":a,"reasoning":r})

    # --- Tab 2: 智能配方 (保留了你的修复) ---
    with tabs[1]:
        st.subheader("🧪 智能配方计算器")
        txt = st.text_area("输入配方 (如: 生牛乳85%, 白砂糖10%, 浓缩乳清蛋白4%, 果胶0.8%, 山梨酸钾0.2%)", height=100)
        
        if st.button("🧮 启动配方引擎"):
            with st.spinner("R1 正在逆向拆解配方结构..."):
                sys = "你是一名配方工程师。请提取原料百分比，计算营养成分(蛋/脂/碳)，并进行GB2760合规预警。请以JSON格式输出预估营养占比(key为成分,value为数值)，然后在JSON后输出详细分析报告。"
                r, a = call_deepseek_advanced([{"role":"system","content":sys},{"role":"user","content":txt}], "reasoner")
                st.session_state["formula_res_a"] = a
                st.session_state["formula_res_r"] = r
                st.session_state["formula_txt"] = txt
        
        if "formula_res_a" in st.session_state:
            c1, c2 = st.columns([3, 2])
            with c1:
                if st.session_state.get("formula_res_r"): 
                    st.expander("🧠 计算逻辑 (CoT)").markdown(st.session_state["formula_res_r"])
                st.markdown(st.session_state["formula_res_a"])
            with c2:
                st.markdown("### 📊 预估营养分布")
                plot_data = {"碳水化合物": 12, "蛋白质": 3.5, "脂肪": 4.0, "水/其他": 80.5}
                st.plotly_chart(plot_nutrition_pie(plot_data))
            
            st.markdown("---")
            if st.button("💾 云端保存配方"): 
                save_to_db("FORMULA", f"配方: {st.session_state['formula_txt'][:10]}", st.session_state["formula_res_a"])

    # --- Tab 3: OCR ---
    with tabs[2]:
        st.subheader("📸 配料表扫描")
        f = st.file_uploader("传图", ["jpg","png"])
        if f:
            st.image(f, width=300, caption="原图预览")
            if st.button("👁️ 开始识别"):
                with st.spinner("正在进行 OCR 像素级提取..."):
                    txt = ocr_image(f)
                st.success("OCR 提取完成")
                with st.expander("查看提取到的原始内容"):
                    st.code(txt)
                
                with st.spinner("R1 正在进行风险成分筛查..."):
                    r, a = call_deepseek_advanced([{"role":"user","content":f"分析配料表风险:{txt}"}], "reasoner")
                
                st.markdown("### 🛡️ 风险评估报告")
                if r: st.expander("🧠 评估逻辑").markdown(r)
                st.markdown(a)
                st.session_state["msg_law"].append({"role":"user","content":f"[OCR]{txt}"})
                st.session_state["msg_law"].append({"role":"assistant","content":a})

    # --- Tab 4: 行业大脑 (RAG 2.0 核心) ---
    with tabs[3]:
        st.subheader("🧠 行业大脑：全量法规检索 (Pinecone)")
        st.info("💡 已连接 Pinecone 向量知识库。无需上传 PDF，直接提问即可检索已入库的数百份国标。")
        
        vector_store = get_vector_store()
        
        if not vector_store:
            st.warning("⚠️ 未检测到 PINECONE_API_KEY，请先在 Secrets 中配置。目前仅支持基础对话。")
        else:
            query = st.text_input("输入你要查询的法规问题 (例如: GB2760中关于山梨酸钾的规定)")
            
            if st.button("🔍 深度检索"):
                if not query:
                    st.warning("请输入问题")
                else:
                    # 1. 检索
                    with st.spinner("正在 Pinecone 向量海中搜寻相关片段..."):
                        docs = vector_store.similarity_search(query, k=3)
                        context_str = "\n\n".join([f"【来源：{d.metadata.get('source', '未知文档')}】\n{d.page_content}" for d in docs])
                    
                    # 2. 展示检索到的证据
                    with st.expander("查看检索到的法规原文片段 (Evidence)"):
                        st.markdown(context_str)
                    
                    # 3. AI 回答
                    with st.spinner("DeepSeek R1 正在基于证据进行推理..."):
                        prompt = f"你是一名食品法规专家。请严格基于以下【参考文档】回答用户问题。\n如果文档中没有答案，请直接说“知识库中未找到相关条款”。\n\n【参考文档】：\n{context_str}\n\n用户问题：{query}"
                        r, a = call_deepseek_advanced([{"role":"user","content":prompt}], current_model)
                    
                    if r: st.expander("🧠 法律推理过程").markdown(r)
                    st.markdown("### ⚖️ 法律意见")
                    st.markdown(a)
                    
                    # 4. 保存
                    if st.button("💾 归档检索记录"):
                        save_to_db("RAG", f"检索: {query}", f"Q:{query}\n\nEvidence:\n{context_str}\n\nA:{a}")

    # --- Tab 5: 新品 (保留了你的修复) ---
    with tabs[4]:
        st.subheader("💡 概念生成")
        col1, col2 = st.columns(2)
        with col1: base_product = st.text_input("基底产品", "0糖酸奶")
        with col2: target_user = st.text_input("目标人群", "减脂打工人")
        trend = st.selectbox("结合趋势", ["药食同源", "0糖0卡", "高蛋白", "助眠/解压", "清洁标签"])
        
        if st.button("🧪 生成概念书"):
            with st.spinner("🧠 AI 正在疯狂头脑风暴中..."):
                prompt = f"生成食品新品概念书，Markdown格式，包含卖点、配料、风味、包装建议。基底：{base_product}，人群：{target_user}，趋势：{trend}"
                res = call_deepseek_once(prompt, "")
                
            st.session_state["idea_res"] = res
            st.session_state["idea_base"] = base_product
        
        if "idea_res" in st.session_state:
            st.markdown(st.session_state["idea_res"])
            st.markdown("#### 🧬 动态风味轮廓")
            st.plotly_chart(plot_radar(base_product, trend))
            st.markdown("---")
            if st.button("💾 云端保存概念"): 
                save_to_db("IDEA",f"概念:{st.session_state['idea_base']}", st.session_state["idea_res"])

# --------------------------------------------------
#  MODE 2: 自媒体工厂
# --------------------------------------------------
elif app_mode == "🎬 自媒体工厂":
    st.title("🎬 自动化内容工厂")
    t1, t2 = st.tabs(["📝 脚本", "🎙️ 配音"])
    with t1:
        c1,c2=st.columns([1,2])
        with c1:
            if st.button("🔄 刷新热搜"): st.cache_data.clear()
            try:
                hot = requests.get("https://top.baidu.com/board?tab=realtime", headers={"UA":"Mozilla/5.0"}).text
                ts = [t.strip() for t in re.findall(r'ellipsis">(.*?)</div>', hot) if len(t)>4][:10]
                sel = st.radio("选取热点", ts, index=None)
            except: sel=None
        with c2:
            top = st.text_input("选题", sel if sel else "")
            c_type, c_style = st.columns(2)
            with c_type: script_type = st.selectbox("类型", ["辟谣粉碎机", "红黑榜测评", "行业内幕揭秘", "热点吃瓜解读"])
            with c_style: visual_style = st.selectbox("风格", ["实拍生活风", "宫崎骏动漫", "赛博朋克风", "微距美食"])
            
            if st.button("🚀 生成脚本"):
                with st.spinner("正在构建分镜表..."):
                    p = f"我是食品科普博主。选题：{top}。类型：{script_type}。风格：{visual_style}。请输出Markdown分镜表格。"
                    s = call_deepseek_once(p, "")
                st.session_state["scr"] = s
                st.rerun()
                
            if "scr" in st.session_state:
                st.markdown(st.session_state["scr"])
                if st.button("💾 云端存脚本"): save_to_db("SCRIPT",top,st.session_state["scr"])

    with t2:
        st.subheader("🎙️ TTS 配音室")
        txt = st.text_area("粘贴文案")
        v = st.selectbox("音色", ["zh-CN-YunxiNeural (男声-稳重)", "zh-CN-XiaoxiaoNeural (女声-亲切)", "zh-CN-YunjianNeural (男声-新闻)"])
        if st.button("🎧 生成语音"):
            with st.spinner("AI 正在合成音频流..."):
                try: 
                    st.audio(asyncio.run(generate_speech(txt,v.split(" ")[0])))
                    st.success("合成完毕")
                except: st.error("Error")

# --------------------------------------------------
#  MODE 3: 云端档案库
# --------------------------------------------------
elif app_mode == "🗄️ 云端档案库":
    st.title("🗄️ 研发与创作档案 (Cloud)")
    filter_type = st.radio("筛选", ["全部","ELN","FORMULA","SCRIPT","IDEA"], horizontal=True)
    t = None if filter_type=="全部" else filter_type
    with st.spinner("正在从 Supabase 同步数据..."):
        recs = get_history(t)
    if not recs:
        st.info("☁️ 云端数据库暂无数据，请去其他模块生成并保存。")
    else:
        for r in recs:
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