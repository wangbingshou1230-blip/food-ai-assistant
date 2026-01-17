import asyncio
import json
import time
import pandas as pd
import requests
import edge_tts
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# ================= ⚙️ 全局配置 =================
# 想要搜什么？在这里改一次就行
KEYWORD = "预制菜进校园" 
VOICE = "zh-CN-YunxiNeural" # 配音角色
CONFIG_FILE = "config.json"

# ================= 🕵️‍♂️ 第一步：情报搜集 (Selenium) =================
def step1_get_news(keyword):
    print(f"\n======== [1/3] 正在启动爬虫搜索：{keyword} ========")
    
    # 启动浏览器
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") # 想看浏览器弹出来就注释掉这行，不想看就留着
    driver = webdriver.Chrome(service=service, options=options)
    
    news_data = []
    try:
        url = f"https://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&word={keyword}"
        driver.get(url)
        time.sleep(2)
        
        # 简单滚动一下
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(1)
        
        # 抓取
        titles = driver.find_elements(By.CSS_SELECTOR, "h3")
        for t in titles[:5]: # 只取前5条最热的
            clean_title = t.text.replace("\n", " ")
            news_data.append(clean_title)
            print(f"✅ 抓取到: {clean_title[:20]}...")
            
    except Exception as e:
        print(f"❌ 爬虫出错: {e}")
    finally:
        driver.quit()
        
    # 保存数据备用
    if news_data:
        df = pd.DataFrame(news_data, columns=["标题"])
        df.to_excel(f"output_files/{keyword}_素材.xlsx", index=False)
        print(f"💾 素材已保存到 Excel，共 {len(news_data)} 条。")
        return news_data # 把数据返回给下一步
    else:
        return []

# ================= 🧠 第二步：大脑思考 (DeepSeek) =================
def step2_write_script(titles):
    print(f"\n======== [2/3] 正在让 AI 撰写文案... ========")
    
    if not titles:
        print("❌ 没有素材，无法写稿！")
        return None

    # 读取密钥
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            api_key = config["deepseek_api_key"]
    except:
        print("❌ 找不到 config.json 或密钥配置错误！")
        return None

    # 准备 Prompt
    titles_text = "\n".join([f"- {t}" for t in titles])
    prompt = f"""
    你是食品安全大V。基于以下新闻标题：
    {titles_text}
    
    写一段200字左右的短视频口播文案。
    风格：开头要炸裂，中间有干货，结尾有引导。
    不要带“镜头1”这种标注，直接写要读出来的字。
    """

    # 调用 API
    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }
        )
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print("📝 文案生成成功！预览前50字：")
            print(f"“{content[:50]}...”")
            
            # 保存文案
            with open("最终脚本.txt", "w", encoding="utf-8") as f:
                f.write(content)
            return content
        else:
            print("❌ AI 罢工了:", response.text)
            return None
    except Exception as e:
        print(f"❌ 网络请求错误: {e}")
        return None

# ================= 🎙️ 第三步：声音合成 (Edge-TTS) =================
async def step3_make_audio(text):
    print(f"\n======== [3/3] 正在生成配音... ========")
    if not text:
        print("❌ 没有文案，无法配音！")
        return

    output_file = f"output_files/最终成品_{int(time.time())}.mp3"# 加个时间戳防止文件名冲突
    
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(output_file)
        print(f"🎉 大功告成！音频已保存为: {output_file}")
        print("👉 现在的你，只需要把音频拖进剪映，配几张图就发了！")
    except Exception as e:
        print(f"❌ 配音失败: {e}")

# ================= 🔗 总指挥中心 =================
async def main_pipeline():
    # 1. 爬虫
    titles = step1_get_news(KEYWORD)
    
    # 2. 写作 (如果爬到了数据)
    if titles:
        script_text = step2_write_script(titles)
        
        # 3. 配音 (如果写出了文案)
        if script_text:
            await step3_make_audio(script_text)
    else:
        print("😭 流程意外终止。")

if __name__ == "__main__":
    asyncio.run(main_pipeline())