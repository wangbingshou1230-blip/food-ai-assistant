from moviepy.editor import ImageClip, AudioFileClip, ColorClip
import os

class VideoEngine:
    def __init__(self, output_fps=24):
        """
        初始化视频引擎
        :param output_fps: 帧率 (24帧是电影标准，足够科普视频使用)
        """
        self.fps = output_fps

    def create_video(self, image_path, audio_path, output_filename):
        """
        将 [一张图片] + [一段音频] 合成为视频
        """
        try:
            print(f"🎬 正在加载素材...")
            
            # 1. 加载音频
            if not os.path.exists(audio_path):
                print(f"❌ 找不到音频文件: {audio_path}")
                return False
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration # 获取音频时长 (秒)
            
            # 2. 加载画面 (如果找不到图片，就生成一个蓝色背景)
            if os.path.exists(image_path):
                print(f"🖼️ 使用图片背景: {image_path}")
                # 创建图片片段，并设置时长与音频一致
                video_clip = ImageClip(image_path).set_duration(duration)
            else:
                print("⚠️ 未找到图片，使用默认纯色背景")
                # ColorClip(size, color) -> 1920x1080 蓝色
                video_clip = ColorClip(size=(1280, 720), color=(0, 120, 215)).set_duration(duration)

            # 3. 合成 (将音频轨道设置给视频轨道)
            final_clip = video_clip.set_audio(audio_clip)

            # 4. 渲染导出
            print(f"🚀 开始渲染视频 (时长: {duration:.2f}秒)...")
            # codec='libx264' 是最通用的 MP4 编码，audio_codec='aac' 是标准音频编码
            final_clip.write_videofile(
                output_filename, 
                fps=self.fps, 
                codec="libx264", 
                audio_codec="aac",
                logger=None # 关掉繁琐的进度条日志，保持控制台清爽
            )
            
            print(f"✅ 视频生成成功: {output_filename}")
            return True

        except Exception as e:
            print(f"❌ 视频合成失败: {e}")
            return False
        finally:
            # 严谨的内存管理：释放资源，防止程序占用文件不放
            if 'audio_clip' in locals(): audio_clip.close()
            if 'video_clip' in locals(): video_clip.close()

# ================= 单元测试 =================
if __name__ == "__main__":
    # 1. 准备素材
    # 注意：这里我们直接用刚才生成的 test_audio.mp3
    test_audio = "test_audio.mp3" 
    test_image = "background.jpg" # 你可以放一张真实的图片试试，没有的话会自动变蓝屏
    output_video = "final_result.mp4"
    
    # 2. 检查音频是否存在 (如果没有，请先运行 9_tts_engine.py 生成一个)
    if not os.path.exists(test_audio):
        print("请先运行上一步的代码生成 test_audio.mp3！")
    else:
        # 3. 运行引擎
        engine = VideoEngine()
        engine.create_video(test_image, test_audio, output_video)
        
        # 4. 自动播放验证
        os.system(f"start {output_video}")