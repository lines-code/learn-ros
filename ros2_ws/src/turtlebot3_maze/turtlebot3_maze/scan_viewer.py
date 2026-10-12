"""Step 2-1. Subscriber: /scan 을 구독해 앞·좌·우·뒤 최소 거리를 1초마다 출력한다."""
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

from turtlebot3_maze.scan_utils import summarize


class ScanViewer(Node):
    def __init__(self):
        super().__init__('scan_viewer')
        self.dist = None
        # 센서 토픽은 'best effort' QoS 로 발행되므로 구독도 센서용 QoS 로 맞춘다
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_timer(1.0, self.report)

    def on_scan(self, msg: LaserScan):
        self.dist = summarize(msg)

    def report(self):
        if self.dist is None:
            self.get_logger().info('/scan 대기 중...')
            return
        d = self.dist
        self.get_logger().info(
            f"앞 {d['front']:.2f}m | 왼쪽 {d['left']:.2f}m | 오른쪽 {d['right']:.2f}m | 뒤 {d['back']:.2f}m")


def main():
    rclpy.init()
    node = ScanViewer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
