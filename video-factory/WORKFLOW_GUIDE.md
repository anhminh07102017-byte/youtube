# Hướng dẫn sử dụng Video Factory

## Tổng quan

Video Factory là hệ thống sản xuất video hỗ trợ **nhiều loại nội dung và phong cách** khác nhau. Mỗi dự án (project) được cấu hình riêng biệt qua các file trong thư mục dự án.

---

## Cấu trúc file của 1 dự án

```
projects/{project-id}/
├── project.json              ← Config chính: tên, loại, nguồn, ghi chú
├── style_guide.md            ← Hướng dẫn phong cách hình ảnh
├── content_guide.md          ← Hướng dẫn nội dung & cấu trúc kịch bản
├── storytelling_guide.md     ← Cách kể chuyện, giọng văn, nhịp điệu
├── characters/               ← Database nhân vật (nếu có)
│   └── {character}.json
└── videos/{video-id}/
    ├── script.md             ← Kịch bản hoàn chỉnh
    ├── narration.md          ← Lời đọc (voice content)
    ├── content_brief.md      ← Tóm tắt nội dung video
    ├── visual_guide.md       ← Hướng dẫn hình ảnh cho video này
    ├── edit_guide.md         ← Hướng dẫn edit cho video này
    ├── brainstorm.md         ← Ghi chú brainstorm
    ├── shot_list.json        ← Danh sách cảnh (scenes)
    ├── visual_plan.json      ← Chi tiết visual từng cảnh
    ├── director_plan.json    ← Kế hoạch đạo diễn theo segment
    ├── audio/                ← File audio giọng đọc
    ├── assets/               ← Hình ảnh & video đã generate
    └── shorts/               ← YouTube Shorts (nếu có)
```

---

## Vai trò từng file cấu hình

### Cấp dự án (project-level)

| File | Vai trò | Bắt buộc? |
|---|---|---|
| `project.json` | Metadata: tên, loại project, nguồn tham khảo | Có |
| `style_guide.md` | Quy định phong cách hình ảnh: art style, prompt rules, ví dụ prompt | Có |
| `content_guide.md` | Quy định nội dung: cấu trúc kịch bản, quy tắc viết, nguồn sử liệu | Có |
| `storytelling_guide.md` | Cách kể chuyện: giọng văn, tốc độ, cảm xúc, đối tượng | Nên có |

### Cấp video (video-level)

| File | Vai trò | Khi nào cần? |
|---|---|---|
| `content_brief.md` | Tóm tắt nội dung video cụ thể | Trước khi viết kịch bản |
| `visual_guide.md` | Hướng dẫn hình ảnh riêng cho video này (override style_guide nếu cần) | Khi video cần style khác project |
| `edit_guide.md` | Hướng dẫn edit: transition, pacing, Ken Burns, text overlay, audio | Trước khi tạo visual plan |
| `brainstorm.md` | Ghi chú ý tưởng khi brainstorm | Tự động tạo khi chat |

---

## Các loại nội dung và cách cấu hình

### 1. Lịch sử kể chuyện (History Storytelling)

**Ví dụ**: "Trận Bạch Đằng 938", "The Fall of Rome", "Cuộc khởi nghĩa Hai Bà Trưng"

**Cấu hình cần thiết:**

| File | Nội dung cần có |
|---|---|
| `project.json` | `type`: bất kỳ, `tone`: "dramatic_narrative", `sources`: danh sách sử liệu |
| `style_guide.md` | Art style (2D animation, watercolor...), prompt 3 lớp (base + era + character), ví dụ prompt |
| `content_guide.md` | Cấu trúc 6 phần: Hook → Bối cảnh → Diễn biến → Cao trào → Kết cục → Outro. Quy tắc ghi nguồn sử liệu |
| `storytelling_guide.md` | Giọng kể: trang trọng nhưng gần gũi, gây tò mò, dramatic |
| `edit_guide.md` | Ken Burns trên ảnh tĩnh, crossfade, pacing chậm-nhanh theo đoạn, nhạc orchestral |
| `characters/` | Character sheet cho mỗi nhân vật lịch sử: visual description, consistency anchors |

**Pipeline**: Kịch bản → Audio → Shot list → Character sheets → Generate assets → CapCut

**Template tham khảo**: `templates/image_styles/2d-hoat-hinh-lich-su.json`, `templates/edit_styles/lich-su-ke-chuyen.json`

