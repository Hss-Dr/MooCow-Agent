"""
数据库初始化脚本

创建所有表并初始化default_user
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 加载.env文件
env_path = backend_dir / ".env"
load_dotenv(env_path)

from infrastructure.database.pg_database import init_db, get_db
from models.user import User
from utils.password import hash_password
from config.settings import settings


def main():
    print("=" * 50)
    print("开始初始化数据库")
    print("=" * 50)

    # 1. 创建所有表
    print("\n1. 创建数据库表...")
    try:
        init_db()
        print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        return

    # 2. 创建default_user
    print("\n2. 创建default_user...")
    db = next(get_db())
    try:
        # 检查是否已存在
        existing_user = db.query(User).filter(User.username == "default_user").first()
        if existing_user:
            print(f"⚠️  default_user已存在 (ID: {existing_user.id})")
        else:
            # 创建新用户
            default_user = User(
                username="default_user",
                password_hash=hash_password(settings.DEFAULT_USER_PASSWORD)
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            print(f"✅ default_user创建成功 (ID: {default_user.id})")

    except Exception as e:
        print(f"❌ 创建default_user失败: {e}")
        db.rollback()
    finally:
        db.close()

    print("\n" + "=" * 50)
    print("数据库初始化完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
