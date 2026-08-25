import pymysql
from dbutils.pooled_db import PooledDB
from config.settings import settings


class DatabasePool:
    """
    数据库连接池管理类

    使用 PooledDB 实现连接池模式，复用数据库连接，
    避免频繁创建和关闭连接带来的性能开销。
    """

    # 类变量，用于存储全局唯一的连接池实例 (单例模式)
    _pool = None

    @classmethod
    def get_pool(cls):
        """
        获取数据库连接池实例（惰性初始化）

        如果连接池尚未创建，则根据配置创建一个新的；
        如果已存在，直接返回现有实例。
        """
        if cls._pool is None:
            # 初始化连接池
            cls._pool = PooledDB(
                # 使用 pymysql 作为底层数据库驱动
                creator=pymysql,

                # 连接池允许的最大连接数，超过此数量的请求需等待
                maxconnections=settings.MYSQL_MAX_CONNECTIONS,

                # 数据库主机地址 (如 localhost)
                host=settings.MYSQL_HOST,

                # 数据库用户名
                user=settings.MYSQL_USER,

                # 数据库密码
                password=settings.MYSQL_PASSWORD,

                # 数据库端口 (通常是 3306)
                port=settings.MYSQL_PORT,

                # 数据库名称
                database=settings.MYSQL_DATABASE,

                # 字符集，推荐使用 utf8mb4 以支持 Emoji 等特殊字符
                charset=settings.MYSQL_CHARSET,

                # 连接超时时间 (秒)
                connect_timeout=settings.MYSQL_CONNECT_TIMEOUT

                # 可选参数补充说明：
                # mincached: 初始化时至少创建的空闲连接数 (默认为0)
                # maxcached: 连接池中允许闲置的最大连接数 (默认为0，代表不限制)
                # maxshared: 允许的最大共享连接数 (默认为0，代表所有连接均专有)
                # blocking: 连接池满了是否阻塞等待 (True) 还是报错 (False)，默认为 True
            )
        return cls._pool

    @classmethod
    def get_connection(cls):
        """
        从连接池中借用一个连接

        Returns:
            connection: 一个 pymysql 连接对象
        """
        # .connection() 方法会自动从池中取出一个可用连接
        return cls.get_pool().connection()


# 在模块导入时直接初始化连接池
# 这样在其他地方 import 这个 pool 对象时，直接就能使用
pool = DatabasePool.get_pool()