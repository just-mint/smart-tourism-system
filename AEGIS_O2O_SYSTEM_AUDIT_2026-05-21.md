# AEGIS O2O - Báo cáo audit hệ thống toàn diện

Ngày audit: 2026-05-21  
Phạm vi: backend, frontend, worker, optimization service, database migrations, Docker Compose, test suite, UI/UX hiện tại.  
Ghi chú: báo cáo này dựa trên trạng thái local hiện tại của repo. Worktree đang có nhiều file đã sửa và một số file chưa tracked, nên đây là audit của "current working tree", không phải một commit sạch.

---

## 1. Tóm tắt điều hành

Hệ thống đã có khung sản phẩm khá rộng: auth, admin CRUD nền tảng, culture/search, spatial map, planner, inventory lock, payment webhook, vision scan, virtual closet, Celery worker, optimization service. Tuy nhiên trạng thái hiện tại chưa sẵn sàng release vì các quality gate đang đỏ, nhiều luồng O2O chưa hoàn chỉnh, dashboard/UI còn mang cảm giác "AI demo/cyber dashboard" hơn là một sản phẩm vận hành thật, và test suite chưa bao phủ các domain mới.

Các blocker lớn nhất:

1. Frontend lint fail, backend ruff fail.
2. Backend tests không chạy được do Postgres test/local không sẵn sàng.
3. Dashboard đang dùng số liệu giả và activity giả, dù đã có API telemetry.
4. Frontend auth guard chỉ dựa vào cookie marker `aegis_logged_in`, lệch với JWT httpOnly thật.
5. Inventory nhiều chỗ hiển thị `stock` tổng thay vì `stock - locked_stock`, dễ bán/giữ hàng sai trạng thái.
6. Luồng order/payment còn thiếu API/màn hình theo dõi đơn, polling trạng thái thanh toán, hủy đơn, lịch sử đơn.
7. Worker vision phụ thuộc CLIP model load lúc import, thiếu readiness/model cache/retention file upload.
8. Compose có cấu hình internal secret và OSRM chưa đủ an toàn/nhất quán cho production.
9. UI hiện tại quá nhiều neon/glass/cyber text, animation, số giả, label tiếng Anh lẫn tiếng Việt, làm giảm độ tin cậy sản phẩm.

---

## 2. Quality gates đã kiểm tra

| Hạng mục | Kết quả | Chi tiết |
|---|---:|---|
| `bun run build` trong `frontend` | PASS | Build thành công, nhưng bundle chính khoảng `916.94 kB`, Vite cảnh báo chunk > 500 kB. |
| `bun run lint` trong `frontend` | FAIL | `itinerary.tsx` có useless switch case và `as any`; `itinerary.tsx`, `spatial.tsx`, `tests/auth.setup.ts` cần format. |
| `uv run --project backend ruff check backend` | FAIL | `backend/scripts/cleanup.py` import chưa sort, unused `sessionmaker`; `backend/scripts/seed_stores.py` có C401. |
| `uv run --project backend pytest backend/tests -q` | FAIL | 59 lỗi ở setup DB: không connect được Postgres `localhost:5432`. |
| `docker compose config` | PASS có warning | Warning biến `CI` chưa set. Compose render được. |
| `bunx playwright test --list` | PASS | Liệt kê được 68 tests, chưa chạy full E2E vì backend/DB không sẵn sàng. |

---

## 3. Trạng thái repo đáng chú ý

Worktree đang dirty:

- Nhiều file backend domain/API/worker/compose đang modified.
- Frontend đang modified ở `frontend/src/index.css`, `_layout.tsx`, `_layout/itinerary.tsx`, `_layout/spatial.tsx`.
- Untracked đáng chú ý: `AEGIS_O2O_AUDIT_2026-05-20.md`, `backend/app/alembic/versions/873624317ede_add_category_to_product.py`, `backend/scripts/cleanup.py`, `1705/`, `.vscode/`, `FixReportAegis.docx`, `mermaid_diagrams.md`.

Khuyến nghị: trước khi sửa lớn tiếp, tạo branch/commit checkpoint để tránh mất trạng thái đã audit.

