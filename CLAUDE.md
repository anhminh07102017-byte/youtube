# Minh Bi Youtube - Hệ thống sản xuất video lịch sử

## Tổng quan
Hệ thống sản xuất video lịch sử phong cách **2D animation/hoạt hình**, gồm 2 phần:
- **Web UI (Docker)**: Giao diện quản lý, duyệt content, review assets, upload audio — chạy `localhost:3000`
- **Claude Code (terminal)**: AI engine — viết kịch bản, tạo prompt, điều khiển browser Veo 3, build project CapCut
- Hai phần **chia sẻ cùng 1 folder** trên máy (`~/Youtube/video-factory/projects/`)
- **KHÔNG dùng API key** cho bất kỳ AI service nào. Claude Code chính là AI engine.

## Kiến trúc hệ thống

```
Web UI (Docker, localhost:3000)          Claude Code (terminal)
  ├── Dashboard projects/videos            ├── Viết kịch bản → lưu file
  ├── Đọc/sửa/duyệt kịch bản             ├── Tạo shot list → lưu file
  ├── Upload audio (kéo thả)              ├── Mở browser Veo 3 (Playwright)
  ├── Xem grid assets → đánh dấu redo     ├── Generate/download assets
  ├── Preview timeline                     ├── Build project CapCut
  └── Trigger export CapCut                └── Re-generate cảnh
          │                                        │
          └──── cùng folder: ~/Youtube/video-factory/projects/ ────┘
```

## Quy tắc chung

### Phong cách hình ảnh
- Luôn sử dụng phong cách **2D animated cartoon**: flat shading, clean bold outlines, simple expressive characters
- KHÔNG dùng realistic/3D/photorealistic
- Hình ảnh phải phù hợp văn hóa Việt Nam (hoặc văn hóa tương ứng với dự án)
- Nhân vật lịch sử phải được tạo **giống nguyên tác nhất có thể** (dựa trên ảnh chụp, tranh vẽ, tượng, mô tả sử liệu)
- Trang phục, kiến trúc, đạo cụ phải chính xác theo thời kỳ lịch sử

### Đồng bộ nhân vật (Character Consistency)
- Mỗi nhân vật có 1 character sheet trong `character_db/`
- Prompt Veo 3 luôn xây theo **3 lớp**: Base Style + Era Style + Character Specific
- Khi tạo nhân vật mới: generate 3-5 test images → user chọn anchor → lưu prompt base
- Mọi cảnh có nhân vật đó đều dùng prompt base đã duyệt

### Nội dung & Sử liệu
- Nội dung phải có nguồn gốc rõ ràng từ sử liệu uy tín
- Tuân thủ pháp luật Việt Nam (Luật Báo chí, Luật An ninh mạng)
- KHÔNG xuyên tạc lịch sử, KHÔNG bịa đặt sự kiện
- Mỗi fact trong kịch bản phải ghi chú nguồn sử liệu
- Nguồn ưu tiên: Đại Việt Sử Ký Toàn Thư, Việt Nam Sử Lược (Trần Trọng Kim), Đại Nam Thực Lục, công trình của Viện Sử học VN, Phan Huy Lê, Hà Văn Tấn, Trần Quốc Vượng

### Ngôn ngữ
- Giao diện hệ thống, kịch bản, mô tả cảnh, ghi chú: **tiếng Việt**
- Prompt gửi Veo 3 để tạo hình ảnh/video: **tiếng Anh**, dùng thuật ngữ chuyên dụng (art style, composition, lighting...)
- Lý do: Veo 3 hiểu tiếng Anh chính xác hơn, thuật ngữ hình ảnh tiếng Anh rõ nghĩa hơn

### Veo 3
- Sử dụng qua **browser** (KHÔNG dùng API) — Claude điều khiển bằng Playwright MCP tools
- Prompt phải bằng **tiếng Anh**, tuân theo hệ thống 3 lớp (Base Style + Era Style + Character Specific)
- Quy định hình ảnh cụ thể đọc từ file `style_guide.md` của mỗi dự án (không hardcode)
- User chỉ cần đăng nhập sẵn tài khoản Google trên browser

