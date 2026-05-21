# AEGIS O2O - Báo cáo rà soát kỹ thuật toàn diện

Ngày rà soát: 2026-05-13  
Phạm vi: backend FastAPI, domain O2O, AI worker, optimization service, PostgreSQL/PostGIS/pgvector, Docker/Compose, frontend React/TanStack Router, test/build/release readiness.

---

## 0. Tóm tắt điều hành

AEGIS O2O đang có nền ý tưởng tốt: bản đồ du lịch, gợi ý mua sắm quanh địa điểm, giữ hàng, QR thanh toán, AI agent, vision scan, virtual closet, route planner. Tuy nhiên trạng thái hiện tại chưa thể coi là production-ready.

Những vấn đề lớn nhất không nằm ở giao diện mà nằm ở ranh giới vận hành:

- Hạ tầng production thiếu các service mà code đang phụ thuộc: Redis, RabbitMQ, Celery/Beat, optimization service, OSRM private server.
- Docker backend hiện chỉ copy `backend/app` và `backend/scripts`, không copy `backend/workers` hay `backend/optimization_service`, trong khi runtime lại import `workers.ai_worker`.
- Alembic chỉ theo `SQLModel.metadata` của module legacy `User/Item`; các domain mới dùng `Base` riêng nên migration không quản trị được `places`, `stores`, `products`, `inventory`, `orders`, `vision_tasks`, `virtual_closets`.
- Frontend build hiện fail TypeScript, nghĩa là chưa qua được cổng release tối thiểu.
- Luồng payment đang là mock: tạo order là "confirmed", trả VietQR demo, không có webhook, không có trạng thái paid, không có idempotency.
- Inventory lock có race condition và thiếu store-level semantics, có thể khóa nhầm tồn kho, oversell, hoặc tạo order không cần lock.
- AI/Vision đang chạy task nặng bằng thread trong API process, không qua Celery thật; khi Docker production chạy 4 workers, rủi ro OOM và timeout rất cao.
- Nhiều endpoint mutation hoặc compute-cost cao không có auth/rate limit: agent chat, review, trigger release, route planning, scan image.
- Frontend có nhiều chức năng "trông như thật" nhưng dữ liệu hard-coded hoặc gọi sai contract backend.

Kết luận: dự án nên được đóng băng tính năng mới trong 2-3 sprint để sửa cổng hạ tầng, migration, build, security và domain correctness trước khi demo quy mô lớn hoặc deploy cho người dùng thật.

---

## 1. Cách đọc báo cáo

Mỗi mục lỗi gồm:

- Mức độ: `P0` chặn release, `P1` lỗi nghiêm trọng, `P2` cần sửa trước beta, `P3` cải thiện dài hạn.
- Chứng cứ: file và dòng đã rà trong repo.
- Tác động: ảnh hưởng tới production, data, security, hiệu năng hoặc UX.
- Khuyến nghị: hướng sửa cụ thể.

Các kết quả kiểm tra đã chạy:

- `bun run build` trong `frontend/`: fail TypeScript.
- `uv run --package app ruff check ...`: không hoàn tất vì sandbox không resolve được PyPI khi uv cố tải dependency; kết quả này không dùng để kết luận code backend pass/fail.

---

## 2. Release Gate

### Gate bắt buộc trước production

1. Frontend build phải pass.
2. Backend test phải chạy được trong container không cần internet runtime.
3. Docker Compose production phải dựng được đầy đủ DB, Redis, broker, backend, frontend, worker, beat, optimization service.
4. Alembic phải quản trị toàn bộ schema domain, không phụ thuộc dump SQL thủ công.
5. Payment phải có gateway/webhook/idempotency hoặc bị gắn nhãn rõ là mock.
6. Inventory reservation phải atomic theo store/product/quantity.
7. Endpoint AI/route/scan phải có auth, rate limit và quota.
8. Upload file phải có object storage hoặc volume chia sẻ giữa API và worker.
9. Secrets/API keys không được log hoặc trả về client.
10. Observability tối thiểu: logs có correlation id, metrics cho latency/error, Sentry/alerting.

### Gate demo nội bộ

1. Có thể dùng public OSRM/Open-Meteo/Wikipedia nhưng phải có timeout, cache, fallback rõ.
2. Có thể dùng VietQR mock nhưng UI không được nói "Order Confirmed" như đã thanh toán.
3. Có thể dùng thread fallback cho AI nhưng phải giới hạn concurrency và ghi status failed đúng.
4. Có dữ liệu seed ổn định và script seed idempotent.
5. Có kịch bản reset môi trường local.

---

## 3. Ma trận rủi ro tổng quan

| Nhóm | Tình trạng | Mức độ | Lý do |
|---|---:|---:|---|
| Docker/infra | Không dựng đủ service | P0 | Code phụ thuộc Redis/RabbitMQ/optimization/worker nhưng compose production thiếu |
| Database migration | Không quản trị domain schema | P0 | Alembic không nhìn thấy Base metadata |
| Frontend build | Fail TypeScript | P0 | Không tạo được artifact release sạch |
| Payment | Mock chưa an toàn | P0 | Order confirmed trước payment, không webhook |
| Inventory lock | Sai atomicity | P0 | Có thể khóa nhầm, oversell, stale lock |
| Vision worker | Thread trong API, worker không được copy | P0 | Scan/closet dễ timeout hoặc không chạy trong Docker |
| Agent | Public cost endpoint | P1 | Bất kỳ ai có thể gọi Gemini qua backend |
| Optimization service | No auth/CORS `*` | P1 | Dễ bị spam CPU và gọi trực tiếp |
| Upload file | Local filesystem, filename collision | P1 | Mất file khi scale, ghi đè ảnh |
| Spatial/route | Public OSRM, no cache | P1 | Rate limit và downtime làm mất tính năng |
| Review/culture | No auth/moderation | P1 | Spam, giả mạo, nội dung độc hại |
| Frontend UX | Nhiều mock/silent catch | P2 | Người dùng khó hiểu lỗi thật |
| Tests | Chưa phủ domain mới | P1 | Không bắt được lỗi lock/payment/AI/planner |

---

## 4. P0 - Lỗi chặn release

### P0-01. Production Compose thiếu Redis, RabbitMQ, AI Worker, Beat, Optimization Service

Chứng cứ:

- `compose.yml:1-176` chỉ có `db`, `adminer`, `prestart`, `backend`, `frontend`.
- `compose.override.yml:48-52` chỉ thêm Redis cho local override, không phải production.
- `backend/app/domains/inventory/router.py:33-42` phụ thuộc Redis qua `get_redis`.
- `backend/app/domains/planner/service.py:34` gọi optimization service ở `http://localhost:8001/api/v1/optimize`.
- `backend/workers/ai_worker/celery_app.py:11-18` định nghĩa Celery nhưng không có service chạy trong compose chính.

Tác động:

- `POST /inventory/lock` sẽ lỗi nếu Redis không tồn tại.
- Planner sẽ không gọi được optimization service trong container vì `localhost:8001` trỏ về chính container backend.
- Celery Beat không chạy nên expired locks không được sweep tự động.
- Vision tasks không có worker thật.

Khuyến nghị:

- Thêm services production: `redis`, `rabbitmq`, `ai_worker`, `ai_beat`, `optimization_service`, và nếu cần `osrm`.
- Backend phải phụ thuộc healthcheck Redis/RabbitMQ nếu endpoint cần chúng.
- Dùng biến môi trường `REDIS_URL`, `RABBITMQ_URL`, `OPTIMIZATION_SERVICE_URL`, `OSRM_BASE_URL`.
- Không hard-code `localhost` trong code production.

Acceptance criteria:

- `docker compose up -d` dựng đủ service.
- `backend` gọi `optimization_service:8001`, không gọi `localhost:8001`.
- Celery worker nhận được task scan.
- Celery beat sweep lock theo lịch.

---

### P0-02. Backend Docker image không copy `workers` và `optimization_service`

Chứng cứ:

- `backend/Dockerfile:30-35` chỉ copy `backend/scripts`, `backend/pyproject.toml`, `backend/alembic.ini`, `backend/app`.
- `backend/app/domains/vision/service.py:15-18` import `workers.ai_worker.vision_tasks`.
- `backend/app/domains/vision/service.py:37-40` import `workers.ai_worker.vision_tasks.process_closet_image`.

Tác động:

- Trong container backend production, import `workers...` có khả năng fail vì thư mục đó không có trong image.
- API vẫn trả task_id nhưng worker thread không khởi chạy; task nằm `processing` rồi bị router đánh `failed` sau 30 giây.
- Người dùng thấy "AI đang xử lý" nhưng hệ thống thực tế không xử lý.

Khuyến nghị:

- Tách Dockerfile cho API và worker.
- API image không import trực tiếp `workers`.
- Khi tạo task, gọi `process_image.delay(task_id, image_path)` qua Celery broker.
- Worker image copy `backend/workers`, `backend/app`, model cache và dependency cần thiết.

Acceptance criteria:

- API container không cần import CLIP model.
- Worker container nhận task từ broker.
- Scan task chuyển `processing -> completed/failed` do worker, không do polling timeout giả.

---

### P0-03. Alembic không quản trị schema domain mới

Chứng cứ:

- `backend/app/alembic/env.py:21-24` đặt `target_metadata = SQLModel.metadata`.
- Domain mới dùng `Base` từ `backend/app/db/session.py`, ví dụ `backend/app/domains/inventory/model.py:2`, `backend/app/domains/culture/model.py:3`, `backend/app/domains/vision/model.py:2`.
- Migration hiện có chủ yếu tạo `user` và `item`, ví dụ `backend/app/alembic/versions/e2412789c190_initialize_models.py:21-45`.
- `backend/create_domain_tables.py:1-8` dùng `Base.metadata.create_all(bind=engine)` như đường tắt ngoài Alembic.

