# Step 2. Topic — Publisher / Subscriber

**목표**: Step 1 에서 CLI 로 하던 `topic echo` / `topic pub` 을 Python 노드로 직접 구현한다.

코드: `ros2_ws/src/turtlesim_basics/turtlesim_basics/`

모든 실습은 터미널 1 에 `ros2 run turtlesim turtlesim_node` 가 떠 있는 상태에서 진행한다.

## 2-1. Subscriber — `pose_listener.py`

`/turtle1/pose` 를 구독해 위치를 1초마다 출력한다.

```bash
# 터미널 2
ros2 run turtlesim_basics pose_listener
# 터미널 3 — 움직여 보면서 터미널 2 의 값이 바뀌는지 확인
ros2 run turtlesim turtle_teleop_key
```

핵심 코드:

```python
self.create_subscription(Pose, '/turtle1/pose', self.on_pose, 10)
```

- 타입(`Pose`)과 토픽 이름은 Step 1 에서 `ros2 topic list -t` 로 찾은 그대로 쓴다.
- 마지막 `10` 은 QoS 큐 깊이다. 처리가 밀리면 최근 메시지를 10개까지 보관한다.
- 콜백은 `rclpy.spin(node)` 이 돌고 있을 때만 호출된다.

## 2-2. Publisher — `draw_circle.py`

타이머로 0.1초마다 `Twist` 를 발행해 원을 그린다.

```bash
ros2 run turtlesim_basics draw_circle
# 파라미터로 속도 변경
ros2 run turtlesim_basics draw_circle --ros-args -p linear:=3.0 -p angular:=2.5
# 실행 중에 바꿀 수도 있다 (다른 터미널에서)
ros2 param set /draw_circle angular -1.0
```

핵심 코드:

```python
self.pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
self.create_timer(0.1, self.tick)   # tick() 안에서 self.pub.publish(msg)
```

> **왜 계속 발행하나?** turtlesim 은 마지막 `cmd_vel` 을 받은 뒤 1초가 지나면 멈춘다.
> 로봇 제어에서는 명령을 주기적으로 계속 보내는 것이 일반적이다. 명령이 끊기면 멈추는 것은 안전장치이기도 하다.

## 2-3. Pub + Sub — `wall_bounce.py`

pose 를 **구독**해 벽 근처인지 판단하고, 그 결과로 cmd_vel 을 **발행**한다.
“입력 → 판단 → 출력” 으로 이어지는 가장 단순한 제어 루프다.

```bash
ros2 run turtlesim_basics wall_bounce
```

구조:

- `on_pose()` 는 최신 pose 를 `self.pose` 에 저장만 한다.
- `tick()`(타이머, 10Hz)은 저장된 pose 를 보고 직진할지 회전할지 정한 뒤 발행한다.

콜백 안에서 바로 발행하지 않고 **수신과 제어 주기를 분리**하는 이유는 두 가지다. 센서 주기(62Hz)와 제어 주기(10Hz)를 따로 정할 수 있고, 아직 pose 를 받지 못한 경우(`None`)도 자연스럽게 처리된다.

## 실습 과제

1. `pose_listener` 가 x, y 를 **소수점 1자리**로, `theta` 는 **도(°)** 단위로 출력하도록 고쳐 보자 (`math.degrees`).
   `.py` 만 수정했다면 재빌드 없이 다시 실행하면 된다.
2. `draw_circle` 과 `wall_bounce` 를 **동시에** 실행하면 어떻게 되는가? `ros2 topic info /turtle1/cmd_vel -v` 로 발행자 수를 확인하고 이유를 설명해 보자.
3. `wall_bounce` 가 `/turtle2/cmd_vel` 을 제어하도록 바꿔 보자. 먼저 CLI 로 turtle2 를 spawn 해 둔다.
   (힌트: 코드를 고치지 않고 `--ros-args -r /turtle1/cmd_vel:=/turtle2/cmd_vel -r /turtle1/pose:=/turtle2/pose` 리매핑으로도 된다)

## 확인 체크리스트

- [ ] `rqt_graph` 에서 `/pose_listener`, `/draw_circle` 노드가 토픽에 연결된 모습을 확인했다
- [ ] 퍼블리셔를 멈추면 약 1초 뒤 거북이가 멈추는 것을 확인했다
- [ ] `--ros-args -p` 로 파라미터를, `-r` 로 토픽 리매핑을 해 봤다

➡ 다음: [Step 3. Service](03-service.md)
