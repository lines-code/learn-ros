# turtlesim 으로 익히는 ROS 2 기초

turtlesim(2D 거북이 시뮬레이터)을 대상으로 ROS 2 의 핵심 통신 방식인 **Topic** 과 **Service** 를 단계별로 익힌다.

| 단계 | 문서 | 배우는 것 | 실습 코드 |
|---|---|---|---|
| 1 | [01-cli.md](01-cli.md) | node / topic / service / interface 를 CLI 로 탐색 | (없음 — CLI 만) |
| 2 | [02-topic.md](02-topic.md) | Publisher, Subscriber, 둘을 합친 제어 루프 | `pose_listener`, `draw_circle`, `wall_bounce` |
| 3 | [03-service.md](03-service.md) | Service Client, 연속 호출, Service Server | `spawn_turtle`, `draw_square`, `pose_reporter` |

실습 코드는 `ros2_ws/src/turtlesim_basics/` (Python, rclpy) 패키지에 있다.

## 준비

```bash
# Mac
docker compose up -d
# 브라우저로 http://localhost:6080 접속 → 데스크톱에서 터미널 열기
```

컨테이너 터미널에서 한 번 빌드한다. `--symlink-install` 이므로 이후 `.py` 수정은 **재빌드 없이** 바로 반영된다
(새 파일을 추가하거나 `setup.py` 를 바꿨을 때만 다시 빌드).

```bash
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 pkg executables turtlesim_basics   # 6개 실행 파일이 보이면 OK
```

## 터미널 사용 요령

- 단계마다 **터미널을 여러 개** 쓴다. 터미널 1 에는 항상 `ros2 run turtlesim turtlesim_node` 를 띄워 둔다.
- 새 터미널은 `.bashrc` 가 ROS 환경을 자동으로 읽는다. 빌드 직후 이미 열려 있던 터미널에서는 `source ~/ros2_ws/install/setup.bash` 를 한 번 해 준다.
- 화면을 초기화하고 싶으면 `ros2 service call /reset std_srvs/srv/Empty`.
- 모든 명령 앞에 나오는 `ROS_LOCALHOST_ONLY is deprecated` 경고는 무시해도 된다.

## 참고

- [Topics / Services / Actions 개념](https://docs.ros.org/en/jazzy/Concepts/Basic/Interfaces-Topics-Services-Actions.html)
- [공식 turtlesim 튜토리얼](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Introducing-Turtlesim/Introducing-Turtlesim.html)
