# Kế hoạch xây dựng hệ thống Minh Bi Youtube

## 1. Tổng quan hệ thống

Hệ thống sản xuất video lịch sử phong cách **2D animation/hoạt hình**, gồm 2 phần chính:

| Thành phần | Vai trò | Chạy bằng |
|-----------|---------|-----------|
| **Web UI** | Giao diện quản lý, duyệt content, review assets, upload audio | Docker (`localhost:3000`) |
| **Claude Code** | AI engine — viết kịch bản, tạo prompt, điều khiển Veo 3, build CapCut | Terminal (đang dùng) |

**Không cần API key nào.** Claude Code chính là AI engine, Veo 3 chạy qua browser.

### Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker (docker compose up)                │
│                                                             │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────┐  │
│  │ Frontend (React) │  │ Backend (FastAPI) │  │ Playwright│  │
│  │ localhost:3000   │→│ localhost:8000    │  │ (browser) │  │
│  └─────────────────┘  └────────┬─────────┘  └───────────┘  │
│                                │                            │
└────────────────────────────────┼────────────────────────────┘
                                 │ mounted volume
                                 │
                    ~/Youtube/video-factory/
                        ├── projects/        ← data chung
                        ├── character_db/
                        └── style_guides/
                                 │
┌────────────────────────────────┼────────────────────────────┐
│  Claude Code (terminal)        │                            │
│  - Viết kịch bản      → lưu vào projects/                  │
│  - Tạo shot list       → lưu vào projects/                  │
│  - Điều khiển Playwright → generate Veo 3 → download assets │
│  - Build CapCut project → lưu vào projects/                 │
└─────────────────────────────────────────────────────────────┘
```

### Tương thích
- **macOS**: Docker Desktop for Mac
- **Windows**: Docker Desktop for Windows
- Cùng 1 `docker-compose.yml`, chạy giống hệt nhau

---

## 2. Kiến trúc thư mục

```
Youtube/
├── CLAUDE.md                       # Quy định chung
├── PLAN.md                         # File này
│
├── video-factory/
│   │
│   ├── docker-compose.yml          # Docker config
│   ├── .env                        # Config (không có API keys)
│   │
│   ├── frontend/                   # Web UI (React/Next.js)
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── src/
│   │       ├── pages/
│   │       │   ├── dashboard/      # Danh sách projects + videos
│   │       │   ├── script/         # Đọc/sửa/duyệt kịch bản
│   │       │   ├── characters/     # Xem/quản lý nhân vật
│   │       │   ├── shotlist/       # Timeline visual, duyệt cảnh
│   │       │   ├── assets/         # Grid review ảnh/video
│   │       │   └── export/         # Preview timeline, build CapCut
│   │       └── components/
│   │
│   ├── backend/                    # API server (FastAPI)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/
│   │       ├── api/                # REST endpoints
│   │       ├── services/           # Business logic
│   │       └── db/                 # SQLite models
│   │
│   ├── core/                       # Python modules (Claude Code dùng trực tiếp)
│   │   ├── script_engine.py        # Engine tạo & format kịch bản
│   │   ├── shot_list_builder.py    # Script → danh sách cảnh
│   │   ├── veo3_prompt_engine.py   # Tạo prompt Veo 3 (3 lớp)
│   │   ├── character_manager.py    # Quản lý nhân vật & đồng bộ prompt
│   │   ├── capcut_builder.py       # Tạo project CapCut tự động
│   │   ├── asset_manager.py        # Quản lý assets
│   │   └── config.py               # Config chung
│   │
│   ├── style_guides/               # Phong cách hình ảnh
│   │   ├── base_2d_style.json      # Style 2D animation chung
│   │   ├── eras/                   # Phong cách theo thời kỳ VN
│   │   │   ├── hung_vuong.json
│   │   │   ├── bac_thuoc.json
│   │   │   ├── ngo_dinh_tien_le.json
│   │   │   ├── ly.json
│   │   │   ├── tran.json
│   │   │   ├── ho_hau_tran.json
│   │   │   ├── le_so.json
│   │   │   ├── mac.json
│   │   │   ├── le_trung_hung.json
│   │   │   ├── trinh_nguyen.json
│   │   │   ├── tay_son.json
│   │   │   ├── nguyen.json
│   │   │   ├── phap_thuoc.json
│   │   │   └── hien_dai.json
│   │   └── world/                  # Lịch sử thế giới (mở rộng)
│   │       └── _template.json
│   │
│   ├── character_db/               # Database nhân vật
│   │   ├── _template.json          # Template tạo nhân vật
│   │   └── projects/               # Nhân vật theo project
│   │       └── {project_id}/
│   │           ├── characters.json
│   │           └── refs/           # Ảnh tham khảo nguyên tác
│   │
│   ├── projects/                   # Các dự án (shared giữa Web UI + Claude Code)
│   │   └── {project_id}/
│   │       ├── project.json        # Config dự án
│   │       └── videos/
│   │           └── {video_id}/
│   │               ├── script.md
│   │               ├── shot_list.json
│   │               ├── audio/
│   │               ├── assets/
│   │               │   ├── images/
│   │               │   └── videos/
│   │               ├── maps/
│   │               ├── music/
│   │               └── output/
│   │
│   ├── templates/                  # Templates dùng chung
│   │   ├── script_template.md
│   │   ├── capcut_template.json
│   │   └── thumbnail_guide.md
│   │
│   └── resources/                  # Tài liệu tham khảo
│       ├── sources.md              # Nguồn sử liệu uy tín
│       └── legal_guidelines.md     # Hướng dẫn pháp luật VN
```

---

## 3. Hệ thống đồng bộ nhân vật (Character Consistency)

### 3.1 Character Sheet

Mỗi nhân vật lịch sử có 1 file mô tả chi tiết:

```json
{
  "id": "tran_hung_dao",
  "name": "Trần Hưng Đạo",
  "historical_name": "Trần Quốc Tuấn",
  "era": "tran",
  "age_range": "50-70",
  "reference_description": "Dựa trên tượng thờ tại đền Kiếp Bạc, tranh vẽ truyền thống",

  "visual_prompt_base": "elderly Vietnamese general, 2D animated cartoon style, long white flowing beard, strong stern face with deep-set wise eyes, wearing red and gold armor with dragon motif, general's helmet with plume, broad shoulders, commanding presence",

  "visual_variants": {
    "court": "...wearing formal court robes, standing in royal palace",
    "battle": "...on horseback, wielding sword, commanding troops",
    "planning": "...sitting at war table with maps, thoughtful expression"
  },

  "color_palette": {
    "skin": "#D4A574",
    "hair": "#FFFFFF",
    "primary_outfit": "#8B0000",
    "secondary_outfit": "#FFD700"
  },

  "consistency_anchors": [
    "long white beard flowing to chest",
    "strong square jaw",
    "deep-set wise eyes",
    "broad shoulders"
  ],

  "appears_in_videos": ["ep01_bach_dang", "ep02_nguyen_mong_1"]
}
```

### 3.2 Hệ thống prompt 3 lớp

```
LỚP 1 - BASE STYLE (chung toàn hệ thống):
  "2D animated cartoon style, flat shading, clean bold outlines,
   simple but expressive character designs, educational history
   animation aesthetic, vibrant historically appropriate colors,
   no text in image, high quality illustration"

LỚP 2 - ERA STYLE (theo thời kỳ, load từ style_guides/eras/):
  Ví dụ thời Trần:
  "13th century Vietnamese setting, Tran dynasty architecture,
   tiled-roof palaces, wooden warships, rice paddies,
   red and gold dominant color palette"

LỚP 3 - CHARACTER + SCENE (theo nhân vật + cảnh cụ thể):
  "elderly Vietnamese general Tran Hung Dao (long white beard,
   red-gold armor, dragon motif, stern wise face) standing on
   warship bow pointing forward, Bach Dang river with wooden
   stakes visible in water, dramatic sunset, wide shot"
```

**Prompt cuối cùng** = Lớp 1 + Lớp 2 + Lớp 3 + Negative prompts

### 3.3 Quy trình tạo nhân vật mới

1. User cung cấp: tên nhân vật + thời kỳ + ảnh tham khảo (nếu có)
2. Claude nghiên cứu tư liệu → tạo character sheet draft
3. Claude mở browser, generate **3-5 test images** qua Veo 3
4. User chọn version ưng nhất → đó là **anchor image**
5. Claude tinh chỉnh prompt base theo anchor → lưu vào `character_db/`
6. Mọi cảnh có nhân vật này đều dùng prompt base đã duyệt

---

## 4. Veo 3 - Browser Automation (Playwright)

### 4.1 Cách hoạt động
- **Không cần API key** — Claude Code điều khiển browser qua Playwright MCP tools
- User chỉ cần đăng nhập tài khoản Google trên browser 1 lần
- Claude tự động: mở trang → paste prompt → generate → download

### 4.2 Workflow tự động

```
Claude đọc shot_list.json
    ↓
