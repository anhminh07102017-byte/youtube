# Phong cách hình ảnh: Anime POV Trải Nghiệm Cuộc Đời

## Tổng quan
- Dạng content: POV nhập vai. Người xem sống qua cuộc đời của một kiểu người cụ thể (học sinh giả vờ chăm chỉ, tuyển thủ, người quá đẹp trai, người giả vờ là thiên tài...) trong 8–15 phút.
- Mục tiêu hình ảnh: làm người xem tin mình là nhân vật. Cảm xúc phải đọc được ngay từ màu và nét mặt.
- Art style: anime 2D kiểu Studio Ghibli / Makoto Shinkai pha manhwa.
- Pipeline: tạo ảnh tĩnh bằng model ảnh (Gemini / Nano Banana hoặc tương đương), rồi image-to-video để có chuyển động nhỏ. Không dùng ảnh tĩnh + Ken Burns.

## Art style
- Nét viền mảnh, sạch, không đậm như flat cartoon.
- Tô bóng mềm (soft cel shading), có rim light và ánh sáng môi trường.
- Background vẽ kỹ, gần như ảnh thật, nhiều chi tiết đời thường: đèn huỳnh quang, quạt treo tường, tủ sắt, bảng xanh, bàn gỗ trầy, dây điện, cửa sổ song sắt.
- Chiều sâu trường ảnh nông: tiền cảnh hoặc hậu cảnh hơi mờ.
- Chữ trong ảnh (đề thi, bảng, màn hình, biển hiệu) là tiếng Việt đọc được, ví dụ: ĐỀ KIỂM TRA TOÁN 12, điểm 3,2 khoanh mực đỏ. Chi tiết này tạo cảm giác thật rất mạnh.

## Bảng màu theo cảm xúc
| Cảm xúc | Tông màu | Nguồn sáng |
|---|---|---|
| Thất bại, áp lực, xấu hổ | Xanh xám lạnh, hơi nhạt màu | Đèn huỳnh quang trắng xanh |
| Cố gắng, học đêm, cô đơn | Cam ấm trên nền tối | Đèn bàn, màn hình |
| Hồi tưởng, vinh quang, ấm áp | Vàng hoàng hôn, hơi bloom | Nắng xiên qua cửa sổ |
| Thi đấu, cao trào, bùng nổ | Neon xanh tím, tương phản mạnh | Ánh sân khấu, LED |

Quy tắc:
- Mỗi Level giữ một tông chủ đạo.
- Màu đi theo đường cong cảm xúc của câu chuyện, không giữ một tông suốt cả video.
- Chuyển tông rõ ràng khi sang Level mới để người xem cảm nhận bước ngoặt.

## Characters
- Một nhân vật chính xuyên suốt cả video, khóa ngoại hình bằng ảnh reference: mặt chính diện, 3/4, và 2–3 bộ trang phục.
- Mẫu nhân vật: thiếu niên, tóc đen hơi rối, gương mặt kiểu nhân vật chính anime. Trang phục theo bối cảnh: sơ mi trắng học sinh, đồng phục thể dục, áo thi đấu, đồ ở nhà.
- Biểu cảm phải rõ và hơi phóng đại: cúi đầu, nghiến răng, cười gượng, mắt rưng, nắm chặt tay, ánh mắt quyết tâm.
- Nhân vật phụ (thầy cô, bố mẹ, bạn bè, đối thủ) cùng art style, ít chi tiết hơn nhân vật chính, thường hơi mờ hoặc ở hậu cảnh.
- Mỗi lần tạo ảnh đều gắn ảnh reference nhân vật để giữ đồng nhất.

## Bối cảnh
- Đời sống Việt Nam cụ thể, nhận ra ngay: lớp học bảng xanh, bàn gỗ, hành lang trường, căng tin, phòng trọ, bàn học có đèn bàn, quán net, sân khấu esports.
- Đồ vật kể chuyện: tờ đề điểm kém, giấy nháp gạch chéo, đồng hồ treo tường, ba lô, điện thoại có tin nhắn, cúp, bảng xếp hạng.

## Bố cục và kiểu shot
Xoay vòng 4 kiểu shot, không để 2 shot liên tiếp cùng kiểu:
1. Góc nhìn thứ nhất: tay của bạn cầm tờ đề, bút, điện thoại, chuột. Đây là shot đặc trưng nhất của dạng POV, tạo cảm giác nhập vai.
2. Cận mặt: lấy cảm xúc, dùng ở hook và ở câu chốt.
3. Toàn cảnh: lớp học, sân trường, khán đài, dùng để đặt bối cảnh khi sang Level mới.
4. Cận đồ vật (insert): đồng hồ, điểm số, giấy nháp, màn hình, chi tiết nhấn ý.

Khung hình 16:9. Chừa khoảng trống phía dưới cho phụ đề và góc trái trên cho watermark.

## Motion (image-to-video)
- Mỗi shot chỉ cần 3–4s chuyển động nhỏ và chậm: tay cử động, đổi nét mặt, tóc và áo lay nhẹ, camera đẩy chậm vào (slow push-in) hoặc pan nhẹ.
- Tránh chuyển động lớn làm méo mặt nhân vật.
- Công thức: camera push-in hoặc pan nhẹ, cộng một hành động nhỏ của nhân vật.

## Prompt structure
Thứ tự phần tử trong prompt ảnh:
[Shot type] + [Nhân vật @ref + hành động + biểu cảm] + [Bối cảnh Việt Nam cụ thể] + [Ánh sáng + tông màu theo cảm xúc] + [Art style lock] + [Chữ tiếng Việt trong ảnh nếu có]

Art style lock (dán cuối mọi prompt):
anime illustration, Makoto Shinkai and Studio Ghibli inspired, manhwa influence, thin clean lineart, soft cel shading, highly detailed semi-realistic background, cinematic lighting, shallow depth of field, 16:9

Ví dụ 1 (thất bại, góc nhìn thứ nhất):
First-person POV, a student's hands holding a math test paper titled ĐỀ KIỂM TRA TOÁN 12 with the score 3,2 circled in red ink, Vietnamese classroom with green chalkboard, wooden desks and wall fans in background slightly blurred, cold blue-grey fluorescent lighting, desaturated melancholic mood, anime illustration, Makoto Shinkai and Studio Ghibli inspired, thin clean lineart, soft cel shading, highly detailed semi-realistic background, 16:9

Ví dụ 2 (cố gắng, cận mặt):
Close-up of @Image1 teenage boy with messy black hair, tired but determined eyes, studying late at night at a small desk, warm orange desk lamp as the only light source, dark room, anime illustration, Makoto Shinkai and Studio Ghibli inspired, thin clean lineart, soft cel shading, cinematic lighting, 16:9

Ví dụ 3 (vinh quang, toàn cảnh):
Wide shot of @Image1 standing alone in an empty Vietnamese school corridor, golden hour sunlight streaming through barred windows, long shadows, warm nostalgic glow with soft bloom, anime illustration, Makoto Shinkai and Studio Ghibli inspired, highly detailed semi-realistic background, 16:9

Ví dụ 4 (cao trào, neon):
Medium shot of @Image1 in a gaming jersey on an esports stage, gripping the mouse, intense focused expression, blue and purple neon stage lights, high contrast, crowd silhouettes blurred in background, anime illustration, thin clean lineart, soft cel shading, cinematic lighting, 16:9

Prompt motion cho image-to-video:
0–1s: hold, subtle breathing. 1–3s: slow camera push-in, character [hành động nhỏ]. 3–4s: hold on expression. No morphing, keep face consistent.

## Checklist mỗi ảnh
- [ ] Đúng nhân vật (đã gắn ảnh reference)
- [ ] Tông màu đúng cảm xúc của Level
- [ ] Kiểu shot khác shot trước
- [ ] Chữ tiếng Việt trong ảnh đọc được, đúng dấu, không sai chính tả
- [ ] Chừa chỗ cho phụ đề và watermark
- [ ] Clip i2v không méo mặt