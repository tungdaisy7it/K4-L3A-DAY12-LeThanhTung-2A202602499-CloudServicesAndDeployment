# Phiếu Phản Ánh — K4 Level 3A, Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: thay dòng placeholder dưới mỗi câu bằng câu trả lời.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: Lê Thành Tùng  Mã học viên: 2A202602499

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

> Tình huống: mình tạo service trên Railway, bấm deploy nhưng quên thêm biến
> `AGENT_API_KEY` trong tab Variables. Vì trường này không có mặc định,
> `Settings()` ném `ValidationError` ngay lúc import, container crash, health
> check đỏ và deployment bị đánh dấu thất bại — mình thấy lỗi trong log sau vài
> giây và sửa trước khi có ai dùng. Nếu mặc định là `"changeme"`, service vẫn
> xanh, URL công khai chạy bình thường, và bất kỳ ai đoán/đọc được chuỗi
> `changeme` trong repo công khai đều gọi `/ask` bằng ngân sách của mình mà mình
> không hề biết. Chết sớm biến một lỗ hổng bảo mật âm thầm thành một lỗi deploy
> hiển nhiên.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

> Dòng log thật từ `docker compose logs agent`:
>
> `{"event": "ask_completed", "level": "info", "timestamp": "2026-09-28T08:11:35.309720+00:00", "user_id": "rl-test", "tokens_in": 1, "tokens_out": 33, "cost_usd": 1.995e-05}`
>
> Hai việc làm được mà `print("đã trả lời xong")` không làm được:
> 1. **Lọc và tổng hợp theo trường**: ví dụ lọc `event = ask_completed AND user_id = rl-test`
>    rồi cộng `cost_usd` để biết một user tiêu bao nhiêu tiền hôm nay, hoặc đếm
>    số request theo phút.
> 2. **Đặt cảnh báo tự động**: ví dụ báo động khi có `level = error`, hoặc khi
>    `tokens_in` vượt ngưỡng (dấu hiệu prompt bị nhồi). Máy đọc được JSON nên
>    không cần regex dễ vỡ; còn chuỗi `print` không có user, không có thời gian
>    chuẩn ISO, không có số liệu để tính.

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | 1.73 GB (~1770 MB) |
| Multi-stage | 271 MB |

Giải thích: phần dung lượng chênh lệch đó là những gì?

> Số đo thật trên máy: `agent:single` 1.73 GB, `agent:multi` 271 MB — nhỏ hơn
> khoảng 6.5 lần. Phần chênh lệch ~1.46 GB gồm:
> - Base image `python:3.11` bản đầy đủ (Debian đầy đủ + gcc, make, header C,
>   git, thư viện dev...) so với `python:3.11-slim` chỉ có đủ để chạy Python.
> - Cache của pip và file tạm lúc cài (bản single không dùng `--no-cache-dir`).
> - Toàn bộ build context bị `COPY . .` (tests, tài liệu, grade.py...) — bản
>   multi-stage chỉ copy `app/` và `utils/`.
> Ở bản multi-stage, stage `builder` cài thư viện vào `/install`, stage runtime
> chỉ `COPY --from=builder /install` — mọi thứ khác của builder bị bỏ lại.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

> Mình đổi `SERVICE_VERSION = "1.0.0"` thành `"1.0.1"` trong `app/main.py` rồi
> build lại với `--progress=plain`. Kết quả: `useradd`, `WORKDIR`,
> `COPY requirements.txt`, `RUN pip install` và `COPY --from=builder /install`
> đều hiện `CACHED`; chỉ hai layer `COPY app ./app` và `COPY utils ./utils` chạy
> lại, build xong trong vài giây. (Utils chạy lại vì nó nằm sau layer app bị
> thay đổi — cache bị hủy từ layer đầu tiên thay đổi trở đi.)
>
> Nếu đặt `COPY . .` trước `RUN pip install`, sửa một ký tự bất kỳ trong code
> cũng làm layer COPY đổi checksum → layer `pip install` phía sau mất cache →
> tải và cài lại toàn bộ thư viện. Trên mạng của mình bước này mất hơn 2 phút
> (lần build đầu còn bị `ReadTimeoutError` từ PyPI), tức mỗi lần sửa code là chờ
> vài phút thay vì vài giây.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

> Chuỗi sự kiện khi chạy root:
> 1. Code Python có lỗ hổng (ví dụ gọi `subprocess`/`eval` với input người dùng,
>    hoặc một thư viện có lỗi RCE) → kẻ tấn công chạy được lệnh trong container.
> 2. Lệnh đó chạy với UID 0 → đọc/sửa mọi file trong container, cài công cụ,
>    đọc biến môi trường chứa secret.
> 3. UID 0 trong container chính là UID 0 trên host (không có user namespace).
>    Chỉ cần một điểm yếu nữa — volume mount thư mục host, `docker.sock` bị
>    mount vào, container `--privileged`, hay một lỗ hổng kernel/runtime để
>    escape — là kẻ tấn công thao tác trên host với quyền root.
>
> `USER appuser` (UID 10001) cắt chuỗi ở bước 2–3: lệnh chiếm được chỉ có quyền
> của một user thường, không ghi được vào thư mục hệ thống, không cài được gói,
> và nếu có escape thì trên host nó cũng chỉ là UID 10001 không có đặc quyền.
> Mình kiểm tra bằng `docker compose exec agent whoami` → `appuser`.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

> Tối đa **20 request trong 2 giây**. Cách đạt được: gửi 10 request lúc
> 10:00:59 (đủ hạn mức của phút 10:00), rồi đồng hồ sang 10:01:00 bộ đếm reset
> về 0, gửi tiếp 10 request lúc 10:01:00–10:01:01. Mỗi phút đồng hồ đều "đúng
> luật" 10 request nhưng thực tế service nhận gấp đôi trong 2 giây.
>
> Với sliding window, lúc 10:01:01 limiter nhìn lại 60 giây trước đó (từ
> 10:00:01) và vẫn thấy 10 request cũ → request thứ 11 bị 429 ngay. Mình đã thấy
> điều này khi gọi 15 lần liên tiếp: `200` × 10 rồi `429` × 5.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

> **Rate limit** giới hạn *số lượng request theo thời gian* (10 request/60
> giây) — chống spam, bảo vệ tài nguyên xử lý. **Cost guard** giới hạn *số tiền
> cộng dồn theo tháng* (10 USD/user) — chống cháy ngân sách LLM. Một cái đếm
> lượt, một cái đếm tiền, và cửa sổ thời gian khác nhau (phút vs tháng).
>
> - Rate limit cho qua nhưng cost guard chặn: user gửi đều đặn 5 request/phút
>   (luôn dưới hạn mức), nhưng mỗi request là một prompt rất dài/lịch sử dài
>   tốn nhiều token; sau vài ngày tổng chi phí vượt 10 USD → nhận 402.
> - Cost guard cho qua nhưng rate limit chặn: user mới, chưa tiêu đồng nào,
>   chạy script gửi 15 câu hỏi ngắn trong 5 giây → request thứ 11 nhận 429 dù
>   ngân sách còn gần như nguyên vẹn.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

> Thứ tự sự kiện nếu một endpoint vừa là liveness vừa kiểm tra Redis:
> 1. Giây 0: Redis mất kết nối. Cả 3 container cùng dùng một Redis nên cả 3
>    đều thấy lỗi cùng lúc.
> 2. Probe gọi `/health` của cả 3 → đều trả 503.
> 3. Sau vài lần probe fail liên tiếp (ví dụ 3 × 10s), orchestrator kết luận
>    cả 3 process "chết" và **restart cả 3** — dù process Python hoàn toàn khỏe.
> 4. Trong lúc restart, request đang xử lý dở bị cắt, cụm có 0 instance phục vụ
>    → user nhận 502 cho mọi request, kể cả những request không cần Redis.
> 5. Container mới khởi động xong mà Redis vẫn chưa về → lại fail → vòng lặp
>    restart (crash loop), log ngập lỗi, có thể bị backoff lâu hơn cả 30 giây.
> 6. Giây 30: Redis về, nhưng cụm còn phải chờ khởi động lại/qua backoff mới
>    phục vụ được — sự cố 30 giây kéo dài thành vài phút.
>
> Tách ra thì: `/health` vẫn 200 (không restart ai), `/ready` trả 503 nên load
> balancer tạm ngừng gửi traffic; Redis về là `/ready` 200 và traffic quay lại
> ngay, không mất container nào.

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

> Mình chạy `docker compose up -d --scale agent=3`, ba container được map ra
> cổng 8000, 8001, 8002. Gọi `/ask` lần lượt vào 8000 → 8001 → 8002 → 8000 →
> 8001 với cùng `X-User-Id: sv02`, `history_length` nhận được là
> **0 → 2 → 4 → 6 → 8**: tăng đều dù mỗi request rơi vào một container khác,
> vì cả ba đọc/ghi cùng một list `history:sv02` trong Redis.
>
> Nếu lịch sử nằm trong dict Python của từng process, mỗi container chỉ nhớ
> những lượt nó tự xử lý: kết quả sẽ là **0 → 0 → 0 → 2 → 2** (lượt thứ 4 quay
> lại container 8000 mới thấy lượt 1 của chính nó). Với load balancer
> round-robin, con số nhảy lung tung theo container nhận request, agent "mất
> trí nhớ", và restart container là mất sạch lịch sử.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

> *Câu trả lời của bạn*
