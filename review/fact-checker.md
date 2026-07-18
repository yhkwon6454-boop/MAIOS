# 제1관문 검토 보고 — Fact Checker (검토자 1)

- 검토자: Fact Checker (제1관문 사실성, 1번 검토자)
- 대상: `docs/MAIOS_단행본.ko.html` (전문 — 본문·표·그림 캡션·SVG 내부 텍스트·코드 블록 포함)
- 검토 일자: 2026-07-18
- 적용 헌장: `review/review-charter.md` (공통 규칙 7항 및 저자 확정 논제)

## 지적 사항

| # | 위치 | 지적(원문 인용 포함) | 근거 | 제안 | 심각도 |
|---|---|---|---|---|---|
| 1 | 2장 4절 그림 2 (SVG 툴팁 첫 데이터 점 및 축 주석) | 첫 데이터 점 툴팁이 `"Sprint 12-3 (Cognitive Loop): 347"`, 축 주석이 `"S12-3부터 S21까지 18개 지점, 347→506"`으로 347을 스프린트 12-3의 테스트 수로 귀속시킴. 그러나 스프린트 12-3 커밋(`7e14553`, cognitive loop) 시점의 실제 테스트 수는 **362**다. 347은 그 직전 커밋(`c4bb347`, world model — 12-3 이전)의 수치다. | 각 커밋을 git worktree로 체크아웃해 `pytest --collect-only`로 실측: `c4bb347`=347, `7e14553`=**362**, `9ece61c`(12-4)=374, `c4f7abc`(13-1)=382, `95f41d2`(13-2)=392 … 이후 13개 지점(374·382·392·402·422·472·478·480·481·490·495·506)은 그림과 전부 일치, 첫 점만 불일치. 본문 서술 "347개에서 출발해"(c2-4)는 스프린트 착수 전 기준선으로 읽으면 참이나, 그림은 347을 12-3 완료 수치로 표기함. | 첫 점을 "S12-3 착수 전 기준선: 347"로 명시하거나 12-3 점 값을 362로 수정. 동일 데이터가 `docs/PAPER.ko.html` 그림 2에도 그대로 있으므로(검토 범위 밖이나) 함께 수정 권고. | P1 |
| 2 | 4장 3절 "정직하게 남겨야 하는 것들" | "그중 지휘관 의도 핵심부만 발췌한 **66개 트리플**짜리 축약본을 썼다" — 저장소에 실재하는 유일한 발췌 온톨로지 `examples/mission_command_intent_core.ttl`(스스로 "실증에 사용한 것과 **동등한** 발췌본"이라 밝힘)을 rdflib로 파싱하면 **71트리플**이다. 실험에 실제 사용된 `.maios/ontology.ttl` 원본은 저장소에 없어 66이라는 수치를 1차 사료로 확인할 수 없다. | `rdflib.Graph().parse('examples/mission_command_intent_core.ttl')` → `len(g)=71` 실측. 66은 CHANGELOG("an excerpt (66 of ~180 triples)")·PAPER.ko.md 7절("66트리플 축약본")과는 일치하나, 세 문서가 같은 자기 서술을 공유할 뿐 실물 파일과는 어긋남. [확인필요] | 실험에 쓴 파일 기준 66이 맞는지 저자가 재확인하고, 맞다면 examples 파일과의 차이(온톨로지 헤더 선언 등 5트리플)를 각주로, 아니라면 수치를 실물에 맞게 수정. | P2 |

## 문제 없음이 확인된 주요 수치·사실 (검사 흔적)

