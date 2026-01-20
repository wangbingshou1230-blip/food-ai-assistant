import os
import sys

# === 导入库 ===
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

# ==========================================
# 🛑 这里的 Key 必须换成你刚才【第三步】新复制的！
# ==========================================
# 请把引号里的内容删掉，粘贴你的新 Key
PINECONE_API_KEY = "pcsk_2pmHMa_NwsLqRjFEfR3H3FiK3d9EqdvUw1Z42BxZCXg2E6Fz42M3GHBWW4jDNKgdkCJXoW" 

# Index 名字 (必须和网页上建立的一模一样)
INDEX_NAME = "food-standards"

# ==========================================
# 🛠️ 关键修复区 (之前报错就是因为少了这一行！)
# ==========================================
# 这一步强制把 Key 写入环境变量，修复 "Unauthorized" 错误
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

def main():
    print("🚀 启动：正在初始化行业大脑构建程序...")
    
    # 1. 检查 Key 是否填了
    if "请在这里粘贴" in PINECONE_API_KEY:
        print("\n❌ 错误：你还没有把 API Key 填进去！")
        print("👉 请打开代码第 15 行，把 PINECONE_API_KEY 的值改成你在官网复制的 Key。")
        return

    print(f"🔑 Key 已加载 (前5位: {PINECONE_API_KEY[:5]}...)")

    # 2. 检查文件夹
    if not os.path.exists("standards"):
        os.makedirs("standards")
        print("❌ 错误：找不到 'standards' 文件夹！已自动创建。")
        return

    # 3. 读取 PDF
    print("📂 第一步：读取 PDF 文件...")
    try:
        loader = DirectoryLoader("standards", glob="*.pdf", loader_cls=PyPDFLoader)
        docs = loader.load()
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return

    if len(docs) == 0:
        print("⚠️ standards 文件夹是空的！请放入 .pdf 文件。")
        return
    
    print(f"✅ 成功读取 {len(docs)} 页文档")

    # 4. 切分
    print("✂️ 第二步：切分文本...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    print(f"📄 生成 {len(splits)} 个切片")

    # 5. 加载模型
    print("🧠 第三步：加载 AI 模型 (sentence-transformers/all-MiniLM-L6-v2)...")
    try:
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return

    # 6. 上传
    print(f"☁️ 第四步：正在上传至 Pinecone (Index: {INDEX_NAME})...")
    
    try:
        PineconeVectorStore.from_documents(
            documents=splits,
            embedding=embeddings,
            index_name=INDEX_NAME
        )
        print("\n🎉🎉🎉 成功！所有数据已上传至 Pinecone！")
        print("✅ 行业大脑知识库构建完成。下一步：运行网页端提问。")
        
    except Exception as e:
        print(f"\n❌ 上传失败: {e}")
        print("-" * 40)
        print("🔍 排查指南：")
        print("1. 网页上 Index 的 Dimensions 必须是 384 (如果你建成了1024，必须删了重建)")
        print("2. API Key 是否粘贴正确？")

if __name__ == "__main__":
    main()