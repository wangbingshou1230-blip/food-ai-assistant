# 🍔 FoodAI Assistant (食品安全 AI 助手)

> 一个集成了 AI 智能问答、RAG 文档分析、动态新闻爬取与自动视频生成的全栈食品安全助手。

## 🌟 项目简介

本项目旨在利用大模型技术解决食品安全领域的知识获取难题。它不仅是一个基于 Web 的问答系统，还包含了一个自动化的自媒体内容生产流水线。

### 核心功能
1.  **🤖 AI 智能问答 (Web)**: 集成 DeepSeek 大模型，提供专业的食品安全咨询。
2.  **📄 论文/文档分析 (RAG)**: 支持上传 PDF/Excel，通过 RAG 技术实现基于文档的精准问答。
3.  **🕷️ 动态情报监测 (Selenium)**: 自动化抓取百度新闻/社交媒体关于特定食品关键词的舆情。
4.  **🎬 内容自动化工厂 (Automation)**: 
    - 自动聚合热点新闻
    - AI 生成短视频脚本
    - Edge-TTS 自动生成语音解说

## 🛠️ 技术栈

* **核心语言**: Python 3.8+
* **Web 框架**: Streamlit (已部署至 Streamlit Cloud)
* **大模型 API**: DeepSeek-V3
* **数据采集**: Selenium + WebDriver Manager
* **语音合成**: Edge-TTS
* **数据处理**: Pandas, PyPDF2, BeautifulSoup4

## 📂 项目结构

```text
AI_Test/
├── 16_food_web_pro.py    # [Web端] Streamlit 主程序
├── full_auto_studio.py   # [本地端] 全自动内容生产流水线
├── config.json           # [配置] API 密钥配置文件 (已脱敏)
├── requirements.txt      # [依赖] 项目依赖库清单
├── output_files/         # [产物] 存放生成的 MP3、Excel 和视频素材
└── old_learning/         # [归档] 早期开发过程中的测试代码
