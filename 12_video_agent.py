import asyncio
import requests
from bs4 import BeautifulSoup
import json
import os
# 👇 导入你的媒体引擎
from m9_tts_engine import AudioEngine 
from m10_video_engine import VideoEngine

# ================= 配置 =================
API_KEY = "sk-44104f41c16f42748973c225aff64f0f" # 你的 DeepSeek 密钥
# =======================================

class AutoVideoBot:
    def __init__(self):
        self.audio = AudioEngine(voice="zh-CN-YunxiNeural") # 严谨男声
        self.video = VideoEngine()
        print("🤖 视频机器人已启动，准备工作...")

    # --- 1. 搜索模块 (复用 Plan A) ---
    def search_bing(self, keyword):
        print(f"🕵️ 正在搜索素材：{keyword}...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}
        try:
            resp = requests.get(f"https://cn.bing.com/search?q={keyword}", headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []
            for t in soup.find_all('h2')[:5]: # 取前5条做素材
                link = t.find('a')
                if link: results.append(f"- {link.get_text()}")
            return "\n".join(results) if results else None
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
            return None

    # --- 2. 编剧模块 (AI 写稿) ---
    def write_script(self, search_data):
        print("🧠 DeepSeek 正在撰写视频脚本...")
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
        
        # 🔥 关键：提示词要让 AI 写“口播稿”，而不是“论文”
        prompt = """
        你是一位专业的食品科普短视频博主。
        请根据以下搜索结果，写一段 100字左右 的视频口播文案。
        要求：
        1. 语气通俗易懂，像在给人讲故事。
        2. 开头要有吸引力（比如“你知道吗...”）。
        3. 结尾要有一句简单的总结。
        4. 不要带任何表情符号、不要带 Markdown 格式，纯文本。
        """
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": search_data}
            ]
        }
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload))
            if resp.status_code == 200:
                script = resp.json()['choices'][0]['message']['content']
                print(f"📝 脚本已生成：\n{script}\n" + "-"*30)
                return script
            return None
        except Exception as e:
            print(f"❌ AI 写作失败: {e}")
            return None

    # --- 3. 生产模块 (Pipeline) ---
    async def produce(self, topic, output_file):
        # Step 1: 找素材
        data = self.search_bing(topic)
        if not data: return
        
        # Step 2: 写剧本
        script = self.write_script(data)
        if not script: return
        
        # Step 3: 合成音频
        temp_audio = "temp_final_audio.mp3"
        await self.audio.generate_audio(script, temp_audio)
        
        # Step 4: 合成视频
        # 自动检测有没有背景图，没有就用蓝屏
        bg_image = "background.jpg" 
        self.video.create_video(bg_image, temp_audio, output_file)
        
        # 清理
        if os.path.exists(temp_audio): os.remove(temp_audio)
        print(f"✅ 全流程结束！文件都在：{output_file}")

# ================= 主程序 =================
if __name__ == "__main__":
    bot = AutoVideoBot()
    
    # 🎯 设定你的题目
    topic = "预制菜的食品安全标准"
    output = "video_result.mp4"
    
    # 🚀 启动！
    asyncio.run(bot.produce(topic, output))
    
    # 自动播放
    if os.path.exists(output):
        os.system(f"start {output}")