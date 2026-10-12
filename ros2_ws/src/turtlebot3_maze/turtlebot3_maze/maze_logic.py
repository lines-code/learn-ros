"""격자 미로 판단 로직 — ROS 없이 테스트할 수 있는 순수 함수 모음.

미로는 1m 칸의 5 x 5 격자다. 방향은 절대 방위(N/E/S/W)로 다룬다.
  E = +x (yaw 0), N = +y (yaw 90°), W = -x, S = -y

탐색 규칙은 트레모 알고리즘(Trémaux)을 단순화한 것:
  지나간 통로마다 표시(mark)를 남기고, 두 번 지나간 통로는 다시 가지 않는다.
  안 가본 통로가 여러 개면 그중 하나를 고르는데, 이 '고르기' 를 OpenJev 에 맡긴다.
"""
import json
import math

HEADINGS = ['E', 'N', 'W', 'S']                       # yaw 가 90° 씩 커지는 순서
YAW = {'E': 0.0, 'N': math.pi / 2, 'W': math.pi, 'S': -math.pi / 2}
STEP = {'E': (1, 0), 'N': (0, 1), 'W': (-1, 0), 'S': (0, -1)}
OPPOSITE = {'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}
REL_TURN = {'front': 0, 'left': 1, 'back': 2, 'right': 3}  # 왼쪽 = 반시계 90°
WORD = {'E': 'east', 'N': 'north', 'W': 'west', 'S': 'south'}


def rel_to_abs(heading, rel):
    """로봇 기준 방향(front/left/right/back) → 절대 방위."""
    return HEADINGS[(HEADINGS.index(heading) + REL_TURN[rel]) % 4]


def abs_to_rel(heading, abs_dir):
    for rel in REL_TURN:
        if rel_to_abs(heading, rel) == abs_dir:
            return rel
    raise ValueError(abs_dir)


def nearest_heading(yaw):
    """현재 yaw 에서 가장 가까운 방위."""
    return min(HEADINGS, key=lambda h: abs(math.atan2(math.sin(yaw - YAW[h]), math.cos(yaw - YAW[h]))))


def neighbor(cell, d):
    return (cell[0] + STEP[d][0], cell[1] + STEP[d][1])


def cell_center(cell, origin=(-2.0, -2.0), size=1.0):
    return (origin[0] + cell[0] * size, origin[1] + cell[1] * size)


def cell_of(x, y, origin=(-2.0, -2.0), size=1.0):
    return (round((x - origin[0]) / size), round((y - origin[1]) / size))


def open_directions(dist, heading, open_threshold=0.8):
    """구간별 거리 {'front': m, ...} → 열린 절대 방위 목록."""
    return [rel_to_abs(heading, rel) for rel in ('front', 'left', 'right', 'back')
            if dist[rel] > open_threshold]


class Marks:
    """통로 표시. 통로(칸 사이 경계)마다 몇 번 지나갔는지 센다."""

    def __init__(self):
        self.count = {}

    @staticmethod
    def _key(cell, d):
        other = neighbor(cell, d)
        return tuple(sorted([(cell, d), (other, OPPOSITE[d])]))

    def get(self, cell, d):
        return self.count.get(self._key(cell, d), 0)

    def add(self, cell, d):
        k = self._key(cell, d)
        self.count[k] = self.count.get(k, 0) + 1


def candidates(open_dirs, cell, marks):
    """트레모 규칙으로 갈 수 있는 후보. 안 가본 통로가 있으면 그것만, 없으면 한 번 간 통로(되돌아가기)."""
    usable = [d for d in open_dirs if marks.get(cell, d) < 2]
    fresh = [d for d in usable if marks.get(cell, d) == 0]
    return fresh if fresh else usable


def right_hand_choice(options, heading):
    """규칙 기반 대안(fallback): 오른쪽 → 앞 → 왼쪽 → 뒤 순서."""
    for rel in ('right', 'front', 'left', 'back'):
        d = rel_to_abs(heading, rel)
        if d in options:
            return d
    return None


def exit_bearing_words(cell, exit_cell):
    """출구가 어느 쪽인지 사람 말로. 예: 'north-east'."""
    dx, dy = exit_cell[0] - cell[0], exit_cell[1] - cell[1]
    ns = 'north' if dy > 0 else 'south' if dy < 0 else ''
    ew = 'east' if dx > 0 else 'west' if dx < 0 else ''
    return '-'.join(p for p in (ns, ew) if p) or 'here'


def describe_option(d, cell, exit_cell, marks, grid_size=5):
    """선택지 하나에 대한 설명(루브릭). OpenJev 는 이 설명과 상태를 읽고 고른다."""
    nxt = neighbor(cell, d)
    if not (0 <= nxt[0] < grid_size and 0 <= nxt[1] < grid_size):
        return 'Leaves the maze grid through an opening in the outer wall; this is the exit.'
    before = abs(exit_cell[0] - cell[0]) + abs(exit_cell[1] - cell[1])
    after = abs(exit_cell[0] - nxt[0]) + abs(exit_cell[1] - nxt[1])
    toward = ('moves closer to the exit' if after < before
              else 'moves farther from the exit' if after > before
              else 'keeps the same distance to the exit')
    seen = marks.get(cell, d)
    explored = 'never explored' if seen == 0 else 'already explored once (going back)'
    return f'Goes {WORD[d]}; {toward}; this passage is {explored}.'


def build_decide_request(cell, heading, options, marks, exit_cell, grid_size=5):
    """/v1/decide 요청 본문. 상태(state) + 선택지 하나짜리 choice 질문."""
    state = (
        f'A wheeled robot is exploring a {grid_size} by {grid_size} grid maze and must reach the exit. '
        f'Columns increase to the east and rows increase to the north. '
        f'The robot is in column {cell[0]}, row {cell[1]}, facing {WORD[heading]}. '
        f'The exit is in column {exit_cell[0]}, row {exit_cell[1]}, on the outer east wall, '
        f'which is to the {exit_bearing_words(cell, exit_cell)} of the robot. '
        f'Open passages from here: {", ".join(WORD[d] for d in options)}.'
    )
    rubric = {WORD[d]: describe_option(d, cell, exit_cell, marks, grid_size) for d in options}
    instructions = (
        'Which open passage should the robot take to reach the exit with the fewest moves?'
        '\nAllowed answers and rubric: ' + json.dumps(rubric, ensure_ascii=False)
    )
    return {
        'state': state,
        'questions': [{'type': 'choice', 'instructions': instructions,
                       'options': [WORD[d] for d in options]}],
    }


def pick_from_probabilities(probs, options):
    """OpenJev 확률 → 방위. 안전 필터: 실제로 열려 있는 선택지(options) 밖의 답은 버린다."""
    by_word = {WORD[d]: d for d in options}
    allowed = {w: p for w, p in probs.items() if w in by_word}
    if not allowed:
        return None, 0.0
    best = max(allowed, key=allowed.get)
    return by_word[best], allowed[best]

