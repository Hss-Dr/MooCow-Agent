#!/usr/bin/env python3
"""
测试优化后的推荐问题生成功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

def test_simple_questions():
    """测试简化后的推荐问题生成"""
    try:
        from service.core.chat import generate_recommended_questions
        
        print("🧪 测试1: 纯问题扩展（无文档）")
        questions1 = generate_recommended_questions("什么是Python？")
        print(f"生成结果: {questions1}")
        
        print("\n🧪 测试2: 有文档上下文")
        mock_content = [
            {"document_name": "Python教程.pdf", "content_with_weight": "..."},
            {"document_name": "编程基础.docx", "content_with_weight": "..."}
        ]
        questions2 = generate_recommended_questions("什么是Python？", mock_content)
        print(f"生成结果: {questions2}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_questions()
    print(f"\n{'✅ 测试通过' if success else '❌ 测试失败'}") 