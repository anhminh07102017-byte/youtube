# Quy định hình ảnh — Lịch sử Việt Nam

## Phong cách chung
- **2D animated cartoon**: flat shading, clean bold outlines, simple expressive characters
- KHÔNG dùng realistic, 3D, photorealistic
- Màu sắc ấm, gợi cảm giác cổ kính nhưng sống động
- Bố cục rõ ràng, dễ nhìn trên điện thoại (đa số viewer xem YouTube trên mobile)

## Nhân vật
- Nhân vật lịch sử phải được tạo **giống nguyên tác nhất có thể** (dựa trên tranh vẽ, tượng, mô tả sử liệu)
- Trang phục đúng thời kỳ: áo dài tấc (thời Lý-Trần), áo tứ thân (thời Lê), áo ngũ thân (thời Nguyễn)
- Biểu cảm rõ ràng, cartoon-style (mắt to, nét mặt đơn giản nhưng truyền cảm)
- Tỉ lệ cơ thể hơi chibi (đầu to hơn bình thường 1 chút) cho dễ thương, gần gũi

## Kiến trúc & Bối cảnh
- Kiến trúc Việt Nam đúng thời kỳ: thành Cổ Loa, Hoàng thành Thăng Long, cung điện Huế...
- Phong cảnh: đồng lúa, sông nước, núi non Việt Nam
- Chi tiết trang trí: hoa văn Đông Sơn (thời cổ), rồng phượng (thời phong kiến)
- Background đơn giản, không quá chi tiết để nhân vật nổi bật

## Vũ khí & Đạo cụ
- Đúng thời kỳ: nỏ thần (An Dương Vương), gươm (thời Trần), súng thần công (thời Nguyễn)
- Phong cách vẽ đồng bộ với nhân vật (clean outline, flat color)

## Hiệu ứng
- Chuyển cảnh: fade, slide đơn giản
- Hiệu ứng chiến trận: khói bụi stylized, tia sáng đơn giản
- Chữ trên màn hình: font sans-serif, rõ ràng, có viền/shadow để đọc dễ

## Ngôn ngữ prompt
- Giao diện hệ thống, kịch bản, mô tả cảnh: **tiếng Việt**
- Prompt gửi Veo 3 để tạo hình ảnh/video: **tiếng Anh**, dùng thuật ngữ chuyên dụng cho chính xác

## Prompt Veo 3 — Cấu trúc 3 lớp (TIẾNG ANH)

### Lớp 1: Base Style (luôn có)
```
2D animated cartoon style, flat cel-shading, clean bold outlines, simple expressive characters, vibrant warm color palette, digital illustration, anime-influenced
```

### Lớp 2: Era Style (chọn theo thời kỳ)

**Thời dựng nước (Hùng Vương, An Dương Vương):**
```
ancient Southeast Asian Bronze Age setting, Dong Son bronze drum patterns, thatched bamboo longhouses, misty mountain valleys, rice paddies, earthy brown and bronze-gold tones, primitive weapons, tribal clothing with geometric patterns
```

**Thời Bắc thuộc & Khởi nghĩa (Hai Bà Trưng, Lý Bí):**
```
ancient Vietnamese rebellion era, Chinese-influenced fortifications, war elephants, jungle guerrilla setting, burning fortresses, deep crimson and black tones, warrior women on elephants, bamboo armor
```

**Thời Lý - Trần (1009-1400):**
```
Vietnamese imperial golden age, Thang Long citadel, ornate Buddhist pagodas, dragon motifs, royal court with mandarins, golden and jade-green tones, elaborate silk robes, lotus ponds, Mongol invasion battlefield
```

**Thời Lê - Mạc (1428-1789):**
```
Vietnamese Le Dynasty, grand imperial palace, Confucian scholars, civil examination halls, classical Vietnamese architecture with curved roofs, rich crimson and deep blue tones, mandarin square badges, ink brush calligraphy
```

**Thời Nguyễn (1802-1945):**
```
Vietnamese Nguyen Dynasty, Hue Imperial City, ornate citadel gates, French colonial influence, imperial yellow and deep purple tones, five-panel ao dai, Forbidden Purple City, elaborate dragon throne
```

**Thời cận hiện đại (1945+):**
```
modern Vietnamese revolution era, jungle warfare setting, tropical landscape, propaganda poster aesthetic, red and gold star motifs, military uniforms, rice field battlegrounds, green and red dominant palette
```

### Lớp 3: Character Specific (mô tả nhân vật cụ thể)
Ví dụ:
```
young Vietnamese warrior king, short black hair tied in topknot, wearing golden dragon-embroidered royal robe, tall ornate golden crown, determined fierce expression, muscular build, holding ornamental sword, confident heroic pose
```

### Negative prompt (luôn thêm)
```
realistic, photorealistic, 3D render, live action, Western features, modern clothing, anachronistic elements, blurry, low quality, deformed faces, extra limbs
```

### Ví dụ prompt hoàn chỉnh
```
2D animated cartoon style, flat cel-shading, clean bold outlines, simple expressive characters, vibrant warm color palette. Vietnamese imperial golden age, Thang Long citadel, ornate Buddhist pagodas, dragon motifs, golden and jade-green tones. A young Vietnamese general in bronze armor standing on a wooden warship, pointing forward with a commanding gesture, rivers with wooden stakes visible below, dramatic sunset sky with orange clouds, army of soldiers behind him. Wide cinematic shot.
```

## Màu sắc theo thời kỳ
- **Thời dựng nước (Hùng Vương, An Dương Vương)**: Nâu đất, xanh rêu, vàng đồng — `earthy brown, moss green, bronze gold`
- **Thời Bắc thuộc & khởi nghĩa**: Đỏ sẫm, đen, vàng — `deep crimson, black, gold`
- **Thời Lý - Trần**: Vàng hoàng gia, đỏ son, xanh ngọc — `royal gold, vermillion red, jade green`
- **Thời Lê - Mạc**: Vàng rực, đỏ thẫm, xanh lam — `bright gold, deep crimson, royal blue`
- **Thời Nguyễn**: Vàng đế vương, tím thẫm, trắng ngà — `imperial yellow, deep purple, ivory white`
- **Thời cận hiện đại**: Xanh lá, đỏ cờ, vàng sao — `forest green, flag red, star gold`