- **버전·날짜**: v1.1.0 및 v1.2.0 릴리스 2026-07-09, v1.3.0 릴리스 2026-07-10(각각 `dfaa561`·`4977be0`·`78293ac`), `VERSION`=1.3.0, `maios --version # 1.3.0` — git log·`VERSION`·`pyproject.toml(version="1.3.0")` 일치. "v1.3.0 릴리스 같은 날 몇 시간 뒤" TF 가중(스프린트 18, `d8757f6` 07-10 05:44)이 v1.3.0(07-10 00:07) 이후이며 CHANGELOG상 Unreleased(develop 미릴리스) — 본문 서술과 일치.
- **테스트·커버리지**: 현재 HEAD에서 전체 수트 실행 — **506 passed, 분기 포함 커버리지 95.93%**(책의 "506개·95.9%" 일치). `pyproject.toml`: `--cov-fail-under=95`, `branch=true`, `omit=["src/maios/cli.py"]` — "분기 커버리지 95% 게이트"·"CLI 진입 모듈 산정 제외" 일치. 그림 2의 "이틀(2026-07-09~07-10)·18개 지점"도 커밋 시각(12-3: 07-09 12:55 → 21: 07-10 10:38)과 일치.
- **3장 실측 수치**: 33파일·728KB·389청크, 수정 전 20초에 69노드, 단일 노드 6.7MB, 그래프 12.7MB→888KB, 흡수 0.9초, 반복 질의 1.2초 — `docs/PAPER.ko.md` 6절(23-26, 215-242행)과 전부 일치. 노드당 8,000자 캡은 코드 실측(`cognitive_loop.py:351`, `world_model.py:379`의 `[:8000]`) 일치.
- **스프린트 대응**: 12-3(인지루프)~21(의도 정렬)의 기능-스프린트 대응이 `docs/산출물목록.ko.md` 3절 및 git 커밋(05903f1=14-1 워크스페이스, 2481e46=14-2 실행기, f8ff55e=14-3 셸, 4236dff=15-1 회상, 3984147=15-2 분해, c1d6a06=15-3 리서치, 4e22e9c=16-1 흡수, 50e6903=16-2, b5d12ae=17, 92b8212=19, a49ae2c=20, 7a01f68=21)과 일치.
- **4장**: 원본 스키마 "약 180트리플"·라벨 중복("지휘관의도"/"지휘관 의도") 섀도잉·"포병⊑화력지원"이 합성 통제 온톨로지였다는 서술 — CHANGELOG Unreleased 및 ttl 파일 헤더와 일치. J1/J2/J4 구현·J3 미구현(실LLM 필요) — CHANGELOG 일치. intent.json 5필드(purpose·end_state·key_tasks·constraints·acceptable_risks)=`intent_alignment.py:24-28`, `ontology_risk_labels` 키=`agi_foundation.py:152`, 워크스페이스의 `ontology.ttl`·`intent.json`·`governance.json` 자동 감지=`workspace.py:31-52` — 코드와 일치. 그림 7의 논문 절 번호(J1→7.2, J2→7.3, J4→7.4)도 PAPER 목차와 일치.
- **5장 사건 일지**: 결제 잠금 발생 2026-07-10경("v1.3.0 릴리스한 바로 그날"), "Too many login attempts on this Link account", 07-13 오전(08:30) Kelvin 회신·같은 날 저녁(18:38) 재답장, 나흘 무응답 후 07-17 팔로업, 07-14 API 키 "maios" 만료 예고 메일(07-16 만료 예정="이틀 뒤"), 07-17 키 정상·모델 목록 조회 성공·`credit balance is too low` 응답 — 프로젝트 기록(auto-memory `project_maios_payment.md`)과 전부 일치. "27개 파일 커밋"은 `5dcaccc`(2026-07-17) `git show --stat` 실측 **27 files changed** 일치(온톨로지 발췌본 신규 포함, README·ARCHITECTURE 정정 포함).
- **6장**: 기본 의존성 중 LLM SDK는 openai뿐(`pyproject dependencies`), `pip install anthropic`/`google-genai` extras 실재, 환경변수명 ANTHROPIC_API_KEY·OPENAI_API_KEY·GEMINI_API_KEY=`config.py`·`.env.example` 일치, `--max-cycles` 기본 3=`cli.py:93`, 고위험 키워드 "deploy, delete, production 등"=`governance/manager.py:127`(실제 deploy·delete·external·production, "등"으로 포섭), `validate_live.py --provider mock` 옵션 실재, 워크스페이스 파일명 5종·GP-/PJ- 접두=`workspace.py`·`agi_foundation.py` 일치, CLI 출력 태그([governance]·[recall]·[ontology]·[alignment]·[verdict]·[memory] 등) 전부 `cli.py`에 실재. Python 3.11/3.12는 `requires-python>=3.11`+분류자·CI(3.11/3.12)와 부합.
- **저장소·문서**: `github.com/yhkwon6454-boop/MAIOS`·develop 브랜치=`git remote`·`git branch` 일치. 각주·상태 블록의 자매 문서 5종(MANUAL.ko.html, PAPER.ko.html, BOOK_NARRATIVE.ko.html, MAIOS_통합본.ko.html, MAIOS_책_v1.docx) 모두 `docs/`에 실재. README의 AGIFoundation 각주("orchestration layer, not artificial general intelligence") 실재(README.md:36-39).
- **서지 노트 12건**: AutoGPT(Significant Gravitas, 2023)·LangChain(H. Chase, 2022)·AutoGen(arXiv:2308.08155)·CrewAI(J. Moura, 2023)·MemGPT(arXiv:2310.08560)·Reflexion(arXiv:2303.11366, NeurIPS 2023)·Generative Agents(arXiv:2304.03442, UIST 2023)·Laird(Soar, MIT Press 2012)·Anderson(OUP 2007)·Rao & Georgeff(ICMAS 1995)·Salton & Buckley(IP&M 24(5), 1988) — 검토자 지식 범위에서 연도·번호·저자·출판사 모두 정확. Auftragstaktik 철자 정확. (저장소로 검증 불가한 외부 사실이나 오류 징후 없음.)

---

총 2건 (P0 0 / P1 1 / P2 1)
