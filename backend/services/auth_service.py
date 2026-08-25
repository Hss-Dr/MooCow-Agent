"""
JWT认证服务

提供用户注册、登录、token生成等功能
"""
from fastapi import Depends
from fastapi_jwt import JwtAccessBearerCookie, JwtAuthorizationCredentials
from datetime import timedelta
from utils.password import hash_password, verify_password
from models.user import User
from infrastructure.database.pg_database import get_db
from config.settings import settings
from sqlalchemy.orm import Session as DBSession
import os
import secrets


# JWT配置（与RAG服务共享密钥）
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    raise RuntimeError('JWT_SECRET_KEY 未配置：请在 .env / 环境变量中设置')
JWT_SECRET_KEY = JWT_SECRET_KEY + 'happy'

# 配置JWT认证
access_security = JwtAccessBearerCookie(
    secret_key=JWT_SECRET_KEY,
    auto_error=False,  # 可选认证，兼容现有未认证流程
    access_expires_delta=timedelta(days=2)
)


def create_token(user_id: int, username: str) -> str:
    """
    生成JWT token

    Args:
        user_id: 用户ID
        username: 用户名

    Returns:
        str: JWT token
    """
    subject = {
        "user_id": user_id,
        "username": username,
        "salting": secrets.token_hex(16)
    }
    return access_security.create_access_token(subject=subject)


def register_user(username: str, password: str, db: DBSession) -> User:
    """
    注册新用户

    Args:
        username: 用户名
        password: 明文密码
        db: 数据库会话

    Returns:
        User: 创建的用户对象

    Raises:
        ValueError: 用户名已存在
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise ValueError("用户名已存在")

    # 创建新用户
    password_hash_value = hash_password(password)
    new_user = User(username=username, password_hash=password_hash_value)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def authenticate(username: str, password: str, db: DBSession) -> str:
    """
    认证用户并返回token

    Args:
        username: 用户名
        password: 明文密码
        db: 数据库会话

    Returns:
        str: JWT token

    Raises:
        ValueError: 用户名或密码错误
    """
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")

    return create_token(user.id, user.username)


def get_current_user_id(
    credentials: JwtAuthorizationCredentials = Depends(access_security),
    db: DBSession = Depends(get_db)
) -> int:
    """
    获取当前用户ID（支持可选认证）

    如果请求携带有效token，返回token中的user_id；
    否则返回default_user的ID（向后兼容）

    Args:
        credentials: JWT认证凭证
        db: 数据库会话

    Returns:
        int: 用户ID
    """
    if credentials:
        return credentials.subject["user_id"]

    # 未认证时，查找或创建default_user
    default_user = db.query(User).filter(User.username == "default_user").first()
    if not default_user:
        # 创建default_user（密码从.env的 DEFAULT_USER_PASSWORD 读取）
        default_user = User(
            username="default_user",
            password_hash=hash_password(settings.DEFAULT_USER_PASSWORD)
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)

    return default_user.id
