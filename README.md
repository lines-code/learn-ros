# ros2-dev

1. `docker compose up -d --build`  (첫 빌드 10~20분, Docker Desktop 자원은 CPU 6 / 메모리 12GB 권장)
2. 브라우저에서 http://localhost:6080 (비밀번호 `ubuntu`)
3. 컨테이너 터미널에서 `ros2 run demo_nodes_cpp talker` / `ros2 run demo_nodes_py listener` 로 통신 확인
4. 코드는 Mac의 `ros2_ws/src/` 에 작성, 빌드는 컨테이너에서 `colcon build --symlink-install`

GUI 없는 작업: `docker exec -it -u ubuntu ros2-dev bash`  (`-u ubuntu` 를 빼면 root 로 들어가 `~/ros2_ws` 가 보이지 않는다)

**처음이라면 → [입문 가이드](docs/learn/getting-started.md)** · 1차수 실습: [turtlesim 기초](docs/learn/turtlesim/README.md)
