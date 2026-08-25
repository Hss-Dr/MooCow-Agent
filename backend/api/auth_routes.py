"""
认证API路由

提供用户注册、登录、登出、获取当前用户信息等接口
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from services.auth_service import register_user, authenticate, access_security, get_current_user_id
from infrastructure.database.pg_database import get_db
from fastapi_jwt import JwtAuthorizationCredentials
import logging

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


# ========== 请求/响应模型 ==========

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    user_id: int
    username: str


# ========== API端点 ==========

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: DBSession = Depends(get_db)):
    """
    用户注册

    - **username**: 用户名（唯一）
    - **password**: 密码
    """
    try:
        register_user(request.username, request.password, db)
        logger.info(f"用户注册成功: {request.username}")
        return {"message": "注册成功"}
    except ValueError as e:
        logger.warning(f"注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"注册异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: DBSession = Depends(get_db)):
    """
    用户登录

    - **username**: 用户名
    - **password**: 密码

    返回JWT token，前端需保存并在后续请求中携带
    """
    try:
        token = authenticate(request.username, request.password, db)
        logger.info(f"用户登录成功: {request.username}")
        return {"access_token": token, "token_type": "bearer"}
    except ValueError as e:
        logger.warning(f"登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"登录异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """
    用户登出

    前端需要删除本地存储的token
    """
    return {"message": "登出成功"}


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user(
    credentials: JwtAuthorizationCredentials = Depends(access_security),
    db: DBSession = Depends(get_db)
):
    """
    获取当前用户信息

    需要携带有效的JWT token
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = credentials.subject["user_id"]
    username = credentials.subject["username"]

    return {"user_id": user_id, "username": username}
