# AEGIS O2O - Báo cáo rà soát dự án

Ngày rà soát: 2026-05-20  
Phạm vi: backend FastAPI, domain O2O, optimization service, Celery worker, Docker Compose, frontend React/TanStack Router, UI/UX, test/build readiness.

## 1. Tóm tắt điều hành

AEGIS O2O đã tiến bộ so với báo cáo audit cũ: Dockerfile hiện đã copy `workers` và `optimization_service`, compose đã có Redis/RabbitMQ/optimization service/worker/beat, Alembic đã gom cả `SQLModel.metadata` và `Base.metadata`, order flow đã chuyển sang `PENDING_PAYMENT` thay vì xác nhận thanh toán sớm.

Tuy vậy dự án vẫn chưa nên coi là hoàn thiện hoặc production-ready. Các rủi ro lớn nhất hiện nằm ở:

- Worker/beat và OSRM đang dùng profile nên nhiều luồng demo dễ chạy thiếu service.
- Các endpoint tốn chi phí như Agent/Planner vẫn chưa yêu cầu đăng nhập ở backend.
- Test suite và UI test đang lệch với giao diện hiện tại.
- Giao diện còn nhiều dấu hiệu "AI generated": neon/glass quá nhiều, telemetry giả, số liệu hard-code, tiếng Anh/Việt trộn lẫn, lộ thuật ngữ kỹ thuật ra người dùng.
- Frontend có build pass nhưng lint fail và bundle chính rất lớn.
- Backend lint fail vài lỗi format, pytest local fail hàng loạt vì không kết nối được Postgres.

## 2. Kết quả kiểm tra đã chạy

### Frontend

- `bun run build`: pass.
- Cảnh báo bundle: `dist/assets/index-aBcWhMVI.js` khoảng 916.78 kB minified, gzip 279.27 kB. Nên code-split mạnh hơn cho map, dashboard, route domain.
- `bun run lint`: fail 1 lỗi format ở `frontend/tests/auth.setup.ts`.

### Backend

- `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend ruff check backend`: fail 4 lỗi fixable trong `backend/app/domains/agent/service.py` gồm import chưa sort và blank line có whitespace.
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend pytest`: 4 test optimization pass, 59 test error do không kết nối được Postgres `localhost:5432/travel_app`.
- `docker compose ps`: không chạy được trong sandbox vì không có quyền Docker socket.

## 3. Điểm đã cải thiện tốt

- Compose đã có `redis`, `rabbitmq`, `optimization_service`, `ai_worker`, `ai_beat`: `compose.yml:81`, `compose.yml:92`, `compose.yml:104`, `compose.yml:123`, `compose.yml:152`.
- Backend image đã copy worker và optimization service: `backend/Dockerfile:34-36`.
- Alembic đã theo dõi cả model SQLModel và domain SQLAlchemy: `backend/app/alembic/env.py:20-21`.
- Inventory lock đã bắt buộc `store_id`, dùng `SELECT ... FOR UPDATE`, tăng `locked_stock` atomically: `backend/app/domains/inventory/service.py:176-193`.
- Order hiện tạo trạng thái `PENDING_PAYMENT`, có webhook cập nhật `PAID/PAYMENT_FAILED/CANCELLED`: `backend/app/domains/inventory/service.py:418-470`, `backend/app/domains/inventory/service.py:492-560`.
- Vision upload đã validate MIME, size, decode ảnh và dùng UUID filename: `backend/app/domains/vision/router.py:26-65`.

## 4. Lỗi và rủi ro backend/infra

### P0 - Cần xử lý trước khi demo nghiêm túc

1. **Worker và beat không chạy mặc định.**  
   `ai_worker` và `ai_beat` nằm trong profile `worker` tại `compose.yml:123-154`. Nếu chỉ chạy backend/frontend, ảnh upload sẽ enqueue task nhưng không có worker xử lý. Router còn tự đánh task `failed` sau 30 giây ở `backend/app/domains/vision/router.py:95-100`, dễ sai với lần load model CLIP đầu tiên.

2. **Backend không phụ thuộc `optimization_service`.**  
   Backend trỏ `OPTIMIZATION_SERVICE_URL=http://optimization_service:8001/api/v1/optimize` tại `compose.yml:216`, nhưng `depends_on` của backend chỉ có db/prestart/redis/rabbitmq tại `compose.yml:184-193`. Khi CI hoặc dev chỉ start `backend frontend`, planner sẽ fallback hoặc lỗi.

