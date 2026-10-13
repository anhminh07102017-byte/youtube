# Hướng dẫn Edit — Lịch sử kể chuyện

## Tổng quan quy trình

Edit video lịch sử gồm 2 lớp lập kế hoạch:
1. **Director Plan** (director_plan.json): Chia video thành các segment lớn, mỗi segment có mood, color tone, camera notes
2. **Edit Plan per-scene** (trong visual_plan.json): Chi tiết transition, ken_burns, pacing, text overlay, sound note cho từng cảnh

---

## Director Plan — Segment-level

Mỗi segment trong director_plan.json:

```json
{
  "name": "Hook - Pháo đài bất khả xâm phạm",
  "scene_numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9],
  "description": "Mô tả nội dung đoạn...",
  "mood_progression": "mysterious → epic → ominous → suspenseful",
  "color_tone": "golden-hour warm amber, turning to cold blue-grey, ending on misty dawn gold",
  "characters": {
    "Tên nhân vật": "Mô tả visual trong đoạn này..."
  },
  "camera_notes": "Sweeping aerial wide shots, fast push-in, low-angle retreating soldiers...",
  "video_count": 7
}
```

### Quy tắc segment:
- `mood_progression`: Chuỗi cảm xúc chuyển dần (dùng mũi tên →)
- `color_tone`: Palette màu cụ thể cho đoạn, có thể thay đổi trong đoạn
- `video_count`: Số cảnh dùng video clip (còn lại là ảnh tĩnh)
- `characters`: Mô tả visual nhân vật **trong context đoạn này** (có thể khác giữa các đoạn nếu nhân vật thay đổi trang phục/tuổi tác)

---

## Edit Plan per-scene

Mỗi cảnh trong visual_plan.json có `edit_plan`:

```json
"edit_plan": {
  "transition_in": "crossfade",
  "transition_out": "crossfade",
  "ken_burns": "Slow zoom in 100% → 110% hướng vào mặt nhân vật trong 5s",
  "pacing": "5s hold, nhịp chậm, suy tư",
  "text_overlay": "\"An Dương Vương\" (dưới trái, sans-serif bold, có shadow, hiện 0-3s)",
  "sound_note": "Piano trầm, thêm tiếng gió lạnh nhẹ, nhạc -20dB"
}
```

---

## Nhịp điệu (Pacing)

### Theo đoạn kịch bản:
- **Hook (0:00 - 0:45)**: Nhịp nhanh, cắt ngắn 2-4 giây/cảnh, gây tò mò
- **Bối cảnh (0:45 - 2:30)**: Chậm lại, mỗi cảnh 5-8 giây, giới thiệu bối cảnh
- **Diễn biến (2:30 - 7:00)**: Nhịp vừa, 4-6 giây/cảnh, xây dựng câu chuyện
- **Cao trào (7:00 - 8:30)**: Nhịp nhanh dần, 3-5 giây/cảnh, kịch tính
- **Kết (8:30 - 10:00)**: Chậm lại, 6-10 giây/cảnh, suy ngẫm

### Pacing per-scene:
- Ghi rõ thời lượng hold ("5s hold", "8.3s hold")
- Ghi lý do nhịp ("dài theo lời đọc", "khoảnh khắc đăng quang")
- Nếu video clip ngắn hơn lời đọc: slow-down (~0.8x) hoặc giữ frame cuối

---

## Chuyển cảnh

### Transition types:
- **crossfade** (0.5-1 giây): Mặc định, ~80% thời lượng
- **fade_from_black / fade_to_black** (0.8 giây): Giữa các đoạn lớn (segment)
- **cut**: Cắt thẳng — cho cao trào, tạo nhịp nhanh kịch tính

### KHÔNG dùng:
- wipe, spin, zoom transition — quá "amateur"

### Ghi trong edit_plan:
- `transition_in`: Cảnh này bắt đầu bằng gì
- `transition_out`: Cảnh này kết thúc bằng gì

---

## Hiệu ứng Ken Burns (ảnh tĩnh)