Với mỗi cảnh (scene):
    ↓
  1. Mở browser → navigate tới Veo 3
  2. Paste prompt (đã build từ 3 lớp)
  3. Chọn cấu hình (image/video, kích thước, thời lượng)
  4. Click generate
  5. Chờ kết quả
  6. Download về → lưu vào assets/{scene_id}.png hoặc .mp4
  7. Chuyển sang cảnh tiếp theo
    ↓
Hoàn thành → User review trên Web UI
```

### 4.3 Xử lý lỗi & retry
- Nếu generate fail → retry tối đa 3 lần
- Nếu kết quả không đạt (user đánh dấu trên Web UI) → Claude re-generate
- Log toàn bộ quá trình vào `assets/generation_log.json`

### 4.4 Phân loại cảnh: Image vs Video

| Loại cảnh | Dùng gì | Khi nào |
|-----------|---------|---------|
| Establishing shot | **Video 5-8s** | Cảnh mở đầu, panorama |
| Nhân vật đứng/nói | **Image + Ken Burns** | Đối thoại, miêu tả |
| Hành động/chiến đấu | **Video 3-5s** | Trận đánh, di chuyển |
| Bản đồ/sơ đồ | **Image (tự tạo)** | Giải thích địa lý, chiến thuật |
| Cảnh chuyển tiếp | **Image + Ken Burns** | Giữa các phần |
| Cao trào | **Video 5-8s** | Bước ngoặt quan trọng |

**Tỷ lệ mục tiêu cho video 10 phút:**
- ~15-20 images (cảnh tĩnh + Ken Burns)
- ~8-12 video clips 3-8s (cảnh chuyển động)
- ~3-5 bản đồ/sơ đồ

---

## 5. CapCut Pro Desktop - Tự động hóa

### 5.1 Cách hoạt động

CapCut Desktop lưu project dạng JSON (`draft_content.json`). Claude sẽ:
1. Reverse-engineer format từ project mẫu do user tạo
2. Viết `capcut_builder.py` để generate project tự động
3. Output: file project mở trực tiếp trong CapCut Pro

### 5.2 Cấu trúc timeline tự động

```
Track 1 (Audio)     : voice_narration.mp3 (main)
Track 2 (Visual)    : scene_001.mp4, scene_002.png, scene_003.mp4, ...
Track 3 (Subtitle)  : auto-generated từ kịch bản (SRT format)
Track 4 (BGM)       : background_music.mp3 (volume 15-20%)
Track 5 (Text)      : tên nhân vật, năm, địa danh (overlay)
Track 6 (Effects)   : transitions (cross dissolve, fade), Ken Burns
```

### 5.3 Tự động áp dụng

| Yếu tố | Tự động | Chi tiết |
|---------|---------|----------|
| Image duration | Co | Theo shot_list.json timing |
| Ken Burns | Co | Zoom/pan cho ảnh tĩnh |
| Transitions | Co | Cross dissolve 0.5s giữa các cảnh |
| Subtitles | Co | Từ kịch bản, sync với audio |
| BGM volume | Co | 15-20%, duck khi có voice |
| Text overlay | Co | Tên, năm, địa danh từ shot_list |
| Color grading | Không | User tự chỉnh trong CapCut |
| Sound effects | Không | User tự thêm nếu cần |

### 5.4 Yêu cầu từ User (1 lần duy nhất)

Để reverse-engineer format CapCut, user cần:
1. Mở CapCut Pro Desktop → tạo 1 project đơn giản:
   - 1 ảnh bất kỳ (kéo vào timeline, khoảng 5s)
   - 1 file audio (kéo vào timeline)
   - 1 text overlay
   - 1 subtitle
   - 1 transition giữa 2 ảnh
2. Lưu project
3. Tìm folder project: thường ở `~/Movies/CapCut/User Data/Projects/com.lemon.lvpro/` hoặc tương tự trên macOS
4. Gửi Claude file `draft_content.json` trong folder project

---

## 6. Quản lý Multi-Project (Session per Project)

### 6.1 Nguyên tắc: 1 tab terminal = 1 project

```
┌─ Tab 1: Claude Code ─────────────┐  ┌─ Tab 2: Claude Code ─────────────┐
│ "Làm việc với project             │  │ "Làm việc với project             │
│  vn_chong_phap"                   │  │  trieu_tran"                     │
│                                   │  │                                   │
│ Claude tự load:                   │  │ Claude tự load:                   │
│ ✓ project.json (era, sources)     │  │ ✓ project.json (era, sources)     │
│ ✓ characters.json (5 nhân vật)    │  │ ✓ characters.json (8 nhân vật)    │
│ ✓ videos/ (3 done, 2 in progress)│  │ ✓ videos/ (1 done, 1 in progress)│
│ ✓ style: phap_thuoc.json         │  │ ✓ style: tran.json               │
│                                   │  │                                   │
│ > "Viết kịch bản ep04"           │  │ > "Generate assets ep02"          │
│   (Claude hiểu context project)  │  │   (Claude hiểu context project)  │
└───────────────────────────────────┘  └───────────────────────────────────┘
```

### 6.2 Khi mở tab mới cho 1 project

User chỉ cần nói: `"Làm việc với project vn_chong_phap"`

Claude tự động:
1. Đọc `projects/vn_chong_phap/project.json` → thời kỳ, sources, tone, notes
2. Đọc `character_db/projects/vn_chong_phap/characters.json` → nhân vật đã có
3. Scan `projects/vn_chong_phap/videos/` → video nào đã làm, đang ở bước nào
4. Load `style_guides/eras/{era}.json` → style guide tương ứng
5. Sẵn sàng nhận lệnh — mọi lệnh sau đó tự hiểu context project

### 6.3 Làm việc song song

| Tình huống | Cách xử lý |
|-----------|-----------|
| 2 project cùng lúc | Mỗi project 1 tab terminal riêng |
| Chờ duyệt kịch bản project A | Chuyển sang tab project B làm việc khác |
| Chờ Veo 3 generate project A | Tab B vẫn hoạt động bình thường |
| Muốn xem tổng quan tất cả | Mở Web UI (localhost:3000) — thấy mọi project |

---

## 7. Edit từng phần (Incremental Editing)

### 7.1 Mỗi cảnh là 1 đơn vị độc lập

```
Video ep01 — 30 cảnh
┌────────┬────────┬────────┬────────┬────────┐
│ C.01 ✅│ C.02 ✅│ C.03 ❌│ C.04 ✅│ C.05 ❌│
│  OK    │  OK    │ Redo   │  OK    │ Sửa    │
│        │        │ hình   │        │ prompt │
└────────┴────────┴────────┴────────┴────────┘
     ↓                ↓                ↓
  Giữ nguyên    Re-generate      Sửa prompt
                 chỉ C.03      → re-generate C.05
