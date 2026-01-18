import streamlit as st
import requests
import re
import pdfplumber
import pandas as pd
import plotly.graph_objects as go # 新增：用于画帅气的雷达图
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

def call_deepseek(system_prompt, user_input):
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    try:
        with st.spinner("AI 正在深度思考..."):
            response = requests.post(url, headers=headers, json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                "stream": False
            })
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"请求异常: {e}"

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

# --- 新增：画雷达图的函数 ---
def plot_sensory_radar(product_name, trend):
    """
    根据产品名称生成一个模拟的感官雷达图。
    (在真实项目中，这里的数据应该由 AI 生成或实验室测得，这里为了演示做模拟)
    """
    categories = ['甜度', '酸度', '苦度', '咸度', '鲜度']
    
    # 简单的预设逻辑，让图表看起来有点逻辑
    if "酸奶" in product_name:
        values = [3, 4, 1, 0, 2]
    elif "咖啡" in product_name:
        values = [2, 3, 5, 0, 1]
    elif "茶" in product_name:
        values = [1, 2, 4, 0, 3]
    elif "麻辣" in product_name or "肉" in product_name:
        values = [1, 1, 1, 4, 5]
    else:
        values = [3, 2, 1, 1, 2] # 默认均衡
        
    # 根据趋势微调
    if "0糖" in trend:
        values[0] = 1 # 甜度降低
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name=product_name,
        line_color='#FF4B4B'
    ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        showlegend=False,
        margin=dict(t=20, b=20, l=40, r=40) # 调整边距
    )
    return fig

# --- 侧边栏 ---
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")

app_mode = st.sidebar.selectbox(
    "选择工作模式",
    ["🔬 R&D 研发与合规 (求职作品)", "🎬 自媒体内容矩阵 (副业工具)", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: R&D 研发 (可视化升级版)
# ==================================================
if app_mode == "🔬 R&D 研发与合规 (求职作品)":
    st.title("🔬 智能研发与法规助手")
    st.markdown("集成 **RAG 文档分析** 与 **数据可视化** 引擎。")
    
    tab1, tab2, tab3 = st.tabs(["⚖️ GB法规咨询", "📄 智能文档分析", "📊 新品概念研发"])

    with tab1:
        st.info("场景：快速合规查询")
        query = st.text_area("输入问题", "果冻中能否添加山梨酸钾？")
        if st.button("开始审查"):
            st.markdown(call_deepseek("你是一名食品法规专员。", query))

    with tab2:
        st.subheader("📄 智能文档分析 (Multi-Docs)")
        uploaded_files = st.file_uploader("上传 PDF 文件", type="pdf", accept_multiple_files=True)
        
        if uploaded_files:
            st.success(f"已上传 {len(uploaded_files)} 个文件")
            if st.button("📥 读取并分析"):
                all_files_content = ""
                progress_bar = st.progress(0)
                for i, file in enumerate(uploaded_files):
                    text = extract_text_from_pdf(file)
                    all_files_content += f"\n--- 文档：{file.name} ---\n{text}\n"
                    progress_bar.progress((i + 1) / len(uploaded_files))
                st.session_state['pdf_context'] = all_files_content
                st.success("✅ 读取完毕！")

            if 'pdf_context' in st.session_state:
                doc_query = st.text_input("你想问什么？", placeholder="例如：对比防腐剂使用规定")
                if st.button("🤖 综合回答"):
                    sys = f"基于以下文档回答：\n{st.session_state['pdf_context'][:6000]}"
                    st.markdown(call_deepseek(sys, doc_query))

    # --- 🔥 核心可视化升级区 ---
    with tab3:
        st.subheader("💡 新品概念生成 & 风味模拟")
        
        c1, c2 = st.columns(2)
        with c1: base_product = st.text_input("基底产品", "0糖酸奶")
        with c2: target_user = st.text_input("目标人群", "减脂党")
        trend = st.selectbox("结合趋势", ["药食同源", "0糖0卡", "高蛋白", "助眠/解压", "清洁标签"])
        
        if st.button("🧪 生成概念书 & 风味雷达"):
            # 1. 生成文字
            sys_prompt = "你是一名食品研发工程师。请生成《新产品开发概念书》（Markdown格式），包含卖点、配料、风味、包装建议。"
            req = f"基底：{base_product}，人群：{target_user}，趋势：{trend}"
            
            # 使用两列布局：左边文字，右边图表
            col_text, col_chart = st.columns([3, 2])
            
            with col_text:
                res = call_deepseek(sys_prompt, req)
                st.markdown(res)
                
            with col_chart:
                st.markdown("### 🧬 预估风味轮廓")
                st.caption("基于基底产品与目标人群的 AI 模拟数据")
                # 调用画图函数
                fig = plot_sensory_radar(base_product, trend)
                st.plotly_chart(fig, use_container_width=True)

# ==================================================
# 模块 2: 自媒体内容矩阵
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵 (副业工具)":
    st.title("🎬 自动化内容生产工厂")
    col_hot, col_gen = st.columns([1, 2])
    with col_hot:
        if st.button("🔄 刷新"): st.cache_data.clear()
        hot_list = get_realtime_news()
        selected_hot = st.radio("选择热点：", hot_list, index=None)
        if selected_hot: st.session_state['selected_topic'] = selected_hot

    with col_gen:
        topic = st.text_input("选题", value=st.session_state.get('selected_topic', ''))
        c1, c2 = st.columns(2)
        with c1: type_ = st.selectbox("类型", ["辟谣", "测评", "揭秘"])
        with c2: style = st.selectbox("风格", ["实拍", "动漫", "赛博"])
        if st.button("🚀 生成脚本"):
            if topic:
                prompt = f"我是科普博主。选题：{topic}。类型：{type_}。风格：{style}。输出Markdown分镜表。"
                st.markdown(call_deepseek(prompt, topic))

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