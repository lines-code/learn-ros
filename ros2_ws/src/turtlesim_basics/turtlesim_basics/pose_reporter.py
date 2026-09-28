"""Step 3-3. Service Server: /report_pose (std_srvs/Trigger) 요청이 오면 현재 거북이 위치를 응답한다.

호출: ros2 service call /report_pose std_srvs/srv/Trigger
"""
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from turtlesim.msg import Pose


class PoseReporter(Node):
    def __init__(self):
        super().__init__('pose_reporter')
        self.pose = None
        self.create_subscription(Pose, '/turtle1/pose', self.on_pose, 10)
        # (서비스 타입, 서비스 이름, 콜백)
        self.create_service(Trigger, '/report_pose', self.on_request)
        self.get_logger().info('/report_pose 서비스 준비 완료')

    def on_pose(self, msg: Pose):
        self.pose = msg

    def on_request(self, request: Trigger.Request, response: Trigger.Response):
        if self.pose is None:
            response.success = False
            response.message = '아직 pose 를 받지 못했습니다'
        else:
            p = self.pose
            response.success = True
            response.message = f'x={p.x:.2f}, y={p.y:.2f}, theta={p.theta:.2f}'
        self.get_logger().info(f'요청 처리: {response.message}')
        return response


def main():
    rclpy.init()
    node = PoseReporter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