```

### 7.2 Những gì có thể chỉnh từng phần

| Phần | Chỉnh được gì | Phạm vi ảnh hưởng |
|------|---------------|-------------------|
| **Kịch bản** | Sửa 1 đoạn | Chỉ cập nhật shot list cho đoạn sửa |
| **Shot list** | Sửa prompt, timing, type của 1 cảnh | Chỉ re-generate cảnh đó |
| **Nhân vật** | Đổi anchor, sửa prompt base | Re-generate các cảnh có nhân vật đó |
| **Asset** | Đánh dấu "Redo" trên Web UI | Claude chỉ re-generate cảnh được đánh dấu |
| **CapCut** | Partial rebuild | Chỉ update cảnh thay đổi, giữ nguyên phần còn lại |

### 7.3 Lịch sử version

Mỗi asset lưu lịch sử version:
```
assets/images/
├── scene_03_v1.png   ← rejected
├── scene_03_v2.png   ← rejected  
├── scene_03_v3.png   ← current ✅
└── scene_05_v1.png   ← current ✅
```

User có thể xem lại version cũ trên Web UI và rollback nếu muốn.

### 7.4 Ví dụ lệnh chỉnh từng phần

```
"Re-generate cảnh 3 và 5"
→ Claude chỉ generate lại 2 cảnh này, giữ nguyên 28 cảnh còn lại

