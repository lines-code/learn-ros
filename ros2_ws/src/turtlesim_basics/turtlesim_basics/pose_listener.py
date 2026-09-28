"""Step 2-1. Subscriber: /turtle1/pose 를 구독해 거북이 위치를 출력한다."""
import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose


class PoseListener(Node):
    def __init__(self):
        super().__init__('pose_listener')
        # (메시지 타입, 토픽 이름, 콜백, QoS 큐 깊이)
        self.create_subscription(Pose, '/turtle1/pose', self.on_pose, 10)

    def on_pose(self, msg: Pose):
        # pose 는 약 60Hz 로 들어오므로 1초에 한 번만 출력
        self.get_logger().info(
            f'x={msg.x:.2f} y={msg.y:.2f} theta={msg.theta:.2f} '
            f'v={msg.linear_velocity:.2f} w={msg.angular_velocity:.2f}',
            throttle_duration_sec=1.0,
        )


def main():
    rclpy.init()
    node = PoseListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
