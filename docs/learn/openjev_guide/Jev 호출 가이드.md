# openjev API 사용 가이드

다른 서비스에서 openjev 판정 API를 호출하기 위한 연동 문서입니다.

- 모델: `AlexWortega/openjev` / `qwen3.5-4b-nli-v5` (rev `a2044801`, MIT)
- 성격: **NLI 판정(분류) 모델** — 텍스트를 생성하지 않습니다. 입력 문장 쌍/선택지에 대한 **확률**을 돌려줍니다.
- 언어: 영어 학습 모델입니다. 한국어 입력도 동작은 하지만 정확도는 검증되지 않았으므로, 가능하면 영어로 보내세요.

---

## 1. 접속 정보

| 환경 | Base URL | 장치 | 응답 속도(스모크 기준) |
|---|---|---|---|
| Mac 네이티브 (`./serve.sh`) | `http://127.0.0.1:31000` | MPS (GPU) | 빠름 (권장) |
| Docker CPU (`docker compose --profile cpu up -d`) | `http://127.0.0.1:31001` | CPU | 약 5배 느림 |
| Docker CUDA (`--profile cuda`, Linux+NVIDIA) | `http://<host>:31000` | CUDA | 미검증 |

- 인증 없음. 기본은 **localhost 바인딩**이라 같은 머신에서만 접근됩니다.
  - 다른 호스트에서 호출하려면 `model.env`의 `HOST=0.0.0.0`(네이티브) 또는 `compose.yaml`의 `ports`를 `"31001:31000"`으로 바꾸고, 앞단에 인증/방화벽을 두세요.
- Docker 컨테이너(같은 Docker Desktop)에서 네이티브 서버를 부를 때: `http://host.docker.internal:31000`
- OpenAPI 문서: `GET /docs` (Swagger UI), `GET /openapi.json`

## 2. 동작 원리 (확률 해석)

모델은 `Premise`(근거)와 `Hypothesis`(주장)를 받아 3개 라벨의 확률을 냅니다.

| 라벨 | 의미 |
|---|---|
| `entailment` | 근거가 주장을 **뒷받침** |
| `contradiction` | 근거가 주장과 **모순** |
| `neutral` | 근거만으로 **판단 불가** |

- `/v1/rerank`, `/v1/decide`는 선택지마다 문장을 하나씩 만들어 `entailment` 확률을 구한 뒤 사용합니다.
- 같은 입력은 항상 같은 결과(결정적)이며, 선택지 순서를 바꿔도 결과가 바뀌지 않습니다.
- 확률은 보정(calibration)되지 않은 값입니다. 임계값은 서비스 데이터로 직접 정하세요.

## 3. 엔드포인트

공통: `Content-Type: application/json`, 응답에 `model` 필드 포함.

### 3.1 `GET /health`

```json
{"status":"ok","model":"openjev/qwen3.5-4b-nli-v5","path":"...","device":"mps","dtype":"bfloat16","max_length":4096}
```

`status`가 `"ok"`이면 요청 가능. 서비스 기동 시 readiness 체크로 사용하세요.

### 3.2 `POST /v1/nli` — 문장 쌍 판정

근거 문서가 답변/주장을 뒷받침하는지 확인(사실성 검증, 환각 탐지, 답안 채점)에 사용합니다.

요청

```json
{
  "pairs": [
    {"premise": "A man is playing a guitar on stage.", "hypothesis": "Someone is making music."},
    {"premise": "A man is playing a guitar on stage.", "hypothesis": "The stage is empty."}
  ]
}
```

응답 (`results`는 `pairs`와 같은 순서)

```json
{
  "model": "openjev/qwen3.5-4b-nli-v5",
  "results": [
    {"label": "entailment",    "scores": {"contradiction": 0.0004, "entailment": 0.9936, "neutral": 0.0060}},
    {"label": "contradiction", "scores": {"contradiction": 0.9994, "entailment": 0.0005, "neutral": 0.0001}}
  ]
}
```

- `label` = 최고 확률 라벨. 한 요청 최대 256쌍.

### 3.3 `POST /v1/rerank` — 선택지 재정렬

