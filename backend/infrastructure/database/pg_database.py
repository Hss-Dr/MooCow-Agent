"""
PostgreSQL数据库配置模块

使用SQLAlchemy ORM进行数据库操作
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# 从环境变量读取数据库连接字符串
DATABASE_URL = os.getenv("DATABASE_URL")

# 创建数据库引擎
engine = create_engine(DATABASE_URL)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建声明式基类
Base = declarative_base()


def get_db():
    """
    依赖注入：获取数据库会话

    使用方式：
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            # 使用db进行数据库操作
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库：创建所有表"""
    Base.metadata.create_all(bind=engine)
