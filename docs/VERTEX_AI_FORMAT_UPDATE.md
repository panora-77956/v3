# Video Generation Request Format Update

## Summary

This update changes the video generation API request structure from Google Labs Flow format to Vertex AI format, matching the structure shown in the problem statement.

## New Request Format

### Structure

```json
{
  "model": "veo-3.1",
  "instances": [
    {
      "prompt": "[COMPLETE PROMPT TEXT]"
    }
  ],
  "parameters": {
    "durationSeconds": 8,
    "aspectRatio": "16:9",
    "resolution": "1080p",
    "seed": 415136406,
    "enhancePrompt": false,
    "generateAudio": true,
    "negativePrompt": "text, words, letters, subtitles, captions, titles, credits, on-screen text, watermarks, logos, brands, camera shake, fisheye, photorealistic, live action, 3D CGI, Disney 3D, Pixar style",
    "sampleCount": 1
  },
  "clientContext": {
    "projectId": "your-project-id"
  }
}
```

## Example: Vietnamese Story (Cô Bé Bán Diêm)

The prompt field in `instances[0].prompt` would contain the complete formatted text as shown in the problem statement:

```
[CONSISTENCY CONTRACT v1 — DO NOT MODIFY]
CONST_ID: LINH-12F
CONST_STYLE: ANIME-2D-CEL
CONST_SETTING: SNOWY-STREET-NIGHT
CONST_PROP: MATCHBOX-RED-SCARF

• Tên nhân vật chuẩn: LINH (Cô Bé Bán Diêm). Luôn gọi đúng tên "LINH".
• Nhận diện cố định: cùng một người, KHÔNG thay mặt/cơ thể/tuổi/chiều cao giữa các cảnh.
• Tuổi & dáng: bé gái ~12 tuổi, cao ~145cm, mảnh khảnh.
• Khuôn mặt: mặt trái xoan; mắt to hơi hạnh nhân; mũi nhỏ hơi hếch; môi mỏng nhợt; má nẻ lạnh.
• Tóc: đen, bob ngang hàm, rối, ngôi lệch trái, hơi ẩm vì tuyết.
• Trang phục: váy nâu sờn rách + khăn quàng đỏ sờn; luôn ôm HỘP DIÊM gỗ cũ.
• Bối cảnh cố định: "đường phố đêm đông" đang có tuyết rơi; ánh đèn natri vàng xa; đường vắng; bóng đổ lạnh xanh.
• Phong cách hình ảnh: anime 2D, flat colors, bold outlines, cel‑shading. KHÔNG photorealistic, KHÔNG 3D/CGI, KHÔNG live‑action.
• Máy quay: cảm giác 24fps; look 50mm; chuyển động chậm, steadicam/dolly; KHÔNG rung lắc; KHÔNG fisheye.
• Quy tắc thoại: mọi câu nói bằng tiếng Việt và đặt trong dấu ngoặc kép.
• Cấm kỵ: KHÔNG HIỂN THỊ CHỮ TRÊN MÀN HÌNH (NO ON‑SCREEN TEXT). Không subtitles, captions, titles, credits, words, letters, numbers, logos, watermarks.

[NEGATIVE — ENFORCE]
text, words, letters, subtitles, captions, titles, credits, on‑screen text, SRT, typographic overlay, watermarks, logos, brand names, camera shake, fisheye, photorealistic, live action, 3D CGI, Disney 3D, Pixar style.

[AUDIO GUIDANCE]
Ambience rất thấp: gió lạnh + tuyết. Nếu có lời thoại, chỉ phát **âm thanh**, **KHÔNG** hiển thị text. Giọng Việt nữ trẻ, thì thầm, hơi thở rõ.
DIALOGUE (audio‑only): "Chỉ một que thôi..."

[SHOTLIST — 00:00–08:00 | 16:9 1080p | giữ đúng ID/Outfit/Location]
[00:00–00:02] WIDE — Phố tuyết trắng, vắng lặng; dolly chậm; đèn vàng xa hắt qua sương.
[00:02–00:04.4] CLOSE‑UP HANDS — Hai bàn tay nhỏ đỏ ửng cọ xát; hộp diêm gỗ cũ; hơi thở trắng.
[00:04.4–00:06.4] SLOW ZOOM IN FACE — Gương mặt xanh xao; một giọt nước mắt; phản chiếu đèn vàng.
[00:06.4–00:08.0] ACTION — LINH rút 1 que diêm, quẹt; lửa cam bùng chiếu sáng gương mặt rồi tắt; hold ổn định.

[CAMERA MACRO]
0.0–2.0: Establish; steady. 2.0–4.4: Gesture; giữ khung. 4.4–6.4: Detail. 6.4–8.0: End beat; micro push‑in.
```

## Conversion Functions

### Aspect Ratio Conversion

| Old Format | New Format |
|-----------|-----------|
| VIDEO_ASPECT_RATIO_LANDSCAPE | 16:9 |
| VIDEO_ASPECT_RATIO_PORTRAIT | 9:16 |
| VIDEO_ASPECT_RATIO_SQUARE | 1:1 |

### Model Key Conversion

| Old Format | New Format |
|-----------|-----------|
| veo_3_1_t2v_fast_ultra | veo-3.1 |
| veo_3_1_i2v_s_fast | veo-3.1 |
| veo_2_t2v | veo-2.0 |

## Implementation Details

### Files Modified
- `services/labs_flow_service.py`
- `services/google/labs_flow_client.py`

### Methods Updated
- `start_one()` - Updated to build Vertex AI format request
- `generate_videos_batch()` - Updated to build Vertex AI format request

### Backward Compatibility
- `clientContext` field is preserved for compatibility
- Existing tests continue to pass
- Content policy filter still works

## Testing

All tests pass:
- ✅ Aspect ratio conversion
- ✅ Model key conversion
- ✅ Negative prompt extraction
- ✅ Request body structure
- ✅ Existing integration tests
- ✅ Security scan (CodeQL: 0 vulnerabilities)

## Notes

1. The `enhancePrompt` parameter is set to `false` to preserve the exact prompt structure
2. `generateAudio` is set to `true` to enable audio generation
3. Negative prompts are extracted from the prompt data structure
4. Default duration is 8 seconds, resolution is 1080p
5. The seed is preserved from the original request
