import requests
import json
import os

def create_chat_session(address, api_key, chat_id, name, user_id=None):
    """
    调用 Create session with chat assistant 接口创建聊天会话。

    :param address: 接口地址（不包含路径）
    :param api_key: API 密钥
    :param chat_id: 聊天助手的 ID
    :param name: 会话的名称
    :param user_id: 可选的用户 ID
    :return: 请求响应的 JSON 数据
    """
    url = f"http://{address}/api/v1/chats/{chat_id}/sessions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    body = {
        "name": name
    }
    if user_id:
        body["user_id"] = user_id
    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        response.raise_for_status()  # 检查请求是否成功
        return response.json()
    except requests.exceptions.RequestException as e:
        # 请求失败时返回错误信息
        return {
            "code": 500,
            "message": f"Request failed: {str(e)}"
        }

# 示例调用
if __name__ == "__main__":
    address = os.getenv("RAGFLOW_BASE_URL")
    api_key = "ragflow-Q4MTM2OTllZjJiMzExZWY5ODBhMDI0Mm"
    chat_id = "c4269168f2b411ef99fc0242ac130005"
    session_name = "new session 01"

    # 调用函数
    response = create_chat_session(address, api_key, chat_id, session_name)
    print(json.dumps(response, indent=4))