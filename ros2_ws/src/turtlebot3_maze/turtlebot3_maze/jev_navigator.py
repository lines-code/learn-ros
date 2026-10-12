"""고도화. OpenJev 판단 + 규칙 기반 안전장치로 미로를 탈출하는 노드.

역할 분담 (Jev 호출 가이드 §7: OpenJev 에게 단독 결정권을 주지 않는다)
  규칙(이 노드)  : 칸 단위 이동, 회전, 충돌 정지, 열린 통로 판별(LiDAR), 두 번 간 통로 금지(트레모)
  OpenJev       : '안 가본 통로가 2개 이상인 갈림길' 에서만 어느 쪽으로 갈지 고른다 (/v1/decide)
  대안(fallback) : OpenJev 가 응답하지 않거나 열려 있지 않은 방향을 고르면 오른손 법칙

상태 흐름
  SETTLE(멈추고 새 LiDAR 기다림) → DECIDE → [ASKING(OpenJev 응답 대기)] → ROTATE → DRIVE → SETTLE ...
  미로 밖 칸에 도착하면 DONE.

위치 추정 (odom 을 그대로 믿지 않는다)
  Gazebo 의 TurtleBot3 는 제자리 회전 때 바퀴가 미끄러져 odom 의 yaw 가 실제보다 크게 틀어진다
  (실측: odom 179° / 실제 115°). 그래서
  - 방향(yaw)  : /imu
  - 이동 거리  : odom 위치 변화량의 크기 (방향과 무관)
  - 현재 칸    : 출발 칸에서 이동한 칸 수로 센다
  - 보정       : 옆 벽과의 거리로 통로 가운데 유지, 앞 벽이 보이면 벽까지 거리로 정지
"""
import json
import math
import threading
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu, LaserScan
from std_msgs.msg import String

from turtlebot3_maze import maze_logic as ml
from turtlebot3_maze.common import clamp, make_cmd, wrap, yaw_from_quaternion
from turtlebot3_maze.openjev_client import OpenJevClient, OpenJevError
from turtlebot3_maze.scan_utils import summarize


