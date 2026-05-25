# 🗺️ AI Coding Test Assistant — 개발 계획

## 현재 완료된 것

- [x] 프로그래머스 문제 페이지 자동 인식 (활성 탭 제목 폴링)
- [x] pywinauto 기반 크롬 주소창 URL 추출 (클립보드 무관, 백그라운드 탭 대응)
- [x] Playwright Headless Chromium으로 SPA 문제 페이지 DOM 파싱
- [x] 3단계 도움 흐름 — 키워드 힌트 / 단계별 접근법 / Python 정답 코드
- [x] 단계별 프롬프트 가드 분리 (힌트는 알고리즘명 금지, 접근법은 시간복잡도까지 명시 등)
- [x] 자유 질문 입력으로 모르는 부분 추가 설명
- [x] LLM Provider 추상화 (`BaseLLMClient` → OpenAI / Gemini 환경변수 한 줄로 전환)
- [x] 응답 캐싱 (`response_cache`, 문제 변경 시 자동 초기화)
- [x] 문제 감지 시점에 hint·approach·solution 병렬 프리패치 (`asyncio.gather`)
- [x] 스트리밍 엔드포인트에도 캐시 적용 — 히트 시 단일 청크 즉시 반환
- [x] PyQt6 드래그 가능 플로팅 위젯 (항상 위, 어디서든 호출)
- [x] Pygments(Monokai) 기반 정답 코드 하이라이팅
- [x] 시행착오 의사결정 기록 — Vision LLM → URL 파싱, pyperclip → pywinauto, httpx → Playwright, Gemini → OpenAI
- [x] 데모 영상 제작 (YouTube)

---

## Phase 1 — 정량 지표 추가

- [ ] 캐시 히트 / 미스 평균 응답 시간 측정 (ms 단위)
- [ ] 프리패치 도입 전후 첫 요청 응답 시간 비교 (% 단축)
- [ ] Vision LLM 방식 vs URL 파싱 방식 정확도·비용 비교 표 작성
  - 인식 실패율, 1회 호출당 비용, 평균 추출 시간
- [ ] OpenAI vs Gemini 무료 티어 응답 품질 간이 비교 (동일 문제 10개 기준)
- [ ] 측정 결과를 README 시행착오 섹션 각 항목에 인라인 삽입

---

## Phase 2 — 문서·사용성 보강

- [ ] 상단 TL;DR 한 줄 요약 추가 ("프로그래머스 문제 페이지를 자동 인식해 단계별 힌트·접근법·정답을 제공하는 데스크톱 위젯")
- [ ] 5~10초 짧은 GIF 추가 — 위젯 호출부터 답변 표시까지
- [ ] 트러블슈팅 / FAQ 섹션
  - Playwright Chromium 설치 실패 대응
  - pywinauto가 크롬 탭 못 찾는 경우
  - 무료 티어로 복귀하는 방법 (LLM_PROVIDER 전환 가이드)
- [ ] LICENSE 파일 추가 (MIT 권장)
- [ ] 무료 티어 복귀 가능성을 별도 섹션으로 분리해 강조

---

## Phase 3 — 기능 확장

- [ ] PyInstaller + Inno Setup 인스톨러 배포
  - Playwright Chromium 바이너리(~200MB) 번들링 처리
  - 첫 실행 시 자동 다운로드 옵션도 비교 검토
- [ ] 백준 / 리트코드 셀렉터 추가
  - 사이트별 파서를 Strategy 패턴으로 분리
  - URL 패턴 매칭으로 자동 라우팅
- [ ] RAG 도입 재검토
  - 백준 골드 이상 문제군에서 RAG 유/무 정답률 측정
  - marginal 개선이 시스템 복잡도 대비 유의미한지 정량 판단
  - 도입 결정 시 ChromaDB + 알고리즘 패턴 임베딩 구조 설계

---

## Phase 4 — 운영 관점 개선

- [ ] 캐시 영속화 — 메모리 딕셔너리에서 SQLite 또는 Redis로 이전
- [ ] 토큰 사용량 / 비용 추적 로깅 (일별 누적)
- [ ] 사용자 풀이 코드 vs 정답 코드 diff 비교 기능
- [ ] LangSmith 또는 자체 로깅으로 프롬프트별 응답 품질 추적

---