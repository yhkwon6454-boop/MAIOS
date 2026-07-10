# MAIOS 사용 설명서

MUSA AI Operating System — 임무 중심 인지형 AI 운영체제 매뉴얼 (v1.3 기준)

---

## 1. MAIOS란 무엇인가

MAIOS는 "AI를 도구로 쓰는 것"과 "AI를 임무 중심으로 운용하는 것"의 차이에서
출발한 로컬 AI 운영체제입니다. 챗봇은 대화가 끝나면 잊지만, MAIOS는:

- **기억합니다** — 모든 목표 수행, 교훈, 지식이 워크스페이스에 영속 저장됩니다.
- **회상합니다** — 새 목표를 받으면 과거의 경험·문서·성찰을 스스로 찾아 반영합니다.
- **일합니다** — LLM을 연결하면 요약·번역·초안 작성 같은 실제 산출물을 만듭니다.
- **성찰합니다** — 매 수행 후 교훈을 추출해 다음 수행에 주입합니다.
- **통제받습니다** — 고위험 목표는 거버넌스가 차단하고 인간 승인을 요구합니다.

### 핵심 개념 세 가지

| 개념 | 설명 |
|---|---|
| **인지 루프** | 모든 목표는 관찰→이해→계획→행동→성찰→학습 6단계를 거칩니다 |
| **워크스페이스** | `.maios/` 디렉터리 = 장기 기억. 지식그래프·수행일지·산출물이 여기 삽니다 |
| **폴백 설계** | LLM이 없어도 모든 기능이 규칙 기반으로 동작합니다 (품질은 낮아짐) |

---

## 2. 설치

Python 3.11 또는 3.12가 필요합니다.

```bash
git clone https://github.com/yhkwon6454-boop/MAIOS.git
cd MAIOS
python -m venv .venv

# Windows
.\.venv\Scripts\python.exe -m pip install -e .[dev]
# macOS/Linux
.venv/bin/python -m pip install -e .[dev]
```

설치 확인:

```bash
maios --version        # 1.3.0
```

### LLM 연결 (선택이지만 강력 권장)

`.env.example`을 `.env`로 복사하고 사용할 프로바이더의 키를 넣습니다:

```ini
ANTHROPIC_API_KEY=sk-ant-...     # Claude
OPENAI_API_KEY=sk-...            # GPT
GEMINI_API_KEY=...               # Gemini
```

키 없이도 모든 명령이 동작하지만, 산출물 생성·목표 분해·상황 이해가
규칙 기반으로 대체됩니다. `--llm mock`은 오프라인 테스트용 가짜 모델입니다.

---

## 3. 5분 훑어보기

```bash
# 1) 목표 하나 수행 (거버넌스 → 인지 루프 → 교훈 축적)
maios pursue "주간 보고서를 세 문장으로 요약"  --llm claude

# 2) 내 문서를 지식으로 흡수 (md/txt/html, 한글 인코딩 자동)
maios ingest ~/내문서폴더

# 3) 흡수한 지식 위에서 연구
maios research "우리 문서에서 드론 방어의 핵심 교훈은?"

# 4) 큰 목표를 하위 목표로 쪼개 순차 수행 후 종합
maios project "드론 위협 분석 2부작 브리핑 작성" --llm claude

# 5) 시스템 자기 점검
maios introspect

# 6) 대화형 세션 (가장 편한 사용법)
maios shell --llm claude
```

모든 명령 끝에 `[memory] nodes=N pursuits=M`이 출력됩니다 —
기억이 쌓이는 것이 눈에 보입니다.

---

## 4. 명령어 상세

### 4.1 `maios pursue <목표>` — 단일 목표 수행

목표 하나를 인지 루프 전체에 태웁니다.

```bash
maios pursue "국방 AI 동향을 다섯 줄로 정리" --llm claude
```

출력 해설:

```text
[MAIOS] objective: ...            목표
[governance] risk=LOW approved=True   거버넌스 심사 결과
[cycles] 1 executed               실행된 인지 사이클 수
  cycle 1: COMPLETED (observe -> understand -> ... -> learn)
  [recall] ...                    과거 기억에서 회상한 항목
  [understanding] ...             LLM의 상황 해석 (--llm 사용 시)
[lessons]                         이번 수행에서 추출된 교훈
[output] ...                      생성된 산출물 미리보기 (500자)
[artifact] .maios\artifacts\GP-xxxx.md   산출물 전문 파일
[status] COMPLETED
[memory] nodes=15 pursuits=3      누적 기억 현황
```

옵션:

| 옵션 | 설명 |
|---|---|
| `--llm PROVIDER` | mock / openai / claude / gemini |
| `--capability NAME` | 요구 능력 지정, 반복 가능 (예: research) |
| `--max-cycles N` | 실패 시 재시도 사이클 상한 (기본 3) |
| `--approve` | 고위험 목표에 인간 승인 부여 |
| `--workspace DIR` | 워크스페이스 위치 (기본 `.maios`) |

### 4.2 `maios project <목표>` — 다단계 프로젝트

큰 목표를 LLM이 하위 목표 목록으로 분해하고, 순차 수행하면서
**앞 단계의 산출물을 뒤 단계에 전달**한 뒤, 최종 종합본을 만듭니다.

```bash
maios project "신간 서평 작성: 자료 조사 후 초안" --max-subgoals 4 --llm claude
```

- 하위 목표 하나가 실패하면 거기서 중단하고 프로젝트는 FAILED가 됩니다.
- 종합 산출물은 `artifacts/PJ-xxxx.md`로 저장됩니다.
- LLM이 없으면 분해 없이 단일 목표로 수행됩니다.

### 4.3 `maios research <질문>` — 자기 지식 연구

지식그래프(흡수한 문서 + 축적된 경험·성찰)를 소스로 연구 보고서를 만듭니다.

```bash
maios ingest ~/책원고
maios research "원고 전체를 관통하는 핵심 주장은?"
```

보고서는 하위 질문·발견·공백·출처 구조의 마크다운으로 산출되며,
**보고서 자체가 다시 지식그래프에 들어가** 다음 연구의 소스가 됩니다.
출처 선정은 문서·개념·근거를 시스템 자신의 활동 기록보다 우선합니다.

### 4.4 `maios ingest <경로>` — 문서 흡수

로컬 문서를 지식그래프의 회상·연구 가능한 노드로 만듭니다.

```bash
maios ingest 보고서.md 메모.txt          # 개별 파일
maios ingest ~/문서폴더                   # 디렉터리 재귀
```

- 지원 형식: `.md` `.txt` `.html` (HTML은 태그·스크립트 제거)
- 마크다운은 제목(`#`) 단위, 텍스트는 문단 단위로 분할 (긴 절은 1,200자)
- 한글 cp949 인코딩 파일 자동 처리
- **같은 파일을 다시 흡수하면 중복 없이 갱신**됩니다 (경로 기반 결정적 ID)
- 대량 흡수는 벌크 모드로 동작합니다 (33개 파일 389청크 기준 약 1초)

### 4.5 `maios introspect` — 자기 점검

시스템이 자기 구성을 보고합니다.

```text
$ maios introspect --llm claude
[MAIOS] identity=maios version=1.3.0 readiness=0.64
[available] cognitive_loop, executive_brain, governance, knowledge_graph, llm, ...
[missing] distributed_runtime, negotiation, swarm, ...
```

(`--llm` 없이 실행하면 llm·task_execution 등이 missing으로 이동하고
readiness가 낮게 나옵니다 — 정상입니다.)

readiness는 전체 계층 중 가용 계층의 비율입니다. missing 항목은
해당 엔진이 주입되지 않았다는 뜻이며 오류가 아닙니다.

### 4.6 `maios shell` — 대화형 세션 (권장 사용법)

한 세션에서 연속으로 목표를 수행하며 기억을 공유합니다.

```bash
maios shell --llm claude
```

