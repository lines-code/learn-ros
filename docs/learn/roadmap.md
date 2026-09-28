# 작업 계획 (로드맵)

> 지금까지 한 것은 [getting-started.md](getting-started.md) 에 정리되어 있다.
> 이 문서는 **다음에 할 일**을 순서대로 정리한 계획이다. 각 단계는 앞 단계가 끝나야 시작할 수 있도록 배치했다.

## 전체 흐름

```mermaid
flowchart LR
    P0["0. 정리 작업<br/>(커밋 · 설정 정리)"] --> P2["2차수<br/>Gazebo 미로 기초"]
    P2 --> P3["3차수<br/>SLAM · Nav2"]
    P3 --> P4["4차수 후보<br/>Action · Launch · 심화"]
```

| 차수 | 핵심 질문 | 범위 | 상태 |
|---|---|---|---|
| 0 | 지금까지 만든 것을 안전하게 보관했는가? | 커밋, 설정 정리 | ⬜ 할 일 |
| 2 | 로봇이 **센서로** 장애물을 피하고 미로를 빠져나갈 수 있는가? | Step 1 ~ 3 | ⬜ 할 일 (환경 검증 완료) |
| 3 | 로봇이 **지도를 만들고**, 지도 위에서 **스스로 길을 찾는가?** | Step 4 ~ 5 | ⬜ 예정 |
| 4 | 코드를 실무 형태로 다듬을 수 있는가? | 선택 | ⬜ 후보 |

상태 표시: ✅ 완료 · 🔄 진행 중 · ⬜ 할 일

---

## 0. 정리 작업 (먼저 하기)

2차수를 시작하기 전에 지금까지의 결과를 저장하고, 매번 보이는 경고를 없앤다.

| # | 할 일 | 내용 | 완료 기준 |
|---|---|---|---|
| 0-1 | Git 커밋 | 현재 `Dockerfile`, `docker-compose.yml`, `docs/`, `ros2_ws/src/`, `README.md` 가 **아직 한 번도 커밋되지 않았다**. `.omc/`(도구 상태 파일)는 `.gitignore` 에 넣고 제외한다 | `git status` 가 깨끗하다 |
| 0-2 | 경고 제거 | `docker-compose.yml` 의 `ROS_LOCALHOST_ONLY=1` 을 `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` 로 바꾼다 (Jazzy 권장 방식) | `docker compose up -d` 후 `ros2 topic list` 에 경고가 없다 |
| 0-3 | 1차수 과제 풀이 (선택) | [02-topic.md](turtlesim/02-topic.md), [03-service.md](turtlesim/03-service.md) 의 실습 과제를 직접 풀어 본다 | 과제별로 동작 확인 |

> 0-2 는 컨테이너를 새로 만들기 때문에, noVNC 터미널에서 실행 중이던 프로그램이 종료된다.

---

## 2차수: Gazebo 미로 — 기초 (Step 1 ~ 3)

**목표**: turtlesim 에서 배운 “구독 → 판단 → 발행” 제어 루프를, 실제 장애물이 있는 3D 환경과 LiDAR 센서로 확장한다.

**만들 것**

- 문서: `docs/learn/maze/` (README + 단계별 문서 3개)
- 코드: `ros2_ws/src/turtlebot3_maze/` 패키지 (Python) — 노드, 미로 월드 파일, launch 파일

**1차수와의 연결**

| 1차수 (turtlesim) | 2차수 (Gazebo) |
|---|---|
| `/turtle1/cmd_vel` — `Twist` | `/cmd_vel` — **`TwistStamped`** |
| `/turtle1/pose` — 좌표 | `/scan` — LiDAR 거리 360개, `/odom` — 주행 기록 |
| `wall_bounce` — 좌표로 벽 판단 | `obstacle_avoider` — 거리로 장애물 판단 |

### Step 1. CLI 로 TurtleBot3 탐색

| 항목 | 내용 |
|---|---|
| 목표 | 코드 없이 로봇을 움직이고 센서 값을 읽는다 |
| 실습 | `turtlebot3_world` 실행 → `ros2 topic list/info/hz` → `/cmd_vel` 로 전진·회전 → `/scan` 의 `ranges` 해석 (0°=앞, 90°=왼쪽, 180°=뒤, 270°=오른쪽) → `teleop_keyboard` 로 조종 |
| 새 개념 | `TwistStamped`, LaserScan 메시지, `use_sim_time`(시뮬레이션 시계), RViz 로 LiDAR 점 보기 |
| 산출물 | `docs/learn/maze/01-cli.md` |
| 완료 기준 | 로봇 앞 장애물까지의 거리를 `/scan` 에서 읽어 말할 수 있다 |

### Step 2. LiDAR 로 장애물 피하기

| 항목 | 내용 |
|---|---|
| 목표 | `/scan` 을 구독해 앞이 막히면 도는 노드를 만든다 |
| 노드 | `scan_viewer` — 앞·좌·우 최소 거리를 1초마다 출력 (Subscriber)<br/>`obstacle_avoider` — 앞이 0.4m 이내면 넓은 쪽으로 회전, 아니면 직진 (Pub + Sub) |
| 새 개념 | 센서 데이터 전처리 (`inf`·0 값 거르기, 각도 구간별 최소값), 파라미터로 안전 거리 조정 |
| 산출물 | `docs/learn/maze/02-avoid.md`, 노드 2개 |
| 완료 기준 | `turtlebot3_world` 에서 3분 동안 기둥에 부딪히지 않고 돌아다닌다 |

