# Phong cách hình ảnh — 2D Hoạt hình Lịch sử

## Phong cách chung
- **2D animated cartoon**: flat cel-shading, clean bold outlines, simple expressive characters
- KHÔNG dùng realistic, 3D, photorealistic
- Màu sắc ấm, gợi cảm giác cổ kính nhưng sống động
- Bố cục rõ ràng, dễ nhìn trên điện thoại (đa số viewer xem YouTube trên mobile)

## Nhân vật
- Nhân vật lịch sử phải được tạo **giống nguyên tác nhất có thể** (dựa trên tranh vẽ, tượng, mô tả sử liệu)
- Trang phục đúng thời kỳ lịch sử
- Biểu cảm rõ ràng, cartoon-style (mắt to, nét mặt đơn giản nhưng truyền cảm)
- Mỗi nhân vật có **character sheet** riêng với prompt base đã duyệt
- Test 3-5 ảnh trước khi chốt prompt base cho nhân vật mới

## Kiến trúc & Bối cảnh
- Kiến trúc đúng thời kỳ lịch sử
- Background đơn giản, không quá chi tiết để nhân vật nổi bật
- Chi tiết trang trí đúng thời kỳ (hoa văn Đông Sơn, rồng phượng...)

## Ngôn ngữ prompt
- Giao diện, kịch bản, mô tả cảnh: **tiếng Việt**
- Prompt gửi Veo 3: **tiếng Anh**, thuật ngữ chuyên dụng
- Text tiếng Việt trong Veo 3 đã khá OK nếu prompt rõ ràng

---

## Pipeline tạo hình ảnh/video

### Tỷ lệ ảnh tĩnh vs video clip
- **~3/4 cảnh**: Ảnh tĩnh + hiệu ứng Ken Burns (zoom/pan) trong CapCut
- **~1/4 cảnh**: Video clip Veo 3 (cho cảnh cần chuyển động thực sự: chiến trận, hành động, establishing shot)
- Ảnh tĩnh có thể bổ sung text, mũi tên, tên nhân vật trực tiếp trong prompt

### Đồng bộ nhân vật qua `@Image` reference
- Upload ảnh anchor của nhân vật lên Veo 3
- Dùng `@Image` trong prompt để tham chiếu → giữ nhất quán diện mạo xuyên suốt video
- Mỗi nhân vật chỉ cần 1 ảnh anchor chốt

---

## Cấu trúc Visual Plan (mỗi cảnh)

Mỗi cảnh trong visual_plan.json có cấu trúc:

```json
{
  "scene_number": 12,
  "visual_brief": "Mô tả chi tiết bằng tiếng Anh: bối cảnh, nhân vật, hành động, ánh sáng, bố cục...",
  "characters": {
    "Tên nhân vật": "Mô tả visual đầy đủ — mặt, tóc, trang phục, tư thế, vũ khí..."
  },
  "story_segment": "Tên đoạn kịch bản (tiếng Việt)",
  "visual_type": "image | video",
  "mood": "epic | calm | tense | mysterious | triumphant...",
  "color_tone": "warm | muted | vibrant | dark...",
  "duration": "6s",
  "camera_style": "cinematic slow aerial glide | dynamic low-angle tracking...",
  "audio_direction": "war drums, elephant footsteps, wind... (cho video clip)",
  "timeline_hints": [
    {"time": "0-3s", "action": "Mô tả hành động cụ thể..."},
    {"time": "3-6s", "action": "..."}
  ],
  "edit_plan": {
    "transition_in": "crossfade | fade_from_black | cut",
    "transition_out": "crossfade | fade_to_black | cut",
    "ken_burns": "Slow zoom in 100% → 110% hướng vào mặt nhân vật (cho ảnh tĩnh)",
    "pacing": "5s hold, nhịp chậm",
    "text_overlay": "\"Tên nhân vật\" (vị trí, thời gian hiện)",
    "sound_note": "Nhạc nền loại gì, mức dB, SFX gì"
  }
}
```

---

## Prompt Veo 3 — Cấu trúc 3 lớp (TIẾNG ANH)

### Lớp 1: Base Style (luôn có)
```
2D animated cartoon style, flat cel-shading, clean bold outlines, simple expressive characters, vibrant warm color palette, digital illustration, anime-influenced
```