---

### 2. Giải thích (Explainer / "Tại sao X?")

**Ví dụ**: "Tại sao bầu trời màu xanh?", "Vì sao Nhật Bản phát triển nhanh sau WWII?"

**Cấu hình cần thiết:**

| File | Nội dung cần có |
|---|---|
| `project.json` | `type`: "custom", `tone`: "educational" hoặc "conversational" |
| `style_guide.md` | Art style phù hợp (infographic, 2D animation, mixed). Prompt rules cho diagram, icon, illustration |
| `content_guide.md` | Cấu trúc explainer — xem mẫu bên dưới |
| `storytelling_guide.md` | Giọng kể: dễ hiểu, gần gũi, ví dụ thực tế, pha chút hài hước |
| `edit_guide.md` | Pacing nhanh (3-5s/cảnh), text overlay nhiều, motion graphics, nhạc upbeat |

**Cấu trúc kịch bản explainer (ghi trong `content_guide.md`):**
```markdown
## Cấu trúc kịch bản — Explainer

### HOOK (15-30 giây)
Câu hỏi trực tiếp hoặc sự thật bất ngờ liên quan đến chủ đề.
Ví dụ: "Bạn có biết, mỗi ngày bạn nuốt trung bình 1.5 lít nước bọt?"

### VẤN ĐỀ (1-2 phút)
Trình bày vấn đề/hiện tượng cần giải thích. Mô tả trải nghiệm quen thuộc để viewer đồng cảm.

### GIẢI THÍCH (3-5 phút)
Chia thành 2-4 luận điểm, mỗi luận điểm:
- Tuyên bố rõ ràng
- Bằng chứng/ví dụ
- Hình ảnh minh họa trực quan (diagram, infographic, animation)

### PHẢN BIỆN / GÓC NHÌN KHÁC (1-2 phút)
Nêu quan điểm ngược lại hoặc ngoại lệ. Giải thích tại sao vẫn đúng hoặc khi nào không đúng.

### KẾT LUẬN (30-60 giây)
Tóm tắt ngắn gọn + mở rộng: "Vậy lần tới khi bạn thấy X, hãy nhớ rằng..."

### OUTRO (15-30 giây)
CTA
```

**Phong cách hình ảnh (ghi trong `style_guide.md`):**
```markdown
## Phong cách hình ảnh — Explainer

### Art style
- Kết hợp: infographic (diagram, biểu đồ) + illustration đơn giản (2D flat)
- Màu sắc: palette sáng, tối đa 3-4 màu chính, contrast cao
- Typography: lớn, rõ ràng, sans-serif

### Loại hình ảnh cần
- **Diagram/Infographic**: Minh họa quy trình, so sánh, thống kê
- **Icon/Symbol**: Đại diện cho khái niệm trừu tượng
- **Illustration**: Ví dụ cụ thể, scenario minh họa
- **Text-heavy frame**: Key point, số liệu, quote
- **Bản đồ**: Khi liên quan đến địa lý

### Prompt rules
- Base: "clean infographic style, flat design, modern vector graphics..."
- Mỗi cảnh: focus 1 ý chính duy nhất
- Background: đơn giản, solid color hoặc subtle gradient
- Ưu tiên clarity over aesthetics
```

**Phong cách edit (ghi trong `edit_guide.md`):**
```markdown
## Hướng dẫn Edit — Explainer

### Pacing
- Hook: 2-3s/cảnh, gây chú ý ngay
- Giải thích: 3-5s/cảnh, vừa đủ đọc text overlay
- Kết luận: 5-7s/cảnh, để ý sink in

### Chuyển cảnh
- Cut thẳng (60%): giữ nhịp nhanh
- Crossfade ngắn 0.3s (30%): chuyển giữa các luận điểm
- Zoom transition (10%): khi zoom vào chi tiết

### Text Overlay
- NHIỀU text overlay — mỗi cảnh nên có text
- Key number: font lớn, bold, giữa màn hình
- Key phrase: dưới 1/3, sans-serif, 3-4 giây
- Label: góc trên, font nhỏ, persistent

### Ken Burns
- Zoom nhanh hơn lịch sử: 100% → 115-120%
- Pan kết hợp zoom khi scan qua infographic

### Âm thanh
- Nhạc: upbeat, modern, electronic/lo-fi, -16dB
- SFX: pop/whoosh khi text xuất hiện, subtle
- Giọng đọc: tốc độ nhanh hơn lịch sử, -3dB
- Không có khoảng lặng dài
```

