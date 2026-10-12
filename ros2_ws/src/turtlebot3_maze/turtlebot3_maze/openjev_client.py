"""OpenJev 판정 API 호출 (docs/learn/openjev_guide/Jev 호출 가이드.md).

ros2-dev 컨테이너에서 Mac 의 Docker OpenJev(CPU)를 부를 때 주소는
http://host.docker.internal:31001 이다 (Mac 에서는 http://127.0.0.1:31001).
CPU 버전은 선택지 하나당 약 3초가 걸리므로 반드시 별도 스레드에서 호출한다.
"""
import requests


class OpenJevError(RuntimeError):
    pass


class OpenJevClient:
    def __init__(self, base_url, timeout=60.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def health(self):
        try:
            r = requests.get(f'{self.base_url}/health', timeout=5)
            r.raise_for_status()
            return r.json().get('status') == 'ok'
        except requests.RequestException:
            return False

    def decide(self, body):
        """/v1/decide 호출 → 첫 질문의 확률 dict {옵션: p}."""
        try:
            r = requests.post(f'{self.base_url}/v1/decide', json=body, timeout=self.timeout)
        except requests.RequestException as e:
            raise OpenJevError(f'연결 실패: {e}') from e
        if r.status_code != 200:
            raise OpenJevError(f'HTTP {r.status_code}: {r.text[:200]}')
        try:
            probs = r.json()['answers'][0]['probabilities']
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise OpenJevError(f'예상과 다른 응답: {r.text[:200]}') from e
        if not isinstance(probs, dict) or not all(isinstance(v, (int, float)) for v in probs.values()):
            raise OpenJevError(f'확률 형식 오류: {probs}')
        return probs
