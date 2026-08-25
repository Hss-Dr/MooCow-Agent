"""
JSONL文件处理工具

用于读写会话历史的JSONL格式文件
"""
from datetime import datetime
from pathlib import Path
import json
from typing import List, Dict, Optional


class JSONLHelper:
    """JSONL文件操作助手类"""

    @staticmethod
    def append_message(
        file_path: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """
        追加一条消息到JSONL文件

        Args:
            file_path: JSONL文件路径
            role: 消息角色（system/user/assistant）
            content: 消息内容
            metadata: 可选的元数据（如模型名、token数等）
        """
        # 确保目录存在
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        # 构建消息对象
        message = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "role": role,
            "content": content
        }
        if metadata:
            message["metadata"] = metadata

        # 追加写入JSONL文件
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(message, ensure_ascii=False) + '\n')

    @staticmethod
    def read_messages(
        file_path: str,
        max_messages: Optional[int] = None
    ) -> List[Dict]:
        """
        读取JSONL文件中的消息

        Args:
            file_path: JSONL文件路径
            max_messages: 最多返回的消息数（从末尾开始）

        Returns:
            List[Dict]: 消息列表
        """
        if not Path(file_path).exists():
            return []

        messages = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))

        # 如果指定了max_messages，返回最后N条
        if max_messages:
            return messages[-max_messages:]
        return messages

    @staticmethod
    def convert_to_openai_format(jsonl_messages: List[Dict]) -> List[Dict]:
        """
        转换JSONL消息为OpenAI格式

        Args:
            jsonl_messages: JSONL格式的消息列表

        Returns:
            List[Dict]: OpenAI格式的消息列表
        """
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in jsonl_messages
        ]

    @staticmethod
    def count_messages(file_path: str) -> int:
        """
        统计JSONL文件中的消息数量

        Args:
            file_path: JSONL文件路径

        Returns:
            int: 消息数量
        """
        if not Path(file_path).exists():
            return 0

        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    @staticmethod
    def get_last_message_time(file_path: str) -> Optional[datetime]:
        """
        获取JSONL文件中最后一条消息的时间

        Args:
            file_path: JSONL文件路径

        Returns:
            Optional[datetime]: 最后一条消息的时间，文件不存在则返回None
        """
        if not Path(file_path).exists():
            return None

        last_line = None
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    last_line = line

        if last_line:
            message = json.loads(last_line)
            timestamp_str = message.get("timestamp", "")
            if timestamp_str:
                # 解析ISO 8601格式时间
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        return None
