import streamlit as st
import requests
import re
import pdfplumber  # 新增：用于读取 PDF
from io import BytesIO

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="FoodMaster 智能工作台",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 🔐 登录验证系统 ---
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

# --- 工具 1: DeepSeek 调用 ---
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

# --- 工具 2: 实时热点抓取 ---
@st.cache_data(ttl=3600)
def get_realtime_news():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=headers)
        titles = re.findall(r'class="c-single-text-ellipsis">(.*?)</div>', resp.text)
        clean_titles = [t.strip() for t in titles if len(t) > 4][:10]
        return clean_titles
    except Exception as e:
        return [f"抓取异常: {e}"]

# --- 工具 3: PDF 文本提取 (新功能!) ---
def extract_text_from_pdf(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            # 为了节省 Token，只取前 5 页 (面试演示足够了)
            for page in pdf.pages[:5]:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        return None

# --- 侧边栏 ---
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")

app_mode = st.sidebar.selectbox(
    "选择工作模式",
    ["🔬 R&D 研发与合规 (求职作品)", "🎬 自媒体内容矩阵 (副业工具)", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: R&D 研发 (新增文档分析功能)
# ==================================================
if app_mode == "🔬 R&D 研发与合规 (求职作品)":
    st.title("🔬 智能研发与法规助手")
    st.markdown("集成 **RAG (检索增强生成)** 技术，实现基于真实文档的精准问答。")
    
    # 增加了一个新 Tab：📄 智能文档分析
    tab1, tab2, tab3 = st.tabs(["⚖️ GB法规咨询", "📄 智能文档分析 (RAG)", "📊 新品概念研发"])

    with tab1:
        st.subheader("通用法规咨询")
        st.info("场景：基于 AI 知识库的快速问答 (注意：AI 可能存在幻觉，精准查询请用右侧文档分析)。")
        query = st.text_area("输入问题", "果冻中能否添加山梨酸钾？")
        if st.button("开始审查"):
            st.markdown(call_deepseek("你是一名食品法规专员。", query))

    # --- 🔥 新增的核心功能区 ---
    with tab3: # 原来的新品研发放到最后
        st.subheader("💡 新品概念生成")
        c1, c2 = st.columns(2)
        with c1: base_product = st.text_input("基底产品", "酸奶")
        with c2: target_user = st.text_input("目标人群", "减脂党")
        if st.button("生成概念书"):
            st.markdown(call_deepseek("我是研发工程师，请生成产品概念书。", f"{base_product} for {target_user}"))

    with tab2:
        st.subheader("📄 智能文档分析 (AI Reading)")
        st.markdown("**核心价值**：上传 GB 标准或英文文献，AI 基于**文件内容**回答，拒绝瞎编。")
        
        uploaded_file = st.file_uploader("上传 PDF 文件 (如 GB2760.pdf 或 英文Paper)", type="pdf")
        
        if uploaded_file is not None:
            # 1. 提取文字
            with st.spinner("正在读取 PDF 内容..."):
                pdf_text = extract_text_from_pdf(uploaded_file)
            
            if pdf_text:
                st.success(f"✅ 文件读取成功！提取到 {len(pdf_text)} 字符")
                
                # 2. 针对文档提问
                doc_query = st.text_input("关于这份文档，你想问什么？", placeholder="例如：这篇文献的核心结论是什么？ / 文档中关于苯甲酸钠的限量是多少？")
                
                if st.button("🤖 基于文档回答"):
                    if doc_query:
                        # RAG 的核心 Prompt：把文档内容喂给 AI
                        sys_prompt = f"""
                        你是一个专业的文档分析助手。
                        请**完全基于**以下【文档内容】来回答用户的问题。
                        如果文档里没有提到，请直接说“文档中未提及”，不要编造。
                        
                        【文档内容摘要】：
                        {pdf_text[:3000]} ... (内容过长已截断)
                        """
                        res = call_deepseek(sys_prompt, doc_query)
                        st.markdown("### 📝 分析结果")
                        st.markdown(res)
            else:
                st.error("无法提取文本，可能是图片扫描版 PDF。")

# ==================================================
# 模块 2: 自媒体内容矩阵 (保持不变)
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵 (副业工具)":
    st.title("🎬 自动化内容生产工厂")
    
    col_hot, col_gen = st.columns([1, 2])
    with col_hot:
        st.subheader("🔥 实时热搜")
        if st.button("🔄 刷新"): st.cache_data.clear()
        hot_list = get_realtime_news()
        selected_hot = st.radio("选择热点：", hot_list, index=None)
        if selected_hot: st.session_state['selected_topic'] = selected_hot

    with col_gen:
        st.subheader("📝 创作区")
        topic = st.text_input("选题", value=st.session_state.get('selected_topic', ''))
        c1, c2 = st.columns(2)
        with c1: type_ = st.selectbox("类型", ["辟谣", "测评", "揭秘"])
        with c2: style = st.selectbox("风格", ["实拍", "动漫", "赛博"])
        
        if st.button("🚀 生成脚本"):
            if topic:
                prompt = f"我是食品科普博主。选题：{topic}。类型：{type_}。风格：{style}。输出Markdown分镜表。"
                st.markdown(call_deepseek(prompt, topic))

# ==================================================
# 模块 3: 云端看板 (保持不变)
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