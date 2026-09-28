# Step 1. CLI 로 turtlesim 탐색하기

**목표**: 코드 없이 `ros2` 명령만으로 “어떤 노드가, 어떤 토픽/서비스로, 어떤 타입의 데이터를 주고받는지” 알아낸다.
이후 단계에서 코드를 짤 때 필요한 이름과 타입은 전부 여기서 확인한다.

## 1-1. 실행하고 조종하기

```bash
# 터미널 1
ros2 run turtlesim turtlesim_node
# 터미널 2 — 이 터미널에 포커스를 두고 방향키로 조종
ros2 run turtlesim turtle_teleop_key
```

## 1-2. Node

```bash
ros2 node list                 # /turtlesim, /teleop_turtle
ros2 node info /turtlesim      # 이 노드의 Subscribers / Publishers / Service Servers
```

`/turtlesim` 이 **구독**하는 `/turtle1/cmd_vel` 과 **발행**하는 `/turtle1/pose` 를 기억해 두자.

## 1-3. Topic

```bash
ros2 topic list -t                        # 토픽 이름과 타입
ros2 topic echo /turtle1/pose             # 거북이 위치가 계속 출력됨 (Ctrl+C 로 종료)
ros2 topic hz /turtle1/pose               # 발행 주기 (약 62Hz)
ros2 topic info /turtle1/cmd_vel -v       # 누가 발행하고 누가 구독하는지
```

### 키보드 대신 CLI 로 직접 발행해 보기

`ros2 topic pub <토픽> <타입> "<YAML 값>"` 형식이다. 먼저 turtlesim 이 움직임을 어떻게 해석하는지 알아 두자.

| 필드 | 의미 | 단위 |
|---|---|---|
| `linear.x` | 앞(+) / 뒤(−) 이동 속도 | 칸/초 (화면 한 변은 약 11칸) |
| `angular.z` | 반시계(+) / 시계(−) 회전 속도 | rad/초 (π/2 ≈ 1.5708 이 90°) |
| `linear.y` | 옆(게걸음) 이동 속도. **`holonomic:=true` 일 때만** 동작 | 칸/초 |

> **1초 규칙**: turtlesim 은 마지막 메시지를 받은 뒤 **1초 동안만** 그 속도로 움직이고 멈춘다.
> 그래서 `--once` 한 번이면 “속도 × 1초” 만큼 움직인다. 예를 들어 `x: 2.0` 이면 2칸, `z: 1.5708` 이면 90° 다.

아래 예제는 모두 컨테이너에서 실제로 실행해 결과를 확인했다. 결과 값은 `/reset` 직후 시작 위치 (5.54, 5.54, θ=0) 기준이다.
긴 명령을 줄이려고 먼저 변수를 잡아 두면 편하다.

```bash
C=/turtle1/cmd_vel
T=geometry_msgs/msg/Twist
echo "$C $T"      # 두 값이 모두 출력되는지 확인
```

> ⚠ 셸 변수는 **설정한 터미널에서만** 유효하다. 새 터미널을 열면 다시 설정해야 한다.
> 변수가 비어 있으면 `error: the following arguments are required: message_type` 가 난다.
> 변수 없이 쓰려면 `$C` → `/turtle1/cmd_vel`, `$T` → `geometry_msgs/msg/Twist` 로 바꿔 쓰면 된다.

#### ① 한 번만 발행: `-1` (`--once`)

```bash
ros2 topic pub -1 $C $T "{linear: {x: 2.0}}"            # 앞으로 2칸        → x 5.54 → 7.56
ros2 topic pub -1 $C $T "{linear: {x: -2.0}}"           # 뒤로 2칸          → x 5.54 → 3.53
ros2 topic pub -1 $C $T "{angular: {z: 1.5708}}"        # 제자리 90° 좌회전 → θ 0 → 1.57
ros2 topic pub -1 $C $T "{angular: {z: -3.1416}}"       # 제자리 180° 우회전  → θ 3.12 (θ 는 −π~π 로 표시되므로 −π 와 π 는 같은 방향)
ros2 topic pub -1 $C $T "{linear: {x: 2.0}, angular: {z: 1.5708}}"   # 앞으로 가며 90° 호 → (6.80, 6.85, θ 1.58)
```

