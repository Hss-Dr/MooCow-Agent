from infrastructure.database.database_pool import pool
import json
import stun
from pymysql.cursors import DictCursor
from agents import function_tool
from infrastructure.tools.mcp.mcp_servers import baidu_mcp_client
from infrastructure.logging.logger import logger
import math


def bd09mc_to_bd09(lng: float, lat: float) -> tuple[float, float]:
    """
    [工具函数] 百度墨卡托坐标 (BD09MC) 转 百度经纬度 (BD09)
    百度地图 IP 定位 API 返回的是墨卡托坐标，导航 API 需要经纬度，因此必须转换。
    来源：https://github.com/wandergis/coordTransform_py/blob/master/coordTransform_utils.py
    """
    x = lng
    y = lat

    # 1. 简单校验：如果坐标值过小，视为无效坐标（通常在中国境外或解析错误）
    if abs(y) < 1e-6 or abs(x) < 1e-6:
        return (0.0, 0.0)

    # 2. 核心算法：墨卡托平面坐标转球面经纬度
    lng = x / 20037508.34 * 180
    lat = y / 20037508.34 * 180
    lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)

    return (lng, lat)


def get_ip_via_stun():
    """
        [辅助函数] 获取本机公网 IP
        注意：在服务器部署时，这获取的是服务器机房 IP。
        如果要获取终端用户 IP，建议使用 ContextVars 从 HTTP Header 中透传。
        真正开发期间--->前端请求的时候携带过来---->FastAPI的request携带过来---注入到工具中，工具使用。
    """

    try:
        # 默认使用公用的 STUN 服务器
        nat_type, external_ip, external_port = stun.get_ip_info()
        return external_ip
    except Exception as e:
        print(f"STUN 获取失败: {e}")
        return None
#  从昌平区温都水城到海淀区清华大学（起点明确）--->地址解析得到经纬度
#  我准备去清华大学（起点模糊问题）---->ip找经纬度
#  离我最近的新能源汽车服务站有哪些----？流程:1.先调用resolve_user_location_from_text工具（用户当前的经纬度）---->2.query_nearest_repair_shops_by_coords(用户当前的经纬度)---->最近的服务返回出来

@function_tool
async def resolve_user_location_from_text(
        user_input: str,
) -> str:
    """
    智能解析用户当前位置（起点），用于导航或新能源汽车服务站查询。
    ⚠️ 注意：
    - 仅用于获取**起点**，不可作为终点使用。

    Args:
        user_input (str): 用户提到的**明确地名**。⚠️重要：如果用户只说了”附近”、”这里”、”我的位置”等相对方位词，请**留空**此参数（传空字符串），不要填入这些词。

    返回 JSON 字符串：
    {
        "ok": bool,
        "lat": float,
        "lng": float,
        "source": "geocode" | "ip" | "fallback",
        "original_input": str,
        "error": str?  # 仅当 ok=False 时存在
    }
    """

    # 1. 相对位置词黑名单 ---
    # LLM 有时会提取出 "附近" 作为参数，但这会导致 Geocode 返回无意义坐标（如城市中心）。
    # 定义这个黑名单，强制这些词触发 IP 定位逻辑。
    RELATIVE_LOCATIONS = {
        "附近", "这", "这里", "这儿", "周围", "周边",
        "我的位置", "当前位置", "所在位置", "nearby", "here"
    }

    user_input = user_input.strip() if user_input else ""

    # 2. 如果输入的是相对词，视为无效输入，清空它以便触发后续 IP 逻辑
    if user_input in RELATIVE_LOCATIONS:
        logger.info(f"[Location] Detected relative term '{user_input}', forcing IP location fallback.")
        user_input = ""

    # 3.  尝试 Geocode（明确地名解）
    if user_input:
        try:
            logger.debug(f"[Location] Trying geocode for: '{user_input}'")

            # 3.1 调用MCP工具 百度地理编码
            geo_result = await baidu_mcp_client.call_tool(tool_name="map_geocode", arguments={"address": user_input})

            # 3.2 MCP 返回的复杂结构
            text = geo_result.content[0].text
            text = json.loads(text)
            result = text['result']

            # 3.3  校验返回数据的完整性
            if isinstance(result, dict) and "lat" in result['location'] and "lng" in result['location']:
                lat = float(result['location']['lat'])
                lng = float(result['location']['lng'])
                logger.info(f"[Location] Geocode success: '{user_input}' → ({lat}, {lng})")
                return json.dumps({
                    "ok": True,
                    "lat": lat,
                    "lng": lng,
                    "source": "geocode"
                }, ensure_ascii=False)
            else:
                logger.warning(f"[Location] Geocode returned invalid result: {geo_result}")
        except Exception as e:
            # 3.4 如果 Geocode 报错，不抛出异常，而是吞掉错误继续向下走 IP 逻辑
            logger.warning(f"[Location] Geocode failed for '{user_input}': {e}")

    #  获取 IP (注意：此处目前是获取运行环境对外的公网IP，生产环境建议改为前端获取传参注入)
    user_ip = get_ip_via_stun()

    # 4. 尝试 IP 定位
    if user_ip and user_ip not in ("127.0.0.1", "localhost", "::1"):
        try:
            logger.debug(f"[Location] Trying IP location for: {user_ip}")

            # 4.1 调用 MCP 工具：百度 IP 定位
            ip_result = await baidu_mcp_client.call_tool("map_ip_location", {"ip": user_ip})

            # 4.2 解析 MCP 返回的 TextContent
            text = ip_result.content[0].text
            data = json.loads(text)

            # 4.3 检查状态
            if data.get("status") != 0:
                logger.warning(f"[Location] IP location API error: {data.get('message', 'unknown')}")
                raise ValueError("IP location API returned non-zero status")

            point = data.get("content", {}).get("point", {})
            x_str = point.get("x")
            y_str = point.get("y")

            if not x_str or not y_str:
                logger.warning(f"[Location] Missing x/y in IP location result: {data}")
                raise ValueError("Missing x/y coordinates")

            # 4.4 坐标转换
            # 百度 IP API 返回的是 墨卡托坐标 (Mercator)，后续的维修站查询和导航使用的是 经纬度坐标 (Lat/Lng)，必须转换。
            x = float(x_str)
            y = float(y_str)

            lng, lat = bd09mc_to_bd09(x, y)  # 注意顺序：返回 (lng, lat)

            logger.info(f"[Location] IP location success: {user_ip} → ({lat:.6f}, {lng:.6f})")
            return json.dumps({
                "ok": True,
                "lat": lat,
                "lng": lng,
                "source": "ip"
            }, ensure_ascii=False)

        except Exception as e:
            logger.warning(f"[Location] IP location failed for {user_ip}: {e}")

    #  5. 兜底
    # 防止整个流程失败导致 Agent 崩溃，返回一个默认坐标（通常是北京天安门）
    fallback_lat, fallback_lng = 39.9042, 116.4074
    logger.info("[Location] Using fallback coordinates (Beijing)")

    return json.dumps({
        "ok": False,
        "error": "无法解析用户位置，使用默认坐标",
        "lat": fallback_lat,
        "lng": fallback_lng,
        "source": "fallback"
    }, ensure_ascii=False)


