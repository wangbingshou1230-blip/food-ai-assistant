import asyncio
import edge_tts
import os

class AudioEngine:
    def __init__(self, voice="zh-CN-YunxiNeural", rate="+0%", volume="+0%"):
        """
        初始化音频引擎
        :param voice: 语音角色 (默认为云希，适合新闻播报的男声)
        :param rate: 语速 (例如 "+10%" 或 "-10%")
        :param volume: 音量
        """
        self.voice = voice
        self.rate = rate
        self.volume = volume

    async def generate_audio(self, text, output_filename):
        """
        [异步方法] 将文本转换为 MP3 文件
        :param text: 要朗读的文本
        :param output_filename: 输出文件名 (包含路径)
        """
        try:
            print(f"🎙️ 正在合成语音，字数：{len(text)} ...")
            
            # 创建沟通对象
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, volume=self.volume)
            
            # 执行合成并保存
            await communicate.save(output_filename)
            
            print(f"✅ 音频已生成: {output_filename}")
            return True
        except Exception as e:
            print(f"❌ 语音合成失败: {e}")
            return False

# ================= 单元测试 (Unit Test) =================
# 严谨的开发习惯：写完模块，必须在下方写一段测试代码，确保它能独立运行。
if __name__ == "__main__":
    # 1. 定义一段测试文本 (模拟食品新闻)
    test_text = """
    你好，我是你的 AI 科研助手。
    根据最新情报，非热杀菌技术在乳制品加工中的应用正在快速增长。
    超高压处理不仅能有效杀灭致病菌，还能最大限度保留免疫球蛋白的活性。
    """
    
    # 2. 定义输出文件
    output_file = "test_audio.mp3"
    
    # 3. 实例化引擎
    engine = AudioEngine(voice="zh-CN-YunxiNeural") # 云希是很好的男声，也可以试 zh-CN-XiaoxiaoNeural (女声)
    
    # 4. 运行异步任务 (这是 Python 运行 async 函数的标准写法)
    asyncio.run(engine.generate_audio(test_text, output_file))
    
    # 5. 自动播放 (仅限 Windows，方便你听结果)
    os.system(f"start {output_file}")