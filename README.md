# Hanzi Studio

App cục bộ tạo video bài học tiếng Trung ngắn từ chủ đề: xem/sửa kịch bản, tạo giọng đọc và xuất MP4 dọc 1080 × 1920.

- **VieNeu-TTS v3 Turbo** đọc lời giải thích tiếng Việt (mặc định giọng Trúc Ly).
- **Xiaoxiao** đọc chữ Hán trực tiếp bằng tiếng Trung. Pinyin chỉ hiển thị, không phiên âm qua tiếng Việt để đọc.
- Video thường 15–35 giây, giới hạn 40 giây; H.264 + AAC, 24 fps.
- Có giáo viên hoạt hình, phụ đề, xem trước cảnh, tiến độ dựng và thư viện video đã tạo.

## Cài đặt trên Windows

Cần **Python 3.11 64-bit** có trong PATH và kết nối mạng. VieNeu chạy CPU/ONNX, không yêu cầu GPU. Bản hiện tại dùng font và môi trường Python của Windows.

```powershell
git clone https://github.com/david-cung/make-video-learn-chinese.git
cd make-video-learn-chinese
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Script cài công cụ dựng video vào `tools/`, tạo môi trường riêng `.venv-vieneu/`, và tạo `windows-ca.pem` từ chứng chỉ công khai của Windows. Không thay đổi cấu hình TLS toàn hệ thống.

Lần xuất đầu VieNeu tải model vào `models/` (cần vài trăm MB, có thể mất vài phút). Những lần sau dùng cache. Giọng Trung cần mạng khi chưa có audio tương ứng. Model, môi trường, chứng chỉ máy và video xuất không nằm trong Git.

## Sử dụng

Mở **BAT-STUDIO.bat**. App tự mở trình duyệt tại **http://127.0.0.1:3015**. Giữ cửa sổ chạy trong lúc dựng video.

1. Nhập chủ đề hoặc chọn gợi ý.
2. Tạo kịch bản và sửa từng cảnh nếu cần.
3. Chọn giọng Việt, bấm **Xuất video MP4**.
4. Xem/tải video trong **Những bài học đã tạo**.

Cũng có thể chạy `python app.py --open`. App chỉ lắng nghe trên loopback. Đổi cổng bằng biến môi trường `PORT` nếu cần.

Kết quả nằm trong `outputs/<id>/`: `video.mp4`, `video.srt`, `script.json`, ảnh bìa, thông số và `render.log`. Miệng nhân vật chuyển động đơn giản, chưa khớp từng âm tiết. Phụ đề canh theo câu bằng ước lượng, chưa căn từng từ.

## Nguồn kịch bản

- Có sẵn bài ngắn: chào hỏi, cảm ơn, cà phê, xin lỗi, nhà hàng, taxi/sân bay, cách học từ vựng.
- Có thể tìm từ trong thư viện HSK hoặc chọn **Tự viết kịch bản**.
- Khi chưa có bài phù hợp, app báo rõ thay vì trả về bài ngẫu nhiên.

Để tự soạn bằng AI cho chủ đề ngoài thư viện, cấu hình ba biến môi trường trước khi chạy app. Endpoint cần hỗ trợ chat completions và JSON response:

```powershell
$env:SCRIPT_API_URL = 'https://your-provider.example/v1/chat/completions'
$env:SCRIPT_API_MODEL = 'your-model-id'
# Đặt SCRIPT_API_KEY trong môi trường; không ghi key vào mã nguồn.
python app.py --open
```

AI là tùy chọn; phần kết nối này cần cấu hình và chưa được kiểm tra với tài khoản nhà cung cấp của bạn. Xem lại nội dung trước khi xuất. Lời đọc Việt không được chứa chữ Hán/pinyin; lời Trung dùng chữ Hán, không nhận phiên âm Latin.

## Mã nguồn

| File | Vai trò |
| --- | --- |
| `app.py` | HTTP server, hàng đợi, trạng thái và tải video |
| `web/` | Giao diện không cần build |
| `lesson_planner.py` | Tạo và kiểm tra kịch bản |
| `render_job.py`, `make_video.py` | Điều phối audio, dựng hình và xuất MP4 |
| `vieneu_narration.py` | VieNeu trong môi trường riêng, cache theo nội dung/giọng |
| `assets/`, `lesson-content/` | Ảnh giáo viên và dữ liệu HSK |

Phiên bản thư viện nằm trong `requirements-tools.txt` và `requirements-vieneu.lock.txt`. `python make_video.py --tts vieneu` dựng bài mẫu chào hỏi độc lập.

## Kiểm tra

```powershell
python -m unittest test_app -v
python -m py_compile app.py lesson_planner.py render_job.py make_video.py vieneu_narration.py
# Node.js chỉ cần cho kiểm tra JavaScript/browser:
node --check web/app.js
```

Khi app đang chạy, `python qa_api.py` kiểm tra HTTP, kịch bản, ngôn ngữ, video Range và phụ đề (cần ít nhất một video hoàn tất). `node qa-browser.mjs` kiểm tra desktop/mobile bằng Microsoft Edge trên Windows.

Đã thử xuất video **Gọi cà phê** 19,9 giây bằng VieNeu và giọng Trung. Video không được commit; tạo lại từ chủ đề này trong app.

## Thành phần sử dụng

- [VieNeu-TTS](https://github.com/pnnbao97/VieNeu-TTS): model và SDK tiếng Việt; xem điều khoản dự án/model tương ứng.
- [edge-tts](https://github.com/rany2/edge-tts): tổng hợp lời Trung.
- [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg), [Pillow](https://github.com/python-pillow/Pillow): mã hóa video và dựng hình.

Ảnh giáo viên và nội dung HSK được chuyển từ project `live-study-chinese` trong cùng workspace; app này không phụ thuộc project đó khi chạy.
