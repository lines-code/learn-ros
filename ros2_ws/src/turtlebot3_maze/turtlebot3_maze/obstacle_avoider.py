"""Step 2-2. Pub + Sub: 앞이 막히면 더 넓은 쪽으로 돌고, 아니면 직진한다.

1차수 wall_bounce(좌표로 벽 판단)를 LiDAR 거리로 바꾼 버전.
"""
import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from turtlebot3_maze.common import make_cmd
from turtlebot3_maze.scan_utils import sector_min


class ObstacleAvoider(Node):
    def __init__(self):
        super().__init__('obstacle_avoider')
        self.declare_parameter('safe_distance', 0.4)   # 앞이 이보다 가까우면 회전 [m]
        self.declare_parameter('linear_speed', 0.15)   # burger 최대 0.22 m/s
        self.declare_parameter('angular_speed', 0.8)
        self.scan = None
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.create_timer(0.1, self.tick)

    def on_scan(self, msg: LaserScan):
        self.scan = msg

    def tick(self):
        if self.scan is None:
            return
        s = self.scan
        args = (s.angle_min, s.angle_increment)
        lim = (s.range_min, s.range_max)
        front = sector_min(s.ranges, *args, 0.0, 30.0, *lim)    # 앞 ±30°
        left = sector_min(s.ranges, *args, 60.0, 30.0, *lim)    # 왼쪽 앞 30~90°
        right = sector_min(s.ranges, *args, -60.0, 30.0, *lim)  # 오른쪽 앞 -30~-90°

        safe = self.get_parameter('safe_distance').value
        if front < safe:
            turn = 1.0 if left >= right else -1.0  # 넓은 쪽으로 제자리 회전
            cmd = make_cmd(self, 0.0, turn * self.get_parameter('angular_speed').value)
        else:
            cmd = make_cmd(self, self.get_parameter('linear_speed').value, 0.0)
        self.pub.publish(cmd)

    def stop(self):
        self.pub.publish(make_cmd(self))


def main():
    rclpy.init()
    node = ObstacleAvoider()
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
