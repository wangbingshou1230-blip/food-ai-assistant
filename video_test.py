from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
import os

# ================= ⚙️ 素材配置 =================
# 1. 图片路径 (背景图)
IMAGE_PATH = "background.jpg"

# 2. 音频路径 (请去 output_files 文件夹里复制一个具体的文件名填在这里)
# ⚠️ 注意：这里必须改！比如 "output_files/最终成品_1737039xxx.mp3"
AUDIO_PATH = "output_files/最终成品_1768649071.mp3" 

# 3. 输出文件名
OUTPUT_VIDEO = "output_files/我的第一个视频.mp4"

def make_video():
    print("🎬 正在初始化视频剪辑引擎...")
    
    # 检查文件是否存在
    if not os.path.exists(IMAGE_PATH) or not os.path.exists(AUDIO_PATH):
        print("❌ 错误：找不到图片或音频文件！请检查路径。")
        return

    try:
        # 1. 加载音频
        audio_clip = AudioFileClip(AUDIO_PATH)
        duration = audio_clip.duration # 获取音频时长(秒)
        print(f"🎵 音频加载成功，时长: {duration} 秒")

        # 2. 加载图片，并设置时长与音频一致
        image_clip = ImageClip(IMAGE_PATH).set_duration(duration)
        
        # 3. (可选) 给图片加个淡入淡出效果，看起来不那么生硬
        image_clip = image_clip.fadein(1).fadeout(1)
        
        # 4. 合并画面和声音
        video = image_clip.set_audio(audio_clip)
        
        # 5. 渲染导出 (最耗时的一步)
        # fps=1 (静态图每秒1帧就够了，为了渲染快)
        print("🚀 开始渲染视频 (请耐心等待)...")
        video.write_videofile(OUTPUT_VIDEO, fps=24, codec="libx264", audio_codec="aac")
        
        print(f"\n🎉 恭喜！视频已生成: {OUTPUT_VIDEO}")
    
    except Exception as e:
        print(f"❌ 渲染失败: {e}")
    finally:
        # 释放资源 (很重要，否则文件会被占用)
        if 'audio_clip' in locals(): audio_clip.close()
        if 'video' in locals(): video.close()

if __name__ == "__main__":
    make_video()