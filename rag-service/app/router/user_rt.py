from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from exceptions.auth import  AuthError
from service.auth import authenticate, register_user
from pydantic import BaseModel
import httpx
import asyncio

router = APIRouter()


# 定义登录请求体的 Pydantic 模型
class LoginRequest(BaseModel):
    username: str
    password: str

# 用户认证接口
@router.post("/login")
async def login(request: LoginRequest):
    try:
        # 调用 authenticate 函数进行认证
        token = authenticate(request.username, request.password)
        return {"access_token": token, "token_type": "bearer"}
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# 定义请求体的 Pydantic 模型
class RegisterRequest(BaseModel):
    username: str
    password: str

# 用户注册接口
@router.post("/register")
async def register(request: RegisterRequest):
    try:
        # 调用 register_user 函数进行注册
        register_user(request.username, request.password)
        return {"message": "User registered successfully"}
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# 定义 STS Token 请求体的 Pydantic 模型
class STSTokenRequest(BaseModel):
    appid: str
    accessKey: str

# STS Token 接口
@router.post("/sts-token")
async def get_sts_token(request: STSTokenRequest):
    try:
        # 构造请求头
        headers = {
            "Authorization": f"Bearer; {request.accessKey}",
            "Content-Type": "application/json"
        }
        
        # 构造请求体
        body = {
            "appid": request.appid,
            "duration": 300
        }
        
        # 调用 ByteDance STS Token API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openspeech.bytedance.com/api/v1/sts/token",
                headers=headers,
                json=body,
                timeout=30.0
            )
            
            # 返回原始响应
            return response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Request timeout when calling STS token API"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error calling STS token API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )