"use client";

import { useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  FolderTree,
  Palette,
  Film,
  Scissors,
  FileText,
  Lightbulb,
  Map,
  Copy,
  Check,
} from "lucide-react";

function CopyBlock({ code, label }: { code: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="relative group">
      {label && <div className="text-[11px] font-semibold text-gray-400 mb-1">{label}</div>}
      <pre className="bg-gray-900 text-gray-100 rounded-xl p-4 text-[12px] font-mono overflow-x-auto whitespace-pre-wrap">{code}</pre>
      <button onClick={handleCopy} className="absolute top-2 right-2 p-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
}

function Section({ title, icon, color, children, defaultOpen = false }: {
  title: string; icon: React.ReactNode; color: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white rounded-2xl overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 px-5 py-4 hover:bg-gray-50 transition-colors text-left">
        <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center flex-shrink-0`}>{icon}</div>
        <h2 className="text-[15px] font-bold text-gray-800 flex-1">{title}</h2>
        {open ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </button>
      {open && <div className="px-5 pb-5 space-y-4">{children}</div>}
    </div>
  );
}

function InfoTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="bg-gray-50">{headers.map((h, i) => <th key={i} className="px-3 py-2 text-left font-semibold text-gray-600 first:rounded-tl-lg last:rounded-tr-lg">{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-gray-100">{row.map((cell, j) => <td key={j} className="px-3 py-2 text-gray-600">{cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function GuidePage() {
  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800 tracking-tight">Hướng dẫn sử dụng</h1>
        <p className="text-[13px] text-gray-400 mt-1">Cách cấu hình dự án cho từng loại nội dung & phong cách</p>
      </div>

      <div className="space-y-4">
        {/* Cấu trúc file */}
        <Section title="Cấu trúc file của 1 dự án" icon={<FolderTree className="w-[18px] h-[18px] text-amber-500" />} color="bg-amber-50" defaultOpen>
          <CopyBlock code={`projects/{project-id}/
├── project.json              ← Config chính: tên, loại, nguồn, base style
├── style_guide.md            ← Phong cách hình ảnh (prompt rules, ví dụ prompt)
├── content_guide.md          ← Cấu trúc kịch bản, quy tắc viết
├── storytelling_guide.md     ← Giọng văn, nhịp kể, đối tượng
├── characters/               ← Database nhân vật
│   └── {character}.json
└── videos/{video-id}/
    ├── script.md             ← Kịch bản hoàn chỉnh
    ├── narration.md          ← Lời đọc (voice content)
    ├── content_brief.md      ← Tóm tắt nội dung video
    ├── visual_guide.md       ← Hướng dẫn hình ảnh (override style_guide)
    ├── edit_guide.md         ← Hướng dẫn edit: transition, pacing, audio
    ├── brainstorm.md         ← Ghi chú brainstorm
    ├── shot_list.json        ← Danh sách cảnh
    ├── visual_plan.json      ← Chi tiết visual từng cảnh
    ├── director_plan.json    ← Kế hoạch đạo diễn
    ├── audio/                ← File audio giọng đọc
    ├── assets/               ← Hình ảnh & video
    └── shorts/               ← YouTube Shorts`} />

          <h3 className="text-[13px] font-bold text-gray-700 mt-4">Vai trò từng file cấu hình</h3>
          <InfoTable
            headers={["File", "Vai trò", "Ghi chú"]}
            rows={[
              ["project.json", "Metadata: tên, loại, nguồn tham khảo, base style", "Bắt buộc"],
              ["style_guide.md", "Phong cách hình ảnh: art style, prompt rules, ví dụ", "Bắt buộc — quyết định AI tạo hình thế nào"],
              ["content_guide.md", "Cấu trúc kịch bản, quy tắc viết, nguồn", "Bắt buộc — Claude dựa vào file này để viết kịch bản"],
              ["storytelling_guide.md", "Giọng văn, tốc độ, cảm xúc, đối tượng", "Nên có"],
              ["visual_guide.md", "Hướng dẫn hình ảnh riêng cho video", "Khi video cần style khác project"],
              ["edit_guide.md", "Transition, pacing, Ken Burns, text overlay, audio", "Bắt buộc trước khi tạo visual plan"],
              ["content_brief.md", "Tóm tắt nội dung video cụ thể", "Trước khi viết kịch bản"],
            ]}
          />
          <div className="bg-sky-50 rounded-xl p-4 text-[12px] text-sky-700">
            <strong>Mẹo:</strong> Dùng trang <strong>Tài nguyên</strong> để áp dụng template có sẵn vào các file guide. Hoặc viết thủ công theo mẫu bên dưới.
          </div>
        </Section>

        {/* Loại nội dung */}
        <Section title="Các loại nội dung & cách cấu hình" icon={<Film className="w-[18px] h-[18px] text-violet-500" />} color="bg-violet-50">

          {/* Lịch sử */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <h3 className="text-[14px] font-bold text-gray-800">1. Lịch sử kể chuyện</h3>
            <p className="text-[12px] text-gray-500">VD: &quot;Trận Bạch Đằng 938&quot;, &quot;The Fall of Rome&quot;</p>
            <InfoTable
              headers={["File cần cấu hình", "Nội dung"]}
              rows={[
                ["style_guide.md", "2D animation hoặc watercolor. Prompt 3 lớp (base + era + character)"],
                ["content_guide.md", "6 phần: Hook → Bối cảnh → Diễn biến → Cao trào → Kết cục → Outro"],
                ["storytelling_guide.md", "Giọng kể trang trọng, dramatic, gây tò mò"],
                ["edit_guide.md", "Ken Burns, crossfade, pacing chậm-nhanh, nhạc orchestral -20dB"],
                ["characters/", "Character sheet cho mỗi nhân vật lịch sử"],
              ]}
            />
            <CopyBlock label="Mẫu content_guide.md — Lịch sử" code={`## Cấu trúc kịch bản

### HOOK (30-45 giây)
Câu hỏi/tình huống gây tò mò, preview cao trào

### BỐI CẢNH (1.5-2 phút)
Thời đại, nhân vật chính, tình hình chính trị/xã hội

### DIỄN BIẾN (2-3 phút)
Nguyên nhân, chuỗi sự kiện, chi tiết quan trọng

### CAO TRÀO (2-3 phút)
Bước ngoặt, xung đột chính, kịch tính

### KẾT CỤC & BÀI HỌC (1.5-2 phút)
Hệ quả, bài học lịch sử, liên hệ

### OUTRO (15-30 giây)
CTA: like, subscribe`} />
          </div>

          {/* Explainer */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <h3 className="text-[14px] font-bold text-gray-800">2. Giải thích (Explainer)</h3>
            <p className="text-[12px] text-gray-500">VD: &quot;Tại sao bầu trời màu xanh?&quot;, &quot;Vì sao Nhật phát triển nhanh?&quot;</p>
            <InfoTable
              headers={["File cần cấu hình", "Nội dung"]}
              rows={[
                ["style_guide.md", "Infographic + illustration. Diagram, icon, data viz"],
                ["content_guide.md", "5 phần: Hook → Vấn đề → Giải thích → Phản biện → Kết luận"],
                ["storytelling_guide.md", "Giọng dễ hiểu, gần gũi, ví dụ thực tế"],
                ["edit_guide.md", "Pacing nhanh 3-5s/cảnh, nhiều text overlay, nhạc upbeat -16dB"],
                ["characters/", "Không cần hoặc mascot đơn giản"],
              ]}
            />
            <CopyBlock label="Mẫu content_guide.md — Explainer" code={`## Cấu trúc kịch bản

### HOOK (15-30 giây)
Câu hỏi trực tiếp hoặc sự thật bất ngờ

### VẤN ĐỀ (1-2 phút)
Trình bày hiện tượng cần giải thích, trải nghiệm quen thuộc

### GIẢI THÍCH (3-5 phút)
2-4 luận điểm, mỗi luận điểm có:
- Tuyên bố rõ ràng
- Bằng chứng / ví dụ
- Hình ảnh minh họa (diagram, infographic)

### PHẢN BIỆN (1-2 phút)
Quan điểm ngược lại hoặc ngoại lệ

### KẾT LUẬN (30-60 giây)
Tóm tắt + mở rộng

### OUTRO (15-30 giây)
CTA`} />
          </div>

          {/* Documentary */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <h3 className="text-[14px] font-bold text-gray-800">3. Phim tài liệu (Documentary)</h3>
            <p className="text-[12px] text-gray-500">VD: &quot;Cuộc sống vùng cao Tây Bắc&quot;</p>
            <InfoTable
              headers={["File cần cấu hình", "Nội dung"]}
              rows={[
                ["style_guide.md", "Watercolor hoặc realistic illustration. Atmospheric, chi tiết"],
                ["content_guide.md", "5 phần: Mở đầu → Bối cảnh → Câu chuyện chính → Chiều sâu → Kết"],
                ["storytelling_guide.md", "Giọng trầm, suy tư, để hình ảnh kể chuyện"],
                ["edit_guide.md", "Pacing chậm 8-15s/cảnh, crossfade dài, nhạc ambient -22dB"],
              ]}
            />
            <CopyBlock label="Mẫu content_guide.md — Documentary" code={`## Cấu trúc kịch bản

### MỞ ĐẦU (1-2 phút)
Establishing shot + giới thiệu chủ đề. Hình ảnh nói trước, giọng đọc sau.

### BỐI CẢNH (2-3 phút)
Bối cảnh lịch sử/địa lý/xã hội. World-building.

### CÂU CHUYỆN CHÍNH (3-4 phút)
Narrative chính, theo timeline hoặc chủ đề.

### CHIỀU SÂU (2-3 phút)
Phân tích, bối cảnh rộng hơn, ý nghĩa.

### KẾT (1-2 phút)
Reflection, suy ngẫm. Không cần CTA mạnh.`} />
          </div>

          {/* Listicle */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <h3 className="text-[14px] font-bold text-gray-800">4. Danh sách / Top N (Listicle)</h3>
            <p className="text-[12px] text-gray-500">VD: &quot;7 điều bạn chưa biết về Hồ Chí Minh&quot;</p>
            <InfoTable
              headers={["File cần cấu hình", "Nội dung"]}
              rows={[
                ["style_guide.md", "2D animation hoặc infographic. Title cards cho mỗi item"],
                ["content_guide.md", "Hook → Intro → N Items → Kết → Outro"],
                ["storytelling_guide.md", "Giọng energetic, tạo suspense cho item tiếp theo"],
                ["edit_guide.md", "Pacing đều 4-6s/cảnh, title card + number mỗi item"],
              ]}
            />
            <CopyBlock label="Mẫu content_guide.md — Listicle" code={`## Cấu trúc kịch bản

### HOOK (15-30 giây)
Tease item hay nhất. "Và điều cuối cùng sẽ khiến bạn bất ngờ..."

### GIỚI THIỆU (15-30 giây)
Context ngắn: tại sao list này thú vị.

### ITEM N (đếm ngược hoặc xuôi)
Mỗi item:
- Title card (3s): Số + tên item
- Nội dung (45-90 giây): Giải thích, fact thú vị
- Transition hook: "Nhưng chưa hết..."

### KẾT (30-45 giây)
Recap + CTA tương tác: "Theo bạn, điều nào thú vị nhất?"

### OUTRO (15-30 giây)
CTA`} />
          </div>
        </Section>

        {/* Phong cách hình ảnh */}
        <Section title="Phong cách hình ảnh (Base Styles)" icon={<Palette className="w-[18px] h-[18px] text-emerald-500" />} color="bg-emerald-50">
          <p className="text-[12px] text-gray-500">
            Hệ thống có các base style sẵn trong <code className="bg-gray-100 px-1.5 py-0.5 rounded text-[11px]">style_guides/</code>. Chọn base style phù hợp rồi customize trong <code className="bg-gray-100 px-1.5 py-0.5 rounded text-[11px]">style_guide.md</code> của dự án.
          </p>

          <InfoTable
            headers={["Base Style", "Phong cách", "Phù hợp cho"]}
            rows={[
              ["base_2d_style", "2D cartoon, flat shading, bold outlines", "Lịch sử, storytelling, listicle"],
              ["base_watercolor", "Watercolor painting, soft washes, artistic", "Documentary, câu chuyện cảm xúc"],
              ["base_infographic", "Flat design, vector graphics, data viz", "Explainer, tutorial, so sánh"],
              ["base_realistic_illustration", "Realistic painting, cinematic, detailed", "Documentary, lịch sử epic"],
            ]}
          />

          <div className="bg-sky-50 rounded-xl p-4 text-[12px] text-sky-700">
            <strong>Cách sử dụng:</strong> Đặt <code className="bg-sky-100 px-1 rounded">base_style</code> trong <code className="bg-sky-100 px-1 rounded">project.json</code> để Veo3 Prompt Engine tự load base style tương ứng. VD: <code className="bg-sky-100 px-1 rounded">{`"base_style": "base_watercolor"`}</code>
          </div>

          <CopyBlock label="Mẫu style_guide.md — Explainer (infographic)" code={`# Phong cách hình ảnh — Explainer

## Phong cách chung
- Infographic + flat illustration
- Màu sắc: palette sáng, tối đa 3-4 màu chính
- Typography: lớn, rõ ràng, sans-serif
- Background: đơn giản, solid color hoặc subtle gradient

## Loại hình ảnh cần
- Diagram / Infographic: minh họa quy trình, so sánh
- Icon / Symbol: đại diện khái niệm trừu tượng
- Illustration: ví dụ cụ thể
- Text-heavy frame: key point, số liệu

## Prompt rules
- Base: "clean infographic style, flat design, modern vector..."
- Mỗi cảnh focus 1 ý chính duy nhất
- Ưu tiên clarity over aesthetics

## Negative prompt
realistic, photograph, 3D render, complex textures, painterly`} />
        </Section>

        {/* Phong cách edit */}
        <Section title="Phong cách edit" icon={<Scissors className="w-[18px] h-[18px] text-amber-500" />} color="bg-amber-50">
          <p className="text-[12px] text-gray-500">
            Edit guide quyết định cách dựng video trong CapCut. Viết vào <code className="bg-gray-100 px-1.5 py-0.5 rounded text-[11px]">edit_guide.md</code> của video.
          </p>

          <InfoTable
            headers={["Loại content", "Pacing", "Chuyển cảnh", "Âm thanh"]}
            rows={[
              ["Lịch sử kể chuyện", "4-8s/cảnh, chậm-nhanh theo đoạn", "Crossfade 80%, fade black, cut cao trào", "Orchestral -20dB, SFX nhẹ"],
              ["Explainer", "3-5s/cảnh, nhịp đều nhanh", "Cut 60%, crossfade ngắn 30%", "Upbeat/lo-fi -16dB, pop/whoosh SFX"],
              ["Documentary", "8-15s/cảnh, rất chậm", "Crossfade dài 1-1.5s, fade black", "Ambient -22dB, natural sounds"],
              ["Listicle", "4-6s/cảnh, nhịp đều", "Cut + title card transition", "Energetic -16dB, ding SFX mỗi item"],
            ]}
          />

          <CopyBlock label="Mẫu edit_guide.md — Explainer" code={`# Hướng dẫn Edit — Explainer

## Pacing
- Hook: 2-3s/cảnh, gây chú ý ngay
- Giải thích: 3-5s/cảnh, vừa đủ đọc text
- Kết luận: 5-7s/cảnh

## Chuyển cảnh
- Cut thẳng (60%): giữ nhịp nhanh
- Crossfade ngắn 0.3s (30%): chuyển luận điểm
- Zoom transition (10%): zoom vào chi tiết

## Text Overlay
- Mỗi cảnh nên có text
- Key number: font lớn, bold, giữa màn hình
- Key phrase: dưới 1/3, sans-serif, 3-4 giây

## Ken Burns
- Zoom nhanh: 100% → 115-120%
- Pan + zoom khi scan infographic

## Âm thanh
- Nhạc: upbeat, electronic/lo-fi, -16dB
- SFX: pop/whoosh khi text xuất hiện
- Giọng đọc: tốc độ nhanh, -3dB
- Không có khoảng lặng dài`} />
        </Section>

        {/* Era Style */}
        <Section title="Era Style (cho lịch sử)" icon={<Map className="w-[18px] h-[18px] text-rose-500" />} color="bg-rose-50">
          <p className="text-[12px] text-gray-500">
            Era style bổ sung chi tiết kiến trúc, trang phục, vũ khí cho từng thời kỳ lịch sử. Tạo file JSON trong <code className="bg-gray-100 px-1.5 py-0.5 rounded text-[11px]">style_guides/eras/</code> (VN) hoặc <code className="bg-gray-100 px-1.5 py-0.5 rounded text-[11px]">style_guides/world/</code> (quốc tế).
          </p>

          <CopyBlock label="Mẫu era style — Lịch sử thế giới" code={`{
  "era_name": "Roman Empire",
  "time_period": "27 BC - 476 AD",
  "prompt_addition": "ancient Roman civilization, Mediterranean setting, classical architecture",
  "architecture": ["Roman columns", "aqueducts", "Colosseum", "Senate building"],
  "clothing": ["toga", "lorica segmentata armor", "laurel wreath", "sandals"],
  "weapons": ["gladius sword", "pilum javelin", "scutum shield"],
  "key_elements": ["Roman eagles (aquila)", "SPQR banners", "olive branches"],
  "color_palette": {
    "primary": "#8B0000",
    "secondary": "#DAA520",
    "accent": "#F5F5DC",
    "background": "#D2B48C"
  },
  "notes": "Roman triumphal arches, marble textures, Mediterranean landscape"
}`} />

          <p className="text-[12px] text-gray-500 mt-3">
            <strong>Era VN có sẵn:</strong> hung_vuong, bac_thuoc, ly, tran, le_so, trinh_nguyen, tay_son, nguyen, phap_thuoc, hien_dai, ngo_dinh_tien_le, ho_hau_tran, mac, le_trung_hung
          </p>
        </Section>

        {/* Tạo template */}
        <Section title="Tạo template mới (cho trang Tài nguyên)" icon={<FileText className="w-[18px] h-[18px] text-indigo-500" />} color="bg-indigo-50">
          <p className="text-[12px] text-gray-500">
            Templates là file JSON trong <code className="bg-gray-100 px-1.5 py-0.5 rounded text-[11px]">templates/</code>. Khi tạo template, nó sẽ xuất hiện trong trang <strong>Tài nguyên</strong> và có thể áp dụng vào dự án/video.
          </p>

          <InfoTable
            headers={["Thư mục", "Category", "Áp dụng vào"]}
            rows={[
              ["templates/image_styles/", "image_style", "style_guide.md (project) hoặc visual_guide.md (video)"],
              ["templates/edit_styles/", "edit_style", "edit_guide.md (video)"],
              ["templates/storytelling_profiles/", "storytelling_profile", "storytelling_guide.md (project)"],
            ]}
          />

          <CopyBlock label="Cấu trúc file template" code={`{
  "id": "ten-template",
  "name": "Tên hiển thị",
  "category": "image_style | edit_style | storytelling_profile",
  "description": "Mô tả ngắn",
  "preview_summary": "- Bullet 1\\n- Bullet 2\\n- Bullet 3",
  "applies_to": ["project_style_guide", "video_visual_guide"],
  "content": "Nội dung markdown đầy đủ — phần này sẽ được ghi vào file guide khi áp dụng"
}`} />
        </Section>

        {/* YouTube Shorts */}
        <Section title="YouTube Shorts" icon={<Film className="w-[18px] h-[18px] text-pink-500" />} color="bg-pink-50">
          <p className="text-[12px] text-gray-500">
            Shorts nằm trong thư mục con <code className="bg-gray-100 px-1.5 py-0.5 rounded text-[11px]">shorts/</code> của video. Format 9:16, 45-50 giây.
          </p>

          <CopyBlock label="Cấu trúc file shorts" code={`videos/{video-id}/shorts/
├── script.md         ← Kịch bản short
├── narration.md      ← Lời đọc
├── content_brief.md  ← Tóm tắt nội dung
├── brainstorm.md     ← Ghi chú
├── audio/            ← File audio
└── assets/           ← Hình ảnh & video`} />

          <InfoTable
            headers={["Đặc điểm", "Chi tiết"]}
            rows={[
              ["Format", "9:16 (1080x1920), 45-50 giây"],
              ["Style", "Kế thừa từ video gốc (style_guide + edit_guide)"],
              ["Scenes", "5-10 cảnh, 3-8s/cảnh"],
              ["Video clip", "~50% cảnh là video (cao hơn video dài)"],
              ["Pacing", "Nhanh xuyên suốt, hook 1-2 giây đầu"],
              ["Ken Burns", "Zoom mạnh 100%→120-125%"],
              ["Text", "Font lớn, tối đa 1 dòng, giữa khung"],
            ]}
          />

          <div className="bg-amber-50 rounded-xl p-4 text-[12px] text-amber-700 space-y-1">
            <p><strong>Lưu ý khi mở rộng:</strong></p>
            <ul className="list-disc list-inside space-y-0.5">
              <li>Shorts kế thừa style từ video gốc — không có file style riêng</li>
              <li>Nếu cần style khác → ghi chú cụ thể trong content_brief hoặc brainstorm của short</li>
              <li>Shorts hoạt động với mọi loại content — chỉ cần đúng format 9:16 và thời lượng ngắn</li>
            </ul>
          </div>
        </Section>

        {/* Tổng hợp */}
        <Section title="Tổng hợp: Muốn làm content kiểu X thì cần gì?" icon={<Lightbulb className="w-[18px] h-[18px] text-yellow-500" />} color="bg-yellow-50" defaultOpen>
          <InfoTable
            headers={["", "Lịch sử", "Explainer", "Documentary", "Listicle"]}
            rows={[
              ["Base style", "2D animation", "Infographic", "Watercolor / Realistic", "2D animation"],
              ["Era style", "Cần (thời kỳ cụ thể)", "Không", "Tùy", "Tùy"],
              ["Characters", "Cần (nhân vật lịch sử)", "Không / Ít", "Tùy", "Tùy"],
              ["Script", "6 phần (Hook→Outro)", "5 phần (Hook→CTA)", "5 phần tự do", "N items + Hook/CTA"],
              ["Edit style", "Chậm, Ken Burns", "Nhanh, text-heavy", "Rất chậm, ambient", "Đều, title cards"],
              ["Pacing", "4-8s/cảnh", "3-5s/cảnh", "8-15s/cảnh", "4-6s/cảnh"],
              ["Nhạc nền", "Orchestral -20dB", "Upbeat -16dB", "Ambient -22dB", "Energetic -16dB"],
            ]}
          />

          <div className="bg-emerald-50 rounded-xl p-4 text-[12px] text-emerald-700 space-y-2">
            <p><strong>Workflow nhanh:</strong></p>
            <ol className="list-decimal list-inside space-y-1">
              <li>Tạo project trên Web UI → điền tên, nguồn, ghi chú</li>
              <li>Cấu hình <strong>style_guide.md</strong> — chọn base style + customize</li>
              <li>Cấu hình <strong>content_guide.md</strong> — chọn cấu trúc kịch bản phù hợp</li>
              <li>Cấu hình <strong>edit_guide.md</strong> — chọn pacing, chuyển cảnh, âm thanh</li>
              <li>Mở terminal → chat brainstorm → &quot;Chốt&quot; → upload audio → generate assets → CapCut</li>
            </ol>
          </div>
        </Section>
      </div>
    </div>
  );
}
