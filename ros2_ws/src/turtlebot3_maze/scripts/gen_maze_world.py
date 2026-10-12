#!/usr/bin/env python3
"""5 x 5 미로 월드(SDF) 생성기.

칸 하나가 1m 인 격자 미로를 '완전 미로'(모든 칸이 이어져 있고 고리가 없음)로 만든다.
고리가 없으므로 오른손 법칙(벽 따라가기)으로도 반드시 출구에 도착한다.

  python3 gen_maze_world.py                 # 미로 그림만 출력
  python3 gen_maze_world.py --write ../worlds/maze.sdf

좌표: 칸 (col, row) 의 중심 = (x, y) = (-2 + col, -2 + row) [m]
      출발 = (0, 0) 칸 = (-2, -2), 출구 = (4, 4) 칸의 동쪽 벽이 뚫려 있음 → x > 2.5 이면 탈출
"""
import argparse
import random

SIZE = 5           # 5 x 5 칸
CELL = 1.0         # 칸 한 변 [m] → 통로 폭 0.9m (벽 두께 0.1m)
WALL_T = 0.1       # 벽 두께 [m]
WALL_H = 0.4       # 벽 높이 [m] — LiDAR(약 0.17m)보다 높게
SEED = 4           # 같은 미로가 나오도록 고정 (최단 14칸, 오른손 법칙 28칸)
START = (0, 0)
EXIT = (SIZE - 1, SIZE - 1)
DIRS = {'N': (0, 1), 'S': (0, -1), 'E': (1, 0), 'W': (-1, 0)}


def carve(seed=SEED):
    """DFS 로 완전 미로를 판다. 반환: 칸 → 열린 방향 집합."""
    rng = random.Random(seed)
    open_dirs = {(c, r): set() for c in range(SIZE) for r in range(SIZE)}
    stack, seen = [START], {START}
    while stack:
        c, r = stack[-1]
        nbrs = [(d, (c + dc, r + dr)) for d, (dc, dr) in DIRS.items()
                if (c + dc, r + dr) in open_dirs and (c + dc, r + dr) not in seen]
        if not nbrs:
            stack.pop()
            continue
        d, nxt = rng.choice(nbrs)
        back = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}[d]
        open_dirs[(c, r)].add(d)
        open_dirs[nxt].add(back)
        seen.add(nxt)
        stack.append(nxt)
    open_dirs[EXIT].add('E')  # 출구
    return open_dirs


def ascii_map(open_dirs):
    lines = []
    for r in reversed(range(SIZE)):
        top = '+'
        mid = '|'
        for c in range(SIZE):
            top += ('   ' if 'N' in open_dirs[(c, r)] else '---') + '+'
            mark = 'S' if (c, r) == START else 'E' if (c, r) == EXIT else ' '
            mid += f' {mark} ' + (' ' if 'E' in open_dirs[(c, r)] else '|')
        lines += [top, mid]
    lines.append('+' + '---+' * SIZE)
    return '\n'.join(lines)


def wall_segments(open_dirs):
    """벽을 (중심 x, 중심 y, 길이 x, 길이 y) 상자로 변환. 이웃끼리 같은 벽은 한 번만 만든다."""
    half = SIZE * CELL / 2
    boxes = []
    for c in range(SIZE):
        for r in range(SIZE):
            x0 = -half + c * CELL
            y0 = -half + r * CELL
            if r == 0 and 'S' not in open_dirs[(c, r)]:
                boxes.append((x0 + CELL / 2, y0, CELL + WALL_T, WALL_T))
            if c == 0 and 'W' not in open_dirs[(c, r)]:
                boxes.append((x0, y0 + CELL / 2, WALL_T, CELL + WALL_T))
            if 'N' not in open_dirs[(c, r)]:
                boxes.append((x0 + CELL / 2, y0 + CELL, CELL + WALL_T, WALL_T))
            if 'E' not in open_dirs[(c, r)]:
                boxes.append((x0 + CELL, y0 + CELL / 2, WALL_T, CELL + WALL_T))
    return boxes


def wall_xml(i, x, y, sx, sy):
    geo = f'<box><size>{sx:.2f} {sy:.2f} {WALL_H:.2f}</size></box>'
    return f"""
    <model name="wall_{i:02d}">
      <static>true</static>
      <pose>{x:.2f} {y:.2f} {WALL_H / 2:.2f} 0 0 0</pose>
      <link name="link">
        <collision name="collision"><geometry>{geo}</geometry></collision>
        <visual name="visual">
          <geometry>{geo}</geometry>
          <material><ambient>0.55 0.6 0.7 1</ambient><diffuse>0.55 0.6 0.7 1</diffuse></material>
        </visual>
      </link>
    </model>"""


def world_sdf(open_dirs):
    walls = ''.join(wall_xml(i, *b) for i, b in enumerate(wall_segments(open_dirs)))
    art = ascii_map(open_dirs).replace('-', '=')  # XML 주석에는 '--' 를 쓸 수 없다
    return f"""<?xml version="1.0"?>
<!-- 자동 생성: scripts/gen_maze_world.py (seed={SEED}). 직접 고치지 말고 생성기를 다시 실행할 것.
{art}
-->
<sdf version="1.6">
  <world name="maze">
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>

    <physics type="ode">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1</real_time_factor>
      <real_time_update_rate>1000</real_time_update_rate>
    </physics>

    <scene>
      <ambient>0.6 0.6 0.6 1</ambient>
      <background>0.8 0.85 0.9 1</background>
      <shadows>false</shadows>
    </scene>

    <gui fullscreen="0">
      <camera name="user_camera">
        <pose>0 -6.5 7.5 0 0.85 1.5708</pose>
      </camera>
    </gui>

    <light type="directional" name="sun">
      <cast_shadows>false</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry>
        </collision>
        <visual name="visual">
          <geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry>
          <material><ambient>0.85 0.85 0.85 1</ambient><diffuse>0.85 0.85 0.85 1</diffuse></material>
        </visual>
      </link>
    </model>

    <!-- 출구 표시 (충돌 없음, 바닥의 초록 사각형) -->
    <model name="exit_marker">
      <static>true</static>
      <pose>3.0 2.0 0.005 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry><box><size>0.8 0.8 0.01</size></box></geometry>
          <material><ambient>0.1 0.8 0.2 1</ambient><diffuse>0.1 0.8 0.2 1</diffuse></material>
        </visual>
      </link>
    </model>
{walls}
  </world>
</sdf>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', metavar='PATH')
    ap.add_argument('--seed', type=int, default=SEED)
    args = ap.parse_args()
    open_dirs = carve(args.seed)
    print(ascii_map(open_dirs))
    if args.write:
        with open(args.write, 'w') as f:
            f.write(world_sdf(open_dirs))
        print(f'wrote {args.write} ({len(wall_segments(open_dirs))} walls)')


if __name__ == '__main__':
    main()
