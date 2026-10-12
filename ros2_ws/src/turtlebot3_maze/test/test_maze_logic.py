import importlib.util
import json
import pathlib

from turtlebot3_maze import maze_logic as ml


def load_maze():
    path = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'gen_maze_world.py'
    spec = importlib.util.spec_from_file_location('gen_maze_world', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.carve(), mod.START, mod.EXIT


def test_rel_abs_roundtrip():
    assert ml.rel_to_abs('E', 'left') == 'N'
    assert ml.rel_to_abs('E', 'right') == 'S'
    assert ml.rel_to_abs('N', 'back') == 'S'
    for h in ml.HEADINGS:
        for rel in ml.REL_TURN:
            assert ml.abs_to_rel(h, ml.rel_to_abs(h, rel)) == rel


def test_cell_math():
    assert ml.cell_of(-2.0, -2.0) == (0, 0)
    assert ml.cell_of(2.04, 1.96) == (4, 4)
    assert ml.cell_center((4, 4)) == (2.0, 2.0)
    assert ml.nearest_heading(1.5) == 'N'
    assert ml.nearest_heading(-3.1) == 'W'


def test_marks_are_shared_by_both_sides():
    m = ml.Marks()
    m.add((0, 0), 'E')
    assert m.get((1, 0), 'W') == 1
    assert ml.candidates(['E', 'N'], (0, 0), m) == ['N']   # 안 가본 통로 우선


def test_pick_filters_unsafe_answers():
    # OpenJev 가 열려 있지 않은 방향(west)을 가장 높게 줘도 후보 안에서만 고른다
    d, p = ml.pick_from_probabilities({'west': 0.9, 'north': 0.06, 'east': 0.04}, ['N', 'E'])
    assert d == 'N' and p == 0.06
    assert ml.pick_from_probabilities({'west': 1.0}, ['N']) == (None, 0.0)


def test_decide_request_shape():
    body = ml.build_decide_request((1, 2), 'E', ['N', 'E'], ml.Marks(), (4, 4))
    q = body['questions'][0]
    assert q['type'] == 'choice' and q['options'] == ['north', 'east']
    marker = '\nAllowed answers and rubric: '
    assert marker in q['instructions']          # 가이드의 루브릭 마커와 정확히 일치해야 한다
    rubric = json.loads(q['instructions'].split(marker)[1])
    assert set(rubric) == {'north', 'east'}
    assert 'closer to the exit' in rubric['north']


def simulate(choose):
    """실제 미로 배치에서 판단 로직만 돌려 본다 (물리 없이 칸 단위)."""
    maze, cell, exit_cell = load_maze()
    marks, heading, moves = ml.Marks(), 'E', 0
    while 0 <= cell[0] < 5 and 0 <= cell[1] < 5:
        # 노드와 같은 순서(앞·왼쪽·오른쪽·뒤)로 열린 방향을 만든다
        open_dirs = [ml.rel_to_abs(heading, rel) for rel in ('front', 'left', 'right', 'back')
                     if ml.rel_to_abs(heading, rel) in maze[cell]]
        opts = ml.candidates(open_dirs, cell, marks)
        exits = [d for d in opts if not (0 <= ml.neighbor(cell, d)[0] < 5 and 0 <= ml.neighbor(cell, d)[1] < 5)]
        d = exits[0] if exits else opts[0] if len(opts) == 1 else choose(cell, heading, opts, marks, exit_cell)
        marks.add(cell, d)
        cell, heading, moves = ml.neighbor(cell, d), d, moves + 1
        assert moves < 100, '탐색이 끝나지 않음'
    return moves


def test_right_hand_fallback_escapes():
    assert simulate(lambda c, h, o, m, e: ml.right_hand_choice(o, h)) == 28 + 1   # 28칸 + 출구 1칸


def test_closer_to_exit_heuristic_escapes():
    # OpenJev 가 루브릭의 'closer to the exit' 를 따른다고 가정한 이상적인 경우
    def closer(c, h, opts, m, e):
        return min(opts, key=lambda d: abs(e[0] - ml.neighbor(c, d)[0]) + abs(e[1] - ml.neighbor(c, d)[1]))
    assert simulate(closer) <= 28 + 1


def test_openjev_client_rejects_bad_shapes(monkeypatch):
    from turtlebot3_maze import openjev_client as oc

    class Resp:
        status_code = 200
        text = '{}'

        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

    c = oc.OpenJevClient('http://x')
    for body in ({'answers': []}, {'answers': [{'noul': 0.5}]}, {'answers': [{'probabilities': [1]}]}):
        monkeypatch.setattr(oc.requests, 'post', lambda *a, b=body, **k: Resp(b))
        try:
            c.decide({})
        except oc.OpenJevError:
            continue
        raise AssertionError(f'통과하면 안 됨: {body}')
