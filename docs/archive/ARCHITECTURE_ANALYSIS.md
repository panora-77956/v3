# Phân Tích Kiến Trúc Tab Video Bán Hàng (videobanhang)

## Tóm Tắt
Tài liệu này phân tích cơ chế hoạt động của tab Video Bán Hàng trong ứng dụng, bao gồm:
- Quy trình tạo kịch bản, ảnh và video
- Các model AI được sử dụng
- Cơ chế quản lý API key
- Đánh giá hiệu quả và khuyến nghị cải thiện

---

## 1. LỖI ĐÃ PHÁT HIỆN VÀ KHẮC PHỤC

### 1.1 AttributeError: 'ScriptWorker' object has no attribute 'cfg'

**Nguyên nhân:**
- File: `ui/workers/script_worker.py`
- Dòng 31: Sử dụng `self.cfg` nhưng constructor (dòng 20) lưu thành `self.config`

**Khắc phục:**
```python
# TRƯỚC:
result = build_outline(self.cfg)

# SAU:
result = build_outline(self.config)
```

**Trạng thái:** ✅ ĐÃ SỬA (commit 0fbcfec)

---

## 2. QUY TRÌNH TẠO VIDEO 3 BƯỚC

Tab videobanhang sử dụng quy trình 3 bước:

### Bước 1: SINH KỊCH BẢN (Script Generation)
**File:** `services/sales_script_service.py`
**Worker:** `ui/workers/script_worker.py`

#### Input:
- Tên dự án (project_name)
- Ý tưởng (idea)
- Nội dung sản phẩm (product_main)
- Style kịch bản (script_style): "Viral", "KOC Review", "Kể chuyện"
- Số cảnh (tính từ duration_sec)
- Thông tin người mẫu (models_json)
- Ngôn ngữ (speech_lang)

#### Model sử dụng:
- **Gemini 2.5 Flash** (`gemini-2.5-flash`) - MẶC ĐỊNH
- **ChatGPT** (tùy chọn)

#### Output:
```json
{
  "scenes": [
    {
      "scene": 1,
      "description": "Mô tả cảnh",
      "voiceover": "Lời thoại",
      "prompt": {
        "Output_Format": {
          "Structure": {
            "character_details": "Chi tiết nhân vật",
            "setting_details": "Chi tiết bối cảnh",
            "key_action": "Hành động chính",
            "camera_direction": "Hướng camera",
            "emotion": "Cảm xúc"
          }
        }
      }
    }
  ],
  "character_bible": [
    {
      "name": "Tên nhân vật",
      "role": "Vai trò",
      "visual_identity": "Đặc điểm nhận dạng"
    }
  ],
  "social_media": {
    "versions": [
      {
        "caption": "Nội dung caption",
        "hashtags": ["#tag1", "#tag2"],
        "thumbnail_prompt": "Prompt tạo thumbnail",
        "thumbnail_text_overlay": "Text trên thumbnail"
      }
    ]
  }
}
```

#### Character Bible System:
- Tạo hồ sơ nhân vật chi tiết với 5 consistency anchors
- Đảm bảo tính nhất quán hình ảnh qua các cảnh
- File: `services/google/character_bible.py`

---

### Bước 2: TẠO ẢNH (Image Generation)
**File:** `ui/video_ban_hang_v5_complete.py` (ImageGenerationWorker)
**Service:** `services/image_gen_service.py`

#### Model sử dụng:

##### Option 1: Gemini Flash Image (MẶC ĐỊNH)
- Model: `gemini-2.5-flash-image`
- Endpoint: `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- Input: Text prompt từ kịch bản
- Output: Base64 encoded image
- Rate limit: 10 giây giữa các request (RATE_LIMIT_DELAY_SEC)

**Ưu điểm:**
- Miễn phí với Google API key
- Tích hợp Character Bible để đảm bảo consistency
- Tự động xử lý rate limiting

**Nhược điểm:**
- Chất lượng không cao bằng Imagen 3
- Rate limit nghiêm ngặt (60 requests/phút)

##### Option 2: Whisk
- Service: `services/whisk_service.py`
- Yêu cầu: Session token từ labs.google
- Input: 
  - Text prompt
  - Model image (người mẫu)
  - Product image (sản phẩm)
- Output: Ảnh blend giữa model + product + prompt

**Ưu điểm:**
- Tích hợp được hình ảnh người mẫu và sản phẩm
- Chất lượng tốt cho use case bán hàng

**Nhược điểm:**
- Phức tạp hơn (cần 3 bước: caption → generate → poll)
- Yêu cầu session token (không phải API key)
- Có thể không ổn định

#### Cơ chế Parallel Processing:
```python
# Sequential mode (mặc định)
- Sử dụng 1 API key
- Xử lý tuần tự từng cảnh
- Rate limit: 10s giữa các request

