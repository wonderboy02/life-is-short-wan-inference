# Wan Worker - API Integration Guide

## 개요
GPU Worker가 Vercel API로부터 작업을 받아 Wan2.2 비디오 생성을 수행합니다.

---

## 현재 API 데이터 구조

### 1. GET /api/worker/next-task
Worker가 다음 작업을 요청하는 엔드포인트

**Request Body:**
```json
{
  "worker_id": "gpu-worker-001",
  "lease_duration_seconds": 600
}
```

**Response (작업이 있을 때):**
```json
{
  "success": true,
  "data": {
    "item_id": "video-item-12345",
    "group_id": "group-abc",
    "photo_id": "photo-001",
    "photo_storage_path": "group-abc/photo-001_original.png",
    "prompt": "A cat sitting on a beach...",
    "leased_until": "2024-12-24T13:00:00Z"
  }
}
```

**Response (작업이 없을 때):**
```json
{
  "success": false,
  "data": null
}
```

---

## 새로운 기능: frame_num 동적 조절

### 변경 사항
Worker가 **작업별로 다른 프레임 수**를 생성할 수 있도록 `frame_num` 필드를 추가했습니다.

### 업데이트된 Response 구조

**GET /api/worker/next-task Response:**
```json
{
  "success": true,
  "data": {
    "item_id": "video-item-12345",
    "group_id": "group-abc",
    "photo_id": "photo-001",
    "photo_storage_path": "group-abc/photo-001_original.png",
    "prompt": "A cat sitting on a beach...",
    "frame_num": 81,  // ← 새로 추가 (optional)
    "leased_until": "2024-12-24T13:00:00Z"
  }
}
```

---

## frame_num 필드 설명

### 필드명
- `frame_num` (integer, optional)

### 설명
- 생성할 비디오의 프레임 수
- **제약 조건**: 반드시 `4n+1` 형태여야 함
  - 유효한 값: `5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61, 65, 69, 73, 77, 81, 85, 89, 93, 97, 101, 105, 109, 113, 117, 121, ...`
  - 무효한 값: `10, 20, 50, 100, ...`

### 기본값
- **필드가 없거나 `null`인 경우**: `121` 프레임 사용 (기본값)
- **필드가 있는 경우**: 해당 값 사용

### 프레임 수와 비디오 길이 관계
- FPS: 24 (고정)
- 예시:
  - `frame_num: 81` → 약 3.4초 비디오
  - `frame_num: 121` → 약 5초 비디오 (기본값)
  - `frame_num: 241` → 약 10초 비디오

---

## API 구현 가이드

### 1. 데이터베이스 스키마 (선택사항)

**video_items 테이블에 컬럼 추가:**
```sql
ALTER TABLE video_items
ADD COLUMN frame_num INTEGER DEFAULT NULL;

-- frame_num이 4n+1 형식인지 체크하는 제약조건 (optional)
ALTER TABLE video_items
ADD CONSTRAINT check_frame_num
CHECK (frame_num IS NULL OR (frame_num - 1) % 4 = 0);
```

### 2. 백엔드 코드 예시

**Task를 생성할 때 (사용자 요청 처리):**
```typescript
// 예: 사용자가 비디오 생성 요청
const videoItem = await db.videoItems.create({
  group_id: groupId,
  photo_id: photoId,
  prompt: userPrompt,
  frame_num: userRequestedFrameNum || null,  // 사용자 지정 or null (기본값 사용)
  status: 'pending'
});
```

**Worker에게 Task를 반환할 때:**
```typescript
// GET /api/worker/next-task 핸들러
const task = await getNextPendingTask();

return {
  success: true,
  data: {
    item_id: task.item_id,
    group_id: task.group_id,
    photo_id: task.photo_id,
    photo_storage_path: task.photo_storage_path,
    prompt: task.prompt,
    frame_num: task.frame_num,  // ← 추가 (null이면 worker가 기본값 121 사용)
    leased_until: task.leased_until
  }
};
```

### 3. 프론트엔드 예시 (선택사항)

사용자에게 프레임 수 선택 옵션을 제공하는 경우:

```typescript
// 비디오 생성 요청
const createVideo = async (photoId: string, prompt: string, frameNum?: number) => {
  const response = await fetch('/api/videos/create', {
    method: 'POST',
    body: JSON.stringify({
      photo_id: photoId,
      prompt: prompt,
      frame_num: frameNum || null  // 81, 121, 241 등
    })
  });
};

// 사용 예시
createVideo('photo-001', 'A cat...', 81);   // 짧은 비디오 (3.4초)
createVideo('photo-001', 'A cat...', 121);  // 보통 비디오 (5초)
createVideo('photo-001', 'A cat...', 241);  // 긴 비디오 (10초)
createVideo('photo-001', 'A cat...');       // 기본값 사용 (121)
```

---

## 주의사항

### 1. 유효성 검사 필수
- `frame_num`이 제공되면 반드시 `4n+1` 형식인지 검증
- 검증 로직 예시:
  ```typescript
  function isValidFrameNum(n: number): boolean {
    return n > 0 && (n - 1) % 4 === 0;
  }

  // 사용
  if (frameNum && !isValidFrameNum(frameNum)) {
    throw new Error('frame_num must be in the form 4n+1 (e.g., 5, 9, 13, 81, 121)');
  }
  ```

### 2. 처리 시간 고려
- 프레임 수가 많을수록 생성 시간이 길어짐
- 권장 범위: `41` ~ `241` (약 1.7초 ~ 10초)
- `lease_duration_seconds`를 충분히 길게 설정 (기본 600초)

### 3. 하위 호환성
- `frame_num` 필드가 없거나 `null`이어도 정상 작동 (기본값 121 사용)
- 기존 API 클라이언트는 수정 없이 계속 사용 가능

---

## 테스트 시나리오

### 1. 기본값 테스트 (frame_num 없음)
```json
// Request
{ "worker_id": "gpu-worker-001" }

// Response
{
  "success": true,
  "data": {
    "item_id": "test-1",
    "prompt": "test prompt",
    "frame_num": null  // Worker가 121 사용
  }
}
```

### 2. 커스텀 값 테스트 (frame_num = 81)
```json
// Response
{
  "success": true,
  "data": {
    "item_id": "test-2",
    "prompt": "test prompt",
    "frame_num": 81  // Worker가 81 사용
  }
}
```

### 3. 잘못된 값 테스트 (frame_num = 100)
```json
// 백엔드에서 에러 반환해야 함
{
  "success": false,
  "error": "frame_num must be in the form 4n+1, got 100"
}
```

---

## 문의사항
Worker 측 담당자에게 연락 바랍니다.