---

### 3. Phim tài liệu (Documentary)

**Ví dụ**: "Cuộc sống ở vùng cao Tây Bắc", "Inside the Amazon Rainforest"

**Cấu hình cần thiết:**

| File | Nội dung cần có |
|---|---|
| `project.json` | `tone`: "documentary" |
| `style_guide.md` | Realistic illustration hoặc watercolor. Chi tiết, atmospheric |
| `content_guide.md` | Cấu trúc narrative dài hơi — xem mẫu bên dưới |
| `storytelling_guide.md` | Giọng kể: trầm, suy tư, khách quan, để hình ảnh kể chuyện |
| `edit_guide.md` | Pacing chậm, hold dài (8-15s/cảnh), nhạc ambient, ít text overlay |

**Cấu trúc kịch bản documentary (ghi trong `content_guide.md`):**
```markdown
## Cấu trúc kịch bản — Documentary

### MỞ ĐẦU (1-2 phút)
Establishing shot + giới thiệu chủ đề. Để hình ảnh nói trước, giọng đọc vào sau.

### PHẦN 1: BỐI CẢNH (2-3 phút)
Bối cảnh lịch sử/địa lý/xã hội. Xây dựng world-building.

### PHẦN 2: CÂU CHUYỆN CHÍNH (3-4 phút)
Narrative chính, theo timeline hoặc theo chủ đề. Interview quotes nếu có.

### PHẦN 3: CHIỀU SÂU (2-3 phút)
Phân tích, bối cảnh rộng hơn, ý nghĩa.

### KẾT (1-2 phút)
Reflection, để lại suy nghĩ, không cần CTA mạnh.
```

**Phong cách edit documentary:**
```markdown
## Hướng dẫn Edit — Documentary

### Pacing
- Chậm, deliberate: 8-15 giây/cảnh
- Để hình ảnh "thở" — không vội chuyển cảnh
- Khoảng lặng có chủ đích giữa các phần

### Chuyển cảnh
- Crossfade dài (1-1.5s): 70%
- Fade to/from black (1s): chuyển phần, 25%
- Cut: chỉ khi cần contrast mạnh, 5%

### Ken Burns
- Rất chậm: 100% → 105-108% trong 10-15s
- Pan chậm, smooth, contemplative
- Tạo cảm giác viewer đang ở trong cảnh

### Text Overlay
- Ít text — chỉ thông tin quan trọng
- Tên người/nơi: font serif elegant, góc dưới trái
- Năm/thời gian: nhỏ, unobtrusive

### Âm thanh
- Ambient/orchestral chậm, -22dB đến -25dB
- Natural sounds: gió, nước, tiếng chim (lấy từ stock)
- Khoảng lặng quan trọng — đừng fill mọi khoảng trống
- Giọng đọc: chậm, trầm, reflective
```

---

### 4. Danh sách / Top N (Listicle)

**Ví dụ**: "7 điều bạn chưa biết về Hồ Chí Minh", "Top 10 trận chiến đẫm máu nhất lịch sử"

**Cấu hình cần thiết:**

| File | Nội dung cần có |
|---|---|
| `project.json` | `tone`: "entertaining" hoặc "educational" |
| `style_guide.md` | 2D animation hoặc infographic. Title cards cho mỗi item |
| `content_guide.md` | Cấu trúc listicle — xem mẫu bên dưới |
| `storytelling_guide.md` | Giọng kể: energetic, tạo suspense cho item tiếp theo |
| `edit_guide.md` | Pacing đều, title card + number cho mỗi item |

**Cấu trúc kịch bản listicle:**
```markdown
## Cấu trúc kịch bản — Listicle

### HOOK (15-30 giây)
Tease item hay nhất (thường cuối list). "Và điều cuối cùng sẽ khiến bạn bất ngờ..."

### GIỚI THIỆU (15-30 giây)
Context ngắn: tại sao list này thú vị.

### ITEM N (đếm ngược hoặc xuôi)
Mỗi item:
- Title card (3s): Số + tên item
- Nội dung (45-90 giây): Giải thích, fact thú vị, ví dụ
- Transition hook: "Nhưng chưa hết..." / "Và điều tiếp theo còn..."

### KẾT (30-45 giây)
Recap nhanh + CTA: "Theo bạn, điều nào thú vị nhất? Comment bên dưới!"
```