### Quy tắc chung:
- Mọi ảnh tĩnh PHẢI có Ken Burns — không bao giờ để ảnh nằm yên
- Ghi cụ thể: hướng, % zoom, thời gian

### Các kiểu Ken Burns:
- **Zoom in chậm**: 100% → 110-115% trong 5-8s — tạo cảm giác sống động
- **Zoom out nhẹ**: 110% → 103% — khám phá toàn cảnh
- **Pan ngang**: di chuyển 5-10% frame — khi bối cảnh dàn ngang (ví dụ: split composition Lạc Việt / Âu Việt)
- **Pan + zoom kết hợp**: pan từ nhân vật sang bối cảnh + zoom out nhẹ

### Ghi trong edit_plan:
```
"ken_burns": "Slow zoom in 100% → 110% hướng vào mặt và vương miện, 5s"
"ken_burns": "Slow pan left to right (~10% frame) over 8s: bắt đầu ở Lạc Việt, kết thúc ở Âu Việt"
"ken_burns": null  ← chỉ khi visual_type là video
```

---

## Text Overlay

### Các loại:
- **Tên nhân vật**: Lần đầu xuất hiện, góc dưới trái, font sans-serif bold, có shadow
- **Năm/Thời kỳ**: Góc trên phải, font nhỏ hơn
- **Địa điểm**: Góc dưới trái hoặc phải
- **Trích dẫn sử liệu**: Giữa màn hình, font italic, nền mờ
- **Label kép**: Khi split composition, 2 label xuất hiện lần lượt (ví dụ: "Lạc Việt" 0-4s → "Âu Việt" 4-8s)

### Ghi trong edit_plan:
```
"text_overlay": "\"Thục Phán — Thủ lĩnh Âu Việt\" (dưới trái, 0-4s); \"Hùng Vương thứ 18\" (dưới phải, 5-8s)"
```

### Quy tắc:
- Thời gian hiển thị: 3-5 giây, fade in/out 0.3 giây
- Tối đa 2 dòng, mỗi dòng ≤ 42 ký tự
- Ghi rõ vị trí (góc nào) và timing (hiện từ giây nào đến giây nào)

---

## Âm thanh

### Sound note per-scene:
Ghi cụ thể trong `edit_plan.sound_note`:
```
"sound_note": "Chuyển nhạc từ epic orchestral sang piano/ambient nhẹ, có sáo trúc; nhạc -20dB"
"sound_note": "Một nhịp trống đồng vang + nhạc nâng lên ngắn, sau đó lặng 0.5s"
"sound_note": "Trống đồng trầm, căng thẳng hơn nhưng vẫn -20dB; không lấn giọng đọc"
```

### Quy tắc chung:
- **Nhạc nền**: Epic orchestral (hook, cao trào), piano/ambient (bối cảnh, kết)
- **Âm lượng nhạc**: -18dB đến -22dB (không lấn át giọng đọc)
- **Giọng đọc**: -6dB đến -3dB
- **Sound effects**: Nhẹ nhàng, chỉ khi phù hợp
- **Khoảng lặng**: 0.5-1 giây sau mỗi câu quan trọng
- **Audio direction** (cho video clip): Ghi riêng trong scene — âm thanh môi trường, KHÔNG nhạc nền trong clip

---

## Phụ đề
- Luôn bật, font sans-serif (Arial/Roboto), size vừa đọc trên mobile
- Màu trắng, viền đen 2px hoặc nền mờ
- Tối đa 2 dòng, mỗi dòng ≤ 42 ký tự
- Đồng bộ chính xác với giọng đọc (từ file SRT)

---

## Màn hình kết
- 10-15 giây cuối: logo kênh + 2 video gợi ý (end screen)
- Nút subscribe animation nhẹ
- Nhạc nền fade out trong 5 giây cuối

---

## CapCut Settings
- Resolution: 1920x1080 (16:9)
- FPS: 30
- Export: H.264, bitrate cao (15-20 Mbps)
- Audio: AAC 320kbps