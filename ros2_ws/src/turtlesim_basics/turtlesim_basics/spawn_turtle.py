"""Step 3-1. Service Client: /spawn 을 호출해 새 거북이를 만든다.

사용: ros2 run turtlesim_basics spawn_turtle --ros-args -p x:=2.0 -p y:=8.0 -p name:=turtle2
"""
import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn


def main():
    rclpy.init()
    node = Node('spawn_turtle')
    node.declare_parameter('x', 2.0)
    node.declare_parameter('y', 2.0)
    node.declare_parameter('theta', 0.0)
    node.declare_parameter('name', '')  # 비우면 turtlesim 이 turtle2, turtle3... 로 자동 지정

    client = node.create_client(Spawn, '/spawn')
    # 서버(turtlesim_node)가 떠 있을 때까지 대기
    while not client.wait_for_service(timeout_sec=1.0):
        node.get_logger().info('/spawn 서비스 대기 중... (turtlesim_node 실행 확인)')

    req = Spawn.Request()
    req.x = node.get_parameter('x').value
    req.y = node.get_parameter('y').value
    req.theta = node.get_parameter('theta').value
    req.name = node.get_parameter('name').value

    # 비동기 호출 후 응답이 올 때까지 spin
    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future)

    # turtlesim 은 이름이 중복되면 예외 대신 빈 name 을 돌려준다
    name = future.result().name
    if name:
        node.get_logger().info(f'spawn 성공: {name}')
    else:
        node.get_logger().error('spawn 실패: 같은 이름의 거북이가 이미 있습니다')

    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
