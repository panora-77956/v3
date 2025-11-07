# Tóm Tắt Sửa Lỗi Text2Video (Tiếng Việt)

## Tổng Quan
Đã sửa thành công 3 vấn đề chính mà bạn đã báo cáo về tính năng text2video.

---

## ❌ VẤN ĐỀ #1: Mô Tả Cảnh Hiển Thị Sai Ngôn Ngữ

### Vấn đề ban đầu:
- Khi chọn **Tiếng Việt** làm ngôn ngữ đích
- Mô tả cảnh trong **bảng kết quả (Cardlist)** vẫn hiển thị bằng **Tiếng Anh**
- Cột "Prompt Tgt" (ngôn ngữ đích) không đúng ngôn ngữ đã chọn

### Nguyên nhân:
LLM (AI tạo kịch bản) nhận được hướng dẫn không rõ ràng:
- Schema gửi mã ngôn ngữ: `"vi"`, `"en"`, `"ja"`, v.v.
- AI hiểu nhầm và thường mặc định trả về Tiếng Anh

### Giải pháp đã áp dụng:
✅ **Thay đổi cách gửi hướng dẫn cho AI**:
- Trước: `"Detailed visual prompt in vi"` → AI không hiểu "vi" là gì
- Sau: `"Detailed visual prompt in Vietnamese (Tiếng Việt)"` → AI hiểu rõ ràng

✅ **Cập nhật tất cả các trường trong schema**:
- `title_tgt`: Tiêu đề ngôn ngữ đích
- `outline_tgt`: Dàn ý ngôn ngữ đích
- `screenplay_tgt`: Kịch bản ngôn ngữ đích
- `prompt_tgt`: Mô tả cảnh ngôn ngữ đích
- `dialogues.text_tgt`: Thoại ngôn ngữ đích

### Kết quả:
🎉 Bây giờ khi chọn **Tiếng Việt**, tất cả mô tả cảnh sẽ hiển thị bằng **Tiếng Việt**  
🎉 Khi chọn ngôn ngữ khác (English, 日本語, 한국어, v.v.), sẽ đúng ngôn ngữ đó

---

## ❌ VẤN ĐỀ #2: Kịch Bản Sinh Ra Không Khớp Với Ý Tưởng

### Vấn đề ban đầu:
Bạn cung cấp kịch bản rất chi tiết:
```
Ý tưởng: Công chúa bạch tuyết và bảy chú lùn
Kịch bản:
=== HỒ SƠ NHÂN VẬT ===
- ANH AI [Biên kịch Hài Độc thoại, AI Đa năng]: ...
=== DÀN Ý ===
ACT 1 (Hook - 0-8s): ...
ACT 2 (Rising Action - 8-24s): ...
ACT 3 (Resolution & Twist - 24-30s): ...
=== KỊCH BẢN (VI) ===
SCENE 1, SCENE 2, ...
```

Nhưng AI tạo ra kịch bản **hoàn toàn khác**, không giữ nguyên:
- Nhân vật "Anh AI" và tính cách của anh
- 7 chú lùn (bạn cùng phòng)
- Cấu trúc ACT 1, 2, 3
- Nội dung các SCENE

### Nguyên nhân:
AI luôn được hướng dẫn là **"Biên kịch sáng tạo"**:
- Nhận "ý tưởng thô sơ" → phát triển thành kịch bản mới
- Mục tiêu: TẠO NỘI DUNG VIRAL, HẤP DẪN
- → AI nghĩ được phép "sáng tạo lại" toàn bộ

### Giải pháp đã áp dụng:
✅ **Thêm tính năng tự động phát hiện loại input**:

AI sẽ quét input tìm các từ khóa:
- `SCENE`, `ACT 1`, `ACT 2`, `INT.`, `EXT.`
- `KỊCH BẢN`, `SCREENPLAY`, `DÀN Ý`, `HỒ SƠ NHÂN VẬT`
- `FADE IN`, `FADE OUT`, `CLOSE UP`, `CUT TO`

