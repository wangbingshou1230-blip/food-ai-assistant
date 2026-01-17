import streamlit as st
import pandas as pd
import os
import json
import requests
import pdfplumber
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
from datetime import datetime

# ================= ⚙️ 1. 全局配置 =================
st.set_page_config(
    page_title="FoodAI 全能工作台", 
    page_icon="🧬", # 图标升级为DNA，代表深入核心
    layout="wide",
    initial_sidebar_state="expanded"
)

FONT_PATH = "simhei.ttf"

# ================= 🔐 2. 核心：精准适配 Secrets =================
def get_config(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get(key_name)
    except:
        pass
    return None

# ================= 🛡️ 3. 安全门禁 =================
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    st.header("🔒 FoodAI 系统登录")
    password = st.text_input("请输入访问密码", type="password")
    
    if st.button("登录"):
        correct_password = get_config("app_password")
        if not correct_password: correct_password = "123456" 
            
        if password == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 密码错误")
    return False

# ================= 📡 4. Bark 推送 =================
def send_bark(title, content):
    device_key = get_config("bark_device_key")
    server = get_config("bark_server")
    if not server: server = "https://api.day.app"
    server = server.rstrip("/")

    if not device_key:
        return False, "⚠️ 未配置 bark_device_key"
    
    # Bark URL 编码处理 (简单处理)
    url = f"{server}/{device_key}/{title}/{content}"
    try:
        res = requests.get(url)
        if res.status_code == 200: return True, "✅ 推送成功"
        else: return False, f"❌ 推送失败: {res.text}"
    except Exception as e:
        return False, f"❌ 网络错误: {e}"

# ================= 🧠 5. AI 引擎 =================
def get_deepseek_response(messages):
    api_key = get_config("deepseek_api_key")
    if not api_key: return "❌ 错误：未找到 deepseek_api_key"

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "deepseek-chat", "messages": messages, "stream": False}
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"❌ API 报错: {response.text}"
    except Exception as e:
        return f"❌ 请求失败: {e}"

# ================= 🧩 6. 功能页面组装 =================