"Sửa prompt cảnh 12: thêm chi tiết lính Pháp cầm súng"
→ Claude update prompt → re-generate cảnh 12

"Đổi cảnh 8 từ image sang video"
→ Claude update type → re-generate cảnh 8 dạng video

"Update CapCut project với cảnh 3, 5, 8, 12 mới"
→ Claude chỉ thay 4 cảnh trong timeline, giữ nguyên phần còn lại
```

---

## 8. Pipeline sản xuất chi tiết

### 8.1 Toàn bộ flow (Web UI + Claude Code)

```
PHASE 1: CONTENT
━━━━━━━━━━━━━━━━
  [Web UI]      User: Tạo project/video mới trên Dashboard
  [Terminal]    User: Mở tab mới → "Làm việc với project X"
  [Claude Code] User: "Viết kịch bản ep01, chủ đề: ..."
  [Claude Code] Claude: Nghiên cứu sử liệu → viết kịch bản → lưu file
  [Web UI]      User: Đọc kịch bản → sửa nếu cần → Bấm "Duyệt"
    ↓

PHASE 2: AUDIO
━━━━━━━━━━━━━━
  [Bên ngoài]   User: Chuyển kịch bản → file audio (TTS hoặc tự đọc)
  [Web UI]      User: Upload audio (kéo thả)
    ↓

PHASE 3: VISUAL PLANNING
━━━━━━━━━━━━━━━━━━━━━━━━
  [Claude Code] User: "Tạo shot list cho ep01"
  [Claude Code] Claude: Tạo shot_list.json (20-30 cảnh, prompt 3 lớp)
  [Web UI]      User: Xem timeline visual → duyệt
    ↓

PHASE 4: CHARACTER SETUP (nếu có nhân vật mới)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Claude Code] Claude: Tạo character sheet → generate test images
  [Web UI]      User: Chọn anchor image
  [Claude Code] Claude: Lưu prompt base
    ↓

PHASE 5: ASSET GENERATION (có thể lặp lại nhiều lần)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Claude Code] Claude: Mở browser Veo 3 → generate → download
  [Web UI]      User: Review grid → đánh dấu cảnh cần redo
  [Claude Code] Claude: Re-generate CHỈ cảnh được đánh dấu
  (Lặp lại cho đến khi tất cả cảnh OK)
    ↓

PHASE 6: AUTO-EDIT (hỗ trợ partial update)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Claude Code] Claude: Build project CapCut (full hoặc partial)
  [CapCut Pro]  User: Mở project → tinh chỉnh → export
  (Nếu re-generate cảnh sau đó → Claude update CapCut chỉ cảnh đó)
```

### 8.2 Cách chạy

```bash
# === SETUP 1 LẦN ===
cd ~/Youtube/video-factory
docker compose up -d
# → Mở localhost:3000