---

### 5. Hướng dẫn / Tutorial

**Ví dụ**: "Cách đọc bản đồ cổ", "Hướng dẫn phân tích sử liệu"

**Cấu trúc kịch bản tutorial (ghi trong `content_guide.md`):**
```markdown
## Cấu trúc kịch bản — Tutorial

### HOOK (15 giây)
Kết quả cuối cùng: "Sau video này, bạn sẽ biết cách..."

### VÌ SAO CẦN BIẾT (30-60 giây)
Motivation: tại sao skill này hữu ích.

### BƯỚC 1-N
Mỗi bước:
- Tuyên bố bước (5s)
- Demo/minh họa (30-60s)
- Tip/lưu ý (15s)

### TỔNG KẾT (30 giây)
Recap các bước + "Bây giờ bạn đã sẵn sàng..."

### OUTRO (15 giây)
CTA
```

---

## Phong cách hình ảnh có sẵn

Hệ thống có các base style trong `style_guides/`:

| File | Phong cách | Phù hợp cho |
|---|---|---|
| `base_2d_style.json` | 2D animated cartoon, flat shading, bold outlines | Lịch sử, storytelling, listicle |
| `base_watercolor.json` | Watercolor painting, soft washes, artistic | Documentary, câu chuyện cảm xúc |
| `base_infographic.json` | Flat design, vector graphics, data viz | Explainer, tutorial, so sánh |
| `base_realistic_illustration.json` | Realistic digital painting, cinematic | Documentary, lịch sử epic |

### Cách sử dụng base style

Khi tạo `style_guide.md` cho project, copy nội dung từ base style phù hợp + thêm era style (nếu lịch sử) + customization riêng.

### Era styles (cho nội dung lịch sử)

Thư mục `style_guides/eras/` chứa các thời kỳ Việt Nam:
- `hung_vuong.json`, `bac_thuoc.json`, `ly.json`, `tran.json`, `le_so.json`...

Thư mục `style_guides/world/` cho lịch sử thế giới:
- `_template.json` — mẫu trống để tạo era mới

**Tạo era style mới** (copy `_template.json` và điền):
```json
{
  "era_name": "Roman Empire",
  "time_period": "27 BC - 476 AD",
  "prompt_addition": "ancient Roman civilization, Mediterranean setting, classical architecture",
  "architecture": ["Roman columns", "aqueducts", "Colosseum", "Senate building", "Roman baths"],
  "clothing": ["toga", "lorica segmentata armor", "laurel wreath", "sandals", "stola"],
  "weapons": ["gladius sword", "pilum javelin", "scutum shield", "Roman siege weapons"],
  "key_elements": ["Roman eagles (aquila)", "SPQR banners", "olive branches", "Roman roads"],
  "color_palette": {"primary": "#8B0000", "secondary": "#DAA520", "accent": "#F5F5DC", "background": "#D2B48C"},
  "notes": "Chú ý: Roman triumphal arches, marble textures, Mediterranean landscape"
}
```

---

## Tạo template mới

Templates nằm trong `templates/` và có thể áp dụng vào dự án qua Web UI (trang Tài nguyên).

### Cấu trúc file template

```json
{
  "id": "ten-template",
  "name": "Tên hiển thị",
  "category": "image_style | edit_style | storytelling_profile",
  "description": "Mô tả ngắn",
  "preview_summary": "• Bullet 1\n• Bullet 2\n• Bullet 3",
  "applies_to": ["project_style_guide", "video_visual_guide", "video_edit_guide", "project_storytelling_guide"],
  "content": "Nội dung markdown đầy đủ — đây là phần sẽ được ghi vào file guide của project/video khi áp dụng"
}
```

### Các loại template

| Thư mục | Category | Áp dụng vào |
|---|---|---|
| `templates/image_styles/` | `image_style` | `style_guide.md` (project) hoặc `visual_guide.md` (video) |
| `templates/edit_styles/` | `edit_style` | `edit_guide.md` (video) |
| `templates/storytelling_profiles/` | `storytelling_profile` | `storytelling_guide.md` (project) |

### Mẫu tạo template image style mới