---

## 4. Kiến trúc hiện tại

Backend:

- FastAPI main app: `backend/app/main.py`
- API router: `backend/app/api/main.py`
- Domain routers: agent, culture, spatial, inventory, vision, planner.
- DB: SQLModel cho user/item cũ + SQLAlchemy Base cho domain models.
- Redis: rate limit, lock TTL/cache telemetry.
- RabbitMQ + Celery: vision tasks, sweep expired inventory locks.
- Optimization service: FastAPI riêng trong `backend/optimization_service`.

Frontend:

- React 19 + TanStack Router.
- Generated SDK tồn tại trong `frontend/src/client`, nhưng domain O2O đang dùng thêm manual API layer `frontend/src/client/aegis-api.ts`.
- Routes chính: dashboard, spatial, itinerary, culture, inventory, vision, admin, items, settings.

Infra:

- `compose.yml` chạy db, redis, rabbitmq, backend, frontend, optimization service, ai worker, beat.
- `compose.override.yml` expose local ports, mailcatcher, playwright.

---

## 5. Lỗi và rủi ro chi tiết

### P0 - Blocker trước khi release

| ID | Khu vực | Phát hiện | Tác động | Đề xuất sửa |
|---|---|---|---|---|
| P0-01 | Frontend quality | `bun run lint` fail ở `frontend/src/routes/_layout/itinerary.tsx:378`, `:491`; format fail ở `itinerary.tsx`, `spatial.tsx`, `tests/auth.setup.ts`. | Không đạt CI/lint, dễ tích lỗi kiểu/type. | Fix switch case, bỏ `as any` bằng typed union, chạy format. |
| P0-02 | Backend quality | `ruff check` fail ở `backend/scripts/cleanup.py` và `backend/scripts/seed_stores.py`. | Backend quality gate đỏ. | Sửa import order, bỏ unused import, đổi generator sang set comprehension. |
| P0-03 | Test/backend | `pytest backend/tests` fail 59 lỗi do không connect Postgres `localhost:5432`. | Không chứng minh được backend đang ổn; các domain mới không được test. | Chuẩn hóa test DB bằng compose profile hoặc testcontainers; thêm hướng dẫn `POSTGRES_PORT`/`.env.test`. |
| P0-04 | Auth/frontend | Protected layout chỉ check `aegis_logged_in` marker cookie trong `frontend/src/hooks/useAuth.ts` và `frontend/src/lib/auth-session.ts`; marker sống 7 ngày, JWT backend chỉ 30 phút. | Người dùng có marker stale vẫn vào shell rồi mới bị API redirect; UX chập chờn và guard không đại diện auth thật. | Trước khi load protected route, gọi `/users/me` hoặc dùng route loader query; đồng bộ marker expiry với token; chỉ redirect 401, không redirect mọi 403. |
| P0-05 | Dashboard | `frontend/src/routes/_layout/index.tsx` dùng `STATS`, `ACTIVITIES`, `TRENDING`, `TelemetryStream` hardcoded/random. | Dashboard hiển thị "All Systems Operational", revenue, locks, activity giả. Sản phẩm trông như demo AI, không đáng tin. | Nối `TelemetryAPI.getStats`, thêm endpoint metrics thật, bỏ fake activity hoặc gắn rõ là sample trong dev. |
| P0-06 | Inventory stock | `get_products_by_store` và `search_stores_and_products` trả `stock: inv.stock` thay vì available stock; vision worker/service cũng dùng `Inventory.stock > 0`. | UI có thể hiện "còn hàng" dù hàng đã bị lock; lock/order dễ gây lỗi muộn. | Chuẩn hóa field `available_stock = max(0, stock - locked_stock)`; API response nên có cả `stock`, `locked_stock`, `available_stock` nếu cần admin. |
| P0-07 | Order/payment | Chỉ có `POST /inventory/orders` và `POST /inventory/payments/webhook`; thiếu `GET my orders`, `GET order status`, cancel order, polling payment, admin reconciliation. | Người dùng tạo QR xong không theo dõi được đơn; frontend không biết khi nào đã thanh toán ngoài webhook nội bộ. | Bổ sung order lifecycle API + frontend order history/status polling; thêm backend tests webhook idempotency/expired/paid/failed. |
| P0-08 | Internal service security | `compose.yml` truyền `INTERNAL_SECRET_KEY=${INTERNAL_SECRET_KEY:-}`; optimization service chỉ check nếu env secret có giá trị. Nếu blank thì bỏ qua auth. | Khi compose/local expose optimization service, endpoint nội bộ có thể gọi không cần secret. | Bắt buộc secret non-empty cho non-local; optimization service fail-fast nếu thiếu; không expose service public. |
| P0-09 | Vision worker | `SentenceTransformer("clip-ViT-B-32")` load ở import trong `backend/workers/ai_worker/vision_tasks.py`; nếu model download/load fail thì mọi scan fail. | Worker khởi động chậm, phụ thuộc network/cache, không có readiness rõ ràng. | Pin/cache model path, build model vào image hoặc mount volume cache; thêm readiness endpoint/task health; fallback UI rõ. |
| P0-10 | Migrations/schema | Migration untracked `873624317ede_add_category_to_product.py` đang cần cho `Product.category`; nếu không commit/apply DB có thể lệch model. | Seed/search/planner category product có thể lỗi hoặc mất dữ liệu. | Commit migration hoặc gộp đúng chain; chạy `alembic upgrade head` trên fresh DB trong CI. |