def page_chat():
    st.title("🤖 智能问答")
    st.caption("DeepSeek-V3 + Bark 远程通知")

    with st.expander("📡 测试手机通知"):
        col1, col2 = st.columns([3, 1])
        with col1:
            test_msg = st.text_input("输入测试内容", value="系统连接正常")
        with col2:
            if st.button("🚀 发送"):
                success, msg = send_bark("FoodAI测试", test_msg)
                if success: st.toast(msg, icon="✅")
                else: st.error(msg)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("请输入问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                reply = get_deepseek_response(st.session_state.messages)
                st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                
                if len(reply) > 50:
                    if st.button("📲 推送摘要到手机"):
                        send_bark("AI回答", reply[:100] + "...")
                        st.success("已推送")

def page_doc_analysis():
    st.title("📄 文档深度分析")
    uploaded_file = st.file_uploader("上传 PDF", type=["pdf"])
    
    if uploaded_file:
        text = ""
        with st.spinner("解析 PDF 中..."):
            try:
                with pdfplumber.open(uploaded_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text: text += page_text + "\n"
                st.success(f"✅ 解析成功，共 {len(text)} 字")
                
                user_q = st.text_input("关于文档你想问什么？")
                if user_q and st.button("分析"):
                    with st.spinner("AI 阅读中..."):
                        context = text[:15000]
                        messages = [
                            {"role": "system", "content": "你是一个学术助手。"},
                            {"role": "user", "content": f"文档：\n{context}\n\n问题：{user_q}"}
                        ]
                        answer = get_deepseek_response(messages)
                        st.markdown("### 💡 分析结果")
                        st.write(answer)
                        send_bark("文档分析完成", f"关于{user_q}的回答已生成")
            except Exception as e:
                st.error(f"解析失败: {e}")

def page_data_viz():
    st.title("📊 科研数据中心")
    viz_mode = st.radio("选择功能模块:", ["📂 舆情爬虫看板", "🧪 实验室电子记录本 (ELN)"], horizontal=True)
    
    # === 模块 A: 爬虫看板 (新增：AI 舆情日报) ===
    if viz_mode == "📂 舆情爬虫看板":
        folder = "output_files"
        if not os.path.exists(folder):
            st.warning("⚠️ output_files 文件夹不存在")
            return
        files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]
        if not files:
            st.info("📂 暂无 Excel 文件")
            return
        selected = st.selectbox("选择爬虫数据:", files)
        if selected:
            try:
                df = pd.read_excel(os.path.join(folder, selected))
                if "标题" in df.columns:
                    st.success(f"✅ 加载 {len(df)} 条舆情数据")
                    
                    # 🔥 升级：三个 Tab
                    tab1, tab2, tab3 = st.tabs(["☁️ 词云图", "📈 频次图", "🗞️ AI 舆情日报"])
                    text = " ".join(df["标题"].astype(str).tolist())
                    
                    with tab1:
                        if st.button("生成词云"):
                            if os.path.exists(FONT_PATH):
                                wc = WordCloud(font_path=FONT_PATH, width=800, height=400, background_color='white').generate(text)
                                plt.figure(figsize=(10, 5))
                                plt.imshow(wc, interpolation='bilinear')
                                plt.axis('off')
                                st.pyplot(plt)
                            else: st.error("❌ 缺少字体文件")
                    
                    with tab2:
                        words = [w for w in text.split() if len(w) > 1]
                        if words:
                            chart_data = pd.DataFrame(Counter(words).most_common(20), columns=["词", "频次"])
                            st.bar_chart(chart_data.set_index("词"))

                    # 🔥 新增核心功能：AI 日报
                    with tab3:
                        st.markdown("### 🤖 舆情风险智能总结")
                        st.caption("DeepSeek 将阅读前 50 条新闻标题，为你生成今日简报。")
                        
                        if st.button("🚀 生成并推送日报"):
                            with st.status("AI 正在工作中...", expanded=True) as status:
                                # 1. 准备数据
                                status.write("👀 正在读取新闻标题...")
                                # 取前 50 条，避免 token 超出
                                news_titles = df["标题"].head(50).tolist()
                                news_str = "\n".join([f"- {t}" for t in news_titles])
                                
                                # 2. AI 思考
                                status.write("🧠 DeepSeek 正在分析舆论风向...")
                                prompt = [
                                    {"role": "system", "content": "你是一个食品安全舆情分析师。请阅读以下新闻标题，总结今日的舆情要点。要求：\n1. 提炼出 3 个核心热点话题。\n2. 分析公众情绪（焦虑/中立/积极）。\n3. 如果有风险事件，请高亮提示。\n4. 输出格式精简，适合手机阅读。"},
                                    {"role": "user", "content": f"今日新闻列表：\n{news_str}"}
                                ]
                                report = get_deepseek_response(prompt)
                                
                                status.write("✅ 报告生成完毕！")
                                status.update(label="任务完成", state="complete", expanded=False)
                            
                            # 3. 显示与推送
                            st.markdown("#### 📄 今日舆情简报")
                            st.info(report)
                            
                            # 推送处理 (Bark URL 长度有限，需截取)
                            # 提取报告的第一段或前 100 字作为摘要
                            summary = report[:150].replace("#", "").replace("*", "") + "..."
                            send_bark("今日舆情日报", summary)
                            st.toast("日报已推送至手机！", icon="📲")

                else: st.error("❌ 缺少 '标题' 列")
            except Exception as e: st.error(f"读取失败: {e}")

    # === 模块 B: 实验室电子记录本 (保持完整，含 AI 诊断) ===
    elif viz_mode == "🧪 实验室电子记录本 (ELN)":
        st.subheader("🧪 智能实验数据中心")
        
        if "lab_data_v2" not in st.session_state:
            st.session_state.lab_data_v2 = pd.DataFrame({
                "样品编号": ["S-001", "S-002", "S-003"],
                "取样时间": ["08:00", "10:00", "12:00"],
                "pH值": [6.80, 5.50, 4.60],
                "温度(°C)": [42.0, 42.5, 43.0],
                "转速(rpm)": [1000, 1000, 0],
                "平均粒径(nm)": [None, 250.5, 260.0],
                "外观描述": ["乳状液初形成", "开始变稠", "凝胶形成良好"],
            })

        column_config = {
            "样品编号": st.column_config.TextColumn("🆔 样品编号", required=True),
            "取样时间": st.column_config.TextColumn("⏰ 取样时间"),
            "pH值": st.column_config.NumberColumn("🧪 pH值", format="%.2f"),
            "温度(°C)": st.column_config.NumberColumn("🌡️ 温度(°C)", format="%.1f"),
            "转速(rpm)": st.column_config.NumberColumn("🔄 转速(rpm)"),
            "平均粒径(nm)": st.column_config.NumberColumn("📏 粒径(nm)"),
            "外观描述": st.column_config.TextColumn("📝 备注", width="large"),
        }
        
        edited_df = st.data_editor(
            st.session_state.lab_data_v2,
            num_rows="dynamic",
            column_config=column_config,
            use_container_width=True,
            key="editor_v2"
        )
        st.session_state.lab_data_v2 = edited_df
        st.divider()
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("### 📈 趋势监控")
            if not edited_df.empty:
                plot_col = st.selectbox("分析参数:", ["pH值", "温度(°C)", "平均粒径(nm)"])
                if plot_col in edited_df.columns:
                    plot_df = edited_df.dropna(subset=[plot_col])
                    if not plot_df.empty:
                        st.line_chart(plot_df.set_index("取样时间")[plot_col])
        with col2:
            st.markdown("### 🧠 AI 深度诊断")
            if st.button("🚀 开始 AI 诊断"):
                if edited_df.empty: st.warning("请先录入数据！")
                else:
                    with st.spinner("AI 诊断中..."):
                        # 依赖 tabulate
                        try:
                            data_str = edited_df.to_markdown(index=False)
                        except ImportError:
                            st.error("❌ 缺少 tabulate 库，请检查 requirements.txt")
                            st.stop()
                            
                        prompt = [
                            {"role": "system", "content": "你是一位食品发酵专家。请分析数据：1.pH变化速率 2.温度稳定性 3.异常点 4.建议。"},
                            {"role": "user", "content": f"实验记录：\n{data_str}"}
                        ]
                        analysis = get_deepseek_response(prompt)
                        st.success("✅ 诊断完成")
                        st.info(analysis)
                        short_analysis = analysis[:100].replace("\n", " ") + "..."
                        send_bark("AI实验诊断", short_analysis)

            st.divider()
            if not edited_df.empty:
                csv = edited_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 备份数据 (Excel)", csv, "lab_data.csv", "text/csv")

# ================= 🚀 7. 主程序 =================
def main():
    if not check_password(): return

    if os.path.exists("background.jpg"):
        st.sidebar.image("background.jpg", use_container_width=True)
    
    st.sidebar.title("🍔 FoodAI 系统")
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"🔑 DeepSeek: {'✅' if get_config('deepseek_api_key') else '❌'}")
    st.sidebar.caption(f"📡 Bark推送: {'✅' if get_config('bark_device_key') else '❌'}")

    page = st.sidebar.radio("功能导航", ["🤖 智能问答", "📄 文档分析", "📊 科研数据中心"])

    if page == "🤖 智能问答": page_chat()
    elif page == "📄 文档分析": page_doc_analysis()
    elif page == "📊 科研数据中心": page_data_viz()

if __name__ == "__main__":
    main()