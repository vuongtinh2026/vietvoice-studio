# 🎙️ VietVoice Studio - Text-to-Speech (Hỗ trợ Cheap-TTS & Web Speech)

Ứng dụng web chuyển đổi văn bản thành giọng nói (Text-to-Speech) đa chế độ: kết hợp giữa **Web Speech API** (chạy trên trình duyệt miễn phí) và **Cheap-TTS AI Cloud** (tích hợp trực tiếp tài khoản từ [cheap-tts.com](https://www.cheap-tts.com/vi/)).

---

## 🌟 2 Chế Độ Chuyển Đổi

### 1. 🌐 Trình duyệt (Web Speech API)
- Hoạt động 100% offline, miễn phí, không cần tài khoản hay kết nối mạng.
- Tự động quét và chọn giọng tiếng Việt có sẵn trên máy (Google Tiếng Việt, Apple Mai, Linh...).
- Tích hợp thuật toán chia nhỏ câu (Sentence Chunking) để không bị ngắt quãng giữa chừng khi đọc văn bản dài.

### 2. ⚡ Cheap-TTS AI Cloud (cheap-tts.com)
- Sử dụng giọng đọc AI tự nhiên chất lượng cao chuyên dùng làm video TikTok, Review phim, YouTube, Podcast.
- Hỗ trợ các model giọng: **Giải trí / Kể chuyện (`vi-entertainment`)**, **Tin tức (`vi-news`)**, **Giọng nữ chuẩn**, **Giọng nam chuẩn**.
- **Xuất và Tải file âm thanh (.WAV / .MP3)** trực tiếp về máy tính chỉ với 1 click.
- Tùy chỉnh khoảng ngắt nghỉ (Pauses) linh hoạt sau mỗi câu và đoạn văn.

---

## 🔑 Hướng dẫn tích hợp tài khoản từ cheap-tts.com

1. Đăng nhập vào tài khoản của bạn tại: [https://www.cheap-tts.com/dashboard/](https://www.cheap-tts.com/dashboard/)
2. Lấy **Publishable Key** (có tiền tố dạng `pk_live_...` hoặc `pk_test_...`).
3. Trong phần cấu hình **Allowed Origins / Domains** trên Dashboard của Cheap-TTS, hãy đảm bảo đã thêm tên miền bạn đang chạy (ví dụ: `http://localhost:3000`).
4. Mở ứng dụng VietVoice Studio, chuyển sang tab **Cheap-TTS Cloud AI**, dán Key vào ô cấu hình và bấm **Lưu & Kết nối**.
*(Hệ thống sẽ tự động lưu Key vào trình duyệt của bạn để các lần dùng sau không cần nhập lại).*

---

## 🚀 Cách Chạy Ứng Dụng

Do tính năng Cheap-TTS sử dụng WebAssembly (WASM) và Web Worker, bạn nên khởi chạy qua HTTP Server:

```bash
cd /Users/mdm/.gemini/antigravity/scratch/text-to-speech-app
python3 -m http.server 3000
```
Sau đó mở trình duyệt và truy cập: `http://localhost:3000`

---

## 📁 Cấu Trúc Dự Án

```
text-to-speech-app/
├── index.html            # Giao diện chính (Tailwind CSS, Font Awesome, Tab chuyển đổi)
├── style.css             # Hiệu ứng visualizer, sóng âm, scrollbar
├── app.js                # Bộ điều khiển Hybrid (Web Speech + Cheap-TTS SDK)
├── cheap-tts-sdk/        # Thư viện Browser SDK chính thức của Cheap-TTS
│   ├── index.js          # ESM client
│   ├── tts-worker.js     # Web Worker xử lý audio
│   └── vendor/           # WebAssembly SIMD ONNX Runtime
└── README.md             # Hướng dẫn chi tiết
```
