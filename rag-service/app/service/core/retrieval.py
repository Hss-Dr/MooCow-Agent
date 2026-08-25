
from service.core.rag.nlp.search_v2 import Dealer
from service.core.rag.utils.es_conn import ESConnection

import json
# 创建 ElasticsearchConnection 实例
es_connection = ESConnection()

# 创建 Dealer 实例
dealer = Dealer(dataStore=es_connection)


def retrieve_content(indexNames: str, question: str):

    # 执行搜索
    # rerank_mdl="siliconflow" 触发 rerank_by_model 走 SiliconFlow /v1/rerank(默认
    # Pro/BAAI/bge-reranker-v2-m3)对 RRF 粗排后的 top 20 做语义精排;若 API 失败
    # 会自动降级到本地 hybrid_similarity(0.4×词项+0.6×余弦),检索不中断。
    results = dealer.retrieval(question = question,
                               embd_mdl = None,
                               tenant_ids = indexNames,
                               kb_ids = None,
                               vector_similarity_weight=0.6,
                               page = 1,
                               page_size = 5,
                               rerank_mdl = "siliconflow"
    )

    # 提取 chunks 中的信息
    extracted_data = []


    for i, chunk in enumerate(results['chunks'], start=1):
        content_with_weight = chunk.get('content_with_weight', 'N/A')
        # similarity = chunk.get('similarity', 'N/A')
        # vector_similarity = chunk.get('vector_similarity', 'N/A')
        # term_similarity = chunk.get('term_similarity', 'N/A')
        doc_id = chunk.get('doc_id', 'N/A')
        docnm = chunk.get('docnm_kwd', 'N/A')
        docnm = docnm.split("/")[-1]

        message = {
            "id": i,
            "document_id": doc_id,
            "document_name": docnm,
            'content_with_weight': content_with_weight,
        }
        
        extracted_data.append(message)

    return extracted_data


if __name__ == '__main__':
    res = retrieve_content(question="世运电路成长性如何", indexNames="test01")
    print(res)
    
    # 将提取的数据写入到文件
    # with open("output.txt", "w", encoding="utf-8") as file:
    #     for data in extracted_data:
    #         file.write(f"content_with_weight: {data['content_with_weight']}\n")
    #         file.write(f"similarity: {data['similarity']}\n")
    #         file.write(f"vector_similarity: {data['vector_similarity']}\n")
    #         file.write(f"term_similarity: {data['term_similarity']}\n")
    #         file.write("\n")
    
    # print("结果已写入到 output.txt 文件中")