### P1 - Rủi ro cao cần xử lý sớm

| ID | Khu vực | Phát hiện | Tác động | Đề xuất sửa |
|---|---|---|---|---|
| P1-01 | API exposure | `culture` story/image và nhiều `spatial` endpoint public; một số endpoint gọi external/LLM hoặc query nặng, chỉ rate limit. | Dễ bị spam chi phí Gemini/Wikipedia/PostGIS/OSRM. | Với endpoint tốn tiền/tốn CPU, yêu cầu auth hoặc quota; cache Redis; tách public search nhẹ với authenticated enrich. |
| P1-02 | Rate limit | Rate limit Redis fail-open; key theo IP + path. | Nếu Redis lỗi, không giới hạn; sau reverse proxy có thể gom IP sai. | Hỗ trợ trusted proxy headers, user-id bucket khi auth, metric cảnh báo Redis fail. |
| P1-03 | Error handling | Nhiều router trả `detail=f"...{str(e)}"` cho 500 (`spatial`, `planner`, optimization). | Rò rỉ chi tiết nội bộ/SQL/HTTP lỗi ra client. | Log internal error, trả mã lỗi generic + request id. |
| P1-04 | Payment config | `_build_vietqr_url` hardcode bank/account demo trong inventory service. | Không phù hợp production, khó đổi môi trường. | Đưa bank/account/accountName/template vào env, validate production. |
| P1-05 | Checkout TTL | Sau `finalize_order`, Redis lock key bị xóa, lock chuyển `checkout_pending` và dựa DB expiry/beat. | UI countdown/cache lock có thể không phản ánh checkout pending; nếu beat fail hàng giữ lâu. | Thêm order expiry/status endpoint; giữ TTL DB rõ, cleanup observable; frontend polling status. |
| P1-06 | Data model | `InventoryLock.store_id` nullable dù API lock yêu cầu store_id. | Legacy/null lock làm logic release chọn inventory đầu tiên, dễ sai cửa hàng. | Migration backfill và set NOT NULL sau khi xử lý legacy. |
| P1-07 | Planner anchor | Anchor Place được gán `store_id = anchor_place.id` trong planner service. | Frontend có thể gọi story/lock theo store_id nhưng thực chất là place id; lẫn place/store identity. | Response cần `stop_type`, `place_id`, `store_id` riêng; attraction không nên giả store_id. |
| P1-08 | Planner category | Category allocation so sánh exact `"food"`, `"store"`, `"attraction"`. | Dataset category tiếng Việt hoặc category khác dễ rơi vào `other`, route kém chất lượng. | Chuẩn hóa taxonomy/category mapping ở seed + service, lưu enum/category_normalized. |
| P1-09 | Search inventory | Comment nói tìm product theo tên/description nhưng code chỉ filter `Product.name`. Không có pagination/filter/sort. | Search kém và dễ quá tải khi data lớn. | Thêm full-text/trigram cho name/description/tags/category; pagination; filter by availability/category/price. |
| P1-10 | Vision storage | Upload lưu local `/uploads`, public static, chưa có retention/cleanup/delete; service đọc toàn file vào memory. | Disk tăng vô hạn, rủi ro privacy ảnh người dùng. | Object storage hoặc volume policy; background cleanup; delete closet image; quota per user. |
| P1-11 | Vision accuracy | Mix-match lấy inventory `.first()` không lọc available stock, không ưu tiên gần user. | Gợi ý sản phẩm có thể hết hàng hoặc sai cửa hàng. | Query available inventory, trả nhiều store options, sort by availability/distance. |
| P1-12 | UI state bugs | Login `performTransition` nằm trong dependency effect nhưng không memo; Culture/Dashboard tạo array trong component và đưa vào deps. | Interval/effect bị recreate nhiều lần, animation/log khó kiểm soát. | `useCallback`, `useMemo`, đưa constants ngoài component, cleanup chắc chắn. |
| P1-13 | Frontend tests stale | `frontend/tests/login.spec.ts` còn expect text cũ như `Log In`, `Welcome back...`; `o2o.spec.ts` expect English copy khác UI hiện tại. | E2E sẽ fail khi chạy thật, không bảo vệ UX. | Cập nhật selectors/testid, bỏ phụ thuộc copy, chạy E2E sau khi stack lên. |
| P1-14 | API client drift | Có generated SDK và manual `aegis-api.ts`. | Type/API dễ lệch OpenAPI thật. | Chọn một nguồn truth; generate domain client từ OpenAPI hoặc viết wrapper typed quanh generated SDK. |
| P1-15 | Docker healthcheck | Backend Dockerfile không cài `curl`, nhưng compose healthcheck dùng `curl`. | Container healthcheck có thể fail nếu image không có curl. | Cài curl hoặc đổi sang Python/uvicorn healthcheck command. |
| P1-16 | OSRM config | `.env.example` khuyên `http://osrm-backend:5000`, compose default fallback public `https://router.project-osrm.org`. | Production phụ thuộc public OSRM, latency/quota/privacy không ổn. | Dùng private OSRM profile rõ ràng; nếu fallback public thì chỉ dev. |
| P1-17 | Cleanup script | `backend/scripts/cleanup.py` untracked và chạy `TRUNCATE inventory, stores, products CASCADE`. | Dễ xóa dữ liệu production nếu chạy nhầm. | Đổi tên rõ `dev_cleanup_inventory.py`, bắt `ENVIRONMENT=local`, confirm flag. |
| P1-18 | Telemetry API | `utils/telemetry` chỉ đếm `InventoryLock` toàn bộ, không filter active; dashboard không dùng API này. | Metrics sai/nghèo thông tin. | Tách metrics admin/user, filter status, thêm orders/revenue/worker status/cache/db latency. |

