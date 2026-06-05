# 소마 에이전트 (Soma Agent)

SW마에스트로 부산 연수생을 위한 RAG 기반 AI 챗봇.
OT 자료와 홈페이지 공지사항에서 정보를 검색해 자연어 질문에 즉시 답변한다.

**팀:** 사다리 (김응현, 김진, 노기현, 배재현, 박태원)

---

## 프로젝트 구조

```
.
├── run.py                        # 서버 실행 진입점
├── requirements.txt
├── .env.example
│
├── src/
│   ├── config.py                 # 환경변수 중앙 관리
│   ├── embed.py                  # 크롤링 문서(.md) 임베딩
│   ├── embed_pdf.py              # PDF 파싱 → 청킹 → 임베딩
│   ├── ingest_chroma.py          # data/raw + data/embeddings → ChromaDB 적재
│   │
│   ├── agent/                    # LangGraph 오케스트레이션
│   │   ├── state.py              # AgentState TypedDict
│   │   ├── prompts.py            # 시스템·노드별 프롬프트
│   │   ├── llm.py                # Upstage LLM / 임베딩 공용 클라이언트
│   │   ├── graph.py              # 그래프 조립 + 컴파일 (싱글톤)
│   │   └── nodes/
│   │       ├── router.py         # 의도 분류 (5종)
│   │       ├── handle_general.py # 일반 대화 응답
│   │       ├── handle_irrelevant.py  # 소마 무관 거절
│   │       ├── retrieve.py       # ChromaDB 벡터 검색
│   │       ├── generate_answer.py    # RAG 답변 생성
│   │       ├── generate_summary.py   # 다중 문서 요약
│   │       ├── format_schedule.py    # 일정·링크 구조화 추출
│   │       └── handle_not_found.py   # 검색 실패 안내
│   │
│   ├── session/                  # 세션 관리
│   │   ├── models.py             # Session 데이터클래스
│   │   └── manager.py            # 인메모리 SessionManager (TTL 30분)
│   │
│   └── api/                      # FastAPI
│       ├── main.py               # 앱 진입점 + 만료 정리 스레드
│       ├── schemas.py            # 요청·응답 Pydantic 모델
│       └── routes/
│           ├── sessions.py       # POST/GET/DELETE /sessions
│           └── chat.py           # POST /chat/{session_id}
│
├── sadari_front/                 # Streamlit UI + Docker 실행 구성
│   ├── Dockerfile                # 루트 API와 UI 공용 이미지
│   ├── docker-compose.yml        # FastAPI + Streamlit 컨테이너 실행
│   └── app/
│       └── ui.py                 # 세션 기반 채팅 UI
│
├── data/                         # 런타임 생성 (git 제외)
│   ├── raw/                      # PDF → 텍스트·마크다운 원문
│   ├── embeddings/               # .npy + .json 임베딩 파일
│   └── chroma/                   # ChromaDB 영구 저장소
│
└── docs/
    └── PRD_orchestration.md      # 오케스트레이션 설계 문서
```

---

## 런타임 워크플로우

```
User Query
    │
    ▼
[router] ── 의도 분류
    ├─ general          → 일반 대화 응답
    ├─ soma_unrelated   → 소마 무관 거절
    └─ soma_* ──────────→ [retrieve_documents] (ChromaDB 검색)
                                 ├─ 결과 없음 → 공식 계정 안내
                                 └─ 결과 있음
                                      ├─ soma_query     → RAG 답변 + 출처
                                      ├─ soma_summarize → 다중 문서 요약
                                      └─ schedule_link  → 일정·링크 추출
```

---

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
# .env 에서 UPSTAGE_API_KEY 입력
```

### 3. 문서 임베딩 및 ChromaDB 적재

```bash
# PDF 파싱 + 임베딩
python -m src.embed_pdf /path/to/file.pdf --name 파일명

# 크롤링 문서(.md) 임베딩
python -m src.embed

# ChromaDB 에 적재
python -m src.ingest_chroma

# 전체 초기화 후 재적재
python -m src.ingest_chroma --reset
```

### 4. 서버 실행

```bash
# 기본 실행
python run.py

# 개발 모드 (핫 리로드)
python run.py --reload

# 포트 변경
python run.py --port 9000
```

서버 기동 후 `http://localhost:8000/docs` 에서 Swagger UI 확인.

### 5. Streamlit UI + API Docker 실행

```bash
cd sadari_front
cp ../.env.example ../.env
# ../.env 에서 UPSTAGE_API_KEY 입력
docker compose up --build
```

- Streamlit UI: `http://localhost:8501`
- FastAPI docs: `http://localhost:8000/docs`

---

## API

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/sessions` | 새 세션 생성 → `session_id` 반환 |
| `GET` | `/sessions/{session_id}` | 세션 정보 조회 |
| `DELETE` | `/sessions/{session_id}` | 세션 삭제 |
| `POST` | `/chat/{session_id}` | 메시지 전송 및 응답 수신 |
| `GET` | `/health` | 헬스체크 |

### 대화 예시

```bash
# 1. 세션 생성
SESSION=$(curl -s -X POST http://localhost:8000/sessions | python -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# 2. 질문
curl -s -X POST http://localhost:8000/chat/$SESSION \
  -H "Content-Type: application/json" \
  -d '{"message": "이번 달 필수 제출 서류 뭐야?"}' | python -m json.tool
```

---

## 기술 스택

| 역할 | 기술 |
|------|------|
| 오케스트레이션 | LangGraph |
| API 서버 | FastAPI + Uvicorn |
| 임베딩 | Upstage Solar Embedding |
| LLM | Upstage Solar Pro |
| 벡터 DB | ChromaDB (로컬) |
| 문서 파싱 | pypdf |
| 프론트엔드 | Streamlit (별도) |