```json
{
  "id": "ten-phong-cach",
  "name": "Tên phong cách",
  "category": "image_style",
  "description": "Mô tả ngắn về phong cách",
  "preview_summary": "• Đặc điểm 1\n• Đặc điểm 2\n• Pipeline tạo hình",
  "applies_to": ["project_style_guide", "video_visual_guide"],
  "content": "# Phong cách hình ảnh — {Tên}\n\n## Phong cách chung\n- ...\n\n## Nhân vật\n- ...\n\n## Pipeline tạo hình ảnh/video\n- Tỷ lệ ảnh tĩnh vs video clip\n- Công cụ: Veo 3 / Flux / ...\n\n## Cấu trúc Prompt\n### Base prompt\n```\n...\n```\n### Negative prompt\n```\n...\n```\n\n## Ví dụ prompt\n### Ảnh tĩnh\n```\n...\n```\n### Video clip\n```\n...\n```"
}
```

### Mẫu tạo template edit style mới

```json
{
  "id": "ten-edit-style",
  "name": "Tên phong cách edit",
  "category": "edit_style",
  "description": "Mô tả ngắn",
  "preview_summary": "• Pacing\n• Chuyển cảnh\n• Âm thanh",
  "applies_to": ["video_edit_guide"],
  "content": "# Hướng dẫn Edit — {Tên}\n\n## Nhịp điệu (Pacing)\n- ...\n\n## Chuyển cảnh\n- ...\n\n## Ken Burns\n- ...\n\n## Text Overlay\n- ...\n\n## Âm thanh\n- ...\n\n## CapCut Settings\n- Resolution: ...\n- FPS: ...\n- Export: ..."
}
```

### Mẫu tạo storytelling profile mới

```json
{
  "id": "ten-storytelling",
  "name": "Tên cách kể chuyện",
  "category": "storytelling_profile",
  "description": "Mô tả ngắn",
  "preview_summary": "• Giọng văn\n• Đối tượng\n• Nhịp kể",
  "applies_to": ["project_storytelling_guide"],
  "content": "# Cách kể chuyện — {Tên}\n\n## Giọng văn\n- ...\n\n## Đối tượng\n- ...\n\n## Nhịp kể\n- ...\n\n## Kỹ thuật gây hứng thú\n- ...\n\n## Ví dụ câu mở đầu\n- ..."
}
```

---

## Workflow tổng thể

### Bước 1: Tạo dự án
- Tạo trên Web UI hoặc tạo thư mục + `project.json` thủ công
- Điền tên, nguồn tham khảo, ghi chú

### Bước 2: Cấu hình phong cách
- **style_guide.md**: Chọn base style phù hợp → copy/customize vào file này. Hoặc áp dụng template từ Web UI (trang Tài nguyên)
- **content_guide.md**: Viết cấu trúc kịch bản phù hợp loại content (xem các mẫu ở trên)
- **storytelling_guide.md**: Định nghĩa giọng kể, đối tượng, nhịp điệu

### Bước 3: Tạo video
- Tạo video trong dự án (Web UI hoặc thủ công)
- Áp dụng edit guide cho video (từ template hoặc viết tay)

### Bước 4: Lên kịch bản
- Mở terminal → "Làm việc với project X, lên kịch bản cho video Y"
- Chat brainstorm → khi hài lòng nói "Chốt"
- Claude đọc `content_guide.md` + `storytelling_guide.md` để viết đúng phong cách

### Bước 5: Audio
- Chuyển kịch bản thành audio (giọng đọc)
- Upload qua Web UI

### Bước 6: Shot list & Visual plan
- Claude tạo shot list từ kịch bản
- Claude đọc `style_guide.md` + `edit_guide.md` để tạo visual plan phù hợp

### Bước 7: Generate assets
- Claude mở browser Veo 3, dùng prompt từ visual plan
- User review từng cảnh trên Web UI → đánh dấu redo nếu cần

### Bước 8: Build CapCut
- Claude build project CapCut từ scenes + assets + audio
- User mở CapCut Pro tinh chỉnh & export

---

## Ví dụ cấu hình nhanh

### Ví dụ: Dự án lịch sử thế giới
```
1. Tạo project trên Web UI: "Lịch sử Đế chế La Mã"
2. Tạo era file: style_guides/world/roman_empire.json (copy từ _template.json)
3. Tạo style_guide.md: copy base_2d_style.json content → thêm era details
4. Tạo content_guide.md: dùng cấu trúc 6 phần lịch sử kể chuyện
5. Áp dụng edit template "Lịch sử kể chuyện" từ trang Tài nguyên
6. Tạo characters: Caesar, Brutus... với visual descriptions
```

