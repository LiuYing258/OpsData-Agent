import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.tools import tool

DB_PATH = "data/faiss_index"
DOC_PATH = "data/knowledge_base.md"

def init_vector_store():
    """Initialize or load the FAISS vector store."""
    # 使用轻量级开源中文模型进行本地向量化
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    if os.path.exists(DB_PATH):
        return FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
        
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DOC_PATH):
        # 初始化一份模拟的运维安全规范文档
        with open(DOC_PATH, "w", encoding="utf-8") as f:
            f.write(
                "# 内部服务器操作规范\n"
                "1. 数据库备份周期为每天凌晨2点。\n"
                "2. 严禁在生产环境执行未经审批的 DROP 或 TRUNCATE 操作。\n"
                "3. 生产服务器默认 SSH 端口已修改为 22022，禁止使用 root 直接登录。\n"
                "4. 遇到服务器 CPU 占用超 90% 时，优先使用 top 命令排查，并立刻向运维主管汇报。"
            )
            
    loader = TextLoader(DOC_PATH, encoding="utf-8")
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    splits = text_splitter.split_documents(docs)
    
    vector_store = FAISS.from_documents(splits, embeddings)
    vector_store.save_local(DB_PATH)
    return vector_store

@tool
def query_knowledge_base(query: str) -> str:
    """
    【最高优先级：内部规范与知识库检索】
    当你被问到公司内部的“规定”、“规范”、“默认配置”、“要求”，或者诸如“应该什么时间备份”、“默认端口是多少”等制度性问题时，
    忽略执行系统命令或查询业务数据库！必须**优先调用**此工具去检索操作手册！
    输入参数 query 应为具体的检索关键词（如“SSH端口”、“数据库备份”）。
    """
    try:
        vector_store = init_vector_store()
        docs = vector_store.similarity_search(query, k=2)
        if not docs:
            return "知识库中未找到相关内容。"
        
        res = "\n".join([doc.page_content for doc in docs])
        return f"检索结果:\n{res}"
    except Exception as e:
        return f"检索失败: {str(e)}"