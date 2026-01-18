import streamlit as st
import requests
import re
import pandas as pd

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

# 检查 Key
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
    """抓取百度热搜"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=headers)
        titles = re.findall(r'class="c-single-text-ellipsis">(.*?)</div>', resp.text)
        clean_titles = [t.strip() for t in titles if len(t) > 4][:10]
        return clean_titles
    except Exception as e:
        return [f"抓取异常: {e}"]

# --- 侧边栏 ---
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")

app_mode = st.sidebar.selectbox(
    "选择工作模式",
    ["🔬 R&D 研发与合规 (求职作品)", "🎬 自媒体内容矩阵 (副业工具)", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: R&D 研发 (已恢复完整功能！)
# ==================================================
if app_mode == "🔬 R&D 研发与合规 (求职作品)":
    st.title("🔬 智能研发与法规助手")
    st.markdown("设计理念：针对食品研发中法规检索繁琐痛点，利用 LLM 构建的垂直领域辅助系统。")
    
    tab1, tab2 = st.tabs(["⚖️ GB法规智能咨询", "📊 新品概念研发"])

    with tab1:
        st.subheader("GB/合规性智能审查")
        st.info("场景：输入配料或添加剂，AI 基于 GB2760/GB7718 进行初步合规预警。")
        query = st.text_area("输入问题 (例如：果冻中能否添加山梨酸钾？限量是多少？)", height=100)
        
        if st.button("🔍 开始合规审查"):
            sys_prompt = (
                "你是一名资深的食品法规专员（Regulatory Affairs Specialist）。"
                "请基于中国食品安全国家标准（GB系列），严谨地回答用户问题。"
                "涉及添加剂时，必须引用 GB 2760；涉及标签时，引用 GB 7718。"
                "如果不能确定，请提示用户查询具体标准原文，不要编造数据。"
            )
            res = call_deepseek(sys_prompt, query)
            st.markdown(res)

    with tab2:
        st.subheader("💡 新品概念生成")
        # --- 这里恢复了完整的输入项 ---
        col1, col2 = st.columns(2)
        with col1:
            base_product = st.text_input("基底产品", "酸奶")
        with col2:
            target_user = st.text_input("目标人群", "熬夜打工人")
            
        trend = st.selectbox("结合趋势", ["药食同源", "0糖0卡", "高蛋白", "助眠/解压", "清洁标签"])
        
        if st.button("🧪 生成产品概念书"):
            sys_prompt = (
                "你是一名食品研发工程师（R&D Engineer）。"
                "请根据用户输入，生成一份简要的《新产品开发概念书》。"
                "输出格式要求：Markdown。"
                "包含：\n1. 产品名称\n2. 核心卖点 (USP)\n3. 建议添加的功能性成分\n4. 风味描述\n5. 包装设计建议"
            )
            req = f"基底：{base_product}，人群：{target_user}，趋势：{trend}"
            res = call_deepseek(sys_prompt, req)
            st.markdown(res)

# ==================================================
# 模块 2: 自媒体内容矩阵 (热点联动版)
# ==================================================
elif app_mode == "🎬 自媒体内容矩阵 (副业工具)":
    st.title("🎬 自动化内容生产工厂")
    st.markdown("打通 **全网热点** -> **AI 选题** -> **分镜脚本** 的全链路。")
    
    col_hot, col_gen = st.columns([1, 2])
    
    with col_hot:
        st.subheader("🔥 实时热搜榜")
        if st.button("🔄 刷新榜单"):
            st.cache_data.clear()
        
        hot_list = get_realtime_news()
        selected_hot = st.radio("点击选择热点：", hot_list, index=None)
        if selected_hot:
            st.session_state['selected_topic'] = selected_hot

    with col_gen:
        st.subheader("📝 智能创作区")
        default_topic = st.session_state.get('selected_topic', '')
        topic = st.text_input("输入选题 (自动回填)", value=default_topic)

        c1, c2 = st.columns(2)
        with c1:
            script_type = st.selectbox("脚本类型", ["辟谣粉碎机", "红黑榜测评", "行业内幕揭秘", "热点吃瓜解读"])
        with c2:
            visual_style = st.selectbox("画面风格", ["🎥 实拍生活风", "✨ 动漫插画风", "🔮 赛博朋克风"])

        if st.button("🚀 生成分镜脚本"):
            if not topic:
                st.warning("请先输入或选择一个选题！")
            else:
                sys_prompt = f"""
                你是一名食品硕士背景的科普博主。请根据选题【{topic}】创作视频脚本。
                要求：类型{script_type}，风格{visual_style}。
                输出格式：Markdown表格，包含三列：| 时间 | 口播文案 | 画面/Prompt |
                """
                res = call_deepseek(sys_prompt, topic)
                st.markdown(res)

# ==================================================
# 模块 3: 云端数据看板
# ==================================================
elif app_mode == "⚙️ 云端数据看板":
    st.title("⚙️ 自动化系统监控")
    st.info("云端任务：daily_task.py 正在 GitHub 服务器上每日 08:00 运行")
    
    if st.button("📲 发送测试推送"):
        if "BARK_SERVER" in st.secrets:
            try:
                url = f"{st.secrets['BARK_SERVER'].rstrip('/')}/{st.secrets['BARK_DEVICE_KEY']}/测试推送/网页端触发成功"
                requests.get(url)
                st.success("✅ 推送成功！")
            except:
                st.error("发送失败")
        else:
            st.error("Secrets配置缺失")