### Ví dụ: Dự án explainer khoa học
```
1. Tạo project: "Khoa học vui"
2. Tạo style_guide.md: copy base_infographic.json content → customize màu sắc
3. Tạo content_guide.md: dùng cấu trúc explainer (Hook → Vấn đề → Giải thích → Phản biện → Kết luận)
4. Viết edit_guide.md: pacing nhanh, nhiều text overlay, nhạc upbeat
5. Không cần characters/ (hoặc chỉ cần mascot đơn giản)
```

### Ví dụ: Dự án documentary
```
1. Tạo project: "Cuộc sống vùng cao"
2. Tạo style_guide.md: copy base_watercolor.json hoặc base_realistic_illustration.json
3. Tạo content_guide.md: dùng cấu trúc documentary
4. Viết edit_guide.md: pacing chậm, hold dài, ambient audio
5. storytelling_guide.md: giọng trầm, reflective, để hình ảnh kể chuyện
```

---

## Veo3 Prompt Engine — Cách hoạt động

Engine đọc config từ files, không hardcode:

1. **Base style**: Load từ `style_guides/base_{style}.json` (mặc định: `base_2d_style.json`)
2. **Era style**: Load từ `style_guides/eras/{era}.json` hoặc `style_guides/world/{era}.json`
3. **Character**: Load từ `characters/` trong project

Engine tự build prompt 3 lớp từ các file trên. Muốn đổi style cho project → đổi base style file mà engine đọc.

Cấu hình base style cho project qua field `base_style` trong `project.json`:
```json
{
  "base_style": "base_2d_style"
}
```

Giá trị có thể: `base_2d_style`, `base_watercolor`, `base_infographic`, `base_realistic_illustration`, hoặc tên file custom (không có đuôi `.json`).

---

## Tóm tắt: Muốn làm content kiểu X thì cần gì?

| Bước | Lịch sử kể chuyện | Explainer | Documentary | Listicle |
|---|---|---|---|---|
| Base style | 2D animation | Infographic | Watercolor/Realistic | 2D animation |
| Era style | Có (thời kỳ cụ thể) | Không | Tùy | Tùy |
| Characters | Có (nhân vật lịch sử) | Không/Ít | Tùy | Tùy |
| Script structure | 6 phần (Hook→Outro) | 5 phần (Hook→CTA) | 5 phần tự do | N items + Hook/CTA |
| Edit style | Chậm, Ken Burns, dramatic | Nhanh, text-heavy | Rất chậm, ambient | Đều, title cards |
| Âm thanh | Orchestral -20dB | Upbeat -16dB | Ambient -22dB | Energetic -16dB |
| Pacing | 4-8s/cảnh | 3-5s/cảnh | 8-15s/cảnh | 4-6s/cảnh |

---

## YouTube Shorts

### Cấu trúc file shorts
Shorts nằm trong thư mục con `shorts/` của video:
```
videos/{video-id}/shorts/
├── script.md         ← Kịch bản short
├── narration.md      ← Lời đọc
├── content_brief.md  ← Tóm tắt nội dung
├── brainstorm.md     ← Ghi chú
├── audio/            ← File audio
└── assets/           ← Hình ảnh & video
```

### Trạng thái hiện tại
- Format: **9:16** (1080x1920), **45-50 giây**
- Shorts **kế thừa** style_guide và edit_guide từ video gốc (không có file riêng)
- Scene model dùng flag `is_short = True` để phân biệt
- Chat brainstorm shorts sử dụng context từ video gốc làm tham chiếu

### Hỗ trợ mở rộng
- Shorts hoạt động với **mọi loại content** — chỉ cần content_guide đúng format
- Base style của project áp dụng cho cả shorts
- Muốn shorts có style khác video gốc → viết thủ công vào `shorts/visual_guide.md` (tính năng mở rộng tương lai)

### Hạn chế cần biết
- System prompt cho shorts hiện tại có nhắc "kênh lịch sử" — sẽ được generic hóa khi có project khác
- Shorts chưa có edit_guide riêng — dùng chung edit_guide của video gốc
- Nếu cần shorts với phong cách edit khác hoàn toàn → ghi chú cụ thể trong brainstorm hoặc content_brief của short