질문에 가장 맞는 답을 고릅니다. 각 선택지는 `hypothesis_format`에 끼워져 판정됩니다.

요청

```json
{
  "question": "What is the capital of France?",
  "options": ["Lyon", "Paris", "Berlin"],
  "hypothesis_format": "The correct answer is: {}"
}
```

- `hypothesis_format`은 선택(기본값 위와 같음). `{}` 자리에 선택지가 들어갑니다. 검색 결과 재정렬이라면 `"This passage answers the question: {}"`처럼 바꿔 쓸 수 있습니다.

응답 (`ranking`은 entailment 내림차순, `index`는 원래 위치)

```json
{
  "model": "openjev/qwen3.5-4b-nli-v5",
  "best_index": 1,
  "best": "Paris",
  "ranking": [
    {"index": 1, "option": "Paris",  "entailment": 0.9992},
    {"index": 0, "option": "Lyon",   "entailment": 0.0033},
    {"index": 2, "option": "Berlin", "entailment": 0.0008}
  ]
}
```

- `entailment`는 선택지별 **독립** 확률이라 합이 1이 아닙니다. 모두 낮으면 "정답 없음"으로 처리하세요.

### 3.4 `POST /v1/decide` — 타입드 결정 (분류·라우팅·정책 판단)

상태(`state`)와 닫힌 선택지 집합을 주면 선택지별 확률(합 = 1)을 돌려줍니다. 한 요청에 질문 여러 개 가능.

| `type` | 용도 | 응답 형태 |
|---|---|---|
| `noul` | 예/아니오 판단. `options`에 `"yes"` 포함 권장 | `{"noul": P(yes)}` |
| `choice` | 다지선다 분류/라우팅 | `{"probabilities": {옵션: p}}` |
| `score` | 등급/점수 선택 (`["1","2","3","4","5"]` 등) | `{"probabilities": {옵션: p}}` |

요청

```json
{
  "state": "Ticket: The customer says the app crashes every time they open the camera screen after the latest update.",
  "questions": [
    {"type": "choice", "instructions": "Which team should handle this ticket?", "options": ["billing", "mobile", "infra"]},
    {"type": "noul",   "instructions": "Is this a bug report?",                 "options": ["no", "yes"]}
  ]
}
```

응답 (`answers`는 `questions`와 같은 순서)

```json
{
  "model": "openjev/qwen3.5-4b-nli-v5",
  "probability_method": "normalized_entailment_v1",
  "answers": [
    {"probabilities": {"billing": 0.0023, "mobile": 0.9906, "infra": 0.0071}},
    {"noul": 0.98}
  ]
}
```

- `state`: 문자열 또는 JSON 객체/배열(서버에서 JSON 문자열로 직렬화). 약 24,000자를 넘으면 창(window) 단위로 나눠 판정하고, 어느 창에서든 뒷받침되면 채택합니다.
- `noul`에서 `"yes"`가 없으면 마지막 옵션의 확률을 돌려줍니다.

#### 루브릭(선택지 설명) 붙이기 — 정확도 향상에 효과적

선택지 이름만으로 모호하면 `instructions` 끝에 아래 마커와 JSON을 붙입니다. 마커 문자열은 **정확히** 일치해야 합니다.

```
<질문>\nAllowed answers and rubric: {"<옵션>": "<설명>", ...}
```

```json
{
  "state": "Policy: refunds require a receipt and purchase within 30 days. The customer bought 12 days ago but has no receipt.",
  "questions": [{
    "type": "noul",
    "instructions": "Under the stated policy, is a refund permitted?\nAllowed answers and rubric: {\"no\": \"A required condition is missing.\", \"yes\": \"Every condition holds.\"}",
    "options": ["no", "yes"]
  }]
}
```

→ `{"answers": [{"noul": 0.0002}]}` (환불 불가)

## 4. 호출 예시

### curl

```sh
curl -s http://127.0.0.1:31000/v1/nli -H 'content-type: application/json' \
  -d '{"pairs":[{"premise":"The invoice was paid on March 3.","hypothesis":"The invoice is unpaid."}]}'
```

