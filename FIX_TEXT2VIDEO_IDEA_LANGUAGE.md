# Text2Video Script Generation Fix - Summary

## Vấn đề (Problem)
Tại tab text2video, ý tưởng và kịch bản trả về không hề có liên quan. Kết quả cảnh không thể hiện lời thoại của ngôn ngữ đích.

**Ví dụ cụ thể:**
- **Ý tưởng nhập vào:** "Công chúa bạch tuyết và bảy chú lùn"
- **Kịch bản nhận được:** Câu chuyện về influencer Bạch Lan, hoàn toàn không liên quan đến Bạch Tuyết

## Nguyên nhân (Root Cause)

### 1. Prompt không đủ mạnh để bắt buộc LLM tuân thủ ý tưởng
- Prompt chỉ nói "TẠO NỘI DUNG VIRAL" mà không nhấn mạnh phải dựa trên ý tưởng người dùng
- LLM quá sáng tạo, tự do tạo câu chuyện hoàn toàn mới
- Không có cơ chế validation để phát hiện kịch bản không khớp

### 2. Hướng dẫn ngôn ngữ không đủ rõ ràng
- Không có ví dụ cụ thể cho từng trường (text_vi, text_tgt)
- Không nhấn mạnh tất cả các trường `*_tgt` phải dùng ngôn ngữ đích
- Không có validation để phát hiện lời thoại dùng sai ngôn ngữ

## Giải pháp đã triển khai (Solutions Implemented)

### Fix #1: Cải thiện Prompt để bắt buộc tuân thủ ý tưởng

**File:** `services/llm_story_service.py`

**Thay đổi:**

1. **Thêm hướng dẫn rõ ràng cho ý tưởng đơn giản:**
```python
input_type_instruction = """
**QUAN TRỌNG**: Người dùng đã cung cấp Ý TƯỞNG. Nhiệm vụ của bạn:
1. PHÁT TRIỂN chính xác theo ý tưởng mà người dùng đưa ra
2. GIỮ NGUYÊN chủ đề, bối cảnh, nhân vật trong ý tưởng gốc
3. Chỉ thêm chi tiết, cảm xúc, và cấu trúc để tạo kịch bản hoàn chỉnh
4. KHÔNG thay đổi concept cốt lõi hoặc tạo câu chuyện hoàn toàn khác
5. Nếu ý tưởng đề cập nhân vật/địa điểm/sự kiện cụ thể → PHẢI xuất hiện trong kịch bản
"""
```

2. **Thêm banner cảnh báo nổi bật:**
```python
⚠️ TUYỆT ĐỐI PHẢI ĐỌC KỸ YÊU CẦU NÀY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kịch bản BẮT BUỘC phải xây dựng dựa trên ý tưởng: "{idea}"

- Nếu ý tưởng nhắc đến nhân vật cụ thể → PHẢI xuất hiện
- Nếu ý tưởng nhắc đến địa điểm → PHẢI đặt câu chuyện ở đó
- Nếu ý tưởng nhắc đến sự kiện → PHẢI là trọng tâm
- Nếu là câu chuyện cổ tích/nổi tiếng → GIỮ NGUYÊN cốt truyện

KHÔNG ĐƯỢC tự ý tạo câu chuyện hoàn toàn khác!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

3. **Thêm ghi chú trong schema:**
```python
**CHÚ Ý:** 
- QUAN TRỌNG: Kịch bản phải LIÊN QUAN TRỰC TIẾP đến ý tưởng người dùng cung cấp
```

### Fix #2: Thêm validation kiểm tra ý tưởng

**Hàm mới:** `_validate_idea_relevance(idea, generated_content, threshold=0.15)`

**Cơ chế hoạt động:**
1. Trích xuất từ khóa quan trọng từ ý tưởng (loại bỏ stopwords)
2. Kiểm tra xem bao nhiêu từ khóa xuất hiện trong kịch bản
3. Tính độ tương đồng = (từ khóa xuất hiện) / (tổng từ khóa)
4. Nếu < 15% → cảnh báo kịch bản không khớp

**Ví dụ:**
```
Ý tưởng: "Công chúa bạch tuyết và bảy chú lùn"
Từ khóa: công, chúa, bạch, tuyết, bảy, chú, lùn

Kịch bản SAI (Influencer):
- Từ khóa xuất hiện: bạch (trong "Bạch Lan")
- Độ tương đồng: 1/7 = 14.3% → CẢNH BÁO!

Kịch bản ĐÚNG (Snow White):
- Từ khóa xuất hiện: công, chúa, bạch, tuyết, bảy, chú, lùn
- Độ tương đồng: 7/7 = 100% → OK!
```

### Fix #3: Cải thiện hướng dẫn ngôn ngữ

**File:** `services/llm_story_service.py`

**Thay đổi:**

```python
language_instruction = f"""
IMPORTANT LANGUAGE REQUIREMENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌍 TARGET LANGUAGE: {target_language}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**CRITICAL - MUST FOLLOW:**
1. ALL "text_tgt" fields in dialogues MUST be in {target_language}
2. ALL "prompt_tgt" fields MUST be in {target_language}
3. "title_tgt", "outline_tgt", "screenplay_tgt" MUST be in {target_language}

**Example for English (en):**
  "text_vi": "Xin chào",
  "text_tgt": "Hello"  ← TRANSLATED to English

**Example for Japanese (ja):**
  "text_vi": "Xin chào", 
  "text_tgt": "こんにちは"  ← TRANSLATED to Japanese

⚠️ DO NOT mix languages - stick to {target_language} for ALL target fields!
"""
```

### Fix #4: Thêm validation kiểm tra ngôn ngữ lời thoại

**Hàm mới:** `_validate_dialogue_language(scenes, target_lang)`

**Cơ chế hoạt động:**
1. Kiểm tra từng dialogue trong mỗi scene
2. Tìm ký tự tiếng Việt (à, á, ả, ã, ạ, ă, ằ, ắ, ẳ, ...)
3. Nếu ngôn ngữ đích KHÔNG phải tiếng Việt nhưng text_tgt có ký tự tiếng Việt → cảnh báo

**Ví dụ:**
```
Target language: English
Dialogue: "text_tgt": "Tôi là Minh"  ← Contains Vietnamese chars
→ CẢNH BÁO!
```

### Fix #5: Hiển thị cảnh báo trong UI

**File:** `ui/text2video_panel_v5_complete.py`

**Thay đổi trong `_on_story_ready()`:**

```python
# Check for warnings
warnings_to_show = []

