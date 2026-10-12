"""Step 3. 오른손 법칙 벽 따라가기 (규칙 기반 기준선).

오른쪽 벽과의 거리를 target_right 로 유지하며 전진한다 (비례 제어, P 제어).
  앞이 막힘         → 제자리 왼쪽 회전
  오른쪽이 뚫림     → 오른쪽으로 크게 돌며 전진 (오른손을 벽에서 떼지 않기)
  그 외             → 오차 × kp 만큼 조향
미로 밖으로 나가면(LiDAR 광선 대부분이 아무것도 맞지 않으면) 멈춘다.
odom 은 쓰지 않는다 — 회전할 때 바퀴가 미끄러져 위치가 크게 틀어지기 때문 (jev_navigator 설명 참고).
"""
import math

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from turtlebot3_maze.common import clamp, make_cmd
from turtlebot3_maze.scan_utils import sector_min


class WallFollower(Node):
    def __init__(self):
        super().__init__('wall_follower')
        p = self.declare_parameter
        p('target_right', 0.40)   # 오른쪽 벽과 유지할 거리 [m] (통로 폭 0.9m)
        p('front_stop', 0.40)     # 앞이 이보다 가까우면 왼쪽 회전 [m]
        p('right_open', 0.75)     # 오른쪽이 이보다 멀면 '뚫렸다' 로 판단 [m]
        p('linear_speed', 0.15)
        p('kp', 2.0)
        p('exit_open_ratio', 0.4)  # 2.5m 안에 아무것도 없는 광선 비율이 이보다 크면 '미로 밖'
        self.scan = None
        self.done = False
        self.t0 = None
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.create_timer(0.1, self.tick)

    def v(self, name):
        return self.get_parameter(name).value

    def on_scan(self, msg):
        self.scan = msg

    def tick(self):
        if self.done or self.scan is None:
            return
        if self.t0 is None:
            self.t0 = self.get_clock().now()
        s = self.scan
        free = sum(1 for r in s.ranges if r == math.inf or r > 2.5) / max(len(s.ranges), 1)
        if free > self.v('exit_open_ratio'):
            self.done = True
            self.pub.publish(make_cmd(self))
            secs = (self.get_clock().now() - self.t0).nanoseconds / 1e9
            self.get_logger().info(f'탈출 성공! 걸린 시간 {secs:.1f}초')
            return

        a = (s.angle_min, s.angle_increment)
        lim = (s.range_min, s.range_max)
        front = sector_min(s.ranges, *a, 0.0, 20.0, *lim)
        right = sector_min(s.ranges, *a, -90.0, 10.0, *lim)
        right_front = sector_min(s.ranges, *a, -45.0, 10.0, *lim)

        if front < self.v('front_stop'):
            cmd = make_cmd(self, 0.0, 0.8)                      # 막힘 → 왼쪽으로
        elif right > self.v('right_open') and right_front > self.v('right_open'):
            cmd = make_cmd(self, 0.10, -0.75)                   # 오른쪽 뚫림 → 오른쪽으로 돌기
        else:
            err = self.v('target_right') - min(right, right_front * 0.7071)
            cmd = make_cmd(self, self.v('linear_speed'), clamp(self.v('kp') * err, -0.8, 0.8))
        self.pub.publish(cmd)

    def stop(self):
        self.pub.publish(make_cmd(self))


def main():
    rclpy.init()
    node = WallFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