```text
maios> 오늘 회의록 요약해줘              ← 일반 목표
maios> /ingest ~/회의록모음              ← 문서 흡수
maios> /research 최근 회의의 반복 쟁점은?  ← 연구
maios> /project 월간 보고서 초안 작성      ← 프로젝트
maios> /history                          ← 최근 수행 이력
maios> /introspect                       ← 자기 점검
maios> /evolve                           ← 누적 성공률·교훈 보고
maios> /approve                          ← 직전 고위험 목표 승인 재실행
maios> /exit
```

### 4.7 기존 v1.0 명령

```bash
maios mission.yaml     # YAML 미션 파일 실행 (v1.0 런타임 파이프라인)
```

### 4.8 온톨로지 확장 검색 (선택)

워크스페이스에 `ontology.ttl`(RDFS/OWL, rdfs:label 한국어 지원)을 넣으면
회상·연구 검색이 온톨로지 관계를 따라 확장됩니다:

```bash
pip install rdflib                        # 선택 의존성
cp 나의온톨로지.ttl .maios/ontology.ttl    # 워크스페이스에 배치하면 자동 감지
maios pursue "지휘관 의도 전파 실태 점검"
  [ontology] 목적, 최종상태, 핵심과업, 제한사항, ...   ← 확장된 용어
  [recall] 훈련메모.md: ... 최종상태를 서로 다르게 이해 ...
```

질의에 온톨로지 용어가 등장하면 그 이웃(상하위 클래스, 인스턴스,
domain/range로 연결된 개념)이 검색어에 합류합니다 — 표층 단어가 하나도
겹치지 않는 문서도 개념적으로 연결되면 회수됩니다. rdflib이 없거나
파일이 없으면 조용히 기존 검색으로 동작합니다(introspect의 ontology
항목으로 가용 여부 확인).

**온톨로지 기반 거버넌스**: 워크스페이스에 `governance.json`을 두면
특정 온톨로지 개념(과 그 이웃)을 건드리는 목표가 자동으로 고위험으로
분류되어 인간 승인을 요구합니다:

```json
{"ontology_risk_labels": ["제한사항", "수용가능위험"]}
```

```text
maios pursue "제한사항을 넘는 야간 침투 기동 승인"
[governance] risk=HIGH approved=False ...
[status] PENDING_APPROVAL          ← --approve로만 실행 가능
```

"제한과 충돌" 같은 이웃 개념을 언급해도 관계를 타고 상향됩니다 —
임무형지휘의 "제한 속 자유"가 거버넌스 규칙이 되는 방식입니다.

---

## 5. 워크스페이스의 구조

```text
.maios/
├── knowledge_graph.json   지식그래프 (문서·경험·성찰·개념 노드와 관계)
├── memory_store.json      장기 기억 저장소
├── pursuits.json          목표 수행 일지 (교훈·산출물 포함)
├── projects.json          프로젝트 일지
└── artifacts/             산출물 (GP-*.md = 목표, PJ-*.md = 프로젝트)
```

- 전부 사람이 읽을 수 있는 JSON/마크다운입니다.
- 프로젝트마다 다른 워크스페이스를 쓰려면 `--workspace 경로`를 지정하세요.
- 워크스페이스를 지우면 기억이 초기화됩니다 (파일 복사 = 백업).
- **평문 저장**이므로 민감한 문서를 흡수할 때는 보관 위치에 주의하세요.

---

## 6. 거버넌스 (안전장치)

모든 목표는 실행 전에 정책 심사를 받습니다.

| 판정 | 조건 | 동작 |
|---|---|---|
| 승인 | 저위험 | 즉시 실행 |
| PENDING_APPROVAL | 고위험 키워드 (deploy, delete, production 등) | `--approve` 또는 셸 `/approve`로 인간 승인 필요 |
| BLOCKED | 금지 키워드 (운영자 설정) | 실행 거부 |

모든 심사는 감사 로그에 기록됩니다. 프로그래밍 방식으로 키워드·위험 등급을
조정하려면 `GovernanceManager`와 `PolicyEngine`을 직접 구성하세요.

---

## 7. 실전 워크플로우 예시

### 7.1 저술 보조: 내 원고 위에서 일하기

