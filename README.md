# 🧬 FoodMaster Pro: 食品研发与自媒体自动化工作流

> **The Digital Co-Pilot for Food Scientists & Creators**
> 专为食品硕士打造的"科研+内容"双轨制 AI 辅助系统。

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://你的Streamlit链接填在这里)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek%20V3%2FR1-brightgreen)](https://www.deepseek.com/)

## 📖 项目背景 (Background)

作为一名食品加工与安全专业的硕士，我发现传统研发与内容创作中存在大量重复性工作。本项目旨在利用 **Python 全栈技术** 与 **LLM (大语言模型)**，构建一套自动化的数字化工作流。

**核心解决痛点：**
1.  **法规检索难**：GB 标准繁多，人工查阅效率低。
2.  **研发周期长**：新品概念落地缺乏数据支撑。
3.  **信息差**：行业热点获取滞后，自媒体内容生产效率低。

## ✨ 核心功能 (Key Features)

### 🔬 1. R&D 智能研发系统
- **🧠 双核大脑**：集成 **DeepSeek-V3** (极速) 与 **DeepSeek-R1** (深度推理)，支持 CoT 思维链展示。
- **📄 RAG 文档分析**：支持上传 PDF (GB标准/文献)，AI 基于文档内容进行精准问答，消除幻觉。
- **📊 可视化风味模拟**：基于 Plotly 绘制产品感官雷达图，辅助配方设计。
- **💬 记忆对话 & ELN**：支持多轮上下文对话，并可一键导出 **Markdown 格式实验记录 (ELN)**。

### 🎬 2. 自媒体自动化工厂
- **🔥 全网情报**：实时抓取全网/百度热搜，AI 自动筛选食品相关选题。
- **📝 脚本生成**：一键生成辟谣/测评/科普类的分镜脚本（Markdown 表格）。
- **🎙️ AI 配音室**：集成 **Edge-TTS**，免费生成新闻级/解说级 AI 语音。

### ⚙️ 3. 云端无人值守监控
- **🤖 GitHub Actions**：每日定时运行爬虫脚本。
- **📲 Bark 推送**：自动将 AI 整理的《今日食品情报简报》推送至手机。

## 🛠 技术栈 (Tech Stack)

* **Frontend**: Streamlit (Web UI)
* **Backend**: Python, Pandas
* **AI Model**: DeepSeek-V3 / DeepSeek-R1 (via API)
* **RAG**: pdfplumber (PDF Parsing)
* **Visualization**: Plotly Interactive Charts
* **Audio**: Edge-TTS (Async Text-to-Speech)
* **DevOps**: GitHub Actions, Streamlit Cloud

## 🚀 快速开始 (Quick Start)

1. **访问在线演示**: [点击这里体验](https://你的Streamlit链接填在这里) (密码: 123456)
2. **本地运行**:
   ```bash
   git clone [https://github.com/你的用户名/你的仓库名.git](https://github.com/你的用户名/你的仓库名.git)
   pip install -r requirements.txt
   streamlit run 16_food_web_pro.py