3. **OSRM private server không chạy mặc định.**  
   `osrm-backend` nằm trong profile `routing` tại `compose.yml:282-285`, trong khi backend/optimization service trỏ tới `http://osrm-backend:5000`. Nếu profile không bật, route thật sẽ fallback đường chim bay.

4. **Agent và Planner chưa bắt buộc auth ở backend.**  
   `/agent/chat` chỉ rate-limit theo IP, không có `get_current_user`: `backend/app/domains/agent/router.py:10-15`. `/planner/generate` cũng vậy: `backend/app/domains/planner/router.py:16-23`. Hai endpoint này tốn Gemini/CPU/OSRM nên cần auth, quota theo user và audit log.

5. **Cookie auth chưa production-safe.**  
   Login set cookie `secure=False` cố định tại `backend/app/api/routes/login.py:44-50`. Production cần `secure=True`, config theo `ENVIRONMENT`, và cân nhắc CSRF token cho mutating endpoints nếu dùng cookie.

### P1 - Lỗi nghiêm trọng cần sửa trước beta

6. **Vision worker phụ thuộc model tải lúc import.**  
   `SentenceTransformer('clip-ViT-B-32')` chạy ngay khi import worker tại `backend/workers/ai_worker/vision_tasks.py:12-20`. Nếu container không có cache/model hoặc mạng bị chặn, worker vẫn boot với `model=None` và task fail. Nên bake/cache model trong image hoặc dùng healthcheck fail-fast.

7. **Payment vẫn là VietQR demo.**  
   `_build_vietqr_url` hard-code bank/account demo tại `backend/app/domains/inventory/service.py:341-347`. Cần provider thật, cấu hình account, trạng thái `EXPIRED`, webhook có chữ ký bắt buộc ở staging/production, và màn hình order history.

8. **Webhook signature được bỏ qua ngoài production nếu thiếu secret.**  
   `backend/app/domains/inventory/service.py:474-478` cho phép webhook không signature khi `PAYMENT_WEBHOOK_SECRET` chưa set và env không phải production. Điều này nguy hiểm nếu staging/local bị public.

9. **Price comparison có thể trả tồn kho âm/không khả dụng.**  
   Query lọc `Inventory.stock > 0` tại `backend/app/domains/inventory/service.py:141-147`, nhưng response trả `stock - locked_stock` tại dòng 165. Nên lọc `stock > locked_stock` và clamp kết quả.

10. **Spatial search chưa rate-limit.**  
    `/spatial/search` không có dependency rate-limit tại `backend/app/domains/spatial/router.py:10-18`. Đây là endpoint DB search có thể spam.

11. **Review chưa có moderation thật.**  
    Review post đã yêu cầu auth, nhưng chỉ chặn một list từ xấu thủ công. Model chưa phản ánh rõ FK/moderation state. Cần report/edit/delete, trạng thái pending/approved, và kiểm duyệt nội dung.

12. **Test backend phụ thuộc DB local đang chạy.**  
    `backend/tests/conftest.py` gọi `init_db(session)` trực tiếp vào Postgres. Khi DB không có, 59 test error. Cần tách unit test không cần DB, integration test có docker/testcontainers, và thông báo rõ prereq.

### P2 - Nợ kỹ thuật nên gom lại

13. **Pydantic V2 deprecation warning.**  
    Nhiều schema còn dùng `class Config: from_attributes = True`; nên đổi sang `ConfigDict(from_attributes=True)`.

14. **Một số catch im lặng làm khó debug.**  
    Frontend và backend có nhiều `catch {}`/fallback rộng; cần log có context và hiển thị lỗi hành động được cho người dùng.

15. **Observability chưa đủ.**  
    Cần structured logs, request id, queue metrics, task failure rate, payment webhook metrics, Sentry release/env, healthcheck cho worker/optimization/OSRM.

