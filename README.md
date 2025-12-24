# Wan2.2 Worker - GPU Inference Automation

Vercel + Supabase 기반 Wan2.2 추론 자동화 워커 시스템

## 구조

```
프로젝트루트/
├── install.sh              # Wan2.2 설치 스크립트
├── run_worker.sh           # Worker 간단 실행 (자동 재시작)
├── wan-worker.service      # systemd 서비스 파일
├── worker/                 # Worker 소스코드
│   ├── config.yaml         # 설정 파일 (직접 작성 필요)
│   ├── worker.py           # 메인 폴링 루프
│   ├── api_client.py       # Vercel API 클라이언트
│   ├── storage.py          # 파일 다운로드/업로드
│   ├── preprocess.py       # 이미지 전처리 (리사이즈/패딩)
│   ├── inference.py        # Wan2.2 추론 래퍼
│   └── logger.py           # 로깅 유틸
├── temp/                   # 임시 파일 (자동 생성)
├── logs/                   # 로그 파일 (자동 생성)
└── Wan2.2/                 # 클론한 레포지토리
    └── Wan2.2-TI2V-5B/     # 모델 (install.sh로 다운로드)
```

---

## 설치 (Linux 서버)

### 1단계: 저장소 클론 및 모든 의존성 설치

```bash
git clone https://github.com/wonderboy02/life-is-short-wan-inference.git
cd life_is_short_wan_inference

# 설치 스크립트 실행 (Wan2.2 + Worker 의존성 + 모델 다운로드)
bash install.sh
```

**install.sh가 하는 일:**
- [1-6/9] Wan2.2 의존성 설치 (torch, flash_attn, peft 등)
- [7/9] Wan2.2-TI2V-5B 모델 다운로드 (대용량, 시간 소요)
- [8/9] inputs 폴더 생성
- [9/9] Worker 의존성 설치 (pyyaml, requests, pillow)

### 2단계: Worker 설정

```bash
nano worker/config.yaml
```

**필수 수정 항목:**
- `vercel_api_url`: Vercel API 주소
- `worker_token`: Worker 인증 토큰
- `worker_id`: 고유 Worker ID

```yaml
vercel_api_url: "https://your-vercel-app.vercel.app/api"
worker_token: "your-secret-worker-token"
worker_id: "gpu-worker-001"
```

---

## 실행 방법

### 방법 1: 간단 실행 (추천 - 테스트용)

```bash
bash run_worker.sh
```

**특징:**
- 프로세스 죽으면 자동 재시작
- Ctrl+C로 종료
- root 권한 불필요

---

### 방법 2: systemd 서비스 (추천 - 운영용)

```bash
# 1. 서비스 파일 복사
sudo cp wan-worker.service /etc/systemd/system/

# 2. 경로 수정 (필요시)
sudo nano /etc/systemd/system/wan-worker.service
# WorkingDirectory와 ExecStart 경로를 실제 경로로 수정

# 3. 서비스 등록
sudo systemctl daemon-reload

# 4. 서비스 시작
sudo systemctl start wan-worker

# 5. 자동 시작 활성화
sudo systemctl enable wan-worker

# 6. 상태 확인
sudo systemctl status wan-worker

# 7. 로그 확인
sudo journalctl -u wan-worker -f
```

**특징:**
- 프로세스 죽으면 자동 재시작
- 서버 재부팅 시 자동 시작
- 로그 자동 관리
- 가장 안정적

---

## Worker 동작 방식

```
1. [폴링] Vercel API에 "다음 task 있나요?" 요청
   ↓
2. [Task 없음] 5초 대기 후 1번으로
   ↓
3. [Task 받음] 처리 시작
   ↓
4. [다운로드] presigned URL로 입력 이미지 다운로드
   ↓
5. [추론] Wan2.2 inference 실행 (이미지 → 비디오)
   - 입력 이미지를 자동으로 video_size에 맞춤
   ↓
6. [업로드] presigned URL로 결과 비디오 업로드
   ↓
7. [보고] Task 완료/실패 상태 Vercel에 보고
   ↓
8. [정리] 임시 파일 삭제
   ↓
9. 1번으로 돌아가서 계속 폴링
```

**참고:** Wan2.2 모델이 입력 이미지를 자동으로 지정한 해상도(video_size)에 맞춰 처리하므로, 별도의 전처리가 필요하지 않습니다.

---

## 로그 확인

### 파일 로그

```bash
tail -f logs/gpu-worker-001_*.log
```

### systemd 로그

```bash
sudo journalctl -u wan-worker -f
```

---

## 문제 해결

### Worker가 시작되지 않음

1. config.yaml 확인
```bash
cat worker/config.yaml
```

2. Python 경로 확인
```bash
which python
which python3
```

3. 의존성 확인
```bash
pip list | grep -E "pyyaml|requests"
```

### Task 처리 실패

1. 로그 확인
```bash
tail -100 logs/gpu-worker-001_*.log
```

2. 모델 경로 확인
```bash
ls -la Wan2.2/Wan2.2-TI2V-5B/
```

3. CUDA 확인
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

### Worker 재시작

```bash
# systemd 사용 시
sudo systemctl restart wan-worker

# run_worker.sh 사용 시
# Ctrl+C로 종료 후 다시 실행
bash run_worker.sh
```

---

## 디렉터리 정리

### 임시 파일 정리

```bash
rm -rf temp/*
```

### 로그 정리

```bash
rm -rf logs/*
```

---

## 보안 주의사항

1. **config.yaml은 절대 git에 커밋하지 마세요**
   - 이미 .gitignore에 포함되어 있음
   - worker_token은 민감 정보입니다

2. **presigned URL은 제한 시간이 있습니다**
   - 다운로드: 10분
   - 업로드: 30분
   - 시간 초과 시 자동 실패 처리됨

3. **Worker는 Supabase 키를 가지고 있지 않습니다**
   - Vercel에서 발급한 presigned URL만 사용
   - 보안이 강화된 구조입니다

---

## 빠른 시작

```bash
# 1. 클론 및 설치 (모든 의존성 포함)
git clone https://github.com/wonderboy02/life-is-short-wan-inference.git
cd life_is_short_wan_inference
bash install.sh

# 2. 설정
nano worker/config.yaml  # vercel_api_url, worker_token 수정

# 3. 실행
bash run_worker.sh
```

---

## 참고 문서

- [docs/guide.md](docs/guide.md) - 전체 아키텍처 설명
- [Wan2.2 공식 README](Wan2.2/README.md)