### P2 - Cần cải thiện để sản phẩm trưởng thành

| ID | Khu vực | Phát hiện | Đề xuất |
|---|---|---|---|
| P2-01 | UI language | Tiếng Anh/Việt trộn lẫn: `O2O Market`, `Nearby Hubs`, `Internal Actions`, `LINK SECURED`, `Commander`. | Chọn một ngôn ngữ chính, với i18n nếu cần. Với thị trường Việt Nam nên ưu tiên tiếng Việt tự nhiên. |
| P2-02 | UI aesthetics | Nhiều neon, glassmorphism, orbs, scanlines, monospace, spinning avatar, fake terminal telemetry. | Chuyển sang giao diện vận hành du lịch - thương mại: sáng, rõ, ít hiệu ứng, ảnh thật, bản đồ và danh mục là trung tâm. |
| P2-03 | Bundle size | Build warning chunk > 500 kB. | Code split theo route, lazy load map/three/leaflet/vision, analyze bundle. |
| P2-04 | Accessibility | Nhiều icon-only button thiếu label, div clickable thay button, màu tương phản mỏng trên nền tối. | Thêm aria-label, keyboard navigation, focus states, semantic buttons. |
| P2-05 | Mobile UX | Panel map/product có width cố định lớn (`420px`, modal lớn, full-height). | Dùng bottom sheet trên mobile, responsive grid, touch targets ổn định. |
| P2-06 | External assets | Unsplash/Wikipedia/remote images hardcoded ở nhiều route. | Lưu asset curated/local CDN, fallback có kích thước ổn định, tránh layout shift. |
| P2-07 | Logs frontend | `console.log`/emoji debug trong login. | Xóa hoặc dùng debug logger gated by dev mode. |
| P2-08 | Pydantic v2 | Vẫn dùng `class Config` trong nhiều schema, pytest warnings. | Đổi sang `model_config = ConfigDict(from_attributes=True)`. |
| P2-09 | Reviews | Moderation chỉ là hardcoded bad words, không có edit/delete/report. | Thêm review ownership, report flow, moderation queue. |
| P2-10 | Observability | Thiếu request id, structured logs, metrics worker/queue, Sentry chưa đầy đủ local/staging check. | Thêm correlation id, Prometheus/OpenTelemetry hoặc Sentry breadcrumbs. |