### Lớp 2: Era Style (chọn theo thời kỳ dự án)
Thêm chi tiết kiến trúc, trang phục, bối cảnh đúng thời kỳ. Ví dụ thời dựng nước:
```
ancient Southeast Asian Bronze Age setting, Dong Son bronze drum patterns, thatched bamboo longhouses, misty mountain valleys, rice paddies, earthy brown and bronze-gold tones
```

### Lớp 3: Character Specific
Mô tả chi tiết nhân vật — phải khớp character sheet:
```
young warrior king, strong square jaw, thick eyebrows, short black beard, bronze Dong Son-style crown with bird feather motif, dark red cape, bronze chest plate with spiral patterns, gold armband with coiled dragon
```

### Negative prompt (luôn thêm)
```
realistic, photorealistic, 3D render, live action, Western features, modern clothing, anachronistic elements, blurry, low quality, deformed faces, extra limbs
```

---

## Prompt cho VIDEO CLIP — Timestamp-based

Khi tạo video clip Veo 3, dùng kỹ thuật timestamp-based prompting:

```
2D animated cartoon style, flat cel-shading, clean bold outlines.
Duration: 8 seconds.
No subtitles. No on-screen text unless specified.

Characters: [mô tả nhân vật từ character sheet]
Camera: [camera style — cinematic, dynamic, static...]
Mood: [epic, tense, calm...]

Summary: [mô tả tổng quan cảnh]

0-3s: [hành động cụ thể, camera angle, ánh sáng]
3-6s: [hành động tiếp theo]
6-8s: [hành động kết thúc]

Audio: [âm thanh môi trường, KHÔNG nhạc nền]
```

### Quy tắc prompt video:
- Chia video thành đoạn 2-3s, mô tả cụ thể hành động từng đoạn
- Dùng `@Image` reference để giữ nhất quán nhân vật
- Mô tả chi tiết: camera angle, movement, ánh sáng, hành động vật lý
- Chỉ định audio cụ thể (âm thanh môi trường, không nhạc nền)
- Negative instructions rõ ràng: "No subtitles. No background music. No cuts, no transitions."

---

## Prompt cho ẢNH TĨNH

```
[Base Style], [Era Style]. [Character description]. [Scene description — bối cảnh, hành động, bố cục]. [Camera shot — wide, medium, close-up]. [Mood]. [Text overlay nếu có].
```

Ảnh tĩnh có thể bổ sung:
- Text tiếng Việt (tên nhân vật, năm, địa điểm)
- Mũi tên chỉ dẫn
- Bản đồ stylized

---

## Ví dụ prompt hoàn chỉnh

### Ảnh tĩnh:
```
2D animated cartoon style, flat cel-shading, clean bold outlines, vibrant warm color palette. Ancient Vietnamese Bronze Age setting, Dong Son bronze drum patterns, misty mountain valleys. A stocky highland chieftain with square jaw, short black beard, woven headband, brown hemp tunic with dark red sash, standing on a raised earthen platform beside a large bronze drum, arms open, crowd raising spears below. Bright golden sunlight bursting behind him. Low-angle hero shot, triumphant epic mood.
```

### Video clip:
```
2D animated cartoon style, flat cel-shading, clean bold outlines.
Duration: 6 seconds.
No subtitles. No background music.

Characters: @Image — stocky highland chieftain, square jaw, short black beard, woven headband, brown hemp tunic with dark red sash, bronze spear
Camera: cinematic slow aerial glide with gentle tilt up
Mood: calm, pastoral

Summary: Sweeping establishing shot of ancient northern Vietnam river delta

0-3s: High aerial wide shot drifting slowly forward over misty flooded rice paddies, early morning golden light piercing thin fog, a calm river reflecting the sky
3-6s: Camera glides gently upward revealing small stilt houses with curved saddle roofs along the riverbank and layered blue mountain ranges emerging from mist

Audio: soft morning birdsong, gentle flowing river water, light breeze through rice stalks
```

## Lưu ý
- Mỗi nhân vật cần character sheet riêng để đảm bảo đồng bộ
- Luôn giữ phong cách nhất quán trong toàn bộ video
- visual_brief trong visual_plan phải đủ chi tiết để Veo 3 tạo đúng ý