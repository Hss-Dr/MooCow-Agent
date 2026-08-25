from openai import OpenAI
from llama_index.core.data_structs import Node
from llama_index.core.schema import NodeWithScore
from llama_index.postprocessor.dashscope_rerank import DashScopeRerank
import numpy as np
import logging
import requests
from typing import List, Optional

import os
from dotenv import load_dotenv
load_dotenv()

def get_chat_completion_block(session_id, question, references):
    """
    结合知识库内容生成回答，并在回答中标注引用来源。

    :param question: 用户问题
    :param references: 知识库内容，格式为 [{"id": 1, "content": "..."}, ...]
    :return: 模型的回答
    """
    try:
        
        # 初始化 OpenAI 客户端
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL")
        )
        # 格式化参考内容
        formatted_references = "\n".join([f"[{ref['id']}] {ref['content']}" for ref in references])
    
        # 构造提示词
        
    
        # 调用模型生成回答
        completion = client.chat.completions.create(
            model="deepseek-r1",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
    
        return completion.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"

def rerank_similarity(query, texts):
    api_key = os.getenv("DASHSCOPE_API_KEY")
    # 创建节点列表
    nodes = [NodeWithScore(node=Node(text=text), score=1.0) for text in texts]

    # 初始化 DashScopeRerank
    dashscope_rerank = DashScopeRerank(top_n=len(texts), api_key=api_key)

    # 执行重排序
    results = dashscope_rerank.postprocess_nodes(nodes, query_str=query)

    # 提取分数
    scores = [res.score for res in results]
    scores = np.array(scores)

    # 返回分数和一个占位符
    return scores, None


def siliconflow_rerank(query: str, documents: List[str], top_n: int = 20) -> Optional[List[float]]:
    """
    SiliconFlow /v1/rerank(Cohere 兼容)语义精排。

    - 模型:env `RERANK_MODEL`(默认 `Pro/BAAI/bge-reranker-v2-m3`)
    - 端点:`{DASHSCOPE_BASE_URL}/rerank`(SiliconFlow 已迁移,DASHSCOPE_* 变量沿用旧名)
    - 返回:与 `documents` 等长的分数列表,按原文档位置对齐(不是按分数降序);
            失败(超时/HTTP错/JSON异常)返回 None,调用方自行降级到本地 hybrid_similarity。

    Args:
        query: 用户问题
        documents: 待精排文档文本列表(通常 20 条以内)
        top_n: 让 API 返回前 top_n 条的分数(未返回的位置补 0)
    """
    if not documents:
        return []
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL")
    model = os.getenv("RERANK_MODEL", "Pro/BAAI/bge-reranker-v2-m3")
    if not api_key or not base_url:
        logging.warning("SiliconFlow rerank 缺 DASHSCOPE_API_KEY/DASHSCOPE_BASE_URL,跳过并降级")
        return None
    top_n = min(top_n, len(documents))
    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/rerank",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
                "return_documents": False,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        # results 已按分数降序,但我们需要对齐到原 documents 索引 → scores[原index] = 分数
        scores = [0.0] * len(documents)
        for r in results:
            idx = r.get("index")
            score = r.get("relevance_score", 0.0)
            if idx is not None and 0 <= idx < len(documents):
                scores[idx] = float(score)
        return scores
    except Exception as e:
        logging.warning(f"SiliconFlow rerank 失败,降级到本地: {e}")
        return None




def generate_embedding(text: str | List[str], api_key: str = None, base_url: str = None, model_name: str = None, dimensions: int = 1024, encoding_format: str = "float", max_batch_size: int = 10):
    """
    生成文本的向量嵌入
    
    Args:
        text: 单个文本或文本列表
        api_key: API密钥
        base_url: API基础URL
        model_name: 模型名称
        dimensions: 向量维度
        encoding_format: 编码格式
        max_batch_size: 最大批量大小，默认为10（阿里云DashScope限制）
    
    Returns:
        单个文本时返回向量，文本列表时返回向量列表
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv("DASHSCOPE_BASE_URL")
    # embedding模型名从env读取，默认SiliconFlow的BAAI/bge-m3。
    # 注意：SiliconFlow的bge-m3不接受dimensions参数（原生1024维），传了会报400。
    if not model_name:
        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

    # 初始化 OpenAI 客户端
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    # 如果是单个文本，直接处理
    if isinstance(text, str):
        try:
            completion = client.embeddings.create(
                model=model_name,
                input=text,
                encoding_format=encoding_format
            )
            return completion.data[0].embedding
        except Exception as e:
            print(f"OpenAI API 请求失败: {e}")
            return None
    
    # 如果是文本列表，需要分批处理
    if isinstance(text, list):
        all_embeddings = []
        
        # 分批处理
        for i in range(0, len(text), max_batch_size):
            batch = text[i:i + max_batch_size]
            
            try:
                completion = client.embeddings.create(
                    model=model_name,
                    input=batch,
                    encoding_format=encoding_format
                )
                
                # 收集这一批的向量
                batch_embeddings = [item.embedding for item in completion.data]
                all_embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"OpenAI API 批量请求失败 (batch {i//max_batch_size + 1}): {e}")
                # 如果批量失败，为这一批添加空向量
                all_embeddings.extend([None] * len(batch))
        
        return all_embeddings


# 示例调用
if __name__ == "__main__":
    # 示例调用
    question = "法国的首都是哪里？"
    references = [
        {"id": 1, "content": "法国的首都是巴黎。"},
        {"id": 2, "content": "巴黎是欧洲的文化中心之一。"},
    ]
    session_id = "sd"
    
    response = get_chat_completion_block(session_id, question, references)
    print(response)