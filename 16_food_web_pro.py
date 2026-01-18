import streamlit as st
import requests
import os
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(
    page_title="FoodMaster 智能工作台",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 侧边栏：双重身份切换 ---
st.sidebar.title("🧬 FoodMaster Pro")
st.sidebar.caption("食品硕士的数字化解决方案")

# 你的简历核心卖点：既懂研发，又懂内容
app_mode = st.sidebar.selectbox(
    "选择工作模式",
    ["🔬 R&D 研发与合规 (求职作品)", "🎬 自媒体内容矩阵 (副业工具)", "⚙️ 云端数据看板"]
)

# --- 核心函数：DeepSeek ---
def call_deepseek(api_key, system_prompt, user_input):
    if not api_key:
        return "❌ 请先配置 DeepSeek API Key"
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    
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

# --- 模块 1: R&D 研发与合规 (面试大杀器) ---
if app_mode == "🔬 R&D 研发与合规 (求职作品)":
    st.title("🔬 智能研发与法规助手")
    st.markdown("""
    **设计理念**：针对食品研发中"法规检索繁琐"、"竞品分析低效"的痛点，
    利用 LLM 构建的垂直领域辅助系统。
    """)
    
    api_key = st.text_input("DeepSeek API Key", type="password")

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
            res = call_deepseek(api_key, sys_prompt, query)
            st.markdown(res)

    with tab2:
        st.subheader("💡 新品概念生成")
        st.info("场景：基于市场热点，辅助研发工程师快速产出产品概念书。")
        
        col1, col2 = st.columns(2)
        with col1:
            base_product = st.text_input("基底产品", "酸奶")
        with col2:
            target_user = st.text_input("目标人群", "熬夜打工人")
            
        trend = st.selectbox("结合趋势", ["药食同源", "0糖0卡", "高蛋白", "助眠/解压"])
        
        if st.button("🧪 生成产品概念书"):
            sys_prompt = (
                "你是一名食品研发工程师（R&D Engineer）。"
                "请根据用户输入，生成一份简要的《新产品开发概念书》。"
                "包含：1. 产品名称 2. 核心卖点 3. 建议添加的功能性成分 4. 口味描述。"
                "风格要专业，符合工业化生产的可行性。"
            )
            req = f"基底：{base_product}，人群：{target_user}，趋势：{trend}"
            res = call_deepseek(api_key, sys_prompt, req)
            st.markdown(res)

# --- 模块 2: 自媒体内容矩阵 (副业工具) ---
elif app_mode == "🎬 自媒体内容矩阵 (副业工具)":
    st.title("🎬 自动化内容生产工厂")
    st.markdown("利用专业背景，批量生产高质量科普/测评脚本。")
    
    api_key = st.text_input("DeepSeek API Key", type="password")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        topic = st.text_input("输入选题 (如：科技与狠活)", placeholder="输入新闻热点或成分名称")
    with col2:
        script_type = st.selectbox("脚本类型", ["辟谣粉碎机", "红黑榜测评", "行业内幕揭秘"])
        
    if st.button("🚀 生成爆款脚本"):
        if script_type == "辟谣粉碎机":
            sys_prompt = "你是一名食品硕士背景的科普博主，请用权威但通俗的语言写一篇辟谣脚本，引用科学原理。"
        elif script_type == "红黑榜测评":
            sys_prompt = "你是一名成分党测评博主，请从配料表角度分析产品优劣，列出红榜和黑榜理由。"
        else:
            sys_prompt = "你是一名食品工厂内部人士，请揭秘行业内幕，分析成本和工艺。"
            
        res = call_deepseek(api_key, sys_prompt, topic)
        st.markdown(res)

# --- 模块 3: 云端数据 (原有功能) ---
elif app_mode == "⚙️ 云端数据看板":
    st.title("⚙️ 自动化系统监控")
    st.write("监控 GitHub Actions 每日爬虫任务状态")
    
    # 这里可以放你之前的 Bark 测试或者简单的热点展示
    st.info("云端任务：daily_task.py 正在 GitHub 服务器上每日 08:00 运行")
    
    bark_url = st.text_input("Bark URL 配置", placeholder="https://api.day.app/...")
    if st.button("📲 发送测试推送到手机"):
         if bark_url:
            try:
                requests.get(f"{bark_url.rstrip('/')}/云端连接测试/网页端指令已发送")
                st.success("推送已发送")
            except Exception as e:
                st.error(f"失败: {e}")