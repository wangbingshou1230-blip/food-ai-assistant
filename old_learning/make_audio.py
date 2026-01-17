import asyncio
import edge_tts

# ================= 🎙️ 升级版配音机 =================

# 1. 指定要读的文件 (刚才生成的那个)
SCRIPT_FILE = "今日脚本.txt"
# 2. 输出音频文件名
OUTPUT_FILE = "今日爆款配音.mp3"
# 3. 选声音 (云希-男声, 晓晓-女声)
VOICE = "zh-CN-YunxiNeural"

async def generate_audio():
    print(f"📖 正在读取文案文件: {SCRIPT_FILE}...")
    try:
        # 打开文件读取内容
        with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
            text = f.read()
            
        print(f"🎙️ 正在让 {VOICE} 录制中 (字数: {len(text)})...")
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(OUTPUT_FILE)
        
        print(f"✅ 录制完成！文件已保存为: {OUTPUT_FILE}")
        print("👉 快去播放听听效果！")
        
    except FileNotFoundError:
        print("❌ 找不到文件！请先运行 auto_content.py 生成文案。")

if __name__ == "__main__":
    asyncio.run(generate_audio())