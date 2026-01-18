import streamlit as st
import requests
import re
import pdfplumber
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

# --- 工具 3: PDF 提取 (保持不变) ---
def extract_text_from_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = ""
            for page in pdf.pages[:5]: # 为了速度，只读前5页
                text += page.extract_text() + "\n"
            return text
    except:
        return ""

# --- 侧边栏 ---
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")

app_mode = st.sidebar.selectbox(
    "选择工作模式",
    ["🔬 R&D 研发与合规 (求职作品)", "🎬 自媒体内容矩阵 (副业工具)", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: R&D 研发 (多文档升级版!)
# ==================================================
if app_mode == "🔬 R&D 研发与合规 (求职作品)":
    st.title("🔬 智能研发与法规助手")
    st.markdown("集成 **RAG (检索增强生成)** 技术，支持**多文档对比分析**。")
    
    tab1, tab2, tab3 = st.tabs(["⚖️ GB法规咨询", "📄 智能文档分析 (RAG)", "📊 新品概念研发"])

    with tab1:
        st.info("场景：快速合规查询")
        query = st.text_area("输入问题", "果冻中能否添加山梨酸钾？")
        if st.button("开始审查"):
            st.markdown(call_deepseek("你是一名食品法规专员。", query))

    with tab3:
        st.subheader("💡 新品概念生成")
        c1, c2 = st.columns(2)
        with c1: base_product = st.text_input("基底产品", "酸奶")
        with c2: target_user = st.text_input("目标人群", "减脂党")
        if st.button("生成概念书"):
            st.markdown(call_deepseek("我是研发工程师，请生成产品概念书。", f"{base_product} for {target_user}"))

    # --- 🔥 核心升级区：多文档分析 ---
    with tab2:
        st.subheader("📄 智能文档分析 (Multi-Docs)")
        st.markdown("**核心价值**：支持上传多个 PDF (如：对比新旧国标、综述多篇文献)。")
        
        # 1. 开启 accept_multiple_files=True
        uploaded_files = st.file_uploader(
            "上传 PDF 文件 (支持多选)", 
            type="pdf", 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.success(f"已上传 {len(uploaded_files)} 个文件")
            
            # 2. 循环读取所有文件内容
            all_files_content = ""
            if st.button("📥 开始读取并分析"):
                progress_bar = st.progress(0)
                
                for i, file in enumerate(uploaded_files):
                    with st.spinner(f"正在读取 {file.name}..."):
                        text = extract_text_from_pdf(file)
                        # 给每个文件的内容打上标签，方便 AI 区分
                        all_files_content += f"\n--- 文档名称：{file.name} ---\n{text}\n"
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                # 将读取到的内容暂存，避免刷新丢失
                st.session_state['pdf_context'] = all_files_content
                st.success("✅ 所有文档读取完毕！请在下方提问。")

            # 3. 针对多文档提问
            if 'pdf_context' in st.session_state:
                doc_query = st.text_input("针对这些文档，你想问什么？", placeholder="例如：对比这几份文档中关于‘防腐剂’规定的异同点")
                
                if st.button("🤖 综合回答"):
                    if doc_query:
                        # RAG Prompt 升级：强调“综合分析”
                        sys_prompt = f"""
                        你是一个专业的文档分析助手。用户上传了多个文档。
                        请基于以下【文档内容集】，回答用户的问题。
                        
                        【文档内容集】：
                        {st.session_state['pdf_context'][:6000]} ... (内容已截断)
                        
                        要求：
                        1. 如果问题涉及对比，请明确指出不同文档的区别。
                        2. 引用时请说明出自哪个文档（如：根据文档A...）。
                        """
                        res = call_deepseek(sys_prompt, doc_query)
                        st.markdown("### 📝 分析结果")
                        st.markdown(res)

# ==================================================
# 模块 2: 自媒体内容矩阵 (保持不变)
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