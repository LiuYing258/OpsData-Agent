import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 定义相对路径常量
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_PATH = os.path.join(BASE_DIR, "data", "ops_manual.md")
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "rag", "faiss_index")

def get_vector_store():
    """
    获取或构建 FAISS 向量库。
    务实设计：优先读取本地持久化索引，避免每次启动重复消耗算力和时间。
    """
    # 选用轻量级本地模型，极其适合普通 PC 运行，无需调 API
    embeddings = HuggingFaceEmbeddings(model_name="shibing624/text2vec-base-chinese")
    
    # 1. 如果本地已经有索引缓存，直接加载
    if os.path.exists(FAISS_INDEX_PATH):
        print("[RAG] 正在加载本地 FAISS 索引缓存...")
        return FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    
    # 2. 如果没有缓存，则读取文件并构建
    print("[RAG] 未检测到本地索引，正在读取文档并构建 FAISS 向量库...")
    if not os.path.exists(DOC_PATH):
        raise FileNotFoundError(f"未找到知识库文件: {DOC_PATH}，请确保该文件存在。")

    loader = TextLoader(DOC_PATH, encoding="utf-8")
    docs = loader.load()

    # 务实切分：200 字符为一块，保留 20 字符重叠防止上下文断裂
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=20,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""]
    )
    splits = text_splitter.split_documents(docs)

    if not splits:
        raise ValueError("文档内容为空，切分失败！请检查 ops_manual.md 里是否有真实文字。")
    # 构建并保存到本地
    vector_store = FAISS.from_documents(splits, embeddings)
    vector_store.save_local(FAISS_INDEX_PATH)
    print("[RAG] FAISS 向量库构建并保存完成。")
    
    return vector_store

# 初始化全局向量库实例，使得工具调用时无需反复加载
try:
    vector_store = get_vector_store()
except Exception as e:
    print(f"[RAG 警告] 向量库初始化失败: {e}")
    vector_store = None

# ==========================================
# 向 Agent 暴露的查询工具
# ==========================================
class KnowledgeQuerySchema(BaseModel):
    query: str = Field(description="需要查询的具体问题或关键字，例如'数据库几点备份'")

@tool(args_schema=KnowledgeQuerySchema)
def query_knowledge_base(query: str) -> str:
    """
    【最高优先级：内部规范检索】
    当你需要回答关于公司内部规范、运维流程、端口号、备份策略等制度性问题时，必须调用此工具。
    绝对不要凭空捏造（幻觉）此类信息。
    """
    if not vector_store:
        return "❌ 检索失败：知识库尚未初始化或文件缺失。"
        
    try:
        # 检索最相关的 2 个片段
        retriever = vector_store.as_retriever(search_kwargs={"k": 2})
        docs = retriever.invoke(query)
        
        if not docs:
            return "知识库中未找到相关规范，请如实告知用户暂无此规定。"
            
        # 将片段组装成字符串返回给大模型作为 Observation
        result_text = "根据内部运维规范检索到以下内容：\n"
        for i, doc in enumerate(docs):
            result_text += f"[{i+1}] {doc.page_content}\n"
            
        return result_text
        
    except Exception as e:
        return f"❌ 检索知识库时发生未知错误: {str(e)}"