### CapCut
- Sử dụng **CapCut Pro Desktop**
- Tự động tạo project bằng script Python (reverse-engineer format .capcut)
- User review và tinh chỉnh trong CapCut trước khi export

### Web UI
- Chạy bằng **Docker** (`docker compose up` → `localhost:3000`)
- Tech stack: FastAPI (backend) + React/Next.js (frontend) + SQLite
- Tương thích **cả macOS và Windows**
- Chỉ là giao diện quản lý/review — KHÔNG chứa logic AI
- Đọc/ghi trực tiếp vào folder `projects/` (mounted volume)

### Kiến trúc project
- Framework chung, hỗ trợ **multi-project** (nhiều dự án khác nhau)
- Mỗi dự án (project) = 1 chủ đề lớn, chứa nhiều video
- Config theo từng dự án trong `projects/{project_id}/project.json`
- Không giới hạn thời đại hay quốc gia - tùy thuộc vào dự án

### Cấu trúc kịch bản (video ~10 phút, 1500-1800 từ)
- Hook (30-45s): Câu hỏi/tình huống gây tò mò
- Bối cảnh (1.5-2 phút): Thời đại, nhân vật, tình hình
- Diễn biến 1 (2-3 phút): Nguyên nhân, chuỗi sự kiện
- Diễn biến 2 - Cao trào (2-3 phút): Bước ngoặt, xung đột chính
- Kết cục & Bài học (1.5-2 phút): Hệ quả, bài học lịch sử
- Outro (15-30s): CTA

### Quản lý session (Multi-project)
- Mỗi **terminal tab** Claude Code = **1 project** duy nhất
- Đầu mỗi session, user nói "Làm việc với project {project_id}"
- Claude tự đọc: project.json, characters.json, danh sách videos, style guide
- **KHÔNG** chuyển project giữa chừng trong 1 tab — mở tab mới cho project mới
- Web UI (localhost:3000) hiển thị tất cả projects trong 1 dashboard

### Edit từng phần (Incremental)
- Mỗi cảnh (scene) là 1 đơn vị độc lập, có thể chỉnh riêng
- Cho phép: sửa prompt 1 cảnh, re-generate 1 cảnh, đổi type (image↔video), sửa timing
- CapCut project hỗ trợ rebuild từng phần (chỉ update cảnh thay đổi)
- Lưu lịch sử version cho mỗi asset (v1, v2, v3...)

### Quy trình lên kịch bản (Brainstorm → Chốt)
- User nói: "Làm việc với project X, lên kịch bản cho video Y"
- Claude đọc: project.json, content_guide.md, style_guide.md, characters
- **Giai đoạn chat**: User đưa ý tưởng, Claude hỏi/gợi ý, trao đổi qua lại
  - Trong giai đoạn này Claude KHÔNG ghi file kịch bản
  - Claude có thể ghi ghi chú brainstorm vào `brainstorm.md` để lưu tiến trình
- **Khi user nói "Chốt"**: Claude ghi các file chính thức:
  - `script.md` — kịch bản hoàn chỉnh
  - `content_brief.md` — tóm tắt nội dung, hướng đi
  - Cập nhật `brainstorm.md` với bản tóm tắt cuối cùng
- User review trên Web UI (tab "Lên kịch bản" và tab "Kịch bản")
- Nếu user muốn chỉnh, quay lại chat tiếp → "Chốt" lại

### Pipeline sản xuất
1. User tạo project/video trên **Web UI** → mở terminal tab mới → "Làm việc với project X"
2. User chat với Claude để **lên kịch bản** → khi hài lòng nói **"Chốt"** → Claude ghi file
3. User duyệt kịch bản trên **Web UI** → chỉnh sửa nếu cần
4. User chuyển kịch bản → file audio → upload qua **Web UI**
5. Claude tạo shot list → User duyệt trên **Web UI**
6. Claude mở browser Veo 3 generate assets → User review từng cảnh trên **Web UI**
7. User đánh dấu cảnh cần redo → Claude re-generate chỉ cảnh đó
8. Claude build project CapCut (hoặc update từng phần) → User mở CapCut Pro tinh chỉnh & export