### Step 3. 직접 만든 미로 탈출

| 항목 | 내용 |
|---|---|
| 목표 | 미로 월드를 직접 만들고, 벽 따라가기(오른손 법칙)로 출구까지 간다 |
| 작업 | ① SDF 로 5m × 5m 미로 월드 작성 (상자 모양 벽 배치)<br/>② launch 파일로 “미로 월드 + 로봇 생성” 을 한 번에 실행<br/>③ `wall_follower` 노드 — 오른쪽 벽과의 거리를 일정하게 유지하며 전진 |
| 새 개념 | SDF 월드 파일, launch 파일(Python), 비례 제어(P 제어) 맛보기 |
| 산출물 | `docs/learn/maze/03-maze.md`, `worlds/maze.sdf`, `launch/maze.launch.py`, 노드 1개 |
| 완료 기준 | `ros2 launch turtlebot3_maze maze.launch.py` 한 줄로 미로가 뜨고, `wall_follower` 가 출구에 도착한다 |

**2차수 위험 요소**

| 위험 | 대응 |
|---|---|
| 미로가 좁으면 burger 로봇(지름 약 0.18m)이 통로에서 끼인다 | 통로 폭 0.6m 이상으로 설계 |
| 벽 따라가기가 모서리에서 진동한다 | 속도를 낮추고, 전방 거리 조건을 먼저 판단 |
| GUI 까지 켜면 CPU 부담이 크다 | 필요하면 서버만 실행(`-s`)하고 RViz 로 확인 |

---

## 3차수: 지도 작성과 자율 주행 (Step 4 ~ 5)

**목표**: 로봇이 미로를 돌아다니며 **지도를 만들고**, 그 지도 위에서 **목표 지점까지 스스로 경로를 찾는다**.

### Step 4. SLAM — 미로 지도 만들기

| 항목 | 내용 |
|---|---|
| 목표 | 2차수 미로를 주행하며 지도를 만들고 파일로 저장한다 |
| 실습 | 미로 실행 → SLAM 실행(`slam_toolbox` 또는 `turtlebot3_cartographer`) → `wall_follower` 나 teleop 으로 미로 전체 주행 → RViz 에서 지도가 채워지는 것 확인 → `map_saver_cli` 로 저장 |
| 새 개념 | TF(좌표 변환: `map` → `odom` → `base_link`), OccupancyGrid(격자 지도), SLAM 원리 개요 |
| 산출물 | `docs/learn/maze/04-slam.md`, `maps/maze.yaml` + `maze.pgm` |
| 완료 기준 | 저장한 지도 이미지에 미로 벽이 끊김 없이 나타난다 |

### Step 5. Nav2 — 목표 지점까지 자율 주행

| 항목 | 내용 |
|---|---|
| 목표 | 저장한 지도를 불러와 RViz 에서 찍은 목표 지점까지 로봇이 스스로 이동한다 |
| 실습 | Nav2 실행(`turtlebot3_navigation2`, 지도 지정) → RViz 에서 초기 위치 지정 → “Nav2 Goal” 로 목표 지정 → 코드로 목표 보내기(`nav2_simple_commander`) |
| 새 개념 | Action(목표 → 진행 피드백 → 결과), costmap, 경로 계획과 추종, AMCL(지도 위 위치 추정) |
| 산출물 | `docs/learn/maze/05-nav2.md`, 목표 지점을 순서대로 도는 노드 1개 |
| 완료 기준 | 미로 입구에서 출구까지 목표 지점 하나만 주고 자율 주행에 성공한다 |

**3차수 위험 요소**

| 위험 | 대응 |
|---|---|
| Gazebo + SLAM/Nav2 + RViz 를 함께 띄우면 자원이 부족할 수 있다 (**아직 측정하지 않음**) | 3차수 시작 전 부하를 측정한다. 부족하면 Gazebo 를 GUI 없이 실행하거나 Docker 메모리를 16GB 로 올린다 |
| `use_sim_time` 설정이 노드마다 다르면 TF 오류가 난다 | 모든 launch 에 `use_sim_time:=True` 를 통일 |

---

## 4차수 후보 (선택)

2·3차수를 진행하며 필요해지면 고른다.

| 주제 | 내용 | 왜 필요한가 |
|---|---|---|
| Action 직접 구현 | Action Server / Client 를 직접 작성 | Nav2 가 Action 으로 동작하는 원리 이해 |
| 커스텀 msg / srv | 우리만의 메시지 타입 정의 | 표준 타입으로 표현하기 어려운 데이터 |
| Launch · 파라미터 파일 심화 | YAML 파라미터, 조건부 실행, 인자 | 노드가 많아질 때 관리 |
| 테스트 | `pytest` 로 노드 로직 단위 테스트 | 판단 로직을 안전하게 수정 |
| C++ 노드 | 같은 노드를 rclcpp 로 작성 | 실무 로봇 코드 대부분이 C++ |

---

## 진행 방식

각 단계는 1차수와 같은 형식으로 만든다.

1. **문서**: 목표 → 명령어 → 핵심 코드 설명 → 실습 과제 → 확인 체크리스트
2. **코드**: 실행할 수 있는 노드와 설정 파일
3. **검증**: 컨테이너에서 실제로 실행해 완료 기준을 확인한 뒤 문서에 결과를 적는다
4. **기록**: 이 문서의 상태 표시(⬜ → ✅)를 갱신한다