```bash
maios ingest ~/책원고                    # 원고 전체 흡수
maios shell --llm claude
maios> /research 3장과 7장의 논리적 충돌은 없는가?
maios> 4장 도입부를 두 문단으로 다시 써줘   # 회상이 원고 맥락을 주입
maios> /project 출판사 투고용 시놉시스 작성
```

### 7.2 연구 보조: 자료 축적형 리서치

```bash
maios ingest ~/수집자료/                 # 수시로 자료 추가 (재흡수 안전)
maios research "수집 자료에서 상반되는 주장 정리"
# 보고서가 지식그래프에 쌓임 → 다음 연구가 이전 연구를 인용
```

### 7.3 정기 업무: 기억이 쌓이는 요약

매일 실행하면 어제의 교훈·맥락이 오늘 요약에 반영됩니다:

```bash
maios pursue "오늘자 안보 뉴스 다섯 꼭지 요약" --llm claude
```

---

## 8. 파이썬 API

CLI가 하는 모든 일은 코드로도 가능합니다:

```python
from maios.governance import GovernanceManager
from maios.kernel import DocumentIngestor, Workspace
from maios.adapters.llm_provider import create_llm_provider
from maios.config import load_config

config = load_config()
config.model_provider = "claude"
provider = create_llm_provider(config)

space = Workspace(".maios")
agi = space.build_foundation(governance=GovernanceManager(), llm_provider=provider)

DocumentIngestor(agi.knowledge_graph).ingest("~/문서")   # ~ 자동 확장
pursuit = agi.pursue("문서 핵심을 요약", capabilities=())
project = agi.pursue_project("2부작 브리핑 작성")
report = agi.evolve()          # 누적 성공률·교훈
model = agi.introspect()       # 자기 모델
space.save(agi)                # 일지·산출물 저장
```

v1.0 API(`maios.run(goal)`, `MAIOSCore`)도 그대로 사용 가능합니다.

---

## 9. 문제 해결

| 증상 | 원인·해법 |
|---|---|
| `[understanding]`이 안 나온다 | LLM 미연결 또는 호출 실패 → 폴백 동작 중. `.env` 키와 크레딧 확인 |
| `credit balance is too low` | API 크레딧 부족 → 콘솔에서 충전 |
| 산출물이 목표 문장 그대로다 | LLM 없이 실행됨 (echo 폴백). `--llm` 지정 |
| 프로젝트가 하위 목표 1개로 돈다 | LLM의 분해 응답이 목록 형식이 아님 → 실모델에서는 정상 동작 |
| 회상이 엉뚱한 것을 가져온다 | 검색은 한글 바이그램 TF-IDF — 질문에 구체적 명사를 넣을수록 정확 |
| 한글 파일이 깨진다 | UTF-8/cp949 외 인코딩 → UTF-8로 재저장 후 흡수 |
| 흡수가 느리다 | v1.3 미만 버전 사용 중 → 업그레이드 (벌크 모드) |

전체 파이프라인 자가 진단:

```bash
python scripts/validate_live.py --provider mock    # 오프라인 점검
python scripts/validate_live.py                    # 실모델 점검 (키·크레딧 필요)
```

---

## 10. 자주 묻는 질문

**Q. 인터넷 없이 쓸 수 있나?**
LLM 프로바이더 호출을 제외한 전부(흡수·회상·연구·기억)가 오프라인입니다.

**Q. 데이터가 외부로 나가나?**
LLM 호출 시 프롬프트(목표·회상된 기억 일부)가 해당 프로바이더로 전송됩니다.
그 외에는 아무것도 로컬을 떠나지 않습니다.

**Q. AGIFoundation이라는 이름은 AGI라는 뜻인가?**
아닙니다. 아키텍처상 최상위 통합 계층이라는 뜻의 이름이며, 실체는
자율 워크플로우 오케스트레이션 계층입니다.

**Q. 여러 사람이 같이 쓸 수 있나?**
현재는 단일 사용자·단일 머신 설계입니다. 워크스페이스 디렉터리를
공유 저장소에 두는 방식은 동시 쓰기에 안전하지 않습니다.
