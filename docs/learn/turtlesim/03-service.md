# Step 3. Service — Client / Server

**목표**: 요청 → 응답 방식의 Service 를 클라이언트와 서버 양쪽에서 구현한다.

| | Topic | Service |
|---|---|---|
| 방식 | 계속 흐르는 스트림, 1:N | 한 번 요청하면 한 번 응답, 1:1 |
| 예 | 센서 값, 속도 명령 | 거북이 생성, 설정 변경, 상태 조회 |
| 응답 확인 | 없음 | 응답이 올 때까지 기다릴 수 있음 |

모든 실습은 `turtlesim_node` 가 떠 있는 상태에서 진행한다.

## 3-1. Client — `spawn_turtle.py`

`/spawn` 서비스를 호출해 새 거북이를 만든다.

```bash
ros2 run turtlesim_basics spawn_turtle --ros-args -p x:=2.0 -p y:=8.0 -p name:=turtle2
ros2 run turtlesim_basics spawn_turtle --ros-args -p name:=turtle2   # 같은 이름 → 실패 메시지
```

클라이언트 호출은 항상 아래 4단계를 거친다.

```python
client = node.create_client(Spawn, '/spawn')          # 1. 클라이언트 생성
client.wait_for_service(timeout_sec=1.0)              # 2. 서버가 뜰 때까지 대기
future = client.call_async(req)                        # 3. 비동기 요청
rclpy.spin_until_future_complete(node, future)         # 4. 응답이 올 때까지 spin
```

> turtlesim 은 이름이 중복되면 에러 대신 **빈 `name`** 을 돌려준다.
> 서비스의 “실패” 를 어떻게 표현할지는 서버마다 다르므로, 응답 필드를 직접 확인해야 한다.

## 3-2. 연속 호출 — `draw_square.py`

`/clear`, `/turtle1/set_pen`, `/turtle1/teleport_absolute` 서비스를 순서대로 호출해 사각형을 그린다.

```bash
ros2 run turtlesim_basics draw_square
```

- `call()` 헬퍼는 요청 하나를 보낸 뒤 응답을 받을 때까지 기다린다. 그래서 여러 호출이 **정확히 순서대로** 실행된다.
- 펜을 들고(`off=1`) 이동하면 선이 그려지지 않는다. 시작점까지 갈 때 이 방법을 쓴다.
- Topic(cmd_vel)으로 움직일 때와 달리 teleport 는 **즉시 그 좌표로** 이동한다.

## 3-3. Server — `pose_reporter.py`

`/report_pose` 서비스를 제공한다. `std_srvs/srv/Trigger` 요청이 오면 현재 거북이 위치를 문자열로 응답한다.
서버 안에서 Topic 구독도 함께 쓰는 예제다.

```bash
# 터미널 2
ros2 run turtlesim_basics pose_reporter
# 터미널 3
ros2 service call /report_pose std_srvs/srv/Trigger
# → success=True, message='x=5.54, y=5.54, theta=0.00'
```

```python
self.create_service(Trigger, '/report_pose', self.on_request)

def on_request(self, request, response):
    response.success = True
    response.message = '...'
    return response        # 반드시 response 를 return
```

`Trigger` 는 요청 필드가 없고 응답이 `bool success, string message` 인 범용 타입이다 (`ros2 interface show std_srvs/srv/Trigger`).
커스텀 `.srv` 를 만들기 전에 표준 타입으로 충분한지 먼저 확인하는 습관을 들이자.

## 실습 과제

1. `spawn_turtle` 로 turtle2 를 만든 뒤, Step 2 의 리매핑을 써서 turtle2 가 `wall_bounce` 로 움직이게 해 보자.
2. `draw_square` 를 고쳐 **삼각형**을 그리고, 변마다 펜 색을 바꿔 보자.
3. `pose_reporter` 에 `/turtle1/cmd_vel` 퍼블리셔를 추가해, 요청을 받을 때마다 거북이를 조금 앞으로 움직여 보자.

## 확인 체크리스트

- [ ] `ros2 service list` 에 내가 만든 `/report_pose` 가 보인다
- [ ] 서버를 끈 상태에서 클라이언트를 실행하면 “서비스 대기 중” 이 반복되는 것을 확인했다
- [ ] 거북이를 계속 움직일 때는 Topic, 한 번만 설정할 때는 Service 가 맞는 이유를 설명할 수 있다

## 다음 차수 후보

Parameter 심화 → Action(`/turtle1/rotate_absolute`) → Launch 파일 → 커스텀 msg/srv → TF2(turtle follow)
