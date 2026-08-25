import xxhash
import datetime
from service.core.rag.app.naive import chunk
from service.core.rag.utils.es_conn import ESConnection
from service.core.rag.nlp.model import generate_embedding
from typing import List, Dict, Any
import numpy as np

def dummy(prog=None, msg=""):
    pass

def parse(file_path):
    # 使用自定义的 PDF 解析器
    result = chunk(file_path, callback=dummy)
    return result

def batch_generate_embeddings(texts: List[str], batch_size: int = 10) -> List[List[float]]:
    """
    批量生成文本的向量嵌入
    
    Args:
        texts: 文本列表
        batch_size: 批处理大小（阿里云DashScope限制为10）
    
    Returns:
        向量列表
    """
    try:
        # 直接使用批量处理功能
        embeddings = generate_embedding(texts)
        return embeddings if embeddings is not None else []
    except Exception as e:
        print(f"批量生成向量失败: {e}")
        return []

def process_items(items: List[Dict[str, Any]], file_name: str, index_name: str) -> List[Dict[str, Any]]:
    """
    批量处理数据项
    
    Args:
        items: 数据项列表
        file_name: 文件名
        index_name: ES索引名称
    
    Returns:
        处理后的数据项列表
    """
    try:
        # 准备批量处理的数据
        texts = [item["content_with_weight"] for item in items]
        # 批量生成向量
        embeddings = batch_generate_embeddings(texts)
        
        # 处理每个数据项
        results = []
        for item, embedding in zip(items, embeddings):
            # 生成 chunk_id
            chunck_id = xxhash.xxh64((item["content_with_weight"] + index_name).encode("utf-8")).hexdigest()

            # 构建数据字典
            d = {
                "id": chunck_id,
                "content_ltks": item["content_ltks"],
                "content_with_weight": item["content_with_weight"],
                "content_sm_ltks": item["content_sm_ltks"],
                "important_kwd": [],
                "important_tks": [],
                "question_kwd": [],
                "question_tks": [],
                "create_time": str(datetime.datetime.now()).replace("T", " ")[:19],
                "create_timestamp_flt": datetime.datetime.now().timestamp()
            }

            d["kb_id"] = index_name
            d["docnm_kwd"] = item["docnm_kwd"]
            d["title_tks"] = item["title_tks"]
            d["doc_id"] = xxhash.xxh64(file_name.encode("utf-8")).hexdigest()
            d["docnm"] = file_name
            
            # 将嵌入向量存储到字典中
            d[f"q_{len(embedding)}_vec"] = embedding
            
# content_ltks: item["content_ltks"]
# 含义：文本内容的粗粒度分词结果
# 处理：使用RAG分词器进行基础分词
# 示例：["人工智能", "是", "一门", "新兴", "技术"]
# content_with_weight: item["content_with_weight"]
# 含义：原始文本内容（带权重信息）
# 作用：保存完整的文本内容，用于显示和检索
# 示例："人工智能是一门新兴技术，在各个领域都有广泛应用。"
# content_sm_ltks: item["content_sm_ltks"]
# 含义：文本内容的细粒度分词结果
# 处理：更详细的分词，包含更多语义信息
# 示例：["人工", "智能", "是", "一门", "新兴", "的", "技术"]
# kb_id: index_name
# 含义：知识库标识符
# 作用：标识文档块属于哪个知识库
# 示例："tech_documents", "company_policies"
# docnm_kwd: item["docnm_kwd"]
# 含义：文档名称关键词
# 来源：从原始文件名提取的关键词
# 作用：用于基于文档名的检索
# title_tks: item["title_tks"]
# 含义：文档标题的分词结果
# 处理：去除文件扩展名后进行分词
# 示例：["人工智能", "技术", "报告"]
# docnm: file_name
# 含义：完整的文档文件名
# 作用：保存原始文件名，用于溯源和显示
# 示例："人工智能技术报告.pdf"

            results.append(d)

        return results

    except Exception as e:
        print(f"process_items error: {e}")
        return []

def execute_insert_process(file_path: str, file_name: str, index_name: str):
    """
    执行文档处理和插入 Elasticsearch 的函数
    
    Args:
        file_path: 文件路径
        file_name: 文件名
        index_name: ES索引名称
    """
    # 解析文档
    documents = parse(file_path)
    if not documents:
        print(f"No documents found in {file_path}")
        return

    # 批量处理文档
    processed_documents = process_items(documents, file_name, index_name)
    if not processed_documents:
        print(f"Failed to process documents from {file_path}")
        return

    # 批量插入 ES
    es_connection = ESConnection()
    errors = es_connection.insert(documents=processed_documents, indexName=index_name)
    # insert() 返回非空表示 bulk 中有失败项;向上抛出,避免"ES 未写入但 PG 仍记录"的不一致
    if errors:
        raise RuntimeError(f"Failed to insert documents into ES (index={index_name}): {errors}")
    print(f"Successfully inserted {len(processed_documents)} documents into ES")

# 测试代码
if __name__ == "__main__":
    file_path = "/mnt/d/wsl/project/gsk-poc/storage/file/【兴证电子】世运电路2023中报点评.pdf"
    session_id = "40e2743ccffa4207"
    output_file = "/mnt/d/wsl/project/gsk-poc/storage/output/result.json"

    # 如果本地文件不存在，则解析文件并保存结果
    if not os.path.exists(output_file):
        documents = parse(file_path)
        
        # 批量处理文档
        result = process_items(documents, file_path, session_id)

        # 将结果保存到本地文件
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"结果已保存到本地文件: {output_file}")
    else:
        # 如果本地文件存在，则从文件中读取结果
        with open(output_file, "r", encoding="utf-8") as f:
            result = json.load(f)
        print(f"从本地文件加载结果: {output_file}")

    # 创建 ESConnection 的实例并插入数据
    es_connection = ESConnection()
    es_connection.insert(documents=result, indexName="世运电路2023中报点评")

