"""LiDAR(/scan) 전처리 — ROS 없이 테스트할 수 있는 순수 함수 모음.

TurtleBot3 burger LiDAR: 360개 거리값, 0° = 앞, 90° = 왼쪽, 180° = 뒤, 270°(-90°) = 오른쪽.
측정 범위 0.12 ~ 3.5m. 아무것도 안 맞으면 inf, 너무 가까우면 0 또는 range_min 미만이 온다.
"""
import math

# 방향 이름 → 중심 각도(도)
SECTORS = {'front': 0.0, 'left': 90.0, 'back': 180.0, 'right': -90.0}


def clean_range(r, range_min, range_max):
    """측정값 하나를 정리한다.

    +inf(안 맞음) → range_max, nan → None(버림),
    -inf·range_min 미만(너무 가까움) → range_min. 가까운 벽을 '멀다' 로 착각하지 않도록 보수적으로 본다.
    """
    if r is None or math.isnan(r):
        return None
    if r == math.inf:
        return range_max
    if r < range_min:
        return range_min
    return min(r, range_max)


def angle_diff_deg(a, b):
    """두 각도의 차이를 -180 ~ 180 도로."""
    return (a - b + 180.0) % 360.0 - 180.0


def sector_min(ranges, angle_min, angle_increment, center_deg, half_width_deg,
               range_min=0.12, range_max=3.5):
    """center_deg ± half_width_deg 구간의 최소 거리. 유효한 값이 없으면 range_max."""
    best = range_max
    for i, r in enumerate(ranges):
        ang = math.degrees(angle_min + i * angle_increment)
        if abs(angle_diff_deg(ang, center_deg)) > half_width_deg:
            continue
        v = clean_range(r, range_min, range_max)
        if v is not None and v < best:
            best = v
    return best


def summarize(scan, half_width_deg=15.0):
    """LaserScan 메시지 → {'front': m, 'left': m, 'back': m, 'right': m} (구간별 최소 거리)."""
    return {
        name: sector_min(scan.ranges, scan.angle_min, scan.angle_increment, center,
                         half_width_deg, scan.range_min, scan.range_max)
        for name, center in SECTORS.items()
    }
