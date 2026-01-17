import asyncio
import os
# 👇 严谨：从你写的文件里导入类 (Class)
# 只要这几个 py 文件在同一个文件夹下，就能直接 import
from m9_tts_engine import AudioEngine 
from m10_video_engine import VideoEngine

class ContentPipeline:
    def __init__(self):
        # 初始化两个子引擎
        self.audio_bot = AudioEngine(voice="zh-CN-YunxiNeural") # 选个稳重的男声
        self.video_bot = VideoEngine()

    async def run(self, text_content, background_image, output_filename):
        """
        全自动流程：文字 -> 音频 -> 视频
        """
        print(f"🎬 [流水线启动] 目标：{output_filename}")
        
        # 1. 定义临时文件名
        temp_audio = "temp_speech.mp3"
        
        # --- 阶段一：生产音频 ---
        success_audio = await self.audio_bot.generate_audio(text_content, temp_audio)
        if not success_audio:
            print("❌ 流水线中断：音频生成失败")
            return
        
        # --- 阶段二：生产视频 ---
        # 这里的 output_filename 必须是 .mp4 结尾
        success_video = self.video_bot.create_video(background_image, temp_audio, output_filename)
        
        # --- 阶段三：清理现场 (严谨的工程习惯) ---
        if os.path.exists(temp_audio):
            os.remove(temp_audio) # 删掉中间产生的临时音频，保持文件夹干净
            print(f"🧹 已清理临时文件: {temp_audio}")

        if success_video:
            print(f"🎉 [流水线完成] 最终成品已生成！")
        else:
            print("❌ 流水线中断：视频合成失败")

# ================= 实际运行 =================
if __name__ == "__main__":
    # 1. 准备一段像模像样的文案 (模拟 AI 分析结果)
    script = """
    大家好，这是今天的食品行业简报。
    最新研究表明，通过控制美拉德反应的程度，可以有效降低预制菜复热后的异味。
    这项技术目前已经在三家头部食品工厂进行中试。
    我是您的 AI 助手，感谢收听。
    """
    
    # 2. 准备背景图 (如果没有 background.jpg，引擎会自动变蓝屏，不影响运行)
    bg_image = "background.jpg" 
    
    # 3. 定义输出文件名
    final_video = "daily_report_v1.mp4"
    
    # 4. 启动流水线
    pipeline = ContentPipeline()
    asyncio.run(pipeline.run(script, bg_image, final_video))
    
    # 5. 自动播放验证
    if os.path.exists(final_video):
        os.system(f"start {final_video}")