**Nếu phát hiện → Chế độ "Chuyển đổi Format":**
```
Vai trò: "Biên kịch Chuyển đổi Format AI"
Nhiệm vụ:
1. TUÂN THỦ chặt chẽ nội dung, nhân vật, cấu trúc đã cho
2. Chỉ điều chỉnh nhẹ để phù hợp format video
3. GIỮ NGUYÊN ý tưởng gốc, tính cách nhân vật, luồng cảm xúc
4. KHÔNG sáng tạo lại hoặc thay đổi concept
```

**Nếu KHÔNG phát hiện → Chế độ "Sáng tạo" (như cũ):**
```
Vai trò: "Biên kịch Sáng tạo AI"
Nhiệm vụ: Phát triển ý tưởng thô thành kịch bản hấp dẫn
```

### Kết quả:
🎉 Bây giờ khi bạn cung cấp **kịch bản chi tiết**:
- AI sẽ **GIỮ NGUYÊN nhân vật** (Anh AI, 7 chú lùn)
- **GIỮ NGUYÊN cấu trúc** (ACT 1, 2, 3)
- **GIỮ NGUYÊN nội dung cốt lõi**
- Chỉ tối ưu hóa cho format video (thêm visual prompts, timing)

🎉 Khi bạn chỉ đưa **ý tưởng đơn giản** ("làm video về du lịch"):
- AI vẫn sáng tạo tự do như trước

---

## ❌ VẤN ĐỀ #3: Thiếu Thoại/Audio Khi Upload Lên Google Lab Flow

### Vấn đề ban đầu:
- Kịch bản có **dialogues** (thoại):
  ```
  CHÚ LÙN CỘC TÍNH (O.S): "Mới sáng ra đã ồn ào!"
  ANH AI: "Thiệt hại vật chất: 5 chiếc bát..."
  ```
- Nhưng khi upload lên Google Lab Flow → **KHÔNG có thoại nào**
- Chỉ có mô tả hình ảnh ("ANH AI ngồi trước laptop...")

### Nguyên nhân:
Hệ thống đang nhầm lẫn giữa 2 loại text:
1. **Visual Prompt** = Mô tả cảnh cho AI tạo video (gửi Google Lab Flow)
   - VD: "ANH AI ngồi trước laptop, mặc vest đen, gõ phím..."
2. **Voiceover Text** = Thoại cho TTS đọc (text-to-speech)
   - VD: "Thiệt hại vật chất: 5 chiếc bát, 2 chiếc đĩa..."

Trước đây, cả 2 đều dùng **Visual Prompt** → không có thoại!

### Giải pháp đã áp dụng:
✅ **Tách biệt Visual Prompt và Voiceover Text**:

1. **Thêm tham số `dialogues`** vào hàm `build_prompt_json`:
   ```python
   def build_prompt_json(..., dialogues: list = None):
   ```

2. **Logic mới cho Voiceover Text**:
   ```
   Ưu tiên 1: Nếu có dialogues → Dùng dialogues
   Ưu tiên 2: Nếu không có → Dùng scene description (như cũ)
   ```

3. **Format thoại**:
   - Có speaker: `"Speaker: thoại"`
   - Không speaker: `"thoại"`
   - Nhiều thoại: Nối lại thành 1 chuỗi

4. **Ngôn ngữ thoại**:
   - Tiếng Việt → Dùng `text_vi`
   - Ngôn ngữ khác → Dùng `text_tgt`

✅ **Cập nhật tất cả 5 chỗ gọi `build_prompt_json`**:
- Trích xuất dialogues từ scene data
- Truyền dialogues vào hàm
- Đảm bảo tất cả chỗ đều nhất quán

### Kết quả:
🎉 Bây giờ **Voiceover Text** sẽ chứa thoại thực sự:
```json
{
  "audio": {
    "voiceover": {
      "text": "CHÚ LÙN CỘC TÍNH: Mới sáng ra đã ồn ào! ANH AI: Thiệt hại vật chất: 5 chiếc bát, 2 chiếc đĩa..."
    }
  }
}
```