@function_tool
def query_nearest_repair_shops_by_coords(lat: float, lng: float, limit: int = 3) -> str:
    """
    根据给定的经纬度坐标，查询数据库中最近的新能源汽车服务站/充电站。

    Args:
        lat (float): 纬度 (BD09LL)
        lng (float): 经度 (BD09LL)
        limit (int): 返回结果数量限制，默认为 3

    Returns:
        str: JSON 格式的查询结果，包含最近的新能源汽车服务站列表。
    """
    connection = None
    cursor = None
    try:
        connection = pool.connection()
        cursor = connection.cursor(DictCursor)

        # 1. Haversine 距离计算公式
        # 6371 是地球平均半径 (km)
        # acos/cos/sin/radians 是三角函数
        # 作用：给定两点坐标代入球面几何公式，算出它们在地球表面的直线距离（公里），并以此作为 distance_km 字段返回
        # 6371 把计算出来的“弧度角度”转化为实际的“地面距离”
        # radians()：经纬度通常是 角度 (Degrees) 三角函数必须使用 弧度 (Radians)

        sql = """
        SELECT
            id,
            service_station_name,
            province,
            city,
            district,
            address,
            phone,
            manager,
            manager_phone,
            opening_hours,
            repair_types,
            repair_specialties,
            repair_services,
            supported_brands,
            rating,
            established_year,
            employee_count,
            service_station_description,
            latitude,
            longitude,
            (
                6371 * acos(
                    cos(radians(%s)) *
                    cos(radians(latitude)) *
                    cos(radians(longitude) - radians(%s)) +
                    sin(radians(%s)) *
                    sin(radians(latitude))
                )
            ) AS distance_km
        FROM repair_shops
        WHERE 
            latitude IS NOT NULL 
            AND longitude IS NOT NULL
            AND ABS(latitude) <= 90
            AND ABS(longitude) <= 180
        ORDER BY distance_km ASC
        LIMIT %s
        """

        # 2. 执行SQL (lat, lng, lat (起点纬度 起点经度 起点纬度))
        cursor.execute(sql, (lat, lng, lat, limit))
        rows = cursor.fetchall()

        logger.info(f"[NearestShops] Found {len(rows)} shops near ({lat}, {lng})")

        return json.dumps({
            "ok": True,
            "count": len(rows),
            "data": rows,
            "query": {
                "lat": lat,
                "lng": lng,
                "limit": limit
            }
        }, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"[NearestShops] DB query failed: {e}", exc_info=True)
        return json.dumps({
            "ok": False,
            "error": f"数据库查询失败: {str(e)}",
            "query": {"lat": lat, "lng": lng, "limit": limit}
        }, ensure_ascii=False)
    finally:
        # 必须确保归还连接到连接池，否则会导致连接耗尽
        if cursor:
            cursor.close()
        if connection:
            connection.close()
