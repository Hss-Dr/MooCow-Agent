from sqlalchemy.orm import Session
from utils.database import get_db
import uuid
from datetime import datetime

class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: str):
        try:
            session_id = str(uuid.uuid4()).replace("-", "")[:16]
            start_time = datetime.now()

            # 插入会话记录
            self.db.execute(
                """
                INSERT INTO sessions (session_id, user_id, start_time)
                VALUES (:session_id, :user_id, :start_time)
                """,
                {"session_id": session_id, "user_id": user_id, "start_time": start_time}
            )
            self.db.commit()

            return {
                "session_id": session_id,
                "status": "success",
                "message": "Session created successfully"
            }
        except Exception as e:
            self.db.rollback()
            raise e

# 服务实例化
def get_session_service(db: Session = next(get_db())):
    return SessionService(db)