🎉 **Visual Prompt** vẫn giữ mô tả hình ảnh (cho Google Lab Flow):
```
"prompt": "ANH AI bước ra hành lang, nhìn CHÚ LÙN VỤNG VỀ ngồi giữa đống bát đĩa vỡ..."
```

🎉 TTS sẽ đọc **thoại**, không phải mô tả hình ảnh

---

## 📊 Tóm Tắt Thay Đổi

### Files đã sửa:
1. **services/llm_story_service.py**
   - Dùng tên ngôn ngữ đầy đủ thay vì mã
   - Thêm phát hiện kịch bản chi tiết
   - Điều chỉnh role và instruction của AI

2. **ui/text2video_panel_impl.py**
   - Thêm tham số `dialogues`
   - Logic tạo voiceover text từ dialogues
   - Code sạch hơn, dễ đọc hơn

3. **ui/text2video_panel_v5_complete.py**
   - Cập nhật tất cả 5 chỗ gọi `build_prompt_json`
   - Trích xuất và truyền dialogues
   - Nhất quán với pattern mới

### Bảo mật:
- ✅ Tất cả files compile thành công
- ✅ CodeQL security check: **0 cảnh báo**
- ✅ Không có lỗ hổng bảo mật mới

### Tương thích ngược:
- ✅ Code cũ vẫn hoạt động bình thường
- ✅ Tham số `dialogues` là optional (mặc định `None`)
- ✅ Không có breaking changes

---

## 🧪 Cách Kiểm Tra

### Test 1: Ngôn ngữ đích
1. Tạo kịch bản mới
2. Chọn **Tiếng Việt** làm ngôn ngữ đích
3. Kiểm tra bảng kết quả → Cột "Prompt Tgt" phải là **Tiếng Việt**
4. Kiểm tra voiceover config → `text` phải là **Tiếng Việt**

### Test 2: Giữ nguyên kịch bản
1. Nhập kịch bản chi tiết (như ví dụ Bạch Tuyết)
2. Bao gồm: HỒ SƠ NHÂN VẬT, DÀN Ý, KỊCH BẢN, SCENE
3. Tạo kịch bản
4. Kiểm tra output → Phải giữ nguyên nhân vật, cấu trúc, nội dung cốt lõi

### Test 3: Thoại trong voiceover
1. Tạo kịch bản có nhiều dialogues
2. Kiểm tra file `scene_XX.json` → `audio.voiceover.text`
3. Phải chứa thoại (có speaker name), không phải mô tả hình ảnh
4. Test với cả Tiếng Việt và Tiếng Anh

---

## 🎯 Kết Luận

### ✅ Đã Hoàn Thành:
1. ✅ Mô tả cảnh hiển thị đúng ngôn ngữ đích
2. ✅ Kịch bản chi tiết được giữ nguyên, không bị sáng tạo lại
3. ✅ Thoại/dialogue được đưa vào voiceover text

### 📝 Lưu Ý Quan Trọng:

**Về Google Lab Flow:**
- Google Lab Flow (Veo) **CHỈ tạo video**, không tạo audio
- Audio/voiceover được tạo **riêng** bằng TTS (Text-to-Speech)
- Sau đó kết hợp video + audio thành video hoàn chỉnh
- Prompt JSON chứa cả 2 phần:
  - `prompt`: Visual prompt cho Veo tạo video
  - `audio.voiceover.text`: Text cho TTS đọc

**Workflow đúng:**
1. AI tạo kịch bản → Có visual prompts + dialogues
2. Upload visual prompts → Google Lab Flow tạo **video không tiếng**
3. Dùng TTS đọc dialogues → Tạo **file audio**
4. Kết hợp video + audio → **Video hoàn chỉnh có thoại**

---

## 🙏 Cảm Ơn

Cảm ơn bạn đã báo cáo các vấn đề chi tiết! Nhờ đó chúng tôi đã có thể:
- Phát hiện và sửa bug về ngôn ngữ
- Cải thiện cách AI xử lý kịch bản chi tiết
- Phân tách rõ ràng giữa visual prompt và voiceover text

Nếu còn vấn đề gì, hãy cho chúng tôi biết! 🚀
