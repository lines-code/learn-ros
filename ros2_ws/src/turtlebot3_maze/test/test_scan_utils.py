import math
from types import SimpleNamespace

from turtlebot3_maze.scan_utils import clean_range, sector_min, summarize


def make_scan(values):
    """360개, 0° 부터 1° 간격 (TurtleBot3 burger 와 같은 배치)."""
    return SimpleNamespace(ranges=values, angle_min=0.0, angle_increment=math.radians(1.0),
                           range_min=0.12, range_max=3.5)


def test_clean_range():
    assert clean_range(math.inf, 0.12, 3.5) == 3.5   # 안 맞음 = 멀다
    assert clean_range(0.0, 0.12, 3.5) == 0.12       # 너무 가까움 → 가깝다고 본다 (보수적)
    assert clean_range(-math.inf, 0.12, 3.5) == 0.12
    assert clean_range(math.nan, 0.12, 3.5) is None
    assert clean_range(1.2, 0.12, 3.5) == 1.2


def test_sector_wraps_around_zero():
    values = [3.0] * 360
    values[355] = 0.5   # -5° (앞쪽 오른편)
    s = make_scan(values)
    assert sector_min(s.ranges, s.angle_min, s.angle_increment, 0.0, 10.0) == 0.5
    assert sector_min(s.ranges, s.angle_min, s.angle_increment, 90.0, 10.0) == 3.0


def test_summarize_directions():
    values = [math.inf] * 360
    values[0], values[90], values[180], values[270] = 0.4, 0.5, 0.6, 0.7
    d = summarize(make_scan(values), half_width_deg=5.0)
    assert d == {'front': 0.4, 'left': 0.5, 'back': 0.6, 'right': 0.7}


def test_too_close_sector_is_not_open():
    # 한 구간의 값이 모두 range_min 미만이어도 '열림(3.5m)' 이 아니라 가까움으로 나와야 한다
    values = [3.0] * 360
    for i in range(-10, 11):
        values[i % 360] = 0.05
    s = make_scan(values)
    assert sector_min(s.ranges, s.angle_min, s.angle_increment, 0.0, 10.0) == 0.12
