import streamlit as st
import requests
import re
from datetime import datetime

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
#  系统配置与工具函数
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

# --- 工具 2: 实时热点抓取 (新功能!) ---
@st.cache_data(ttl=3600) # 缓存1小时，避免频繁请求
def get_realtime_news():
    """简单的百度热搜抓取"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        # 这里用百度即时热点接口
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, headers=headers)
        # 正则提取热搜标题
        titles = re.findall(r'class="c-single-text-ellipsis">(.*?)</div>', resp.text)
        # 只要前 10 条，且过滤掉太短的
        clean_titles = [t.strip() for t in titles if len(t) > 4][:10]
        return clean_titles
    except Exception as e:
        return [f"抓取失败: {e}", "手动输入试试"]

# --- 侧边栏 ---
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")

app_mode = st.sidebar.selectbox(
    "选择工作模式",
    ["🎬 自媒体内容矩阵 (副业工具)", "🔬 R&D 研发与合规 (求职作品)", "⚙️ 云端数据看板"]
)

# ==================================================
# 模块 1: 自媒体内容矩阵 (热点联动版)
# ==================================================
if app_mode == "🎬 自媒体内容矩阵 (副业工具)":
    st.title("🎬 自动化内容生产工厂")
    st.markdown("打通 **全网热点** -> **AI 选题** -> **分镜脚本** 的全链路。")
    
    # --- 布局：左边看热点，右边生成 ---
    col_hot, col_gen = st.columns([1, 2])
    
    with col_hot:
        st.subheader("🔥 实时热搜榜")
        if st.button("🔄 刷新全网热点"):
            st.cache_data.clear() # 清除缓存强制刷新
            
        hot_list = get_realtime_news()
        
        # 使用 Radio 单选框让用户选择热点
        selected_hot = st.radio("点击选择一个热点：", hot_list, index=None)
        
        if selected_hot:
            st.success(f"已选：{selected_hot}")
            # 将选择的热点存入 session供右侧使用
            st.session_state['selected_topic'] = selected_hot

    with col_gen:
        st.subheader("📝 智能创作区")
        
        # 自动填充：如果左边选了，这里自动填入
        default_topic = st.session_state.get('selected_topic', '')
        topic = st.text_input("输入选题 (或从左侧选择)", value=default_topic)

        # 选项配置
        c1, c2 = st.columns(2)
        with c1:
            script_type = st.selectbox("脚本类型", ["辟谣粉碎机", "红黑榜测评", "行业内幕揭秘", "热点吃瓜解读"])
        with c2:
            visual_style = st.selectbox("画面风格", ["🎥 实拍生活风", "✨ 动漫插画风", "🔮 赛博朋克风"])

        if st.button("🚀 立即生成分镜脚本"):
            if not topic:
                st.warning("请先输入或选择一个选题！")
            else:
                # 融合 Prompt
                sys_prompt = f"""
                你是一名食品硕士背景的科普博主。请根据选题【{topic}】创作视频脚本。
                
                【要求】：
                1. 类型：{script_type} (利用专业知识深度分析)
                2. 风格：{visual_style}
                3. **输出格式**：Markdown表格，包含三列：
                   | 时间 | 口播文案 (逐字稿) | 画面/AI绘画指令 (Prompt) |
                """
                res = call_deepseek(sys_prompt, topic)
                st.markdown(res)

# ==================================================
# 模块 2: R&D 研发 (求职专用 - 保持稳定)
# ==================================================
elif app_mode == "🔬 R&D 研发与合规 (求职作品)":
    st.title("🔬 智能研发与法规助手")
    st.info("💡 提示：面试演示时，重点展示这里的'合规审查'功能。")
    
    tab1, tab2 = st.tabs(["⚖️ GB法规智能咨询", "📊 新品概念研发"])
    
    with tab1:
        query = st.text_area("输入合规问题 (例如：山梨酸钾在果冻中的限量)", height=100)
        if st.button("开始审查"):
            sys = "你是一名食品法规专员，请依据GB2760/GB7718回答，引用标准原文。"
            st.markdown(call_deepseek(sys, query))
            
    with tab2:
        base = st.text_input("产品基底", "酸奶")
        if st.button("生成概念书"):
            st.markdown(call_deepseek("我是研发工程师，请生成产品概念书。", base))

# ==================================================
# 模块 3: 云端数据看板
# ==================================================
elif app_mode == "⚙️ 云端数据看板":
    st.title("⚙️ 自动化系统监控")
    st.info("云端爬虫任务状态监控")
    
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