- 지정하지 않은 필드는 0 이 된다. `{linear: {x: 2.0}}` 은 `linear.y/z`, `angular.*` 이 모두 0 이다.
- `x: 2` 처럼 정수로 써도 자동으로 `2.0` 으로 변환된다.
- `-1` 은 구독자(turtlesim)가 연결될 때까지 기다렸다가 발행한다. turtlesim 이 꺼져 있으면 멈춰 있는 것처럼 보인다.

#### ② 정해진 횟수만 발행: `-t N`

```bash
ros2 topic pub -t 3 -r 1 $C $T "{linear: {x: 1.0}}"     # 1초 간격 3번 → 약 3칸 전진 (x 5.54 → 8.55)
ros2 topic pub -t 4 -r 1 $C $T "{angular: {z: 1.5708}}" # 90° × 4 → 한 바퀴 돌아 θ ≈ 0 으로 복귀
```

#### ③ 계속 발행: `-r Hz` (Ctrl+C 로 중지)

```bash
ros2 topic pub -r 1  $C $T "{linear: {x: 2.0}, angular: {z: 1.8}}"   # 1Hz — 원을 그림
ros2 topic pub -r 10 $C $T "{linear: {x: 2.0}, angular: {z: 1.8}}"   # 10Hz — 같은 원, 명령이 더 촘촘
```

두 명령은 같은 원을 그린다. 다른 것은 명령 사이의 간격뿐이다(1초 vs 0.1초). Ctrl+C 를 누르면 둘 다 약 1초 뒤에 멈춘다.
실제 로봇 제어처럼 명령을 자주 바꿔야 할 때는 10Hz 이상을 쓴다.

#### ④ 원의 크기와 방향 바꾸기

원의 반지름은 **r = linear.x ÷ angular.z** 이다.

```bash
ros2 topic pub -r 10 $C $T "{linear: {x: 1.0}, angular: {z: 2.0}}"   # r = 0.5 — 작은 원
ros2 topic pub -r 10 $C $T "{linear: {x: 3.0}, angular: {z: 1.0}}"   # r = 3   — 큰 원 (벽에 닿을 수 있음)
ros2 topic pub -r 10 $C $T "{linear: {x: 2.0}, angular: {z: -1.0}}"  # r = 2   — 시계 방향
ros2 topic pub -r 10 $C $T "{linear: {x: -2.0}, angular: {z: 1.0}}"  # 후진하며 원
```

#### ⑤ 즉시 멈추기

1초를 기다리지 않고 바로 세우려면 속도 0 을 한 번 보낸다. 값을 비우면 모든 필드가 0 이다.

```bash
ros2 topic pub -1 $C $T "{}"
```

#### ⑥ 옆으로 이동 (holonomic 모드)

turtlesim 은 기본 설정에서 `linear.y` 를 **무시**한다. 옆으로 움직이려면 turtlesim 을 파라미터와 함께 다시 띄워야 한다.

```bash
# 터미널 1: 기존 turtlesim 을 Ctrl+C 로 끄고
ros2 run turtlesim turtlesim_node --ros-args -p holonomic:=true
# 터미널 2
ros2 topic pub -1 $C $T "{linear: {y: 2.0}}"            # 왼쪽으로 2칸 (y 5.54 → 7.56), 방향 θ 는 그대로
```

#### ⑦ 셸 반복문으로 도형 그리기

`-1` 명령을 순서대로 이어 붙이면 간단한 경로를 만들 수 있다. 명령마다 1초씩 움직이므로 사이에 `sleep` 을 준다.