Tác động:

- Production schema phụ thuộc vào dump SQL hoặc script thủ công, không có lịch sử migration chuẩn.
- Không rollback được domain tables.
- Autogenerate Alembic không phát hiện thay đổi model domain.
- CI không thể đảm bảo DB mới dựng lên đúng schema.

Khuyến nghị:

- Hợp nhất metadata: Alembic target phải gồm cả `SQLModel.metadata` và `Base.metadata`.
- Viết migration chính thức cho `places`, `reviews`, `stores`, `products`, `inventory`, `inventory_locks`, `orders`, `vision_tasks`, `virtual_closets`.
- Di chuyển extension/index vào migration: `postgis`, `vector`, `pg_trgm`, GiST, GIN trigram, HNSW.
- Loại bỏ `create_all` khỏi flow production.

Acceptance criteria:

- DB trống + `alembic upgrade head` tạo đầy đủ schema.
- Không cần import dump SQL để API boot.
- `alembic downgrade` tối thiểu rollback được migration mới trong staging.

---

### P0-04. Main Compose không chạy init extension PostGIS/pgvector/pg_trgm

Chứng cứ:

- `backend/app/infrastructure/init_db.sql:5-12` có `CREATE EXTENSION`.
- `backend/app/infrastructure/docker-compose.yml:16` mount init script, nhưng file này không phải compose chính.
- `compose.yml:3-23` build DB từ `backend/db/Dockerfile` nhưng không mount/copy `init_db.sql`.
- `backend/db/Dockerfile:1-7` cài pgvector package nhưng không tạo extension trong database.

Tác động:

- DB mới có thể thiếu `vector` hoặc `pg_trgm`.
- Query pgvector và PostGIS có thể fail runtime nếu extension chưa được tạo.
- Search similarity/trigram và HNSW index không có bảo đảm.

Khuyến nghị:

- Đưa extension creation vào Alembic migration.
- Hoặc copy init script vào DB image dưới `/docker-entrypoint-initdb.d/`.
- Compose chính và compose local phải thống nhất.

Acceptance criteria:

- DB mới có `SELECT extname FROM pg_extension` trả đủ `postgis`, `vector`, `pg_trgm`, `uuid-ossp`.

---

### P0-05. Frontend build đang fail TypeScript

Lệnh kiểm tra:

```bash
bun run build
```

Kết quả chính:

- `frontend/src/routes/_layout/inventory.tsx(34,7)`: `_CATEGORIES` khai báo nhưng không dùng.
- `frontend/src/routes/_layout/inventory.tsx(129,28)`: `product_id` có thể `undefined` nhưng truyền vào state `number | null`.
- `frontend/src/routes/_layout/inventory.tsx(130,63)`: truyền `number | undefined` vào hàm yêu cầu `number`.
- `frontend/src/routes/_layout/inventory.tsx(274,51)`: truyền `number | undefined` vào formatter yêu cầu `number`.
- `frontend/src/routes/_layout/spatial.tsx(126,7)`: `_getClusterIcon` khai báo nhưng không dùng.
- `frontend/src/routes/_layout/vision.tsx(328,17)`: `unknown` không assign được cho `ReactNode`.
- `frontend/src/routes/_layout/vision.tsx(351,66)`: `map` không tồn tại trên `{}`.

Tác động:

- Không thể tạo build artifact sạch.
- CI/CD sẽ fail nếu build được bật nghiêm túc.
- Các lỗi type này phản ánh contract frontend/backend chưa được chốt, đặc biệt `detected_objects`.

Khuyến nghị:

- Sửa type `ProductResponse.product_id` thành required ở nơi dùng hoặc guard trước khi gọi.
- Xóa biến unused hoặc dùng thật.
- Định nghĩa type rõ cho `detected_objects`, ví dụ `{ similar_items?: VisionSimilarItem[]; error?: string }`.
- Không dùng `Record<string, unknown>` rồi truy cập trực tiếp như object có shape cố định.

Acceptance criteria:

- `bun run build` pass.
- TypeScript strict build không có lỗi ở domain pages.

---

### P0-06. Vision API chạy AI bằng thread trong API process thay vì queue thật

Chứng cứ:

- `backend/app/domains/vision/service.py:15-18` gọi `threading.Thread(target=process_image, ...)`.
- `backend/app/domains/vision/service.py:37-40` gọi thread cho closet embedding.
- `backend/workers/ai_worker/vision_tasks.py:20` và `:79` có Celery task decorator nhưng API không gọi `.delay()`.
- `backend/workers/ai_worker/vision_tasks.py:10-18` load CLIP model ở module import.

Tác động:

- API worker có thể load CLIP model ngay khi import task, làm tăng RAM mạnh.
- Thread không có queue, retry, backpressure, visibility timeout, rate limit.
- Nếu API process restart, task đang chạy mất.
- Khi chạy `fastapi run --workers 4`, mỗi process có thể load model riêng.
- Nếu scan nhiều ảnh đồng thời, API process bị nghẽn CPU/RAM.

Khuyến nghị:

- API chỉ ghi task row và enqueue Celery: `process_image.delay(task_id, image_path)`.
- Worker xử lý model trong process riêng.
- Thêm queue name, concurrency thấp, prefetch thấp.
- Ghi trạng thái `failed` trong DB khi exception.

Acceptance criteria:

- 10 request scan đồng thời không làm API latency tăng đột biến.
- Task failure được lưu vào `vision_tasks.detected_objects.error`.

---

### P0-07. Payment hiện là mock nhưng UI nói như đã xác nhận đơn

Chứng cứ:

- `backend/app/domains/inventory/service.py:241-247` tạo VietQR URL với MB Bank demo `0123456789`.
- `backend/app/domains/inventory/service.py:301` tạo order status `PENDING_SHIP`.
- `frontend/src/routes/_layout/inventory.tsx:329-335` hiển thị "Order Confirmed!" và "Your order will be shipped soon" ngay khi backend tạo order.
- Không thấy endpoint webhook payment trong router/domain.

Tác động:

- Người dùng có thể đặt hàng mà không thanh toán.
- Hệ thống trừ tồn kho trước khi có xác nhận tiền.
- Vận hành không phân biệt unpaid/paid/cancelled/refunded.
- Rủi ro thất thoát tồn kho và nhầm kỳ vọng người dùng.

Khuyến nghị:

- Đổi status ban đầu thành `PENDING_PAYMENT`.
- Chỉ chuyển `PAID` khi webhook gateway hợp lệ.
- Thêm payment table: provider, amount, currency, status, transaction_id, idempotency_key, raw_payload.
- UI đổi copy thành "Đơn đã tạo, chờ thanh toán" thay vì "Order Confirmed".

Acceptance criteria:

- Không có order nào sang trạng thái fulfill/shipping khi chưa có webhook hợp lệ.
- Webhook kiểm tra chữ ký và idempotency.

---

### P0-08. `finalize_order` cho phép tạo order không cần lock đang active

Chứng cứ:

- `backend/app/domains/inventory/service.py:250-317` tạo order dựa vào `OrderCreate`.
- `backend/app/domains/inventory/service.py:283-287` chỉ tìm lock cũ để đánh dấu completed nếu có, không bắt buộc lock tồn tại.
- `backend/app/domains/inventory/service.py:278-280` trừ stock bằng `max(0, stock - quantity)`.

Tác động:

- Client có thể gọi `POST /inventory/orders` trực tiếp để mua sản phẩm chưa reserve.
- Nếu stock = 0, code vẫn tạo order và set stock về 0.
- Locked stock có thể âm logic nhưng bị `max(0)` che mất lỗi.

Khuyến nghị:

- `OrderCreate` phải nhận `lock_id`.
- Transaction phải lock `InventoryLock` và `Inventory` cùng lúc.
- Nếu không có lock active đúng user/product/store/quantity thì trả 409/400.
- Không dùng `max(0)` để che oversell; phải raise lỗi khi không đủ tồn kho.

Acceptance criteria:

- Gọi create order không có lock active trả lỗi.
- Gọi order quá quantity locked trả lỗi.

---

### P0-09. Inventory lock không atomic theo store và quantity

Chứng cứ:

- `backend/app/domains/inventory/service.py:139` Redis key chỉ là `lock:prod:{product_id}`.
- `backend/app/domains/inventory/service.py:151-153` lock row đầu tiên theo `product_id`.
- `backend/app/domains/inventory/service.py:160-162` tính tổng tồn kho tất cả store.
- `backend/app/domains/inventory/service.py:167` cộng `locked_stock` vào `inv` đầu tiên.
- `backend/app/domains/inventory/schema.py:17-20` `LockRequest` không có `store_id`.

Tác động:

- Một sản phẩm ở nhiều store bị khóa global, làm giảm khả dụng sai.
- Nếu store đầu tiên chỉ còn ít stock nhưng tổng nhiều store đủ, code vẫn cộng locked_stock vào row đầu tiên.
- Không thể đảm bảo khách giữ hàng tại đúng cửa hàng họ chọn.
- Race condition vẫn còn vì chỉ lock một row nhưng đọc tổng nhiều row ngoài lock.

Khuyến nghị:

- `LockRequest` phải có `store_id`, `product_id`, `quantity`.
- Unique/partial index cho active lock theo user/store/product nếu cần.
- Redis key nên gồm store/product/user/lock id hoặc chỉ dùng Postgres advisory/row lock.
- Tính available trên đúng `Inventory(store_id, product_id)` dưới `SELECT ... FOR UPDATE`.

Acceptance criteria:

- Hai user có thể giữ cùng product ở hai store khác nhau nếu stock đủ.
- Không user nào giữ được quantity vượt `stock - locked_stock`.

---

### P0-10. Expired lock phụ thuộc Celery Beat nhưng service Beat không chạy

Chứng cứ:

- `backend/workers/ai_worker/celery_app.py:29-35` định nghĩa beat schedule.
- `compose.yml` không có Celery beat service.
- `backend/app/domains/inventory/router.py:44-48` có endpoint thủ công `/trigger-release`.

Tác động:

- Lock hết hạn không được release tự động trong production compose.
- Tồn kho có thể bị giữ ảo vô thời hạn nếu Redis key hết hạn nhưng DB lock chưa sweep.
- Endpoint thủ công là workaround, không phải vận hành production.

Khuyến nghị:

- Thêm service `ai_beat` hoặc dùng scheduler managed.
- Sweep task phải chạy idempotent, có metric released_count.
- Endpoint trigger release nếu còn giữ phải yêu cầu superuser/internal secret.

Acceptance criteria:

- Sau TTL + 1 phút, lock expired được chuyển status và locked_stock giảm đúng.

---

## 5. P1 - Hạ tầng, cấu hình và deploy

### P1-01. Cấu hình service đang phân mảnh thành nhiều compose không thống nhất

Chứng cứ:

- `compose.yml` là compose chính cho backend/frontend/db/adminer.
- `compose.override.yml` thêm Redis local.
- `backend/app/infrastructure/docker-compose.yml` định nghĩa db/redis/rabbitmq/osrm nhưng không có backend/frontend/worker/optimization.

Tác động:

- Developer dễ chạy một compose và tưởng đủ, nhưng production thiếu service.
- Infra script nằm sâu trong `backend/app/infrastructure` không được wire vào release.
- Hành vi local khác production.

Khuyến nghị:

- Một compose chính có profile: `local`, `worker`, `routing`, `observability`.
- Tách file override chỉ cho port mapping/dev reload.
- Document rõ lệnh chạy: `docker compose --profile worker --profile routing up`.

---

### P1-02. Các biến môi trường quan trọng chưa có trong `.env.example`

Chứng cứ:

- `.env.example:1-54` không có `REDIS_URL`, `RABBITMQ_URL`, `OPTIMIZATION_SERVICE_URL`, `OSRM_BASE_URL`, `INTERNAL_SERVICE_SECRET`, `PAYMENT_*`, `UPLOAD_*`.
- `backend/app/db/redis_client.py:13` default `redis://localhost:6379/0`.
- `backend/workers/ai_worker/celery_app.py:8-9` default RabbitMQ/Redis localhost.
- `backend/app/domains/planner/service.py:34` hard-code optimization URL.

Tác động:

- Container network fail vì `localhost` không trỏ service khác.
- Secrets nội bộ không được quản lý.
- Payment/storage/routing không thể cấu hình theo môi trường.

Khuyến nghị:

- Bổ sung đầy đủ env contract vào `.env.example`.
- Config tập trung qua `Settings`.
- Startup validate các env bắt buộc theo `ENVIRONMENT`.

---

### P1-03. Optimization service không có auth và CORS mở

Chứng cứ:

- `backend/optimization_service/main.py:27-33` `allow_origins=["*"]`, allow credentials/methods/headers.
- `backend/optimization_service/api/v1/optimize.py:18-29` endpoint không yêu cầu token.

Tác động:

- Nếu port lộ ra public, bot có thể spam payload lớn để đốt CPU.
- Có thể dùng service như routing compute proxy miễn phí.

Khuyến nghị:

- Service nội bộ không cần CORS public.
- Thêm middleware `X-Internal-Secret` hoặc mTLS/service mesh.
- Giới hạn payload `shops <= 50`, timeout, rate limit.

---

### P1-04. Backend API có endpoint cost cao không auth

Chứng cứ:

- `backend/app/domains/agent/router.py:8-13` `/agent/chat` không có `get_current_user`.
- `backend/app/domains/vision/router.py:43-48` `/vision/scan` không auth.
- `backend/app/domains/culture/router.py:22-27` post review không auth.
- `backend/app/domains/spatial/router.py` các route compute không auth.
- `backend/app/domains/planner/router.py:14-27` planner không auth.

Tác động:

- Bất kỳ client nào biết URL API có thể gọi LLM, upload ảnh, tạo route compute, spam review.
- Chi phí Gemini/CPU/storage tăng không kiểm soát.

Khuyến nghị:

- Tất cả endpoint domain O2O nên yêu cầu auth trừ search public có rate limit.
- Thêm quota theo user/IP cho agent, scan, planner.
- Gắn cost metrics theo endpoint.

---

### P1-05. Devtools frontend luôn được import/render

Chứng cứ:

- `frontend/src/routes/__root.tsx:1-3` import React Query/TanStack Router devtools.
- `frontend/src/routes/__root.tsx:12-13` render devtools không guard production.

Tác động:

- Tăng bundle production.
- Lộ route/query state nội bộ cho người dùng production.

Khuyến nghị:

- Render devtools chỉ khi `import.meta.env.DEV`.
- Kiểm tra bundle sau build.

---

### P1-06. Healthcheck hiện quá nông

Chứng cứ:

- `backend/app/api/routes/utils.py:33-35` `/health-check/` chỉ trả `True`.
- `compose.yml:114-118` healthcheck backend gọi endpoint này.

Tác động:

- Backend có thể healthy dù DB/Redis/optimization/worker hỏng.
- Orchestrator sẽ route traffic vào instance không dùng được.

Khuyến nghị:

- Tách `/live` và `/ready`.
- Readiness kiểm tra DB connection, Redis ping, optional dependencies theo feature flags.
- Worker có healthcheck riêng.

---

## 6. P1 - Database, migration và hiệu năng

### P1-07. DateTime default bị evaluate tại import time

Chứng cứ:

- `backend/app/domains/inventory/model.py:39` `default=datetime.now(timezone.utc)`.
- `backend/app/domains/inventory/model.py:77` tương tự cho `Order.created_at`.
- `backend/app/domains/vision/model.py:16` và `:25` tương tự.

Tác động:

- Tất cả row tạo bởi cùng process có thể nhận cùng timestamp import-time.
- Audit/order sorting/timeouts không chính xác.

Khuyến nghị:

- Dùng callable: `default=lambda: datetime.now(timezone.utc)`.
- Hoặc dùng server default `func.now()` tùy chiến lược.

---

### P1-08. TTL Redis và `expires_at` DB có thể lệch nhau

Chứng cứ:

- `backend/app/core/config.py:97-98` TTL cấu hình `INVENTORY_LOCK_TTL`.
- `backend/app/domains/inventory/model.py:10-11` `get_expire_time()` hard-code 15 phút.
- `backend/app/domains/inventory/service.py:179` Redis dùng settings TTL.

Tác động:

- Nếu đổi TTL env, Redis hết hạn một thời điểm, DB lock hết hạn thời điểm khác.
- UI countdown có thể sai.

Khuyến nghị:

- Tạo `expires_at` từ cùng TTL settings ở service layer, không hard-code model default.
- Lưu `ttl_seconds` hoặc `expires_at` rõ trong row.

---

### P1-09. Domain schema thiếu constraints quan trọng

Chứng cứ:

- `backend/app/domains/inventory/model.py:41-49` Inventory không khai báo unique `(store_id, product_id)` trong model.
- `travel_app_full_data.sql` có unique constraint trong dump, nhưng model/Alembic domain không quản lý.
- `backend/app/domains/inventory/model.py:31` price là integer default 0, không check non-negative.
- `backend/app/domains/inventory/model.py:46-48` stock/locked_stock không check non-negative.
- `backend/app/domains/culture/model.py:29` review rating không check 1-5.

Tác động:

- Data invalid có thể lọt vào nếu tạo bằng ORM/API.
- Dump và model có thể drift.

Khuyến nghị:

- Thêm constraints trong migration: check `stock >= 0`, `locked_stock >= 0`, `price >= 0`, rating range.
- Unique inventory store/product.
- Foreign key review -> place nếu dùng numeric place id hoặc place_id chuẩn.

---

### P1-10. `ILIKE '%keyword%'` xuất hiện nhiều nơi, cần index và query strategy

Chứng cứ:

- `backend/app/domains/inventory/service.py:64-73` Store/Product search dùng `ilike`.
- `backend/app/domains/culture/service.py:8-10` Place search dùng `ilike`.
- `backend/app/domains/agent/service.py:133-135` Agent product search dùng `ilike`.
- `backend/app/domains/planner/service.py:57-60` keyword filters dùng `ilike`.

Tác động:

- Với bảng lớn, scan chậm nếu không có trigram index.
- User gõ search nhiều có thể gây load DB cao.

Khuyến nghị:

- Migration tạo `pg_trgm` và GIN index cho `places.name`, `places.category`, `stores.name`, `stores.category`, `products.name`, `products.description`.
- Search API có min length, debounce server-side/rate limit.
- Xem xét `similarity`/`%` operator hoặc full-text search tiếng Việt có normalization.

---

### P1-11. PostGIS query cast sang Geography có thể không dùng index hiện có

Chứng cứ:

- `backend/app/domains/spatial/service.py:35`, `:40`, `:96-98` dùng `Place.geom.cast(Geography(...))`.
- `travel_app_full_data.sql` có `idx_places_geom` trên geometry, không thấy functional geography index trong model/migration.

Tác động:

- Query radius có thể chậm nếu planner không dùng geometry GiST index.
- Khi dataset lớn, nearby search và omnisearch degrade.

Khuyến nghị:

- Hoặc tạo functional index trên `geography(geom)`.
- Hoặc dùng geometry distance với SRID 4326 + transform phù hợp.
- Kiểm tra bằng `EXPLAIN ANALYZE` cho query thực tế.

---

### P1-12. Vector search cần migration index, không chỉ dump SQL

Chứng cứ:

- `backend/workers/ai_worker/vision_tasks.py:42-49` order by cosine distance.
- `backend/app/domains/vision/service.py:68-75` mix match order by cosine distance.
- Dump `travel_app_full_data.sql` có `idx_products_embedding` HNSW, nhưng Alembic domain không quản lý.

Tác động:

- DB dựng bằng Alembic sẽ thiếu HNSW index, vector search seq scan.
- Khi product embeddings tăng, scan/mix-match chậm và tốn CPU.

Khuyến nghị:

- Migration: `CREATE INDEX CONCURRENTLY idx_products_embedding_hnsw ON products USING hnsw (embedding vector_cosine_ops)`.
- Thêm index cho `virtual_closets.vector_embedding` nếu cần reverse search.
- Monitor query time.

---

### P1-13. Telemetry count live trên bảng lớn

Chứng cứ:

- `backend/app/api/routes/utils.py:37-49` count live `User`, `Place`, `Store`, `InventoryLock`.

Tác động:

- Dashboard có thể tạo load DB không cần thiết.
- Count trên bảng lớn không rẻ trong Postgres.

Khuyến nghị:

- Cache Redis TTL 1-5 phút.
- Với bảng rất lớn, dùng materialized view hoặc approximate counts.
- Endpoint telemetry nên yêu cầu admin/superuser.

---

### P1-14. `get_place_o2o_context` có N+1 query

Chứng cứ:

- `backend/app/domains/spatial/service.py:299-302` query stores.
- `backend/app/domains/spatial/service.py:306` query inventory cho từng store.
- `backend/app/domains/spatial/service.py:310` query products cho từng store.

Tác động:

- Một địa điểm có nhiều store sẽ tạo nhiều DB round trips.
- UI map click có thể chậm và gây DB load.

Khuyến nghị:

- Query join Store -> Inventory -> Product một lần.
- Group result trong Python.
- Limit số store/product rõ ràng.

---

### P1-15. Planner có N+1 query và budget semantics sai

Chứng cứ:

- `backend/app/domains/planner/service.py:71-73` query inventory từng store.
- `backend/app/domains/planner/service.py:80` `_get_store_avg_price` từng store.
- `backend/app/domains/planner/service.py:83-84` budget so với average store price.
- `backend/app/domains/planner/service.py:111-115` enrich products từng store.

Tác động:

- Planner chậm khi raw candidates nhiều.
- Budget của user không thật sự là giỏ hàng hay lộ trình; chỉ là avg price store.
- Store không có inventory có avg 0 nên dễ được ưu tiên vì rẻ.

Khuyến nghị:

- Query aggregate inventory/product theo store trong một statement.
- Budget phải dựa trên product match hoặc total route cart estimate.
- Store không có product không nên được ưu tiên vì price 0.

---

## 7. P1 - Backend domain correctness

### P1-16. `compare_product_prices` không so sánh giá thật theo store

Chứng cứ:

- `backend/app/domains/inventory/model.py:31` price nằm ở Product, không nằm ở Inventory.
- `backend/app/domains/inventory/service.py:125` mọi store trả `price: product.price`.

Tác động:

- "So sánh giá" không thể khác nhau giữa cửa hàng.
- UI có thể hiển thị tính năng nhưng giá trị nghiệp vụ sai.

Khuyến nghị:

- Nếu giá khác theo store, thêm `Inventory.price_override` hoặc bảng `StoreProduct`.
- Nếu không khác, đổi tính năng thành "So sánh tồn kho/địa điểm", không gọi là price compare.

---

### P1-17. Order code random 6 chữ số không retry collision

Chứng cứ:

- `backend/app/domains/inventory/service.py:236-238` sinh `AE` + 6 chữ số.
- `backend/app/domains/inventory/model.py:76` order_code unique index.
- `backend/app/domains/inventory/service.py:305` commit không catch IntegrityError/retry.

Tác động:

- Khi số đơn tăng, collision gây 500.

Khuyến nghị:

- Dùng sequence/time-sortable id hoặc retry loop khi unique violation.
- Order code nên đủ entropy, ví dụ `AEYYYYMMDD-XXXXXX`.

---

### P1-18. Endpoint `/inventory/trigger-release` là mutation không auth

Chứng cứ:

- `backend/app/domains/inventory/router.py:44-48` không có current user/superuser dependency.

Tác động:

- Client public có thể trigger sweep bất kỳ lúc nào.
- Có thể tạo load DB hoặc race với checkout nếu logic chưa chặt.

Khuyến nghị:

- Xóa endpoint public.
- Nếu cần admin action, yêu cầu superuser.
- Sweep nên do worker/beat.

---

### P1-19. Mix-match closet không kiểm tra ownership

Chứng cứ:

- `backend/app/domains/vision/router.py:85-98` `/closet/{item_id}/matches` không inject current user.
- `backend/app/domains/vision/service.py:58-60` lấy closet item chỉ theo id.

Tác động:

- User có thể query item closet của user khác nếu đoán id.
- Rò metadata ảnh cá nhân và match behavior.

Khuyến nghị:

- Route phải yêu cầu `current_user`.
- Query `VirtualCloset.id == item_id AND user_id == current_user.id`.
- Nếu không thuộc user, trả 404.

---

### P1-20. Upload file có rủi ro ghi đè và lưu local không bền vững

Chứng cứ:

- `backend/app/domains/vision/router.py:35-37` dùng `os.path.basename(file.filename)` và ghi vào folder local.
- `backend/app/domains/vision/router.py:46` upload scan vào `uploads/scans/`.
- `backend/app/domains/vision/router.py:75` upload closet vào `uploads/closet/`.
- Không thấy `StaticFiles` mount trong `backend/app/main.py`.

Tác động:

- Hai user upload cùng filename sẽ ghi đè.
- Khi scale nhiều API replicas, worker replica khác không thấy file.
- File mất khi container recreate nếu không mount volume.
- Frontend đang load ảnh `/uploads/...` nhưng backend không serve static.

Khuyến nghị:

- Generate filename bằng UUID + extension đã kiểm chứng.
- Dùng object storage/S3/MinIO hoặc shared volume rõ ràng.
- Mount static route an toàn hoặc trả signed URL.
- Thêm cleanup policy.

---

### P1-21. Upload validation tin vào MIME header, chưa verify nội dung

Chứng cứ:

- `backend/app/domains/vision/router.py:19-23` kiểm `file.content_type`.
- `backend/app/domains/vision/router.py:25-31` đọc toàn bộ file vào memory.
- `backend/workers/ai_worker/vision_tasks.py:28` `Image.open(image_path)`.

Tác động:

- File giả MIME có thể lọt tới PIL.
- Ảnh decompression bomb có thể tốn RAM/CPU.
- Đọc toàn bộ file vào RAM không phù hợp khi tăng size/concurrency.

Khuyến nghị:

- Verify bằng PIL trong safe mode, `Image.verify()`, set max pixels.
- Stream upload nếu tăng size.
- Normalize ảnh sang định dạng nội bộ.
- Scan malware nếu production.

---

### P1-22. Vision task failure không ghi status failed vào DB

Chứng cứ:

- `backend/workers/ai_worker/vision_tasks.py:75-77` catch exception và return dict, không update task row.
- `backend/app/domains/vision/router.py:58-63` polling tự đổi failed sau 30 giây nếu vẫn processing.

Tác động:

- Failure reason thật bị mất.
- Task có thể nằm processing tới khi user poll.
- Nếu không poll, DB không phản ánh trạng thái thật.

Khuyến nghị:

- Worker catch exception phải update row status `failed` và error payload.
- Router polling không nên là nơi quyết định failure state.

---

### P1-23. Agent endpoint public có thể làm phát sinh chi phí Gemini

Chứng cứ:

- `backend/app/domains/agent/router.py:8-13` không auth.
- `backend/app/domains/agent/service.py:218` gọi Gemini 2.5 Flash API.
- `backend/app/domains/agent/service.py:228-232` loop tối đa 5 lần.

Tác động:

- Một request agent có thể gọi Gemini nhiều lần.
- Không có quota/rate limit/user attribution.
- Có thể bị spam tốn tiền.

Khuyến nghị:

- Require auth.
- Rate limit theo user/IP.
- Log token usage/cost nếu API trả usage metadata.
- Guard loop/tool calls.

---

### P1-24. Gemini API key đưa trong URL và lỗi trả raw về user

Chứng cứ:

- `backend/app/domains/agent/service.py:218` key nằm trong query string.
- `backend/app/domains/agent/service.py:241-243` trả `res.text` vào `bot_answer`.
- `backend/app/domains/culture/service.py:26` cũng đưa key trong URL.

Tác động:

- API key có thể xuất hiện trong logs/proxy traces.
- Lỗi upstream raw có thể lộ thông tin không cần thiết.

Khuyến nghị:

- Dùng SDK hoặc header nếu provider hỗ trợ.
- Sanitize error trước khi trả client.
- Không log URL chứa key.

---

### P1-25. `test_gemini.py` in API key ra stdout

Chứng cứ:

- `test_gemini.py:7-8` đọc và print `GEMINI_API_KEY`.
- `test_gemini.py:15-16` print response text.

Tác động:

- Dễ lộ secret trong terminal, CI logs, screen recordings.

Khuyến nghị:

- Xóa print key hoặc chỉ print masked key.
- Đưa script vào `scripts/` và đánh dấu local-only.
- Không commit script test gọi external API nếu không cần.

---

### P1-26. Agent không dùng tọa độ request

Chứng cứ:

- `backend/app/domains/agent/schema.py:4-7` request có `current_lat/current_lon`.
- `backend/app/domains/agent/service.py:224-226` history chỉ đưa `request.query`.

Tác động:

- Agent không biết vị trí hiện tại dù frontend/schema đã chuẩn bị.
- Tool `create_itinerary` bắt buộc lat/lon nhưng model phải tự suy luận từ text.

Khuyến nghị:

- Inject tọa độ vào system/user context nếu có.
- Nếu thiếu tọa độ khi cần itinerary, agent hỏi lại user.

---

### P1-27. Culture review thiếu auth, validation, moderation

Chứng cứ:

- `backend/app/domains/culture/router.py:22-27` post review public.
- `backend/app/domains/culture/schema.py:17-20` không có rating range/text length.
- `frontend/src/routes/_layout/culture.tsx:178-182` client gửi `author_name` tự nhập.

Tác động:

- Spam review, rating ngoài 1-5, giả mạo tên.
- Không có audit trail user_id.
- Không có moderation/report.

Khuyến nghị:

- Require auth hoặc CAPTCHA/rate limit cho public review.
- Rating `Field(ge=1, le=5)`, text max length.
- Lưu `user_id`, `status=pending/approved/rejected`.
- Moderation workflow cho admin.

---

### P1-28. Culture story gọi LLM mỗi lần mở, chưa cache

Chứng cứ:

- `backend/app/domains/culture/service.py:12-43` gọi Gemini trong mỗi request story nếu có API key.
- Không thấy cache Redis/DB cho `ai_story`.

Tác động:

- Click nhiều tốn chi phí và latency.
- Nội dung cùng địa điểm có thể thay đổi không kiểm soát.

Khuyến nghị:

- Cache story theo `place_id`, language, prompt version.
- Admin có thể regenerate.
- Timeout/fallback có metric.

---

### P1-29. Spatial route fallback trả distance 0

Chứng cứ:

- `backend/app/domains/spatial/service.py:267-275` khi OSRM lỗi trả `total_distance_meters: 0.0`.

Tác động:

- UI hiển thị lộ trình có khoảng cách 0 dù có nhiều điểm.
- Metrics sai nghiêm trọng.

Khuyến nghị:

- Fallback tính Haversine từ user qua các điểm.
- Gắn `routing_fallback_used=true` trong schema.
- UI phải hiển thị cảnh báo rõ.

---

### P1-30. Planner fallback cũng trả metrics 0

Chứng cứ:

- `backend/app/domains/planner/service.py:243-248` fallback khi optimization lỗi set `total_price: 0`, `total_distance_km: 0`.

Tác động:

- Khi optimization chết, UI vẫn có route nhưng metrics sai.
- Người dùng không biết kết quả chỉ là fallback rating-sort.

Khuyến nghị:

- Tính fallback distance/price từ raw candidates.
- Trả `routing_fallback_used=true` và `optimization_fallback_reason`.

---

### P1-31. Optimization service dùng public OSRM hard-code

Chứng cứ:

- `backend/optimization_service/core/algorithms/tsp_solver.py:21` `OSRM_BASE_URL = "http://router.project-osrm.org"`.
- `backend/app/domains/spatial/service.py:236` cũng gọi public OSRM trip API.

Tác động:

- Public demo server có rate limit và không phù hợp production.
- Tính năng route bị phụ thuộc internet và service bên ngoài.

Khuyến nghị:

- Dùng `OSRM_BASE_URL` env.
- Deploy private OSRM hoặc dùng provider có SLA.
- Cache route/matrix theo coordinate hash.

---

### P1-32. Optimization service dùng sync httpx trong request path

Chứng cứ:

- `backend/optimization_service/core/algorithms/tsp_solver.py:81-82` `httpx.Client`.
- `backend/optimization_service/core/algorithms/tsp_solver.py:124-125` `httpx.Client`.
- Endpoint `backend/optimization_service/api/v1/optimize.py:19` là sync def.

Tác động:

- Mỗi request giữ worker thread trong lúc chờ OSRM.
- Nếu OSRM chậm, throughput giảm mạnh.

Khuyến nghị:

- Dùng async endpoint + `httpx.AsyncClient`.
- Hoặc chạy optimization service với worker/concurrency riêng và queue.
- Thêm circuit breaker.

---

### P1-33. TSP fallback distance không tính đoạn từ user tới stop đầu tiên

Chứng cứ:

- `backend/optimization_service/core/algorithms/tsp_solver.py:216-239` tính distance giữa các `ordered_shops` liên tiếp, không bao gồm origin user.
- OSRM path ở `run_tsp_pipeline` lại có origin user ở `ordered_coords`.

Tác động:

- Metrics fallback thấp hơn thực tế.
- Fallback và OSRM metrics không cùng nghĩa.

Khuyến nghị:

- `calculate_total_metrics` nhận `user_lat/user_lon`.
- Tính origin -> stop1 -> stop2...

---

## 8. P2 - Frontend/API contract và UX

### P2-01. API base fallback về localhost trong production

Chứng cứ:

- `frontend/src/main.tsx:16` `OpenAPI.BASE = ... PROD ? "http://localhost:8000" : ""`.
- `frontend/src/client/aegis-api.ts:8` axios client cũng fallback như vậy.
- `frontend/src/routes/_layout/vision.tsx:432` và `:494` cũng fallback localhost khi render image.

Tác động:

- Nếu quên `VITE_API_URL`, browser user production gọi chính máy user.
- Lỗi network khó hiểu.

Khuyến nghị:

- Production build phải fail nếu thiếu `VITE_API_URL`.
- Hoặc dùng relative `/api` qua Nginx reverse proxy.
- Một config API duy nhất, không trùng OpenAPI client và axios client.

---

### P2-02. Token lưu trong localStorage

Chứng cứ:

- `frontend/src/main.tsx:17-19`.
- `frontend/src/client/aegis-api.ts:15-20`.
- `frontend/src/hooks/useAuth.ts` theo grep cũng dùng localStorage.

Tác động:

- XSS có thể lấy access token.
- Không có refresh token rotation.

Khuyến nghị:

- Ưu tiên httpOnly secure cookie nếu phù hợp.
- Nếu giữ bearer token, harden CSP, sanitize, short TTL, refresh flow.

---

### P2-03. Nhiều catch im lặng làm mất tín hiệu lỗi

Chứng cứ:

- `frontend/src/routes/_layout/inventory.tsx:106-110`, `:120-122`.
- `frontend/src/routes/_layout/vision.tsx:60-64`, `:89-94`, `:107-113`, `:123-128`.
- `frontend/src/routes/_layout/culture.tsx:146-148`, `:166-168`.

Tác động:

- User không biết lỗi do auth, network, server, validation hay data empty.
- Debug khó hơn vì không có toast/log chuẩn.

Khuyến nghị:

- Centralize API error handling.
- Hiển thị toast/message có context.
- Log lỗi có correlation id ở backend.

---

### P2-04. Culture page có số liệu và nội dung hard-coded

Chứng cứ:

- `frontend/src/routes/_layout/culture.tsx:369-391` stat `48`, `120+`, `2000+`, `1M+`.
- `frontend/src/routes/_layout/culture.tsx:456-486` visitor info hard-coded.
- `frontend/src/routes/_layout/culture.tsx:507-525` product suggestions hard-coded.

Tác động:

- UI nhìn production nhưng dữ liệu không đáng tin.
- Dễ demo sai sự thật.

Khuyến nghị:

- Gắn label "demo" nếu giữ hard-code.
- Hoặc tạo endpoint content/culture metadata và O2O recommendations thật.

---

### P2-05. Frontend gọi Wikipedia trực tiếp

Chứng cứ:

- `frontend/src/routes/_layout/culture.tsx:205-220` gọi `https://vi.wikipedia.org/w/api.php`.

Tác động:

- Phụ thuộc CORS/internet/client network.
- Không cache được hiệu quả.
- Rủi ro rate limit và privacy: browser user gọi bên thứ ba trực tiếp.

Khuyến nghị:

- Backend proxy/cache ảnh Wikipedia.
- Cache URL ảnh vào DB hoặc Redis.
- Có fallback ảnh theo category/place.

---

### P2-06. `handleTrendingClick` dùng state cũ

Chứng cứ:

- `frontend/src/routes/_layout/culture.tsx:192-195` setSearchQuery rồi `setTimeout(() => handleSearch(), 50)`.
- `handleSearch` đọc `searchQuery` từ closure.

Tác động:

- Có thể search query cũ hoặc rỗng tùy timing.

Khuyến nghị:

- `handleSearch(queryOverride?: string)`.
- Gọi trực tiếp `CultureAPI.searchPlaces(query)`.

---

### P2-07. Object URL không revoke

Chứng cứ:

- `frontend/src/routes/_layout/vision.tsx:148` và `:163` dùng `URL.createObjectURL(file)`.
- Không thấy `URL.revokeObjectURL`.

Tác động:

- Upload/preview nhiều ảnh làm rò memory browser.

Khuyến nghị:

- Revoke URL khi file đổi/unmount.

---

### P2-08. Vision UI có button không làm gì

Chứng cứ:

- `frontend/src/routes/_layout/vision.tsx:361-363` button "Thêm tủ đồ" không có `onClick`.

Tác động:

- Người dùng tưởng thêm sản phẩm vào closet/cart nhưng không có hành động.

Khuyến nghị:

- Gắn action thật hoặc bỏ button.
- Nếu thêm vào closet cần upload ảnh của user, không thể thêm product image thay closet item nếu business không định nghĩa.

---

### P2-09. Itinerary gọi sai endpoint mix-match

Chứng cứ:

- `frontend/src/routes/_layout/itinerary.tsx:151-158` gọi `VisionAPI.getMixMatch(productId)`.
- Backend endpoint `backend/app/domains/vision/router.py:85-98` nhận `closet/{item_id}/matches`, tức closet item id.

Tác động:

- Product id bị hiểu nhầm là closet item id.
- Kết quả sai hoặc 404.

Khuyến nghị:

- Nếu muốn match product-to-product, tạo endpoint riêng `/vision/products/{product_id}/matches`.
- Nếu muốn closet-to-product, UI phải chọn closet item trước.

---

### P2-10. Itinerary gọi Culture story bằng `storeId`

Chứng cứ:

- `frontend/src/routes/_layout/itinerary.tsx:128-137` `CultureAPI.getPlaceStory(storeId)`.
- Backend `culture/places/{id}/story` dùng Place.id, không phải Store.store_id.

Tác động:

- Drawer văn hóa có thể hiển thị sai địa điểm hoặc 404.

Khuyến nghị:

- Planner response cần trả `place_id`/`place_db_id` nếu muốn story.
- Hoặc tạo store culture endpoint riêng.

---

### P2-11. Inventory cart chỉ hiển thị Product ID, không có checkout/cancel

Chứng cứ:

- `frontend/src/routes/_layout/inventory.tsx:392-400` cart item hiển thị `Product #{lock.product_id}`, qty, lock id.
- Không có nút release/cancel lock.
- Checkout mở ngay sau reserve, không mở từ cart item.

Tác động:

- User không biết đang giữ sản phẩm nào.
- Không thể hủy giữ hàng chủ động.
- Nếu đóng checkout, khó quay lại thanh toán lock đó.

Khuyến nghị:

- Lock response trả product/store summary hoặc frontend fetch detail.
- Thêm cancel lock endpoint.
- Cart item có CTA checkout.

---

### P2-12. Inventory không refresh locks theo TTL

Chứng cứ:

- `frontend/src/routes/_layout/inventory.tsx:113` chỉ load locks khi mount.
- Countdown chạy local nhưng không refetch khi lock expire.

Tác động:

- Cart có thể hiển thị lock hết hạn cho tới khi reload.

Khuyến nghị:

- Refetch locks sau khi countdown về 0.
- Hoặc polling nhẹ khi cart mở.

---

### P2-13. Store/product images dùng random external fallback

Chứng cứ:

- `frontend/src/routes/_layout/inventory.tsx:23-31` hard-coded Unsplash images.
- `frontend/src/routes/_layout/inventory.tsx:221` store image theo index.
- `frontend/src/routes/_layout/inventory.tsx:256-263` product fallback theo index.

Tác động:

- Store thật có thể hiển thị ảnh không liên quan.
- CDN bên ngoài ảnh hưởng privacy/performance.

Khuyến nghị:

- Backend trả image_url/category image rõ.
- Có asset fallback local theo category.

---

### P2-14. Layout search box chưa có chức năng

Chứng cứ:

- `frontend/src/routes/_layout.tsx:248-260` input "Query system..." không có state/search handler.

Tác động:

- UI gây kỳ vọng sai.

Khuyến nghị:

- Gắn global command/search hoặc ẩn cho tới khi có tính năng.

---

### P2-15. Notifications bell chưa có dữ liệu

Chứng cứ:

- `frontend/src/routes/_layout.tsx:263-266` Bell có dot pulse hard-coded.

Tác động:

- User tưởng có thông báo chưa đọc.

Khuyến nghị:

- Gắn notification API hoặc bỏ badge.

---

### P2-16. Geolocation input thiếu validation UX

Chứng cứ:

- `frontend/src/routes/_layout/spatial.tsx` và `itinerary.tsx` cho nhập lat/lon/radius thủ công.
- Backend spatial router nhận radius không có schema `ge/le`.

Tác động:

- User nhập radius cực lớn hoặc lat/lon ngoài phạm vi gây query nặng/lỗi.

Khuyến nghị:

- Validate lat `[-90,90]`, lon `[-180,180]`, radius max.
- Backend cũng phải enforce.

---

### P2-17. Frontend auto-fetch nearby khi input đổi có thể hammer API

Chứng cứ:

- `frontend/src/routes/_layout/spatial.tsx` useEffect fetch nearby theo `lat`, `lon`, `radius`.
- Input debounce 300ms cập nhật lat/lon/radius.

Tác động:

- Khi user chỉnh số, API bị gọi liên tục.

Khuyến nghị:

- Có nút Apply/Search.
- Hoặc debounce dài hơn + cancel request.
- Backend rate limit.

---

### P2-18. Type `any` lan rộng ở map pages

Chứng cứ:

- Gần như toàn bộ `frontend/src/routes/_layout/spatial.tsx` dùng `any` cho map refs, results, clusters, nodes.
- `frontend/src/routes/_layout/vision.tsx:347` dùng `prod: any`.
- `frontend/src/routes/_layout.tsx:209` event `any`.

Tác động:

- TypeScript không bắt được contract mismatch.
- Build fail hiện tại là triệu chứng của typing lỏng.

Khuyến nghị:

- Tách DTO từ backend OpenAPI hoặc manual types.
- Không để `detected_objects` là unknown/any khi render.

---

## 9. P2 - Security, privacy và abuse prevention

### P2-19. Không thấy rate limiting toàn cục

Chứng cứ:

- Không thấy middleware rate limit trong `backend/app/main.py`.
- Endpoint agent/vision/planner/search đều có thể gọi liên tục.

Tác động:

- Abuse dễ dàng.
- DDoS tầng app bằng LLM/AI/route/upload.

Khuyến nghị:

- Dùng Redis-based rate limit theo IP/user/endpoint.
- Đặc biệt: `/agent/chat`, `/vision/scan`, `/vision/closet`, `/planner/generate`, `/spatial/route-plan`, review post.

---

### P2-20. Không có CSRF strategy nếu chuyển sang cookie

Hiện tại dùng bearer localStorage nên CSRF ít liên quan hơn, nhưng nếu cải thiện sang httpOnly cookie cần:

- SameSite strategy.
- CSRF token cho mutation.
- CORS credentials cấu hình chặt.

---

### P2-21. CORS backend phụ thuộc env nhưng chưa có production guard rõ

Chứng cứ:

- `backend/app/main.py:23-31` add CORS nếu `settings.all_cors_origins`.
- `backend/app/core/config.py:44-49` luôn thêm `FRONTEND_HOST`.

Tác động:

- Nếu env sai, có thể mở origin không mong muốn hoặc block production frontend.

Khuyến nghị:

- Validate `BACKEND_CORS_ORIGINS` trong production.
- Không dùng wildcard với credentials.

---

### P2-22. Upload ảnh cá nhân chưa có privacy model

Chứng cứ:

- VirtualCloset lưu `user_id`, `image_path`, vector embedding.
- Không thấy delete closet endpoint.
- Không thấy data retention policy.

Tác động:

- Ảnh người dùng và embedding là dữ liệu nhạy cảm.
- User không thể xóa dữ liệu cá nhân.

Khuyến nghị:

- Thêm delete closet item.
- Retention policy.
- Privacy notice.
- Không expose image path raw nếu không có signed URL.

---

### P2-23. Không có audit log cho order/payment/lock

Chứng cứ:

- Models hiện không có event log.
- Lock/order thay đổi trực tiếp trong service.

Tác động:

- Khó điều tra tranh chấp tồn kho/thanh toán.

Khuyến nghị:

- Thêm `inventory_events` hoặc `order_events`.
- Ghi actor, action, before/after, correlation id.

---

## 10. P2 - AI/ML reliability

### P2-24. CLIP model load runtime có thể cần internet/cache

Chứng cứ:

- `backend/workers/ai_worker/vision_tasks.py:14` `SentenceTransformer('clip-ViT-B-32')`.

Tác động:

- Lần boot đầu có thể tải model từ internet.
- Production network restricted sẽ fail startup hoặc xử lý scan.

Khuyến nghị:

- Bake model vào image hoặc mount model cache.
- Startup healthcheck worker xác nhận model loaded.

---

### P2-25. Không có versioning embedding/model

Chứng cứ:

- `Product.embedding` và `VirtualCloset.vector_embedding` chỉ lưu vector.
- Không thấy `embedding_model`, `embedding_version`, `embedded_at`.

Tác động:

- Khi đổi model, vector cũ/mới trộn lẫn làm similarity sai.
- Không biết item nào cần re-embed.

Khuyến nghị:

- Thêm metadata embedding.
- Batch reindex pipeline.

---

### P2-26. Product embeddings generation là script riêng, không nằm trong pipeline dữ liệu

Chứng cứ:

- `scripts/sync_product_vectors.py` tồn tại riêng.
- Không thấy cron/job trong compose/CI để đảm bảo product mới có embedding.

Tác động:

- Product mới có thể không xuất hiện trong scan/mix-match.

Khuyến nghị:

- Khi tạo/cập nhật product image, enqueue embedding job.
- Admin UI hiển thị embedding status.

---

### P2-27. Agent tool calling thiếu guardrail và structured observability

Chứng cứ:

- `backend/app/domains/agent/service.py:7-83` tool declarations.
- `backend/app/domains/agent/service.py:228-290` loop tool calls tối đa 5.
- `backend/app/domains/agent/service.py:273` internal action string lưu raw args.

Tác động:

- Prompt injection có thể ép gọi tool không mong muốn trong phạm vi đã khai báo.
- Args có thể chứa dữ liệu nhạy cảm và được trả về frontend trong `internal_actions`.

Khuyến nghị:

- Validate tool args bằng Pydantic trước khi execute.
- Redact internal actions trước khi trả client.
- Audit log tool call server-side.
- Agent phải có policy "không thực hiện hành động mua/lock/payment tự động".

---

## 11. P2 - Testing và CI

### P2-28. Test suite hiện chủ yếu là template legacy

Chứng cứ:

- `backend/tests/api/routes/test_items.py`, `test_users.py`, `test_login.py` theo template.
- Không thấy tests cho `inventory`, `vision`, `spatial`, `culture`, `planner`, `agent`.

Tác động:

- Những lỗi domain chính không được CI bắt.

Khuyến nghị:

- Thêm unit tests cho service logic.
- Thêm integration tests với Postgres/Redis test container.
- Mock Gemini/OSRM/Open-Meteo.

---

### P2-29. Frontend Playwright chưa phủ domain mới

Chứng cứ:

- `frontend/tests` hiện có login/signup/admin/items/settings/reset-password.
- Không thấy tests cho culture/spatial/inventory/vision/itinerary.

Tác động:

- Các page O2O có thể broken mà CI vẫn xanh.

Khuyến nghị:

- Playwright smoke cho từng route O2O.
- Mock API responses để test empty/loading/error/success.
- Test checkout copy không nói paid khi chưa paid.

---

### P2-30. Lint command frontend có `--write --unsafe`

Chứng cứ:

- `frontend/package.json:9` `"lint": "biome check --write --unsafe ..."`

Tác động:

- Chạy lint trong CI hoặc audit có thể sửa code thay vì chỉ kiểm tra.
- Khó phân biệt lỗi thật và formatter churn.

Khuyến nghị:

- Tách `lint` read-only và `format` write.
- Ví dụ `lint: biome check .`, `format: biome check --write .`.

---

### P2-31. Ruff backend không chạy được trong sandbox do dependency download

Kết quả:

- `uv run --package app ruff check ...` tạo venv rồi cố tải dependency từ PyPI.
- Fail DNS khi tải `pygments`.

Tác động:

- CI/offline environment có thể fail nếu không cache dependency.
- Audit này chưa thể kết luận backend lint pass.

Khuyến nghị:

- CI cache uv.
- Prebuild dev environment.
- Có target lint không kéo toàn bộ heavy AI deps nếu chỉ cần ruff.

---

## 12. P3 - Chất lượng code và maintainability

### P3-01. Trộn SQLModel legacy và SQLAlchemy Base domain

Chứng cứ:

- `backend/app/models.py` dùng SQLModel.
- Domain mới dùng SQLAlchemy Base.

Tác động:

- Metadata/migration/session patterns bị chia đôi.
- Developer mới khó biết pattern chuẩn.

Khuyến nghị:

- Chọn một style cho domain mới.
- Nếu giữ cả hai, document rõ và Alembic include cả hai metadata.

---

### P3-02. Service layer có import nội hàm quá nhiều

Chứng cứ:

- `backend/app/domains/inventory/service.py:16-17`.
- `backend/app/domains/spatial/service.py:278-279`.
- `backend/app/domains/agent/service.py` nhiều import trong function.

Tác động:

- Khó phát hiện dependency graph.
- Có thể che lỗi import tới runtime.

Khuyến nghị:

- Tách module dependency rõ.
- Chỉ import nội hàm khi tránh circular thật sự, có comment.

---

### P3-03. Bare `except` xuất hiện nhiều

Chứng cứ:

- `backend/app/domains/agent/service.py:100`, `:127`.
- `backend/app/domains/culture/service.py:39-41`.
- `backend/app/domains/spatial/service.py:217-218`.

Tác động:

- Nuốt lỗi thật, khó observability.

Khuyến nghị:

- Catch exception cụ thể.
- Log warning/error với context.
- Trả error state có cấu trúc.

---

### P3-04. Logging dùng print trong production-like paths

Chứng cứ:

- `backend/app/domains/agent/service.py:86` print tool execution.
- `backend/create_domain_tables.py:7-9` print.
- Scripts khác print nhiều.

Tác động:

- Logs không structured.
- Có thể lộ args người dùng.

Khuyến nghị:

- Dùng logger.
- Redact PII/secret.

---

### P3-05. Copy UI text trộn tiếng Anh/tiếng Việt

Chứng cứ:

- Inventory: "Order Confirmed", "Shipping Details", "Place Order via VietQR".
- Vision: "Start AI Scan", "Virtual Closet".
- Itinerary: tiếng Việt nhiều phần.

Tác động:

- UX thiếu nhất quán.

Khuyến nghị:

- i18n layer hoặc copy deck thống nhất.
- Với thị trường Việt Nam, ưu tiên tiếng Việt cho luồng checkout/payment.

---

### P3-06. Thiết kế CSS/theme đang quá phụ thuộc hiệu ứng nặng

Chứng cứ:

- Layout/culture/spatial/vision có nhiều animation, blur, gradient, pulse.

Tác động:

- Có thể giảm FPS trên mobile/laptop yếu.
- Map và image-heavy pages càng nặng.

Khuyến nghị:

- Respect `prefers-reduced-motion`.
- Giảm animation liên tục.
- Performance budget cho route map/vision.

---

## 13. Chức năng còn thiếu để thành O2O production

### 13.1. Payment và order management

Cần có:

- Payment provider thật: PayOS, VNPAY, MoMo hoặc ngân hàng có webhook.
- Payment webhook: verify signature, idempotency, replay protection.
- Bảng `payments`.
- Order state machine: `DRAFT`, `PENDING_PAYMENT`, `PAID`, `PAYMENT_FAILED`, `CANCELLED`, `EXPIRED`, `FULFILLING`, `READY_FOR_PICKUP`, `SHIPPED`, `COMPLETED`, `REFUNDED`.
- Order history cho user.
- Admin order dashboard.
- Cancel/refund flow.
- Payment timeout job.
- Receipt/invoice.
- Audit trail order/payment.

Hiện trạng:

- Có order table đơn giản.
- Có VietQR URL demo.
- Chưa có webhook/status thật.

Ưu tiên: P0.

---

### 13.2. Inventory và reservation

Cần có:

- Store-level reservation.
- Lock id gắn vào checkout.
- Cancel lock.
- Expire lock tự động.
- Reconcile job giữa Redis và Postgres.
- Admin cập nhật stock.
- Low-stock alert.
- Inventory event log.
- Unique constraint `(store_id, product_id)`.
- API list lock kèm product/store detail.
- Test race condition.

Hiện trạng:

- Lock theo product global.
- Không có store_id trong LockRequest.
- Không có cancel lock.
- Sweep phụ thuộc worker chưa chạy trong compose chính.

Ưu tiên: P0.

---

### 13.3. Catalog và merchant/store management

Cần có:

- CRUD store.
- CRUD product.
- Upload product image.
- Price per store hoặc chính sách giá rõ.
- Store owner/merchant role.
- Store opening hours.
- Store geofence/service radius.
- Product categories/tags chuẩn hóa.
- Search facets: price, category, distance, availability.

Hiện trạng:

- Product/store chủ yếu từ seed/dump.
- Không có admin domain UI/API rõ cho catalog O2O.

Ưu tiên: P1.

---

### 13.4. Route planner production

Cần có:

- Private OSRM hoặc routing provider SLA.
- Cache matrix/route.
- Route constraints: opening hours, max walking/driving time, user preference, budget, category.
- Return fallback reason.
- Accurate distance/time metrics.
- Avoid stores out of stock.
- Product-aware route: tìm nơi bán keyword product, không chỉ store name/category.

Hiện trạng:

- Gọi public OSRM.
- Planner keyword filter chỉ trên store name/category.
- Metrics fallback = 0.

Ưu tiên: P1.

---

### 13.5. Culture/heritage content

Cần có:

- Backend cache story.
- Content provenance/source.
- Image cache/proxy.
- Review auth/moderation.
- Place detail model: opening hours, ticket price, rules, images.
- O2O recommendations thật quanh place.

Hiện trạng:

- Story gọi Gemini mỗi lần.
- Wikipedia gọi từ frontend.
- Nhiều info hard-coded.

Ưu tiên: P2.

---

### 13.6. AI agent

Cần có:

- Auth/quota/rate limit.
- Conversation history optional theo user.
- Tool arg validation.
- Tool permissioning.
- Agent observability: tool calls, latency, failures, token/cost.
- Prompt injection guardrails.
- Refusal/safety behavior.
- No raw provider errors to client.

Hiện trạng:

- Public endpoint.
- Tool calls trực tiếp DB/API.
- Raw args trả về frontend.

Ưu tiên: P1.

---

### 13.7. Vision/virtual closet

Cần có:

- Real queue worker.
- Shared object storage.
- Image validation/sniffing.
- Model cache.
- Embedding versioning.
- Delete closet item.
- Ownership check.
- Product-to-product match endpoint nếu UI cần.
- Status/retry UI.

Hiện trạng:

- Thread trong API.
- Local upload path.
- No ownership check cho matches.
- Frontend gọi sai endpoint ở Itinerary.

Ưu tiên: P0/P1.

---

### 13.8. Observability

Cần có:

- Structured logging.
- Request id/correlation id.
- Metrics: request latency, error rate, DB query latency, Redis errors, Celery queue depth, worker memory, Gemini cost, OSRM failure rate.
- Sentry configured production.
- Alerting.
- Dashboard admin thật.

Hiện trạng:

- Sentry optional.
- Healthcheck shallow.
- Telemetry count live.

Ưu tiên: P1.

---

### 13.9. Security/privacy/compliance

Cần có:

- Threat model.
- Rate limit.
- CSP.
- Secure token storage strategy.
- Data retention for uploads.
- User data deletion.
- Secret scanning.
- Dependency scanning.
- Audit log.
- Payment compliance depending provider.

Hiện trạng:

- localStorage token.
- Public expensive endpoints.
- Image uploads personal but no deletion.

Ưu tiên: P1.

---

### 13.10. CI/CD

Cần có:

- Backend lint/test.
- Frontend typecheck/build.
- Playwright smoke for new domains.
- Docker build test.
- Migration test on empty DB.
- Seed test.
- Contract test OpenAPI.
- Dependency cache.

Hiện trạng:

- Frontend build fail.
- Domain tests thiếu.
- Backend lint chưa xác nhận được trong sandbox do dependency download.

Ưu tiên: P0/P1.

---

## 14. Backlog sửa lỗi theo sprint

### Sprint 0: Chặn máu release

1. Sửa TypeScript build errors.
2. Sửa Docker Compose đầy đủ service.
3. Tách API và worker, enqueue Celery thật.
4. Thêm env config cho Redis/RabbitMQ/Optimization/OSRM.
5. Alembic quản trị domain schema.
6. Payment UI đổi thành pending payment.
7. `create_order` yêu cầu active lock.
8. Lock theo store/product/quantity.
9. Auth/rate limit cho agent/scan/planner/review.
10. Static/object storage cho upload.

### Sprint 1: Nghiệp vụ O2O thật

1. Payment gateway + webhook.
2. Order state machine.
3. Cancel lock/order.
4. Inventory event log.
5. Admin order/inventory dashboard.
6. Product/store CRUD.
7. Price semantics per store.
8. Tests race condition lock.
9. Tests payment webhook.
10. Tests order lifecycle.

### Sprint 2: AI và route ổn định

1. Private OSRM/env URL/cache.
2. Planner fallback metrics đúng.
3. Product-aware planner search.
4. Agent quota and tool validation.
5. Story cache.
6. Embedding versioning.
7. Product embedding job.
8. Vision ownership check.
9. Model cache in worker image.
10. Observability dashboard.

### Sprint 3: UX và trust

1. Cart detail/cancel/checkout from cart.
2. Order history.
3. Payment status screen.
4. Review moderation UI.
5. Replace hard-coded culture stats/products.
6. Consistent Vietnamese copy.
7. Error states for every domain page.
8. Responsive/mobile pass.
9. Accessibility pass.
10. Reduced motion support.

---

## 15. Test plan đề xuất

### Backend unit tests

- `create_lock` rejects quantity <= 0.
- `create_lock` rejects when inventory row unavailable.
- `create_lock` locks exact store/product row.
- `create_lock` concurrent requests cannot oversell.
- `finalize_order` rejects missing lock.
- `finalize_order` rejects expired lock.
- `finalize_order` handles order_code collision.
- `check_and_release_expired_locks` idempotent.
- `generate_smart_itinerary` no candidates returns clean no_results.
- Planner fallback computes non-zero distance.
- Culture review validates rating.
- Vision match checks ownership.
- Agent tool args validate schema.

### Backend integration tests

- Postgres + Redis lock lifecycle.
- Celery worker processes scan mock.
- Alembic empty DB upgrade creates all tables/extensions.
- Payment webhook idempotency.
- Optimization service requires internal secret.
- OSRM unavailable fallback.

### Frontend tests

- Inventory page loads stores/products.
- Reserve item opens pending payment, not confirmed paid.
- Cart shows product/store details.
- Expired lock disappears/refetches.
- Vision upload shows failure reason.
- Itinerary generate handles optimization error.
- Culture review requires valid rating/text.
- Login token invalid redirects.
- Production build fails if API URL missing.

### E2E smoke

1. Login.
2. Open spatial map.
3. Search place.
4. Open O2O context.
5. Reserve product.
6. Checkout pending payment.
7. Webhook marks paid.
8. Order appears in history.

---

## 16. Checklist kỹ thuật chi tiết

### Docker/Infra

- [ ] Compose chính có Redis.
- [ ] Compose chính có RabbitMQ.
- [ ] Compose chính có Celery worker.
- [ ] Compose chính có Celery beat.
- [ ] Compose chính có optimization service.
- [ ] Backend dùng service DNS, không `localhost`.
- [ ] Worker image copy `backend/workers`.
- [ ] Model cache strategy.
- [ ] Upload volume/object storage.
- [ ] Healthcheck readiness sâu.

### Database

- [ ] Alembic include `Base.metadata`.
- [ ] Migration tạo domain tables.
- [ ] Migration tạo extensions.
- [ ] Migration tạo GiST indexes.
- [ ] Migration tạo GIN trigram indexes.
- [ ] Migration tạo HNSW vector index.
- [ ] Check constraints stock/price/rating.
- [ ] Unique inventory store/product.
- [ ] Order/payment schema.
- [ ] Audit/event tables.

### Backend

- [ ] Auth cho expensive endpoints.
- [ ] Rate limit.
- [ ] Payment webhook.
- [ ] Lock requires store_id.
- [ ] Order requires lock_id.
- [ ] Cancel lock endpoint.
- [ ] Worker failure updates DB.
- [ ] Agent sanitize errors.
- [ ] Review moderation.
- [ ] Static/signed URL for uploads.

### Frontend

- [ ] `bun run build` pass.
- [ ] Devtools only in dev.
- [ ] API base production guard.
- [ ] Replace hard-coded culture stats.
- [ ] Cart details.
- [ ] Payment wording fixed.
- [ ] Object URLs revoked.
- [ ] Mix-match endpoint contract fixed.
- [ ] Culture drawer id contract fixed.
- [ ] Error states visible.

### Testing

- [ ] Backend domain tests.
- [ ] Redis/Postgres integration tests.
- [ ] Worker tests.
- [ ] Payment webhook tests.
- [ ] Frontend O2O Playwright tests.
- [ ] Migration test.
- [ ] Docker build test.
- [ ] CI cache dependencies.

---

## 17. Các lỗi cần sửa ngay theo file

### `compose.yml`

- Thiếu Redis/RabbitMQ/worker/beat/optimization/OSRM.
- Backend env thiếu Redis/RabbitMQ/optimization URL.
- DB init extension chưa rõ.
- Healthcheck chỉ kiểm API shallow.

### `backend/Dockerfile`

- Không copy `backend/workers`.
- Không copy `backend/optimization_service`.
- API image có thể không chạy được vision import.
- Chạy 4 workers trong khi AI thread/model design chưa an toàn.

### `backend/app/alembic/env.py`

- Chỉ dùng `SQLModel.metadata`.
- Không include SQLAlchemy Base domain.

### `backend/app/domains/inventory/service.py`

- Lock không theo store.
- Order không cần lock.
- Payment mock.
- Redis delete trước DB commit.
- Order code collision không retry.
- Compare price không thật.
- Expire sweep phụ thuộc worker chưa chạy.

### `backend/app/domains/vision/router.py`

- Upload scan no auth.
- Filename collision.
- Local filesystem.
- MIME trust.
- Polling tự fail task.
- Mix-match no ownership check.

### `backend/app/domains/vision/service.py`

- Thread thay vì Celery.
- Import worker trong API process.
- Không backpressure/retry.

### `backend/workers/ai_worker/vision_tasks.py`

- Load CLIP global.
- Failure không update DB.
- DB session close không đảm bảo trong finally.
- Vector search phụ thuộc index ngoài Alembic.

### `backend/app/domains/agent/router.py`

- Public endpoint.
- Không rate limit.

### `backend/app/domains/agent/service.py`

- API key trong URL.
- Raw provider error trả user.
- current_lat/current_lon bị bỏ qua.
- Tool args chưa validate bằng schema.
- print raw args.

### `backend/app/domains/culture/service.py`

- Search `ILIKE` không guard min length.
- Story không cache.
- Review không gắn user.

### `backend/app/domains/spatial/service.py`

- Public OSRM.
- Fallback distance 0.
- N+1 O2O context.
- Geography cast cần index strategy.

### `backend/app/domains/planner/service.py`

- Optimization URL hard-code localhost.
- N+1 queries.
- Fallback metrics 0.
- Budget semantics yếu.
- `_call_optimization_service` duplicate/unused.

### `backend/optimization_service/main.py`

- CORS `*`.
- No internal auth.

### `backend/optimization_service/core/algorithms/tsp_solver.py`

- OSRM public hard-code.
- Sync HTTP calls.
- Fallback distance omit origin.

### `frontend/src/main.tsx`

- API fallback localhost production.
- Token localStorage.

### `frontend/src/client/aegis-api.ts`

- Duplicate API base logic.
- Token localStorage.
- Types drift với backend.

### `frontend/src/routes/__root.tsx`

- Devtools always rendered.

### `frontend/src/routes/_layout/inventory.tsx`

- Build fail type errors.
- `_CATEGORIES` unused.
- Payment copy sai.
- Cart thiếu product detail/cancel/checkout.
- Hard-coded external image fallbacks.

### `frontend/src/routes/_layout/vision.tsx`

- Build fail `detected_objects` shape.
- Object URL leak.
- Closet image URL localhost fallback.
- Button "Thêm tủ đồ" không action.

### `frontend/src/routes/_layout/itinerary.tsx`

- Mix-match gọi product id vào closet endpoint.
- Culture story gọi store id vào place endpoint.
- Fallback UX chưa phân biệt rõ.

### `frontend/src/routes/_layout/culture.tsx`

- Wikipedia fetch client-side.
- Hard-coded stats/info/products.
- Review author spoofing.
- Trending search timing bug.

---

## 18. Kết luận

AEGIS O2O hiện là một prototype giàu ý tưởng nhưng đang lẫn ba lớp trạng thái:

1. Phần nền template FastAPI/React khá ổn cho user/admin/items.
2. Phần domain O2O đã có nhiều API và UI nhưng chưa được nối hạ tầng/migration/test đầy đủ.
3. Phần AI/payment/routing đang có nhiều mock hoặc hard-code, cần được đóng khung lại trước khi gọi là production.

Việc ưu tiên đúng là rất quan trọng. Không nên tiếp tục thêm màn hình mới trước khi các cổng dưới đây pass:

- Frontend build pass.
- Docker production dựng đủ stack.
- Alembic tạo đủ domain schema.
- Worker chạy Celery thật.
- Payment không còn "confirmed" trước khi paid.
- Inventory lock/order atomic.
- Expensive endpoints có auth/rate limit.

Sau khi sửa nhóm P0/P1, dự án sẽ có nền đủ chắc để phát triển các tính năng hay hơn: route planner theo ngân sách, gợi ý sản phẩm theo văn hóa địa phương, AI agent đáng tin, virtual closet cá nhân hóa, và dashboard vận hành cho merchant/admin.
