"""Step 2-3. Pub + Sub: pose 를 구독해 벽에 가까워지면 방향을 틀도록 cmd_vel 을 발행한다.

구독(입력) → 판단 → 발행(출력) 으로 이어지는 가장 단순한 제어 루프.
"""
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from turtlesim.msg import Pose

# turtlesim 화면 좌표는 대략 0 ~ 11.08
MIN_XY = 1.0
MAX_XY = 10.0


class WallBounce(Node):
    def __init__(self):
        super().__init__('wall_bounce')
        self.pose = None
        self.create_subscription(Pose, '/turtle1/pose', self.on_pose, 10)
        self.pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.create_timer(0.1, self.tick)

    def on_pose(self, msg: Pose):
        self.pose = msg

    def tick(self):
        if self.pose is None:
            return  # 아직 pose 를 한 번도 받지 못함
        p = self.pose
        near_wall = not (MIN_XY < p.x < MAX_XY and MIN_XY < p.y < MAX_XY)

        msg = Twist()
        if near_wall:
            msg.linear.x = 1.0
            msg.angular.z = 2.0  # 벽 근처: 천천히 가며 회전
        else:
            msg.linear.x = 2.0  # 직진
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = WallBounce()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