---

## 6. Các chức năng còn thiếu để hoàn thiện sản phẩm

### Backend/domain

1. Order management:
   - `GET /inventory/orders/me`
   - `GET /inventory/orders/{id}`
   - `GET /inventory/orders/{id}/status`
   - `POST /inventory/orders/{id}/cancel`
   - admin order list/filter/status update
   - expiry job + reconciliation report

2. Payment:
   - Tích hợp provider thật thay vì `vietqr_mock`
   - cấu hình VietQR/provider qua env
   - webhook HMAC tests
   - trạng thái `pending/paid/failed/cancelled/expired/refunded`
   - polling hoặc realtime notification cho frontend

3. Inventory/admin:
   - CRUD stores/products/inventory
   - import/export CSV
   - điều chỉnh tồn kho có audit log
   - quản lý ảnh sản phẩm
   - batch embedding products
   - availability API chuẩn

4. Planner:
   - lưu itinerary theo user
   - lịch sử hành trình
   - opening hours/business hours
   - travel mode
   - preference profile
   - phân biệt `place` và `store`

5. Spatial:
   - pagination/filter/category normalized
   - cache cho nearby/search
   - private OSRM
   - reverse geocoding/geofence

6. Culture:
   - Redis cache story/image
   - curation/admin edit content
   - review CRUD/report/moderation
   - rate limit/auth cho endpoint tốn Gemini

7. Vision:
   - worker readiness
   - model cache/offline build
   - delete closet item
   - upload quota
   - cleanup old scan images
   - vector embedding versioning/migration

8. Agent:
   - conversation history/session
   - tool result cards thay vì raw internal actions
   - quota per user
   - graceful fallback khi thiếu Gemini key

9. Observability:
   - metrics dashboard thật
   - queue length/worker health
   - payment/order audit
   - error tracking/request id

### Frontend

1. Dashboard thật:
   - active users, stores, active locks, orders, revenue, worker status
   - không dùng fake telemetry/activity

2. Inventory/O2O:
   - order history
   - order status page
   - payment pending/paid/expired UI
   - cancel lock/cancel order rõ ràng
   - product detail page
   - filters/sort/pagination
   - available stock đúng

3. Admin:
   - quản lý store/product/inventory
   - xem order/payment
   - xem inventory events
   - upload/import data

4. Planner/spatial:
   - save route
   - route detail
   - distinguish attraction/store stop
   - mobile bottom sheets
   - empty/error/loading states chuẩn

5. Vision:
   - polling với timeout/retry rõ
   - trạng thái worker/model unavailable
   - delete closet item
   - privacy copy/quota

6. Auth:
   - route guard dựa vào `/users/me`
   - session expired UI
   - không redirect 403 admin thành logout chung

7. UI system:
   - language nhất quán
   - design tokens
   - component states chuẩn
   - accessibility/testid ổn định

---