## 5. Lỗi và rủi ro frontend

### P0/P1 - Ảnh hưởng chất lượng release

1. **Frontend lint fail.**  
   `frontend/tests/auth.setup.ts` thiếu newline cuối file. Đây là lỗi nhỏ nhưng làm CI lint đỏ.

2. **Playwright tests đang lệch UI.**  
   Test login kỳ vọng nút `Log In`, link `Forgot your password?`, welcome text tiếng Anh tại `frontend/tests/login.spec.ts:26-50`, nhưng UI hiện dùng `Đăng nhập`, `Quên?` tại `frontend/src/routes/login.tsx:355-386`. O2O test kỳ vọng `Place Order via VietQR`, `Order Created`, text tiếng Anh tại `frontend/tests/o2o.spec.ts:159-165`, nhưng UI hiện là `Tạo đơn chờ thanh toán` và text tiếng Việt tại `frontend/src/routes/_layout/inventory.tsx:518-607`.

3. **Auth guard chỉ dựa vào marker cookie phía client.**  
   Route protected kiểm `aegis_logged_in` tại `frontend/src/routes/_layout.tsx:43-51`. Cookie này do JS set, không phải bằng chứng session hợp lệ. Interceptor sẽ redirect sau khi `/users/me` 401, nhưng vẫn có flicker và logic bảo vệ yếu. Nên validate session trong route loader/query trước khi render layout.

4. **Bundle chính quá lớn.**  
   Build pass nhưng `index` chunk ~917 kB. Nên lazy-load routes nặng (`spatial`, `itinerary`, `vision`, `culture`) và tách Leaflet/React Leaflet/cluster/three/devtools ra chunk riêng.

### P2 - UI/UX đang tạo cảm giác "AI code"

5. **Dashboard là dữ liệu giả/hard-code.**  
   `STATS`, `ACTIVITIES`, `TRENDING`, telemetry random nằm ở `frontend/src/routes/_layout/index.tsx:42-89` và `frontend/src/routes/_layout/index.tsx:160-180`. Người dùng thấy "System Telemetry" nhưng không phải dữ liệu thật.

6. **Quá nhiều hiệu ứng sci-fi/cyberpunk.**  
   Layout nền glow/orb, scanline, avatar spin, typewriter logo ở `frontend/src/routes/_layout.tsx:54-77`, `frontend/src/routes/_layout.tsx:281-334`. Phần này làm giao diện giống demo AI hơn là sản phẩm du lịch-thương mại.

7. **Lộ thuật ngữ kỹ thuật ra người dùng.**  
   UI có `AEGIS_AGENT`, `SMART_PLANNER`, `System Telemetry`, `CLIP`, `pgvector`, `Internal Actions`. Với người dùng du lịch/mua sắm, nên đổi sang ngôn ngữ tác vụ: "Trợ lý", "Lên lịch trình", "Gợi ý phù hợp", "Đang xử lý ảnh".

8. **Ngôn ngữ không thống nhất.**  
   Có màn tiếng Việt, có form checkout tiếng Anh (`Full Name`, `Phone Number`, `Delivery Address`) tại `frontend/src/routes/_layout/inventory.tsx:536-591`. Nên thống nhất VI hoặc thêm i18n.

9. **Ảnh và placeholder phụ thuộc nguồn ngoài.**  
   Inventory/login/culture/vision dùng nhiều Unsplash/Pexels/via.placeholder. Điều này giảm độ tin cậy, chậm tải, và làm sản phẩm thiếu bản sắc. Nên có asset pack/local CDN đúng domain du lịch Việt Nam.

10. **Login page log debug ra console production.**  
    Các `console.log` transition ảnh nằm tại `frontend/src/routes/login.tsx:78-122`. Nên bỏ debug log và giảm preload ảnh 2500px.

11. **Nhiều lỗi bị nuốt im lặng.**  
    Vision upload, closet, mix-match, itinerary fetch có `catch {}` hoặc `// silent`: `frontend/src/routes/_layout/vision.tsx:168-249`, `frontend/src/routes/_layout/itinerary.tsx:180-235`. Cần toast/error panel/retry.

