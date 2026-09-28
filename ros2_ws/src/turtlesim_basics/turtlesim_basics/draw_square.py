"""Step 3-2. 여러 서비스를 순서대로 호출: clear → set_pen → teleport_absolute 로 사각형을 그린다."""
import rclpy
from rclpy.node import Node
from std_srvs.srv import Empty
from turtlesim.srv import SetPen, TeleportAbsolute


class DrawSquare(Node):
    def __init__(self):
        super().__init__('draw_square')
        self.clear_cli = self.create_client(Empty, '/clear')
        self.pen_cli = self.create_client(SetPen, '/turtle1/set_pen')
        self.tp_cli = self.create_client(TeleportAbsolute, '/turtle1/teleport_absolute')
        for cli in (self.clear_cli, self.pen_cli, self.tp_cli):
            while not cli.wait_for_service(timeout_sec=1.0):
                self.get_logger().info(f'{cli.srv_name} 대기 중...')

    def call(self, client, req):
        """요청을 보내고 응답을 받을 때까지 기다리는 동기식 헬퍼."""
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def pen(self, r, g, b, width=3, off=False):
        self.call(self.pen_cli, SetPen.Request(r=r, g=g, b=b, width=width, off=int(off)))

    def teleport(self, x, y, theta=0.0):
        self.call(self.tp_cli, TeleportAbsolute.Request(x=x, y=y, theta=theta))

    def run(self):
        # 펜을 들고 시작점으로 이동 → 화면 지우기 → 펜을 내리고 꼭짓점을 차례로 이동
        self.pen(0, 0, 0, off=True)
        self.teleport(3.0, 3.0)
        self.call(self.clear_cli, Empty.Request())
        self.pen(255, 80, 80, width=4)
        for x, y in [(8.0, 3.0), (8.0, 8.0), (3.0, 8.0), (3.0, 3.0)]:
            self.teleport(x, y)
        self.get_logger().info('사각형 완료')


def main():
    rclpy.init()
    node = DrawSquare()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
