# Worker 수정 내역

## 수정 개요
Wan2.2 추론 설정을 업데이트하고 `frame_num`을 동적으로 조절할 수 있게 수정

---

## 1. 기본값 변경

### worker/config.yaml
```yaml
# 변경 전
frame_num: 81
sample_steps: 30
cfg_scale: 5.0

# 변경 후
frame_num: 121  # ti2v-5B 공식 기본값
sample_steps: 50
cfg_scale: 7.5
```

**변경 이유:**
- Wan2.2 공식 config(`wan_ti2v_5B.py`)의 기본값과 일치
- 더 나은 품질을 위한 설정

---

## 2. 메모리 최적화 옵션 추가

### worker/inference.py
추가된 명령어 옵션:
- `--offload_model True` - GPU 메모리 부족 시 모델을 CPU로 offload
- `--convert_model_dtype` - 모델 dtype 변환으로 메모리 절약
- `--t5_cpu` - T5 모델을 CPU에서 실행

**변경 전:**
```python
cmd = [
    "python", "generate.py",
    "--task", "ti2v-5B",
    "--ckpt_dir", str(abs_model_path),
    "--sample_steps", "30",
    "--sample_guide_scale", "5.0"
]
```

**변경 후:**
```python
cmd = [
    "python", "generate.py",
    "--task", "ti2v-5B",
    "--ckpt_dir", str(abs_model_path),
    "--sample_steps", "50",
    "--sample_guide_scale", "7.5",
    "--offload_model", "True",
    "--convert_model_dtype",
    "--t5_cpu"
]
```

---

## 3. frame_num 동적 조절 기능 추가

### 3-1. worker/inference.py
`run()` 메서드에 `frame_num` 파라미터 추가

**변경 전:**
```python
def run(self, input_image_path: str, output_video_path: str,
        prompt: str = None, video_size: str = None) -> str:
    ...
    final_frame_num = self.config.get("frame_num", 81)
```

**변경 후:**
```python
def run(self, input_image_path: str, output_video_path: str,
        prompt: str = None, video_size: str = None, frame_num: int = None) -> str:
    ...
    # 우선순위: 함수 파라미터 > config > 기본값(121)
    final_frame_num = frame_num if frame_num is not None else self.config.get("frame_num", 121)
```

### 3-2. worker/worker.py
API에서 받은 `frame_num`을 inference에 전달

**변경:**
```python
def process_task(self, task: Dict[str, Any]) -> bool:
    item_id = task["item_id"]
    prompt = task.get("prompt")
    frame_num = task.get("frame_num")  # ← 추가

    ...

    self.inference.run(
        input_image_path=str(temp_input),
        output_video_path=str(temp_output),
        prompt=prompt,
        frame_num=frame_num  # ← 추가 (None이면 기본값 121 사용)
    )
```

---

## 4. 데이터 흐름

```
API Response (frame_num: 81 또는 null)
    ↓
worker.py: task.get("frame_num")
    ↓
inference.py: run(frame_num=81 또는 None)
    ↓
최종 결정: 81 또는 config의 121 또는 기본값 121
    ↓
generate.py 실행: --frame_num 81
```

### 우선순위
1. **API에서 전달된 값** (가장 높은 우선순위)
2. config.yaml의 값
3. 하드코딩된 기본값 (121)

---

## 5. 사용 예시

### Case 1: API에서 frame_num 지정
```python
# API response
task = {
    "item_id": "video-001",
    "prompt": "A cat...",
    "frame_num": 81  # ← API에서 지정
}

# 결과: 81 프레임으로 생성
```

### Case 2: API에서 frame_num 없음 (config 사용)
```python
# API response
task = {
    "item_id": "video-002",
    "prompt": "A dog...",
    "frame_num": null  # 또는 필드 없음
}

# config.yaml: frame_num: 121
# 결과: 121 프레임으로 생성
```

### Case 3: config도 없음 (기본값 사용)
```python
# API response
task = {
    "item_id": "video-003",
    "prompt": "A bird...",
    # frame_num 없음
}

# config.yaml에도 frame_num 없다면
# 결과: 121 프레임으로 생성 (하드코딩된 기본값)
```

---

## 6. 검증 로직

### worker/inference.py: validate_config()
```python
def validate_config(self) -> bool:
    # frame_num이 제공되면 4n+1 형식인지 검증
    frame_num = self.config.get("frame_num", 121)
    if (frame_num - 1) % 4 != 0:
        raise ValueError(f"frame_num must be 4n+1, got {frame_num}")
    return True
```

**검증 시점:**
- Worker 초기화 시 config 검증
- API에서 받은 값은 inference.run()에서 Wan2.2가 자동 검증

---

## 7. 수정된 파일 목록

1. **worker/config.yaml** - 기본값 업데이트
2. **worker/inference.py** - 메모리 옵션 추가 + frame_num 파라미터 추가
3. **worker/worker.py** - API에서 frame_num 수신 및 전달

---

## 8. 하위 호환성

✅ 기존 코드와 100% 호환
- API에서 `frame_num` 필드가 없어도 정상 작동
- config.yaml에서 `frame_num`을 제거해도 기본값(121) 사용
- 기존 API 응답 형식 그대로 사용 가능

---

## 9. 테스트 방법

### 로컬 테스트
```bash
# 1. config.yaml 확인
cat worker/config.yaml

# 2. Worker 실행
python -m worker.worker

# 3. 로그 확인
tail -f logs/gpu-worker-001_*.log
```

### 로그 출력 예시
```
[INFO] Frame num: 81
[INFO] Running Wan2.2 inference...
[INFO] Generating video with 81 frames...
```

---

## 문의사항
Worker 개발자에게 연락 바랍니다.