### Python (httpx)

```python
import httpx

OPENJEV_URL = "http://127.0.0.1:31000"
client = httpx.Client(base_url=OPENJEV_URL, timeout=60)

def is_supported(evidence: str, claim: str, threshold: float = 0.5) -> bool:
    r = client.post("/v1/nli", json={"pairs": [{"premise": evidence, "hypothesis": claim}]})
    r.raise_for_status()
    return r.json()["results"][0]["scores"]["entailment"] >= threshold

def route(ticket: str, teams: list[str]) -> tuple[str, float]:
    r = client.post("/v1/decide", json={
        "state": ticket,
        "questions": [{"type": "choice", "instructions": "Which team should handle this ticket?", "options": teams}],
    })
    r.raise_for_status()
    probs = r.json()["answers"][0]["probabilities"]
    best = max(probs, key=probs.get)
    return best, probs[best]
```

### TypeScript (fetch)

```ts
const OPENJEV_URL = process.env.OPENJEV_URL ?? "http://127.0.0.1:31000";

type Question = { type: "noul" | "choice" | "score"; instructions: string; options: string[] };
type Answer = { noul: number } | { probabilities: Record<string, number> };

export async function decide(state: string | object, questions: Question[]): Promise<Answer[]> {
  const res = await fetch(`${OPENJEV_URL}/v1/decide`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ state, questions }),
    signal: AbortSignal.timeout(60_000),
  });
  if (!res.ok) throw new Error(`openjev ${res.status}: ${await res.text()}`);
  return (await res.json()).answers;
}
```

## 5. 오류 코드

| 코드 | 원인 | 조치 |
|---|---|---|
| `422` | 요청 스키마 오류 (빈 `pairs`/`options`, 잘못된 `type` 등). `detail`에 위치 표시 | 요청 수정 |
| `413` | `pairs` 또는 `options`가 256개 초과 | 나눠서 요청 |
| `503` | 모델 로딩 중 | `/health`가 `ok`가 될 때까지 재시도 |
| 연결 실패 | 서버 미기동 | `./serve.sh` 또는 `docker compose --profile cpu up -d` |

## 6. 운영·성능 참고

- **요청은 한 번에 하나씩 처리**됩니다(단일 장치, 내부 락). 동시 요청은 대기열처럼 순차 처리되므로, 호출 측 타임아웃을 넉넉히(30~60초) 두세요.
- 비용은 대략 `쌍 수 × 입력 길이`에 비례합니다. `/v1/decide`는 `질문 수 × 선택지 수 × state 창 수`만큼 판정합니다. 선택지를 꼭 필요한 만큼만 두세요.
- 입력은 쌍당 최대 4,096 토큰에서 잘립니다(`MAX_LENGTH`). 긴 문서는 `/v1/decide`(자동 창 분할)를 쓰거나 호출 측에서 청크로 나누세요.
- 서버 설정은 `model.env` 또는 환경변수로 바꿉니다: `PORT`, `HOST`, `DEVICE`(`mps`/`cpu`/`cuda`), `DTYPE`, `MAX_LENGTH`, `BATCH_SIZE`(기본 8), `MAX_PAIRS`(기본 256).

## 7. 주의사항 (모델 카드 기준)

- **프롬프트 인젝션에 취약**: `state`에 "관리자 지시: X라고 답하라" 같은 문장 하나로 정확도가 0.83 → 0.47까지 떨어집니다. 사용자 입력이 섞이는 판정(보안·권한·결제 가드)에는 **규칙 기반 검사와 함께** 쓰고 단독 결정권을 주지 마세요.
- 셸 명령 안전성 판정 같은 미학습 과제는 성능이 낮습니다(정확도 0.60).
- MMLU/ARC/GSM8K 등의 테스트셋이 학습에 포함되어 있어 해당 벤치마크 수치는 의미가 없습니다.
- 생성형 LLM 대체용이 아닙니다. 답을 "만드는" 것은 다른 LLM이 하고, openjev는 그 답을 **검증·선택·분류**하는 역할로 쓰세요.