## 7. Đề xuất nâng cấp giao diện

### Vấn đề UI hiện tại

UI hiện tại dễ bị nhận xét là "AI code" vì:

- Quá nhiều neon/cyber/glass: `AEGIS_AGENT`, `LINK SECURED // GEMINI ACTIVE`, scanlines, spinning rings, glow, terminal telemetry.
- Dashboard dùng số liệu giả nhưng trình bày như live production.
- Copywriting kiểu game/sci-fi: `Commander`, `All Systems Operational`, `Internal Actions`.
- Quá nhiều card bo lớn, hiệu ứng hover/animate, màu tối cyan/purple/emerald dày đặc.
- Tiếng Anh/Việt trộn lẫn trong cùng workflow.
- Một số trang trông như landing/demo thay vì công cụ vận hành thật.

### Hướng thiết kế mới nên dùng

Định vị giao diện: "Nền tảng vận hành du lịch - thương mại O2O", không phải cyber AI dashboard.

Phong cách đề xuất:

- Nền sáng hoặc neutral, sidebar gọn, topbar rõ.
- Dùng màu chủ đạo teal/green rất tiết chế, thêm amber/red/blue cho trạng thái.
- Card radius 8px, table/list rõ ràng, tránh nested cards.
- Bản đồ full-bleed ở spatial/planner, panel thông tin dạng sheet.
- Ảnh địa điểm/sản phẩm thật, rõ, không dùng ảnh tối/blur làm nền chính cho công cụ.
- Copy tiếng Việt tự nhiên: "Bảng điều khiển", "Cửa hàng gần bạn", "Giữ hàng", "Đơn hàng", "Đang chờ thanh toán".
- AI Agent là trợ lý phụ, không phải theme chính của toàn app.

### Nâng cấp theo trang

Dashboard:

- Bỏ fake map SVG/activity stream.
- Dùng metrics thật từ backend.
- Layout: hàng KPI, bảng đơn mới, lock sắp hết hạn, trạng thái worker/payment, bản đồ store coverage nếu có dữ liệu thật.

Inventory:

- Chuyển từ dark marketplace sang catalog vận hành rõ ràng.
- Sidebar filter: khu vực, category, availability, price.
- Product card hiển thị `available_stock`, store, price override, CTA "Giữ hàng".
- Thêm order drawer/status.

Spatial:

- Map là trung tâm, controls tối giản.
- O2O context panel dùng bottom sheet/mobile sheet.
- Marker icon không dùng neon HTML; dùng icon rõ theo category.

Itinerary:

- Tách form tạo route, route results, map.
- Stop card phải phân biệt "Điểm tham quan" và "Cửa hàng".
- CTA giữ hàng chỉ hiện khi stop có `store_id` thật và sản phẩm còn hàng.

Culture:

- Giảm hero/AI storytelling engine.
- Tập trung search, kết quả, story, reviews.
- AI story cần cache và trạng thái "được tạo bởi AI" kín đáo.

Vision:

- Giảm scan animation.
- Hiển thị trạng thái task rõ: queued/processing/completed/failed.
- Cho người dùng xóa ảnh/tủ đồ.

Login:

- Bỏ console logs/animation shatter nặng.
- Dùng ảnh du lịch rõ + form đơn giản; copy nhất quán với sản phẩm.

---

## 8. Roadmap sửa đề xuất

### Sprint 0 - Ổn định nền

1. Commit/checkpoint trạng thái hiện tại.
2. Fix frontend lint/format.
3. Fix backend ruff.
4. Chuẩn hóa local test DB để `pytest` chạy được.
5. Commit/apply migration `873624317ede`.
6. Chạy Alembic fresh DB trong CI/local.

### Sprint 1 - O2O correctness

1. Chuẩn hóa available stock trên toàn backend/frontend.
2. Bổ sung order status/history/cancel API.
3. Thêm payment webhook tests.
4. Sửa planner place/store identity.
5. Bổ sung tests cho lock concurrency, expired lock, paid/failed webhook.

### Sprint 2 - Frontend sản phẩm thật

