import asyncio
import json
import time
import os
import re
import pandas as pd
import requests
import edge_tts
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from moviepy.editor import ImageClip, AudioFileClip

# ================= ⚙️ 配置中心 =================
KEYWORD = "预制菜进校园" 
VOICE = "zh-CN-YunxiNeural" 
CONFIG_FILE = "config.json"
OUTPUT_DIR = "output_files"
BACKGROUND_IMAGE = "background.jpg" # 确保根目录下有这张图

# 自动创建输出目录
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

# ================= 🧹 工具：文案清洗 =================
def clean_script_text(text):
    """清洗AI生成的文案，去掉括号和无关指令"""
    print("🧹 正在清洗文案...")
    # 去掉 【...】 (...) （...）
    text = re.sub(r"[\(\[（【].*?[\)\]）】]", "", text)
    # 去掉 "镜头：" "画面："
    text = re.sub(r"(镜头|画面|场景)\d?[:：]", "", text)
    return text.replace("\n", " ").strip()

# ================= 🕵️‍♂️ Step 1: 爬虫 =================
def step1_get_news(keyword):
    print(f"\n======== [1/4] 启动爬虫: {keyword} ========")
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") # 如果不想看浏览器弹窗，取消这行注释
    driver = webdriver.Chrome(service=service, options=options)
    
    news_data = []
    try:
        driver.get(f"https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&word={keyword}")
        time.sleep(2)
        titles = driver.find_elements(By.CSS_SELECTOR, "h3")
        for t in titles[:5]: 
            clean_title = t.text.replace("\n", " ")
            news_data.append(clean_title)
            print(f"✅ {clean_title[:15]}...")
    except Exception as e:
        print(f"❌ 爬虫出错: {e}")
    finally:
        driver.quit()
        
    if news_data:
        df = pd.DataFrame(news_data, columns=["标题"])
        df.to_excel(os.path.join(OUTPUT_DIR, f"{keyword}_素材.xlsx"), index=False)
        return news_data
    return []

# ================= 🧠 Step 2: 写作 =================
def step2_write_script(titles):
    print(f"\n======== [2/4] AI 撰写文案... ========")
    if not titles: return None

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            api_key = json.load(f)["deepseek_api_key"]
    except: return None

    titles_text = "\n".join([f"- {t}" for t in titles])
    prompt = f"""
    你是食品安全博主。基于以下新闻：
    {titles_text}
    
    写一段200字的短视频口播文案。
    要求：犀利、干货、接地气。
    【严禁】出现任何括号、动作指示或语气词。只写要读出来的字。
    """

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]}
        )
        if response.status_code == 200:
            raw = response.json()['choices'][0]['message']['content']
            clean = clean_script_text(raw)
            
            with open(os.path.join(OUTPUT_DIR, "最终脚本.txt"), "w", encoding="utf-8") as f:
                f.write(clean)
            return clean
    except Exception as e:
        print(f"❌ API 请求出错: {e}")
        return None

# ================= 🎙️ Step 3: 配音 =================
async def step3_make_audio(text):
    print(f"\n======== [3/4] 生成配音... ========")
    if not text: return None
    audio_path = os.path.join(OUTPUT_DIR, f"配音_{int(time.time())}.mp3")
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(audio_path)
        return audio_path
    except Exception as e:
        print(f"❌ 配音失败: {e}")
        return None

# ================= 🎬 Step 4: 视频 (单图版) =================
def step4_make_video(audio_path):
    print(f"\n======== [4/4] 渲染最终视频... ========")
    
    if not os.path.exists(BACKGROUND_IMAGE):
        print(f"❌ 根目录缺少 {BACKGROUND_IMAGE}！请找一张图片放进去。")
        return

    output_path = os.path.join(OUTPUT_DIR, f"最终成品_{int(time.time())}.mp4")

    try:
        audio_clip = AudioFileClip(audio_path)
        # 核心逻辑：图片展示时长 = 音频时长
        video = ImageClip(BACKGROUND_IMAGE).set_duration(audio_clip.duration)
        video = video.set_audio(audio_clip)
        
        # fps=1 就够了，渲染飞快
        video.write_videofile(output_path, fps=1, codec="libx264", audio_codec="aac")
        print(f"\n🎉 搞定！视频都在这里: {output_path}")
        
    except Exception as e:
        print(f"❌ 渲染失败: {e}")
    finally:
        if 'audio_clip' in locals(): audio_clip.close()
        if 'video' in locals(): video.close()

# ================= 🔗 总指挥 =================
async def main_pipeline():
    titles = step1_get_news(KEYWORD)
    if titles:
        text = step2_write_script(titles)
        if text:
            audio = await step3_make_audio(text)
            if audio:
                step4_make_video(audio)

if __name__ == "__main__":
    asyncio.run(main_pipeline())