```bash
# 한 변 2칸짜리 정사각형 → 거의 제자리로 돌아온다 (5.60, 5.50, θ≈0.05)
for i in 1 2 3 4; do
  ros2 topic pub -1 $C $T "{linear: {x: 2.0}}";      sleep 1.2
  ros2 topic pub -1 $C $T "{angular: {z: 1.5708}}";  sleep 1.2
done

# 나선: 반복할 때마다 전진 속도를 키운다
for v in 0.5 1.0 1.5 2.0 2.5 3.0; do
  ros2 topic pub -1 $C $T "{linear: {x: $v}, angular: {z: 2.0}}"; sleep 1.1
done
```

> 오차가 조금 생기는 이유는 “1초” 가 정확하지 않고 명령 간격도 흔들리기 때문이다.
> 정확한 위치 이동이 필요할 때는 Step 3 의 `teleport_absolute` 서비스를 쓴다.

#### ⑧ 다른 거북이 움직이기

토픽 이름만 바꾸면 된다.

```bash
ros2 service call /spawn turtlesim/srv/Spawn "{x: 2.0, y: 2.0, theta: 0.0, name: 'turtle2'}"
ros2 topic pub -r 10 /turtle2/cmd_vel $T "{linear: {x: 1.5}, angular: {z: 1.0}}"   # turtle1 과 별개로 움직인다
```

#### ⑨ 발행하면서 결과 관찰하기

다른 터미널에서 필요한 값만 골라 보면 명령 효과를 숫자로 확인하기 쉽다.

```bash
ros2 topic echo /turtle1/pose --field theta     # 회전 각도만
ros2 topic echo /turtle1/pose --field x         # x 좌표만
ros2 topic info /turtle1/cmd_vel -v             # 지금 cmd_vel 발행자가 몇 개인지 (teleop 과 동시에 쓰면 2개)
```

#### 자주 하는 실수

| 증상 | 원인 |
|---|---|
| `the following arguments are required: message_type` | 이 터미널에서 `C`, `T` 변수를 설정하지 않았다 |
| 명령을 보냈는데 반응이 없다 | turtlesim 이 꺼져 있거나, 다른 터미널이 다른 `ROS_DOMAIN_ID` 를 쓰고 있다 |
| `linear.y` 를 줘도 옆으로 안 간다 | holonomic 모드가 아니다 (⑥ 참고) |
| `Failed to populate field: ... no attribute 'x:2.0'` | 콜론 뒤에 공백이 없다 (`x:2.0` ✗ → `x: 2.0` ✓) |
| teleop 과 동시에 쓰니 거북이가 떨린다 | 발행자 두 개가 서로 다른 명령을 보내고 있다 |

## 1-4. Interface (메시지 타입)

```bash
ros2 interface show geometry_msgs/msg/Twist   # linear(x,y,z), angular(x,y,z)
ros2 interface show turtlesim/msg/Pose        # x, y, theta, linear_velocity, angular_velocity
ros2 interface show turtlesim/srv/Spawn       # --- 위는 Request, 아래는 Response
```

## 1-5. Service

```bash
ros2 service list -t
ros2 service call /spawn turtlesim/srv/Spawn "{x: 2.0, y: 2.0, theta: 0.0, name: 'turtle2'}"
ros2 service call /turtle1/set_pen turtlesim/srv/SetPen "{r: 255, g: 0, b: 0, width: 5, 'off': 0}"
ros2 service call /clear std_srvs/srv/Empty
ros2 service call /reset std_srvs/srv/Empty
```

## 1-6. 그래프로 보기

```bash
rqt_graph      # 노드와 토픽 연결을 그림으로 확인
```

## 확인 체크리스트

- [ ] `/turtle1/cmd_vel` 의 타입이 `geometry_msgs/msg/Twist` 임을 CLI 로 찾아냈다
- [ ] `ros2 topic pub` 으로 거북이를 움직였다
- [ ] `ros2 service call /spawn` 으로 두 번째 거북이를 만들었다
- [ ] Topic(계속 흐르는 데이터, 1:N) 과 Service(요청 → 응답, 1:1) 의 차이를 한 문장으로 설명할 수 있다

➡ 다음: [Step 2. Topic](02-topic.md)
