# Vercel + Supabase + Vast GPU 워커 기반 추론 자동화 아키텍처 (Option 2)

## 목적
- Vercel에서 호스팅되는 Admin 페이지에서 **버튼 한 번으로 대량 이미지 추론 실행**
- GPU 추론은 Vast AI 인스턴스에서 수행
- SSH 기반 수동 작업 제거
- 이미지 단위(1장씩) 순차 추론
- 작업 큐, 상태 추적, 결과 다운로드까지 자동화

---

## 전체 아키텍처 개요

### 역할 분리
- **Vercel (Control Plane)**
  - Admin UI 제공
  - 작업(Job / Task) 생성 및 큐잉
  - 워커에 작업 할당
  - Supabase Storage presigned URL 발급
  - 상태 조회 및 다운로드 링크 제공

- **Supabase**
  - **Postgres(DB)**: Job / Task 상태 저장 (큐 역할)
  - **Storage**: 입력 이미지 및 추론 결과 저장

- **Vast GPU Worker (Data Plane)**
  - WAN 추론 실행
  - Vercel에서 발급한 presigned URL로만 파일 접근
  - Supabase 서비스 키 미보유 (보안)

---

## 데이터 모델

### jobs 테이블
| 컬럼 | 설명 |
|----|----|
| id | Job ID |
| status | queued / running / done / failed |
| created_at | 생성 시각 |
| params | (선택) 모델/추론 옵션 |

### tasks 테이블
| 컬럼 | 설명 |
|----|----|
| id | Task ID |
| job_id | 소속 Job |
| input_path | Supabase Storage 입력 이미지 key |
| status | queued / processing / done / failed |
| lease_expires_at | 워커 락 만료 시각 |
| locked_by | 처리 중인 워커 ID |
| output_path | 결과 이미지 key |
| error | 실패 시 에러 메시지 |
| created_at | 생성 시각 |
| updated_at | 수정 시각 |

> `status + lease_expires_at` 조합으로 DB 기반 큐 및 워커 장애 복구 구현

---

## API 설계 (Vercel)

### 1. Job 큐잉 (Admin 전용)
POST /api/jobs/:jobId/enqueue

yaml
코드 복사
**역할**
- Admin UI에서 선택한 이미지들을 Task로 생성
- status = `queued` 로 tasks 테이블에 insert

**입력**
- input_paths: string[] (Supabase Storage object keys)

**출력**
- 생성된 task 개수
- job 상태 업데이트 결과

---

### 2. 다음 Task 요청 (Worker)
POST /api/worker/next-task

diff
코드 복사
**역할**
- 워커가 처리할 다음 Task 1개를 안전하게 할당받음
- DB에서 원자적으로 Task를 lock

**입력**
- worker_id (UUID)

**동작**
- status = `queued`
  또는
- status = `processing` AND lease_expires_at < now()

중 하나를 선택
- status → `processing`
- locked_by = worker_id
- lease_expires_at = now() + lease_duration

**출력**
- task_id
- job_id
- input_path
- params (필요 시)

---

### 3. Presigned URL 발급 (Worker)
POST /api/worker/presign

markdown
코드 복사
**역할**
- 워커에게 Supabase Storage 접근용 단기 URL 발급

**입력**
- task_id
- type: download_input | upload_output
- (upload 시) content_type, filename

**동작**
- Vercel 서버에서 Supabase Service Role Key 사용
- signed download / upload URL 생성

**출력**
- url
- expires_at
- output_path (upload 시)

---

### 4. Task 결과 보고 (Worker)
POST /api/worker/report

yaml
코드 복사
**역할**
- Task 처리 결과 상태 반영

**입력**
- task_id
- status: done | failed
- output_path (done 시)
- error (failed 시)

**동작**
- tasks 상태 업데이트
- job 전체 상태 갱신 (모든 task done → job done)

---

## Worker 실행 흐름 (Vast GPU 인스턴스)

1. `next-task` 호출 → Task 1개 수령
2. `presign(download_input)` → 입력 이미지 다운로드
3. 전처리 (리사이즈 / 패딩 등)
4. WAN 추론 실행 (1장)
5. `presign(upload_output)` → 결과 업로드
6. `report(done)` 또는 `report(failed)`
7. 반복

### Lease / 장애 대응
- Task 처리 시간이 길 경우 heartbeat 또는 lease 연장 필요
- 워커 장애 시 lease 만료 후 자동 재큐잉

---

## Admin UI 기능 (최소)

- Storage 이미지 목록 조회
- 이미지 선택 후 “Run Inference” 버튼
- Job / Task 상태 실시간 표시
- 완료된 결과 다운로드 버튼
- 실패 Task 재시도 버튼

---

## 보안 정책

- Supabase **Service Role Key는 Vercel 서버에만 존재**
- 워커는 presigned URL만 사용
- presigned URL 만료 시간 짧게 유지
- 워커 ↔ Vercel API 통신 시 Bearer Token 인증
- Supabase Storage 버킷은 Public 비활성화

---

## 장점

- SSH 완전 제거
- 워커에 민감한 키 미보유
- Vercel UI 기반 완전한 컨트롤
- 워커 장애에도 작업 유실 없음
- 대량 이미지 순차 처리 가능

---

## 한계 및 주의점

- DB 큐는 초고속 대규모 처리에는 한계
- Vercel 장애 시 새 작업 할당 불가
- 추론 환경은 반드시 Docker 등으로 고정 필요

---

## 핵심 요약 (한 줄)
**Vercel은 작업을 관리하고 URL을 발급하며, Vast 워커는 URL로 이미지를 받아 한 장씩 추론하고 결과를 다시 업로드한다