class JevNavigator(Node):
    def __init__(self):
        super().__init__('jev_navigator')
        p = self.declare_parameter
        p('use_openjev', True)                                   # False 면 오른손 법칙만
        p('openjev_url', 'http://host.docker.internal:31001')    # Docker OpenJev(CPU)
        p('openjev_timeout', 60.0)
        p('open_threshold', 0.8)     # 이보다 멀면 '열린 통로' [m] (칸 중심에서 벽까지 약 0.45m)
        p('linear_speed', 0.18)
        p('wall_center', 0.47)       # 칸 중심에 있을 때 LiDAR 로 잰 벽까지 거리 [m] (실측)
        p('start_x', -2.0)           # 로봇을 생성한 월드 좌표 → 출발 칸 계산에 사용
        p('start_y', -2.0)
        p('grid_size', 5)
        p('exit_col', 4)
        p('exit_row', 4)

        self.client = OpenJevClient(self.v('openjev_url'), self.v('openjev_timeout'))
        self.marks = ml.Marks()
        self.state = 'SETTLE'
        self.odom_xy = self.yaw = None
        self.cell = None               # 현재 칸 (이동한 칸 수로 센다)
        self.drive_from = None         # DRIVE 시작 때의 odom 위치
        self.aligned_ticks = 0         # 목표 방위 안에 연속으로 머문 횟수
        self.blocked_retries = 0       # 출발 방향이 막혀 다시 회전한 횟수
        self.dist = None
        self.scan_count = 0
        self.settle_until = 0          # 이 번호 이후의 scan 이 와야 판단한다
        self.target = None             # (칸, 방위)
        self.pending = None            # OpenJev 스레드 결과
        self.ask_ctx = None
        self.stats = {'moves': 0, 'decisions': 0, 'jev_calls': 0, 'jev_secs': 0.0,
                      'fallbacks': 0, 'path': []}
        self.t0 = None

        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.create_subscription(Imu, '/imu', self.on_imu, qos_profile_sensor_data)
        self.pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.decision_pub = self.create_publisher(String, '/jev/decision', 10)
        self.create_timer(0.05, self.tick)

        if self.v('use_openjev'):
            ok = self.client.health()
            self.get_logger().info(
                f"OpenJev {self.v('openjev_url')} → {'정상' if ok else '응답 없음 (오른손 법칙으로 대체)'}")

    def v(self, name):
        return self.get_parameter(name).value

    # ---------- 입력 ----------
    def on_scan(self, msg):
        self.dist = summarize(msg, half_width_deg=10.0)
        self.scan_count += 1

    def on_odom(self, msg):
        p = msg.pose.pose.position
        self.odom_xy = (p.x, p.y)

    def on_imu(self, msg):
        self.yaw = yaw_from_quaternion(msg.orientation)

    # ---------- 메인 루프 (20Hz) ----------
    def tick(self):
        if self.odom_xy is None or self.yaw is None or self.dist is None or self.state == 'DONE':
            return
        if self.t0 is None:
            self.t0 = time.monotonic()
            self.cell = ml.cell_of(self.v('start_x'), self.v('start_y'))
            self.settle_until = self.scan_count + 2
        getattr(self, f'do_{self.state.lower()}')()

    def do_settle(self):
        self.pub.publish(make_cmd(self))
        if self.scan_count >= self.settle_until:
            self.state = 'DECIDE'

    def do_decide(self):
        cell = self.cell
        n = self.v('grid_size')
        if not (0 <= cell[0] < n and 0 <= cell[1] < n):
            return self.finish(cell)

        heading = ml.nearest_heading(self.yaw)
        open_dirs = ml.open_directions(self.dist, heading, self.v('open_threshold'))
        opts = ml.candidates(open_dirs, cell, self.marks)
        self.stats['path'].append(cell)
        d = self.dist
        self.get_logger().info(
            f"{cell} 방향 {math.degrees(self.yaw):.0f}° | "
            f"앞 {d['front']:.2f} 왼 {d['left']:.2f} 오 {d['right']:.2f} 뒤 {d['back']:.2f} → 열림 {open_dirs}")
        if not opts:
            self.get_logger().error(f'{cell}: 갈 곳이 없습니다 (열린 방향 {open_dirs}) — 정지')
            return self.finish(cell)

        exits = [d for d in opts
                 if not (0 <= ml.neighbor(cell, d)[0] < n and 0 <= ml.neighbor(cell, d)[1] < n)]
        if exits:
            return self.commit(cell, heading, exits[0], 'rule:출구 보임', opts)
        if len(opts) == 1:
            return self.commit(cell, heading, opts[0], 'rule:외길' if opts[0] != ml.OPPOSITE[heading]
                               else 'rule:막다른 길 → 되돌아가기', opts)
        if not self.v('use_openjev'):
            return self.commit(cell, heading, ml.right_hand_choice(opts, heading), 'rule:오른손 법칙', opts)

        # 갈림길 → OpenJev 에 묻는다 (별도 스레드, 그동안 로봇은 정지)
        exit_cell = (self.v('exit_col'), self.v('exit_row'))
        body = ml.build_decide_request(cell, heading, opts, self.marks, exit_cell, n)
        self.ask_ctx = (cell, heading, opts, time.monotonic())
        self.pending = None
        self.state = 'ASKING'
        self.get_logger().info(f'{cell} 갈림길: 후보 {opts} → OpenJev 에 질문 중...')
        threading.Thread(target=self._ask, args=(body,), daemon=True).start()

    def _ask(self, body):
        try:
            self.pending = ('ok', self.client.decide(body))
        except Exception as e:  # noqa: BLE001 — 어떤 오류든 결과를 남겨야 ASKING 에서 빠져나온다
            self.pending = ('error', f'{type(e).__name__}: {e}')

    def do_asking(self):
        self.pub.publish(make_cmd(self))
        if self.pending is None:
            return
        cell, heading, opts, started = self.ask_ctx
        secs = time.monotonic() - started
        self.stats['jev_calls'] += 1
        self.stats['jev_secs'] += secs
        kind, payload = self.pending
        if kind == 'ok':
            choice, prob = ml.pick_from_probabilities(payload, opts)
            if choice is not None:
                probs = ', '.join(f'{k} {v:.2f}' for k, v in payload.items())
                return self.commit(cell, heading, choice, f'openjev:{prob:.2f} ({secs:.1f}s) [{probs}]', opts)
            reason = f'fallback:OpenJev 답이 후보 밖 {payload}'
        else:
            reason = f'fallback:OpenJev 오류 {payload[:80]}'
        self.stats['fallbacks'] += 1
        self.commit(cell, heading, ml.right_hand_choice(opts, heading), reason, opts)

    def commit(self, cell, heading, d, reason, opts):
        self.marks.add(cell, d)
        self.target = (ml.neighbor(cell, d), d)
        self.drive_from = self.odom_xy   # 회전 중에는 위치가 거의 변하지 않는다. 다시 회전해도 이동 거리는 이어서 센다
        self.blocked_retries = 0
        self.stats['decisions'] += 1
        self.state = 'ROTATE'
        rel = ml.abs_to_rel(heading, d)
        self.get_logger().info(f'{cell} → {ml.WORD[d]}({rel}) | 후보 {opts} | {reason}')
        self.decision_pub.publish(String(data=json.dumps({
            'cell': cell, 'heading': heading, 'options': opts, 'choice': d, 'reason': reason},
            ensure_ascii=False)))

    def do_rotate(self):
        err = wrap(ml.YAW[self.target[1]] - self.yaw)
        # 한 순간 맞았다고 끝내지 않는다. CPU 가 바쁘면(GUI 등) 제어가 늦어 지나쳐 버리므로
        # 목표 ±0.03rad 안에 0.25초(5 tick) 연속으로 머물러야 회전 완료로 본다.
        self.aligned_ticks = self.aligned_ticks + 1 if abs(err) < 0.03 else 0
        if self.aligned_ticks >= 5:
            self.aligned_ticks = 0
            self.state = 'DRIVE'
            self.pub.publish(make_cmd(self))
            return
        w = clamp(1.5 * err, -0.8, 0.8)
        if abs(err) >= 0.03 and abs(w) < 0.12:
            w = math.copysign(0.12, w)   # 너무 느리면 마찰 때문에 멈춘다
        elif abs(err) < 0.03:
            w = 0.0
        self.pub.publish(make_cmd(self, 0.0, w))

    def do_drive(self):
        cell, d = self.target
        d_now = self.dist
        moved = math.hypot(self.odom_xy[0] - self.drive_from[0], self.odom_xy[1] - self.drive_from[1])
        remaining = 1.0 - moved
        heading_err = wrap(ml.YAW[d] - self.yaw)
        if abs(heading_err) > 0.25:
            # 방향이 크게 틀어졌다 (밀림·지연) → 멈추고 다시 회전
            self.get_logger().warn(f'방향 오차 {math.degrees(heading_err):.0f}° — 다시 회전')
            self.state = 'ROTATE'
            self.pub.publish(make_cmd(self))
            return
        if moved < 0.3 and d_now['front'] < self.v('open_threshold'):
            # 출발 직후인데 앞이 막혀 있다 → 열린 통로를 향하지 않은 것. 다시 회전
            self.pub.publish(make_cmd(self))
            self.blocked_retries += 1
            if self.blocked_retries >= 2:
                # 다시 돌아도 막혀 있다 → 이 통로를 '두 번 지나감' 으로 표시해 후보에서 빼고 다시 판단
                self.get_logger().warn(f"{self.cell} → {ml.WORD[d]} 막힘(앞 {d_now['front']:.2f}m) — 후보에서 제외")
                self.marks.add(self.cell, d)
                self.state = 'SETTLE'
                self.settle_until = self.scan_count + 2
            else:
                self.get_logger().warn(f"출발 방향이 막힘(앞 {d_now['front']:.2f}m) — 다시 회전")
                self.state = 'ROTATE'
            return
        # 다음 칸 끝에 앞 벽이 보이면 odom 대신 벽까지 거리로 멈춘다 (방향이 맞을 때만)
        # 가운데 맞추기 중에는 방향이 조금 비스듬하므로 cos 로 진행 방향 성분만 쓴다
        if d_now['front'] < 1.2 and abs(heading_err) < 0.2:
            remaining = d_now['front'] * math.cos(heading_err) - self.v('wall_center')
        if d_now['front'] < 0.18:
            self.get_logger().warn(f"앞 {d_now['front']:.2f}m — 충돌 방지 정지")
            remaining = 0.0
        if remaining < 0.01:
            self.cell = cell
            self.stats['moves'] += 1
            self.state = 'SETTLE'
            self.settle_until = self.scan_count + 2
            self.pub.publish(make_cmd(self))
            return
        # 방위 유지 + 옆 벽으로 통로 가운데 맞추기 (양수 = 왼쪽으로)
        wc, side = self.v('wall_center'), 0.7
        left, right = d_now['left'], d_now['right']
        if left < side and right < side:
            lateral = (left - right) / 2
        elif right < side:
            lateral = wc - right
        elif left < side:
            lateral = left - wc
        else:
            lateral = 0.0
        w = clamp(2.5 * wrap(ml.YAW[d] - self.yaw) + clamp(1.5 * lateral, -0.3, 0.3), -1.0, 1.0)
        lin = min(self.v('linear_speed'), 0.6 * remaining + 0.03)
        self.pub.publish(make_cmd(self, lin, w))

    def finish(self, cell):
        self.state = 'DONE'
        self.pub.publish(make_cmd(self))
        s = self.stats
        secs = time.monotonic() - self.t0
        avg = s['jev_secs'] / s['jev_calls'] if s['jev_calls'] else 0.0
        self.get_logger().info(
            f"종료 {cell} | 이동 {s['moves']}칸 · 판단 {s['decisions']}회 · "
            f"OpenJev {s['jev_calls']}회(평균 {avg:.1f}s) · 대안 {s['fallbacks']}회 · 총 {secs:.0f}s")
        self.decision_pub.publish(String(data=json.dumps({'done': cell, **{
            k: v for k, v in s.items() if k != 'path'}}, ensure_ascii=False)))

    def stop(self):
        self.pub.publish(make_cmd(self))


def main():
    rclpy.init()
    node = JevNavigator()
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