# === MỖI PROJECT ===
# Mở tab terminal mới → chạy Claude Code → nói:
# "Làm việc với project vn_chong_phap"
# → Claude tự load context, sẵn sàng nhận lệnh
```

**Ví dụ lệnh tự nhiên:**
```
"Viết kịch bản ep01, chủ đề: Vì sao Pháp đưa 2500 quân đánh 3 làng Thanh Hóa"
"Tạo shot list cho ep01"
"Generate assets cho ep01"
"Re-generate cảnh 5 và 12"
"Sửa prompt cảnh 8: thêm cảnh sông nước"
"Build CapCut cho ep01"
"Update CapCut chỉ cảnh 5, 8, 12"
```

---

## 9. Style Guide - 2D Animation theo thời kỳ

### 9.1 Base style (chung)

```
Prompt prefix:
"2D animated cartoon style, flat shading, clean bold outlines,
simple but expressive character designs, educational history
animation aesthetic, vibrant historically appropriate colors,
high quality illustration, consistent art style"

Negative prompts:
"realistic, 3D render, photorealistic, photograph, blurry,
low quality, text, watermark, modern elements, anime style,
manga style, chibi, pixel art"
```

### 9.2 Ví dụ theo thời kỳ Việt Nam

**Thời Hùng Vương - Văn Lang:**
- Palette: nâu đất, xanh lá, vàng đồng
- Kiến trúc: nhà sàn, trống đồng Đông Sơn
- Trang phục: đóng khố, áo choàng lông vũ, trang sức đồng
- Vũ khí: rìu đồng, giáo, cung tên

**Thời Lý - Trần:**
- Palette: đỏ vàng, xanh ngọc
- Kiến trúc: chùa Một Cột, thành Thăng Long, thuyền chiến
- Trang phục: áo bào, mũ miện, giáp trụ
- Đặc trưng: rồng thời Lý (mảnh mai), rồng thời Trần (mạnh mẽ)

**Thời Lê sơ:**
- Palette: đỏ thẫm, vàng kim, đen
- Kiến trúc: điện Kính Thiên, thành lũy
- Trang phục: long bào, áo mũ quan
- Đặc trưng: ảnh hưởng phong cách Minh triều

**Triều Nguyễn:**
- Palette: vàng hoàng gia, đỏ son, xanh lam
- Kiến trúc: kinh thành Huế, cổng Ngọ Môn
- Trang phục: áo dài ngũ thân, khăn đóng, mũ miện kiểu Nguyễn
- Đặc trưng: ảnh hưởng phong cách nhà Thanh

**Thời Pháp thuộc:**
- Palette: tối, nâu đất, xanh olive, xám
- Kiến trúc: làng quê tre nứa, nhà Pháp xen kẽ
- Trang phục VN: áo dài, áo bà ba, nón lá
- Trang phục Pháp: quân phục xanh, mũ cối
- Đặc trưng: tương phản giàu-nghèo, Đông-Tây

---

## 10. Config dự án (project.json)

Mỗi dự án có 1 file config riêng:

```json
{
  "project_id": "string",
  "name": "Tên dự án hiển thị",
  "type": "vietnamese_history | world_history | custom",
  "era": "tên thời kỳ (tương ứng file trong style_guides/eras/)",
  "style_override": null,
  "time_period": "khoảng thời gian (vd: 1858-1945)",
  "tone": "dramatic_narrative | epic_narrative | educational | documentary",
  "target_duration": 600,
  "sources": ["danh sách nguồn sử liệu"],
  "notes": "ghi chú riêng cho dự án",
  "characters_shared": true,
  "videos": ["danh sách video_id"]
}
```

Các trường `notes`, `sources`, `style_override` là nơi ghi chú đặc thù cho từng dự án khác nhau.

---

## 11. Web UI - Chi tiết các trang

### 11.1 Docker Compose

```yaml
# docker-compose.yml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./projects:/app/projects        # Shared với Claude Code
      - ./character_db:/app/character_db
      - ./style_guides:/app/style_guides
    environment:
      - DATABASE_URL=sqlite:///app/data/db.sqlite3
