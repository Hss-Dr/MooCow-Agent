from enum import Enum
from typing import Optional, Union, List, Literal
from pydantic import BaseModel, Field


class ContentKind(str, Enum):
    """
    内容语义分类：用于前端区分 UI 渲染逻辑。
    """
    THINKING = 'THINKING'  # 思考/推理内容 (渲染在折叠区域)
    PROCESS = 'PROCESS'    # 系统流程/工具调用 (渲染在折叠区域)
    ANSWER = 'ANSWER'      # 最终回答 (渲染在主聊天气泡)
    REFERENCE = 'REFERENCE'  # 参考文档来源 (渲染在回答下方的来源标记)


class StreamStatus(str, Enum):
    """
    流状态：控制 SSE 连接的生命周期。
    """
    IN_PROGRESS = 'IN_PROGRESS'  # 流传输中
    FINISHED = 'FINISHED'        # 传输结束


class StopReason(str, Enum):
    """
    结束原因：仅当状态为 FINISHED 时有效。
    """
    NORMAL = 'NORMAL'          # 正常结束
    MAX_TOKENS = 'MAX_TOKENS'  # 达到长度限制
    ERROR = 'ERROR'            # 异常结束


# --- 消息体定义 ---

class MessageBody(BaseModel):
    """消息体基类"""
    contentType: str


class TextMessageBody(MessageBody):
    """
    文本消息体：承载具体的流式内容。
    """
    contentType: Literal['sagegpt/text'] = 'sagegpt/text'
    text: str = Field(default='', description="实际文本内容")
    kind: ContentKind = Field(..., description="内容分类：THINKING/PROCESS/ANSWER")


class FinishMessageBody(MessageBody):
    """
    结束信号体：不包含内容，仅作为结束标志。
    """
    contentType: Literal['sagegpt/finish'] = 'sagegpt/finish'


# --- 顶层数据包定义 ---

class PacketMeta(BaseModel):
    """数据包元数据"""
    createTime: str
    finishReason: Optional[StopReason] = None
    errorMessage: Optional[str] = None


class StreamPacket(BaseModel):
    """
    SSE 流数据包 (原 MessageResponse)。
    这是后端 yield 给前端的最小数据单元。
    """
    id: str
    content: Union[TextMessageBody, FinishMessageBody]
    status: StreamStatus
    metadata: PacketMeta