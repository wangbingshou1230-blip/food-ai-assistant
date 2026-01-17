import streamlit as st
import pandas as pd
import os
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# ================= ⚙️ 配置中心 =================
# 设置页面标题和图标
st.set_page_config(page_title="FoodAI 安全助手", page_icon="🍔", layout="wide")

# 中文字体路径 (Windows 默认黑体)
# 改成相对路径 (只要字体文件在根目录，这样写就行)
FONT_PATH = "simhei.ttf"

# ================= 🧹 工具函数 =================
def load_excel_files():
    """扫描 output_files 文件夹，找到所有的 Excel 文件"""
    folder = "output_files"
    if not os.path.exists(folder):
        os.makedirs(folder)
        return []
    files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]
    return files

def draw_word_cloud(text_data):
    """绘制词云图"""
    try:
        # 创建词云对象
        wc = WordCloud(
            font_path=FONT_PATH,      # 必须指定中文字体！
            width=800, height=400,    # 图片大小
            background_color='white', # 背景颜色
            max_words=100             # 最多显示多少个词
        ).generate(text_data)
        
        # 使用 matplotlib 画图
        plt.figure(figsize=(10, 5))
        plt.imshow(wc, interpolation='bilinear')
        plt.axis('off') # 关掉坐标轴
        return plt
    except Exception as e:
        st.error(f"生成词云失败，可能是字体路径不对: {e}")
        return None

# ================= 🏠 页面 1: AI 问答 (原来的功能) =================
def page_chat():
    st.title("🤖 食品安全 AI 专家")
    st.caption("基于 DeepSeek-V3 · 你的私人科研顾问")
    
    # 简单的对话框 (为了代码简洁，这里保留最基础的对话功能)
    user_input = st.chat_input("请输入你的问题，例如：亚硝酸盐超标怎么办？")
    if user_input:
        st.chat_message("user").write(user_input)
        st.chat_message("assistant").write("AI 正在思考... (这里接入你的 DeepSeek 逻辑)")

# ================= 📊 页面 2: 舆情分析 (新功能!) =================
def page_analysis():
    st.title("📊 舆情热词分析")
    st.markdown("---")

    # 1. 侧边栏：选择数据源
    files = load_excel_files()
    if not files:
        st.warning("⚠️ output_files 文件夹里没有 Excel 文件！请先去运行 full_auto_studio.py 抓点新闻回来。")
        return

    selected_file = st.selectbox("📂 选择要分析的爬虫数据:", files)

    if selected_file:
        file_path = os.path.join("output_files", selected_file)
        
        # 2. 读取数据
        try:
            df = pd.read_excel(file_path)
            st.success(f"✅ 成功读取文件：{selected_file}，共 {len(df)} 条数据")
            
            # 显示前 5 行给用户看看
            with st.expander("👀 查看原始数据 (前5条)"):
                st.dataframe(df.head())

            # 3. 数据处理：把所有标题拼成一个大字符串
            # 假设 Excel 里有一列叫 "标题" (我们在爬虫脚本里定义的)
            if "标题" in df.columns:
                all_text = " ".join(df["标题"].astype(str).tolist())
                
                # 4. 按钮：点击生成词云
                if st.button("🎨 生成词云图"):
                    st.markdown("### 🔥 热点词云")
                    fig = draw_word_cloud(all_text)
                    if fig:
                        st.pyplot(fig) # 把图显示在网页上
            else:
                st.error("❌ 这个 Excel 里找不到 '标题' 这一列！请检查文件格式。")

        except Exception as e:
            st.error(f"读取文件出错: {e}")

# ================= 🚀 主程序入口 =================
def main():
    # 侧边栏导航
    st.sidebar.image("background.jpg", caption="FoodAI Lab", use_container_width=True)
    st.sidebar.title("导航")
    page = st.sidebar.radio("去哪里？", ["🤖 AI 问答", "📊 舆情分析"])

    if page == "🤖 AI 问答":
        page_chat()
    elif page == "📊 舆情分析":
        page_analysis()

if __name__ == "__main__":
    main()