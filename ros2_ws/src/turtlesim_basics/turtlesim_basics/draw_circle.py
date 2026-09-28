"""Step 2-2. Publisher: /turtle1/cmd_vel 에 Twist 를 주기적으로 발행해 원을 그린다."""
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class DrawCircle(Node):
    def __init__(self):
        super().__init__('draw_circle')
        # 파라미터로 속도를 바꿀 수 있다: --ros-args -p linear:=3.0 -p angular:=1.5
        self.declare_parameter('linear', 2.0)
        self.declare_parameter('angular', 1.0)
        self.pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        # turtlesim 은 cmd_vel 이 1초간 끊기면 멈추므로 계속 발행해야 한다
        self.create_timer(0.1, self.tick)

    def tick(self):
        msg = Twist()
        msg.linear.x = self.get_parameter('linear').value
        msg.angular.z = self.get_parameter('angular').value
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = DrawCircle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