1. Thay dashboard fake bằng telemetry thật.
2. Sửa auth guard bằng `/users/me`.
3. Cập nhật E2E selectors/copy.
4. Làm lại Inventory + Order status.
5. Giảm animation/debug logs.

### Sprint 3 - UI redesign

1. Thiết kế lại design tokens.
2. Thay dark cyber theme bằng operational UI.
3. Làm mobile sheets cho map/order.
4. Chuẩn hóa tiếng Việt/i18n.
5. Accessibility pass.

### Sprint 4 - Production readiness

1. Secrets validation cho production.
2. Private OSRM hoặc config routing rõ.
3. Worker readiness/model cache.
4. Object storage/cleanup upload.
5. Observability: request id, logs, metrics, Sentry.

---

## 9. Checklist hành động ưu tiên

Nên làm ngay:

- [ ] Fix `bun run lint`.
- [ ] Fix `ruff check`.
- [ ] Dựng Postgres test và chạy lại `pytest`.
- [ ] Chạy/commit Alembic migration mới.
- [ ] Sửa auth marker guard.
- [ ] Sửa `available_stock` toàn hệ thống.
- [ ] Bỏ fake stats/activity khỏi dashboard.
- [ ] Thêm order status/history API.
- [ ] Bỏ hardcoded VietQR account khỏi code.
- [ ] Cập nhật Playwright tests theo UI thật.

Nên làm sau khi pass quality gates:

- [ ] Redesign dashboard/inventory/spatial theo style sản phẩm vận hành.
- [ ] Thêm admin store/product/inventory/order.
- [ ] Thêm worker readiness/model cache.
- [ ] Thêm upload retention/delete.
- [ ] Thêm CI chạy lint/build/pytest/alembic/playwright.

---

## 10. Appendix - Evidence tham chiếu nhanh

Một số file/line đáng chú ý:

- Frontend route guard: `frontend/src/routes/_layout.tsx:45`, `frontend/src/hooks/useAuth.ts:19`, `frontend/src/lib/auth-session.ts:5`.
- Login cookie thật: `backend/app/api/routes/login.py:45`.
- Auth marker cookie 7 ngày: `frontend/src/lib/auth-session.ts:14`.
- Dashboard fake stats/activity: `frontend/src/routes/_layout/index.tsx:42`, `:74`, `:160`, `:397`.
- Agent panel cyber/internal actions: `frontend/src/routes/_layout.tsx:178`, `:386`.
- Inventory stock tổng: `backend/app/domains/inventory/service.py:97`, `:135`.
- Vision worker stock tổng/model import: `backend/workers/ai_worker/vision_tasks.py:18`, `:85`, `:99`.
- Planner anchor place giả store_id: `backend/app/domains/planner/service.py:280`.
- Planner enrich dùng `store_id or id`: `backend/app/domains/planner/service.py:427`, `:453`.
- Optimization auth skip nếu secret blank: `backend/optimization_service/api/v1/optimize.py:31`.
- Compose blank internal secret/default public OSRM: `compose.yml:116`, `:117`, `:221`, `:223`.
- Docker healthcheck curl: `compose.yml:123`, `:232`; backend Dockerfile không cài curl.
- Culture story public/no rate limit: `backend/app/domains/culture/router.py:24`.
- Spatial public endpoints: `backend/app/domains/spatial/router.py:11`, `:30`, `:55`, `:89`, `:106`.
- Upload local/public: `backend/app/domains/vision/router.py:57`, `backend/app/main.py:39`.
- Cleanup script destructive: `backend/scripts/cleanup.py:17`.

---

## 11. Kết luận

AEGIS O2O đã có nhiều module đúng hướng, nhưng hiện tại giống một prototype lớn hơn là sản phẩm hoàn thiện. Trọng tâm không nên là thêm hiệu ứng hay thêm màn hình mới ngay, mà là làm cho core O2O đúng và tin cậy: auth thật, stock thật, order/payment thật, metrics thật, tests chạy thật. Sau khi nền đó xanh, UI nên được thiết kế lại theo hướng công cụ vận hành du lịch - thương mại rõ ràng, ít "AI show", nhiều dữ liệu thật và luồng người dùng hoàn chỉnh.