12. **Mobile và accessibility cần kiểm lại.**  
    Nhiều panel cố định `w-[420px]`, icon-only button thiếu `aria-label`, clickable `div`, test a11y bị tắt nhiều rule trong `frontend/biome.json`. Cần audit mobile 375px/768px và keyboard navigation.

## 6. Chức năng còn thiếu để hoàn thiện sản phẩm

### Must-have cho MVP đáng tin

- Auth backend cho toàn bộ domain O2O: spatial mutate/route, planner, agent, vision, inventory lock/order.
- Quota/rate-limit theo user, không chỉ IP.
- Order lifecycle đầy đủ: `PENDING_PAYMENT`, `PAID`, `PAYMENT_FAILED`, `EXPIRED`, `CANCELLED`, `FULFILLED`; UI order history và polling/payment status.
- Payment provider thật hoặc ghi rõ mock ở mọi môi trường demo.
- Inventory admin/merchant portal: CRUD store/product, stock adjustment, price override, upload ảnh, audit inventory events.
- Background jobs chuẩn: worker/beat chạy mặc định ở môi trường demo, task status không timeout giả 30 giây.
- Data seed idempotent: stores/products/images/embeddings ổn định cho demo.
- Contract tests cho API domain mới và E2E cập nhật theo UI hiện tại.
- Observability: logs có request id, metrics queue/payment/lock, Sentry env/release, healthcheck cho worker và optimization.

### Should-have cho beta

- Object storage cho upload, retention/delete, scan virus/content-type sâu hơn.
- Search nâng cấp: full-text/trigram có ranking, filter category/price/stock/distance.
- Planner lưu itinerary, chia sẻ lịch trình, cập nhật route khi GPS thay đổi.
- Review moderation, report abuse, edit/delete review của chính user.
- Notification center cho lock sắp hết hạn, payment thành công, order hết hạn.
- i18n hoặc chuẩn hóa toàn bộ copy tiếng Việt.

## 7. Đề xuất nâng cấp giao diện

### Hướng thiết kế mới

Đổi từ "cyberpunk command center" sang "travel commerce concierge": yên tĩnh, tin cậy, dùng dữ liệu thật, nhiều ảnh điểm đến/sản phẩm rõ ràng, ít glow, ít thuật ngữ kỹ thuật.

### Palette gợi ý

- Nền: `#F8FAF7`, `#FFFFFF`, text `#17211B`.
- Accent: xanh ngọc/teal cho hành động chính, amber nhẹ cho giá/khuyến mãi, đỏ chỉ cho lỗi/hết hạn.
- Dark mode nếu giữ thì dùng slate/charcoal dịu, không neon tím-xanh chiếm màn.

### Cấu trúc màn hình

- **Dashboard:** thay telemetry giả bằng KPI thật từ API: active locks, orders pending payment, nearby stores, recent itinerary, quick actions.
- **Spatial:** map full-bleed, panel trái search/filter, bottom sheet mobile, card địa điểm/store rõ ràng.
- **Itinerary:** form nhu cầu bên trái, bản đồ ở giữa, summary bên phải; stepper "Nhu cầu → Cửa hàng phù hợp → Lộ trình → Giữ hàng".
- **Inventory:** marketplace chuẩn: filter, sort, product card có tồn kho, giá, store, reserve CTA; checkout drawer tiếng Việt.
- **Vision:** upload stepper, preview ảnh lớn, trạng thái xử lý có ETA/retry, kết quả gắn store availability.
- **Culture:** trang editorial: ảnh thật, câu chuyện, review, cửa hàng gần đó; bỏ số liệu demo.

### Quy tắc UI nên áp dụng

- Bỏ `System Telemetry`, `Internal Actions`, `CLIP/pgvector` khỏi UI người dùng.
- Chuẩn hóa một bộ component: button, input, card, sheet, toast, skeleton, empty/error state.
- Không dùng card lồng card quá nhiều; giảm blur/glass/shadow.
- Icon-only button phải có tooltip/aria-label.
- Mọi request fail phải có trạng thái lỗi, nút thử lại, và thông báo dễ hiểu.
- Dữ liệu demo phải gắn nhãn demo rõ hoặc thay bằng dữ liệu seed thật.