# Parallel mode (nếu bật multi-account)
- Sử dụng nhiều Google accounts
- Round-robin distribution
- Mỗi thread xử lý 1 batch cảnh
- Tốc độ tăng N lần (N = số accounts)
```

**File:** `services/account_manager.py`

---

### Bước 3: TẠO VIDEO (Video Generation)
**Status:** 🚧 CHƯA TRIỂN KHAI ĐẦY ĐỦ

#### Dự kiến sử dụng:
- **Google Veo** (Video Generation Model)
- Service: `services/labs_flow_service.py`
- Input: Image + Text prompt
- Output: Video clip

**Hiện tại:**
- Chỉ có placeholder trong UI
- Hiển thị thông báo: "Chức năng tạo video sẽ được triển khai trong phiên bản tiếp theo"

---

## 3. CƠ CHẾ QUẢN LÝ API KEY

### 3.1 Kiến trúc Key Management

```
services/core/
├── config.py              # Load/save config từ ~/.veo_image2video_cfg.json
├── key_manager.py         # Quản lý key pools với round-robin
├── api_key_rotator.py     # Rotation logic khi key bị rate limit
└── api_key_manager.py     # Legacy manager
```

### 3.2 Các loại API Keys

#### 1. Google API Keys
- **Mục đích:** Gemini Text + Gemini Image generation
- **Format:** AIza...
- **Storage:** `config.google_api_keys[]`
- **Rotation:** Round-robin trong KeyPool
- **Rate Limit:** 
  - Text: 15 requests/minute
  - Image: 60 requests/minute

#### 2. Labs Tokens (OAuth Bearer)
- **Mục đích:** Veo video generation, Whisk image generation
- **Format:** ya29...
- **Storage:** `config.labs_tokens[]`
- **Multi-account support:** ✅ (AccountManager)
- **Rate Limit:** Không rõ (cần test)

#### 3. OpenAI API Keys (tùy chọn)
- **Mục đích:** ChatGPT script generation
- **Storage:** `config.openai_api_keys[]`

#### 4. ElevenLabs API Keys (tùy chọn)
- **Mục đích:** Text-to-Speech
- **Storage:** `config.elevenlabs_api_keys[]`

### 3.3 Key Rotation Strategy

```python
class KeyPool:
    def get_next(self) -> str:
        """Round-robin rotation"""
        key = self._keys[self._index % len(self._keys)]
        self._index += 1
        return key
```

**Ưu điểm:**
- Thread-safe với Lock
- Đơn giản, dễ hiểu
- Tự động phân phối đều load

**Nhược điểm:**
- Không track key nào bị rate limit
- Không có backoff strategy
- Không có health check

### 3.4 Rate Limiting

#### Image Generation:
```python
# Cơ chế hiện tại
RATE_LIMIT_DELAY_SEC = 10.0

if i > 0:  # Delay for subsequent requests
    time.sleep(RATE_LIMIT_DELAY_SEC)

# Enhanced version trong image_gen_service.py
def generate_image_with_rate_limit(
    delay_before=10,
    enforce_rate_limit=True
):
    if enforce_rate_limit:
        time.sleep(delay_before)
    # ... API call
```

**Vấn đề:**
- Fixed delay, không adaptive
- Không xử lý 429 response một cách thông minh
- Có thể chậm hơn cần thiết

---

## 4. ĐÁNH GIÁ HIỆU QUẢ

### 4.1 Điểm Mạnh ✅

1. **Kiến trúc rõ ràng:**
   - Tách biệt concerns (workers, services, UI)
   - Single Responsibility Principle
   - Dễ maintain

2. **Character Bible System:**
   - Đảm bảo consistency nhân vật
   - 5 unique anchors per character
   - Inject vào prompts tự động

3. **Multi-account Support:**
   - Parallel image generation
   - Round-robin load balancing
   - Thread-safe

4. **Error Handling:**
   - Parse JSON với 5 fallback strategies
   - Detailed error messages
   - Retry logic

5. **UI/UX:**
   - 3-step workflow rõ ràng
   - V5 modern design
   - Collapsible sections

### 4.2 Điểm Yếu ⚠️

1. **Rate Limiting:**
   - Fixed delay, không intelligent
   - Không track failed keys
   - Waste time với unnecessary delays

2. **API Key Management:**
   - Không có health check
   - Không blacklist bad keys
   - Không có usage analytics

3. **Error Recovery:**
   - Không tự động retry với backoff
   - Không cache successful results
   - Mất tiến độ khi crash

4. **Video Generation:**
   - Chưa implement
   - Phụ thuộc Labs API (không stable)

5. **Testing:**
   - Không có unit tests
   - Không có integration tests
   - Khó verify changes

---

## 5. KHUYẾN NGHỊ CẢI THIỆN

### 5.1 Ngắn hạn (Quick Wins)

#### 1. Cải thiện Rate Limiting
```python
class AdaptiveRateLimiter:
    def __init__(self):
        self.last_call_time = {}
        self.min_delay = 10.0
        self.backoff_multiplier = 1.5
    
    def wait_if_needed(self, key):
        if key in self.last_call_time:
            elapsed = time.time() - self.last_call_time[key]
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
        self.last_call_time[key] = time.time()
    
    def mark_rate_limited(self, key):
        self.min_delay *= self.backoff_multiplier
