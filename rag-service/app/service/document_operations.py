from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.message import KnowledgeBase
from service.core.rag.utils.es_conn import ESConnection
import os
import logging

logger = logging.getLogger(__name__)

def delete_document(user_id: str, file_name: str, db: Session) -> dict:
    """
    删除文档及其相关数据
    
    Args:
        user_id: 用户ID
        file_name: 文件名
        db: 数据库会话
        
    Returns:
        包含操作状态的字典
    """
    try:
        # 1. 从数据库中删除记录
        db_document = db.query(KnowledgeBase).filter(
            and_(
                KnowledgeBase.user_id == user_id,
                KnowledgeBase.file_name == file_name
            )
        ).first()
        
        if not db_document:
            return {"status": "error", "message": "Document not found"}
            
        # 获取 user_id 作为 ES 索引名（因为 KnowledgeBase 没有 session_id 字段）
        index_name = user_id
        
        # 2. 从 Elasticsearch 中删除数据
        es_connection = ESConnection()
        
        # 先搜索文档，查看实际存在的文档
        print(f"搜索索引 {index_name} 中的所有文档...")
        try:
            search_result = es_connection.es.search(
                index=index_name,
                body={
                    "query": {"match_all": {}},
                    "size": 100
                }
            )
            print(f"找到 {search_result['hits']['total']['value']} 个文档")
            
            # 打印前几个文档的关键字段
            for i, hit in enumerate(search_result['hits']['hits'][:3]):
                source = hit['_source']
                print(f"文档 {i+1}:")
                print(f"  docnm: {source.get('docnm', 'N/A')}")
                print(f"  docnm_kwd: {source.get('docnm_kwd', 'N/A')}")
                print(f"  kb_id: {source.get('kb_id', 'N/A')} (类型: {type(source.get('kb_id', 'N/A'))})")
                print(f"  doc_id: {source.get('doc_id', 'N/A')}")
                
        except Exception as e:
            print(f"搜索文档失败: {e}")
        
        # 检查字段映射
        try:
            mapping = es_connection.es.indices.get_mapping(index=index_name)
            print(f"索引映射信息: {mapping}")
        except Exception as e:
            print(f"获取映射失败: {e}")
        
        # 尝试删除文档，同时支持字符串和数字类型的 kb_id
        deleted_count = 0
        
        # 准备两种可能的 kb_id 值
        kb_id_candidates = [user_id]  # 字符串类型
        try:
            kb_id_int = int(user_id)
            if kb_id_int != user_id:  # 避免重复
                kb_id_candidates.append(kb_id_int)  # 数字类型
        except ValueError:
            pass
        
        print(f"尝试的 kb_id 候选值: {kb_id_candidates}")
        
        # 对每个 kb_id 候选值尝试删除
        for kb_id_candidate in kb_id_candidates:
            if deleted_count > 0:
                break  # 如果已经删除了文档，就不需要继续尝试
                
            print(f"尝试使用 kb_id={kb_id_candidate} (类型: {type(kb_id_candidate)}) 删除文档")
            
            # 尝试使用 match 查询而不是 term 查询
            try:
                delete_query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"docnm": file_name}},  # 使用 match 查询
                                {"term": {"kb_id": kb_id_candidate}}
                            ]
                        }
                    }
                }
                
                print(f"使用 match 查询删除: {delete_query}")
                
                response = es_connection.es.delete_by_query(
                    index=index_name,
                    body=delete_query,
                    refresh=True
                )
                
                deleted_count = response["deleted"]
                print(f"match 查询删除响应: {response}")
                
                if deleted_count > 0:
                    print(f"使用 match 查询成功删除 {deleted_count} 个文档")
                    break
                    
            except Exception as e:
                print(f"match 查询删除失败: {e}")
            
            # 如果 match 查询失败，回退到原来的 term 查询
            deleted_count = es_connection.delete(
                condition={
                    "docnm": file_name,
                    "kb_id": kb_id_candidate
                },
                indexName=index_name,
                knowledgebaseId=None
            )
            
            if deleted_count > 0:
                print(f"成功删除 {deleted_count} 个文档")
                break
        
        print(f"从 ES 中删除了 {deleted_count} 个文档")
        
        # 3. 删除本地文件（如果有文件路径字段的话）
        # 注意：KnowledgeBase 模型中没有 file_path 字段，我们需要构造文件路径
        # 假设文件存储在 storage/file/{user_id}/ 目录下
        file_path = f"storage/file/{user_id}/{file_name}"
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"删除本地文件: {file_path}")
            
        # 4. 从数据库中删除记录
        db.delete(db_document)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Successfully deleted {deleted_count} document(s) from ES and database"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting document: {str(e)}")
        return {"status": "error", "message": f"Failed to delete document: {str(e)}"} 