## 8. Lộ trình đề xuất

### Sprint 1 - Stabilize

- Sửa lint/ruff.
- Cập nhật Playwright theo UI hiện tại.
- Bắt auth cho Agent/Planner/Spatial search nặng.
- Đưa worker/beat vào profile demo mặc định hoặc cập nhật compose/dev script bắt buộc chạy.
- Thêm `depends_on` optimization service cho backend khi planner là core feature.

### Sprint 2 - Domain correctness

- Test inventory lock/order/payment webhook.
- Hoàn thiện payment lifecycle UI và order history.
- Backfill và enforce `inventory_locks.store_id NOT NULL` nếu không còn hỗ trợ lock không store.
- Sửa price comparison và stale lock handling.
- Bổ sung healthcheck/metrics cho worker, optimization, OSRM.

### Sprint 3 - UI redesign

- Thiết kế lại dashboard/spatial/itinerary/inventory theo hướng concierge.
- Loại bỏ telemetry giả, debug copy, neon/glow quá mức.
- Chuẩn hóa copy tiếng Việt.
- Code-split route nặng và tối ưu ảnh.

### Sprint 4 - Beta readiness

- Seed dữ liệu demo ổn định.
- E2E domain O2O chạy trong Docker compose có worker/routing.
- Object storage/upload retention.
- Monitoring và runbook deploy.

## 9. Kết luận

Dự án có nền kỹ thuật tốt và nhiều phần P0 cũ đã được vá. Trạng thái hiện tại phù hợp để tiếp tục làm prototype/demo nội bộ, nhưng để hoàn thiện cần ưu tiên ổn định infra worker/optimization, khóa endpoint tốn chi phí bằng auth/quota, cập nhật test suite, và thiết kế lại UI theo hướng sản phẩm du lịch-thương mại thực tế thay vì giao diện AI demo.

## 10. Cập nhật sau vòng sửa toàn diện

Đã xử lý trong lần sửa này:

- Frontend lint/format sạch, cập nhật Playwright selectors/copy theo UI hiện tại.
- Backend ruff/format sạch.
- Cookie đăng nhập bật `secure` ngoài môi trường `local`.
- Agent chat và Planner bắt buộc user đăng nhập; Spatial/Culture search có rate limit.
- Vision scan trả `202 Accepted`, timeout task chuyển sang cấu hình `VISION_TASK_TIMEOUT_SECONDS`.
- Inventory compare chỉ trả tồn kho khả dụng; webhook payment yêu cầu secret ngoài mock local.
- Compose chạy `ai_worker` và `ai_beat` mặc định, backend chờ `optimization_service` healthy, OSRM dùng public fallback có thể override bằng `OSRM_BASE_URL`.
- Dashboard, layout, sidebar, settings/admin/auth/inventory/vision/itinerary được làm lại copy và styling theo hướng vận hành sáng, bớt neon/glass/AI-debug.
- Chat panel không còn hiển thị `Internal Actions` cho người dùng.

Kiểm tra đã chạy:

- `bun run lint`: pass.
- `bun run build`: pass, còn cảnh báo chunk chính lớn khoảng 903 kB.
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend ruff check backend`: pass.
- `docker compose config`: pass, có cảnh báo biến `CI` chưa set.
- `bunx playwright test --list`: pass phần load test definitions.
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project backend pytest backend/tests -q`: chưa chạy qua vì Postgres `localhost:5432/travel_app` không kết nối được trong môi trường hiện tại; toàn bộ 59 lỗi đều fail ở fixture DB trước khi vào assertion.

Việc còn lại để beta-ready:

- Chạy lại backend pytest và Playwright full sau khi bật Postgres/Redis/RabbitMQ bằng Docker compose.
- Code-split bundle route nặng để giảm cảnh báo chunk.
- Bổ sung test domain mới cho inventory lock/order/payment, agent/planner auth và vision worker timeout.
- Chuẩn hóa nốt email template/backend message nếu cần một trải nghiệm tiếng Việt 100%.