```

### 11.2 Các trang giao diện

| Trang | Chức năng | Chi tiết |
|-------|-----------|----------|
| **Dashboard** | Tổng quan | Danh sách projects, videos, trạng thái (draft/audio/assets/done) |
| **Project Config** | Cấu hình dự án | Sửa project.json, thêm sources, notes |
| **Script Editor** | Kịch bản | Đọc/sửa script.md, highlight nguồn sử liệu, nút Duyệt/Từ chối |
| **Audio Upload** | Upload audio | Kéo thả file .mp3/.wav, preview player |
| **Shot List** | Timeline visual | Hiển thị từng cảnh + prompt + timing, nút Duyệt |
| **Character Manager** | Nhân vật | Grid nhân vật, xem character sheet, chọn anchor image |
| **Asset Review** | Duyệt assets | Grid ảnh/video đã generate, click đánh dấu "Redo", so sánh trước/sau |
| **CapCut Export** | Build & export | Preview timeline, chọn BGM, bấm "Build Project" |

### 11.3 Tốc độ

- Web UI load: **< 1 giây** (localhost, không qua internet)
- Mọi thao tác đọc/ghi: **instant** (SQLite + file local)
- Bottleneck duy nhất: **chờ Veo 3 generate** (30s-2 phút/cảnh, phụ thuộc Google)

---

## 12. Những gì user cần chuẩn bị

| # | Hạng mục | Ưu tiên | Chi tiết |
|---|----------|---------|----------|
| 1 | **Docker Desktop** | P0 | Cài trên Mac/Windows → chạy Web UI |
| 2 | **CapCut Pro Desktop** | P0 | Tạo 1 project mẫu → gửi `draft_content.json` để reverse-engineer |
| 3 | **Tài khoản Google (Veo 3)** | P0 | Đăng nhập sẵn trên browser, không cần API key |
| 4 | **Công cụ tạo audio** | P0 | TTS (FPT.AI / Viettel AI / ElevenLabs) hoặc mic tự đọc |
| 5 | **Nhạc nền không bản quyền** | P1 | YouTube Audio Library (free) hoặc Epidemic Sound |
| 6 | **Ảnh tham khảo nhân vật** | P1 | Ảnh chân dung, tượng, tranh cổ → cho character sheet |
| 7 | **Sách sử (bản digital)** | P1 | Để Claude tra cứu khi viết kịch bản |

**Không cần chuẩn bị:** API keys, Python, Node.js (tất cả đã có trong Docker)

---

## 13. Roadmap triển khai

### Phase 0 - Chuẩn bị (ngay)
- [ ] User cài Docker Desktop
- [ ] User cài CapCut Pro Desktop → tạo project mẫu → gửi `draft_content.json`
- [ ] Claude tạo folder structure + docker-compose.yml

### Phase 1 - Web UI + Core Engine
- [ ] Build Docker containers (frontend + backend)
- [ ] Trang Dashboard + Project Config
- [ ] Trang Script Editor + Audio Upload
- [ ] Viết `script_engine.py`, `character_manager.py`
- [ ] Viết `veo3_prompt_engine.py`, `shot_list_builder.py`
- [ ] Tạo style guides cho các thời kỳ chính

### Phase 2 - Veo 3 + CapCut Automation
- [ ] Trang Shot List + Character Manager + Asset Review
- [ ] Claude Code + Playwright: automation generate Veo 3
- [ ] Reverse-engineer CapCut format → viết `capcut_builder.py`
- [ ] Trang CapCut Export
- [ ] Test end-to-end pipeline

### Phase 3 - Video Pilot
- [ ] Sản xuất 1 video hoàn chỉnh end-to-end
- [ ] Tinh chỉnh prompt Veo 3 cho character consistency
- [ ] Fix bugs pipeline
- [ ] Tối ưu UX trên Web UI

### Phase 4 - Scale (ongoing)
- [ ] Sản xuất video thường xuyên
- [ ] Mở rộng character_db
- [ ] Thêm style guides cho thời kỳ/quốc gia mới
- [ ] Cải thiện chất lượng dựa trên feedback