if data.get("idea_relevance_warning"):
    warnings_to_show.append(
        f"⚠️ KỊCH BẢN KHÔNG KHỚP Ý TƯỞNG:\n{warning_msg}\n\n"
        f"Đề xuất:\n"
        f"1. Thử lại với ý tưởng chi tiết hơn\n"
        f"2. Chọn Domain/Topic phù hợp\n"
        f"3. Chỉnh sửa kịch bản trong tab 'Chi tiết kịch bản'\n"
    )

if data.get("dialogue_language_warning"):
    warnings_to_show.append(
        f"⚠️ LỜI THOẠI KHÔNG ĐÚNG NGÔN NGỮ:\n{dialogue_warning}\n\n"
        f"Đề xuất:\n"
        f"1. Tạo lại kịch bản\n"
        f"2. Kiểm tra và chỉnh sửa lời thoại\n"
    )

if warnings_to_show:
    QMessageBox.warning(self, "⚠️ Cảnh báo về Kịch bản", combined_warnings)
```

## Kết quả (Results)

### Trước khi fix:
- ❌ LLM tự do tạo câu chuyện mới, không liên quan đến ý tưởng
- ❌ Người dùng không biết kịch bản sai cho đến khi đọc hết
- ❌ Lời thoại có thể dùng sai ngôn ngữ
- ❌ Không có cách nào kiểm tra tự động

### Sau khi fix:
- ✅ LLM được hướng dẫn rõ ràng phải tuân thủ ý tưởng
- ✅ Validation tự động phát hiện kịch bản không khớp (< 15% similarity)
- ✅ Validation tự động phát hiện lời thoại dùng sai ngôn ngữ
- ✅ UI hiển thị cảnh báo ngay khi kịch bản được tạo
- ✅ Đưa ra đề xuất cụ thể cho người dùng

## Testing

### Test 1: Idea Validation
```
Test Case: "Công chúa bạch tuyết và bảy chú lùn"

Good Script (Snow White): 100% similarity ✓
Bad Script (Influencer): 14.3% similarity → WARNING ✓
```

### Test 2: Dialogue Language Validation
```
Test Case: Target = English

Correct dialogues ("Hello", "Hi"): No warning ✓
Wrong dialogues ("Xin chào", "Tôi là Minh"): WARNING ✓
Mixed (some correct, some wrong): WARNING ✓
```

## Files Changed

1. **services/llm_story_service.py**
   - Enhanced prompt with idea adherence instructions
   - Enhanced language instructions with examples
   - Added `_validate_idea_relevance()` function
   - Added `_validate_dialogue_language()` function
   - Integrated validations into `generate_script()`

2. **ui/text2video_panel_v5_complete.py**
   - Updated `_on_story_ready()` to display warnings
   - Shows combined warnings in a single dialog
   - Provides actionable suggestions

## Cách sử dụng (How to Use)

1. **Nhập ý tưởng chi tiết hơn:**
   - ❌ Xấu: "làm video"
   - ✅ Tốt: "Công chúa bạch tuyết và bảy chú lùn trong rừng sâu"

2. **Chọn Domain/Topic phù hợp:**
   - Giúp LLM hiểu rõ hơn ngữ cảnh

3. **Kiểm tra cảnh báo:**
   - Nếu có cảnh báo → xem xét tạo lại hoặc chỉnh sửa
   - Nếu không có → kịch bản đã match với ý tưởng

4. **Đối với ngôn ngữ đích:**
   - Chọn đúng ngôn ngữ đích từ đầu
   - Kiểm tra lời thoại sau khi tạo
   - Nếu có cảnh báo → tạo lại

## Limitations

1. **Validation chỉ là heuristic:**
   - Không thể 100% chính xác
   - Có thể có false positives/negatives
   - Nên kết hợp với đánh giá thủ công

2. **Ngôn ngữ validation:**
   - Chỉ detect được tiếng Việt
   - Không phân biệt được giữa các ngôn ngữ khác (en, ja, ko, ...)
   - Cần người dùng kiểm tra thủ công

3. **LLM vẫn có thể sai:**
   - Prompt tốt hơn nhưng không đảm bảo 100%
   - Đôi khi LLM vẫn có thể bỏ qua hướng dẫn
   - Validation sẽ catch những trường hợp này

## Next Steps

1. ✅ Code review
2. ⏳ Test end-to-end với LLM thực tế
3. ⏳ Thu thập feedback từ người dùng
4. ⏳ Cải thiện threshold và heuristics nếu cần
5. ⏳ Có thể thêm validation cho các ngôn ngữ khác (English, Japanese, ...)

## Conclusion

Các fix này giải quyết cả hai vấn đề:
1. ✅ Kịch bản không khớp ý tưởng → Cải thiện prompt + validation
2. ✅ Lời thoại không đúng ngôn ngữ → Cải thiện hướng dẫn + validation

Người dùng sẽ được thông báo ngay khi có vấn đề và biết cách xử lý.