```

#### 2. Key Health Tracking
```python
class KeyHealthTracker:
    def __init__(self):
        self.success_count = {}
        self.failure_count = {}
        self.blacklist = set()
    
    def is_healthy(self, key):
        if key in self.blacklist:
            return False
        failures = self.failure_count.get(key, 0)
        successes = self.success_count.get(key, 0)
        return failures < 5 or successes / (failures + 1) > 0.3
    
    def mark_success(self, key):
        self.success_count[key] = self.success_count.get(key, 0) + 1
    
    def mark_failure(self, key):
        self.failure_count[key] = self.failure_count.get(key, 0) + 1
        if self.failure_count[key] > 10:
            self.blacklist.add(key)
```

#### 3. Result Caching
```python
import hashlib
import pickle
from pathlib import Path

class ResultCache:
    def __init__(self, cache_dir=".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def _hash(self, data):
        return hashlib.sha256(str(data).encode()).hexdigest()[:16]
    
    def get(self, key, params):
        cache_key = f"{key}_{self._hash(params)}"
        cache_file = self.cache_dir / cache_key
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None
    
    def set(self, key, params, result):
        cache_key = f"{key}_{self._hash(params)}"
        cache_file = self.cache_dir / cache_key
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)
```

### 5.2 Trung hạn (Medium Priority)

#### 1. Retry with Exponential Backoff
```python
def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
```

#### 2. Progress Persistence
- Lưu progress sau mỗi cảnh
- Resume từ checkpoint khi crash
- File: `{project_name}/.progress.json`

#### 3. Model Fallback Chain
```python
MODELS = [
    ("gemini", generate_with_gemini),
    ("whisk", generate_with_whisk),
    ("imagen", generate_with_imagen),
]

def generate_with_fallback(prompt):
    for model_name, generator in MODELS:
        try:
            return generator(prompt)
        except Exception as e:
            logger.warning(f"{model_name} failed: {e}")
    raise Exception("All models failed")
```

### 5.3 Dài hạn (Strategic)

#### 1. Monitoring & Analytics
- Track usage per API key
- Alert khi rate limit
- Dashboard hiển thị performance

#### 2. Testing Infrastructure
```python
# Unit tests
def test_script_worker_uses_correct_config():
    worker = ScriptWorker({"duration_sec": 30})
    assert hasattr(worker, 'config')
    assert worker.config['duration_sec'] == 30

# Integration tests
def test_end_to_end_video_generation():
    # Test full pipeline
    pass
```

#### 3. Video Generation Implementation
- Tích hợp Google Veo API
- Fallback sang alternatives (Runway, Pika)
- Quality control

#### 4. Cost Optimization
- Estimate cost trước khi generate
- Option chọn quality (fast/normal/high)
- Batch processing để tối ưu API calls

---

## 6. KẾT LUẬN

### 6.1 Tổng Quan
Kiến trúc hiện tại của tab videobanhang là **tốt** về mặt cấu trúc nhưng cần cải thiện về **robustness** và **efficiency**.

### 6.2 Mức Độ Phù Hợp
- **Script Generation:** ✅ Tốt (Gemini 2.5 Flash đủ nhanh và chính xác)
- **Image Generation:** ⚠️ Khá (cần cải thiện rate limiting)
- **Video Generation:** ❌ Chưa có
- **API Key Management:** ⚠️ Khá (cần health tracking)

### 6.3 Ưu Tiên Cao Nhất
1. ✅ **Fix AttributeError** - DONE
2. 🔄 Implement adaptive rate limiting
3. 🔄 Add key health tracking
4. 🔄 Add result caching
5. 📋 Implement video generation

### 6.4 Model Recommendations

#### Cho Script Generation:
- **Hiện tại:** Gemini 2.5 Flash ✅ (tốt)
- **Alternative:** GPT-4 (nếu cần chất lượng cao hơn)

#### Cho Image Generation:
- **Hiện tại:** Gemini Flash Image ⚠️ (tạm ổn)
- **Recommend:** Imagen 3 (nếu có quota)
- **Alternative:** DALL-E 3, Midjourney API

#### Cho Video Generation:
- **Recommend:** Google Veo (khi có API stable)
- **Alternative:** Runway Gen-2, Pika

---

## PHỤ LỤC

### A. Config File Format
```json
{
  "google_api_keys": ["AIza...", "AIza..."],
  "labs_tokens": ["ya29...", "ya29..."],
  "openai_api_keys": ["sk-..."],
  "elevenlabs_api_keys": ["..."],
  "download_root": "/path/to/downloads",
  "default_project_id": "uuid"
}
```

### B. API Endpoints
- Gemini Text: `generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`
- Gemini Image: `generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent`
- Whisk: `labs.google/fx/api/trpc/backbone.*`
- Veo: `aisandbox-pa.googleapis.com/v1/projects/{pid}/locations/*/operations`

### C. Rate Limits (Google Free Tier)
- Gemini Text: 15 RPM (requests per minute)
- Gemini Image: 60 RPM
- Imagen 3: 10 RPM
- Veo: Unknown (likely very low)

---

**Ngày phân tích:** 2025-11-07  
**Phiên bản:** v3  
**Tác giả:** GitHub Copilot Agent
