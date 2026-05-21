import { createFileRoute, useNavigate } from "@tanstack/react-router"
import type { FeatureCollection, LineString } from "geojson"
import L from "leaflet"
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Loader2,
  Lock,
  MapPin,
  Search,
  ShoppingBag,
  Sparkles,
  Thermometer,
} from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import {
  Circle,
  GeoJSON,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet"
import "leaflet/dist/leaflet.css"
import { toast } from "sonner"
import {
  CultureAPI,
  InventoryAPI,
  type MixMatchProduct,
  type NearbyStoreItem,
  PlannerAPI,
  type PlannerResponse,
  type PriceComparison,
  SpatialAPI,
  type StopInRoute,
  VisionAPI,
} from "@/client/aegis-api"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

export const Route = createFileRoute("/_layout/itinerary")({
  component: ItineraryPage,
})

// Icons
const createDivIcon = (html: string, size: number) =>
  L.divIcon({
    className: "bg-transparent",
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })

const userIcon = createDivIcon(
  `<div class="w-6 h-6 bg-[#008080] rounded-full border-[3px] border-white shadow-lg flex items-center justify-center">
    <div class="w-2 h-2 bg-white rounded-full"></div>
  </div>`,
  24,
)
const getStopIcon = (num: number, isFirst: boolean = false) => {
  const bgClass = isFirst ? "bg-[#008080]" : "bg-[#008080]"
  const html = `
    <div class="relative flex items-center justify-center w-8 h-8 ${bgClass} rounded-full rounded-br-none -rotate-45 shadow-md border-2 border-white">
      <span class="text-white font-bold text-xs rotate-45">${num}</span>
    </div>
  `
  return createDivIcon(html, 32)
}
const storeIcon = createDivIcon(
  `<div class="w-8 h-8 bg-white rounded-full border border-zinc-200 flex items-center justify-center text-[#2B0B3F] shadow-md"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></svg></div>`,
  32,
)

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length > 1)
      map.fitBounds(points, { padding: [60, 60], animate: true, duration: 1.2 })
    else if (points.length === 1) map.setView(points[0], 15, { animate: true })
  }, [points, map])
  return null
}

function ItineraryPage() {
  const [lat, setLat] = useState(10.7769)
  const [lon, setLon] = useState(106.7009)
  const [originText, setOriginText] = useState("")
  const [radius, setRadius] = useState(3000)
  const [keywords, setKeywords] = useState("")
  const [topN, setTopN] = useState(5)
  const [wRating, setWRating] = useState(0.4)
  const [wDistance, setWDistance] = useState(0.3)
  const [wPrice, setWPrice] = useState(0.3)
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<PlannerResponse | null>(null)
  const [frontendRouteGeoJson, setFrontendRouteGeoJson] = useState<FeatureCollection<LineString> | null>(null)
  const [expandedStop, setExpandedStop] = useState<number | null>(null)
  const [lockingId, setLockingId] = useState<number | null>(null)
  const [isTracking] = useState(false)
  const [isLocating, setIsLocating] = useState(false)

  const mapRef = useRef<L.Map | null>(null)
  const navigate = useNavigate()

  // --- O2O Shopping Filter States ---
  const [selectedShoppingCategory, setSelectedShoppingCategory] =
    useState<string>("Tất cả")
  const [nearbyStores, setNearbyStores] = useState<NearbyStoreItem[]>([])
  const [loadingNearbyStores, setLoadingNearbyStores] = useState(false)
  const [errorNearbyStores, setErrorNearbyStores] = useState("")

  const handleShoppingCategory = async (cat: string) => {
    setSelectedShoppingCategory(cat)
    setLoadingNearbyStores(true)
    setErrorNearbyStores("")
    try {
      const res = await SpatialAPI.nearbyStores(
        lat,
        lon,
        radius,
        cat === "Tất cả" ? undefined : cat,
        0, // min_rating
        "distance", // order_by
      )
      setNearbyStores(res.data.stores)
    } catch (_err) {
      setErrorNearbyStores("Lỗi tải danh sách cửa hàng")
      setNearbyStores([])
    } finally {
      setLoadingNearbyStores(false)
    }
  }

  // Overlay states
  const [cultureDrawerOpen, setCultureDrawerOpen] = useState(false)
  const [cultureDrawerData, setCultureDrawerData] = useState<{
    name: string
    story: string
    storeId: number
  } | null>(null)
  const [cultureDrawerLoading, setCultureDrawerLoading] = useState(false)
  const [priceModalOpen, setPriceModalOpen] = useState(false)
  const [priceCompareData, setPriceCompareData] = useState<PriceComparison[]>(
    [],
  )
  const [priceCompareProduct, setPriceCompareProduct] = useState<{
    name: string
    price: number
  } | null>(null)
  const [priceLoading, setPriceLoading] = useState(false)
  const [mixMatchOpen, setMixMatchOpen] = useState(false)
  const [mixMatchResults, setMixMatchResults] = useState<MixMatchProduct[]>([])
  const [mixMatchLoading, setMixMatchLoading] = useState(false)
  const [mixMatchProduct, setMixMatchProduct] = useState<{
    name: string
    image_url?: string
  } | null>(null)

  const handleLocate = () => {
    if (!navigator.geolocation) {
      toast.error("Trình duyệt không hỗ trợ Geolocation")
      return
    }
    setIsLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords
        setLat(latitude)
        setLon(longitude)
        if (mapRef.current) {
          mapRef.current.flyTo([latitude, longitude], 15, { animate: true, duration: 1.5 })
        }
        toast.success("Đã cập nhật GPS")
        setIsLocating(false)
      },
      (err) => {
        setIsLocating(false)
        if (err.code === err.PERMISSION_DENIED) {
          toast.error("Vui lòng cấp quyền truy cập vị trí")
        } else {
          toast.error("Không lấy được GPS")
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  // [v2] Bước 6: Realtime Tracking — watchPosition
  useEffect(() => {
    if (!isTracking || !result) return
    if (!navigator.geolocation) return

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setLat(pos.coords.latitude)
        setLon(pos.coords.longitude)
      },
      () => {
        /* silent */
      },
      { enableHighAccuracy: true, maximumAge: 5000 },
    )
    return () => navigator.geolocation.clearWatch(watchId)
  }, [isTracking, result])

  const handleGenerate = async () => {
    // Validation
    if (lat < -90 || lat > 90) {
      toast.error("Vĩ độ (Latitude) phải nằm trong khoảng [-90, 90]")
      return
    }
    if (lon < -180 || lon > 180) {
      toast.error("Kinh độ (Longitude) phải nằm trong khoảng [-180, 180]")
      return
    }
    if (radius <= 0 || radius > 20000) {
      toast.error("Bán kính phải từ 1m đến 20,000m")
      return
    }

    setIsLoading(true)
    setResult(null)
    try {
      const res = await PlannerAPI.generate({
        current_lat: lat,
        current_lon: lon,
        radius,
        keywords,
        weights: { rating: wRating, distance: wDistance, price: wPrice },
        top_n: topN,
        local_hour: new Date().getHours(),
        max_budget: undefined,
      })
      setResult(res.data)
      if (res.data.optimized_route.length === 0)
        toast.warning("Không tìm thấy cửa hàng phù hợp trong bán kính")
    } catch {
      toast.error("Lỗi kết nối Backend / Optimization Service")
    } finally {
      setIsLoading(false)
    }
  }

  const handleLock = async (productId: number, storeId?: number) => {
    if (!storeId) {
      toast.error("Không xác định được cửa hàng để giữ hàng")
      return
    }
    setLockingId(productId)
    try {
      await InventoryAPI.createLock(productId, 1, storeId)
      toast.success("Đã giữ hàng thành công! (15 phút)")
    } catch {
      toast.error("Hết hàng hoặc lỗi hệ thống")
    } finally {
      setLockingId(null)
    }
  }

  // === OVERLAY HANDLERS ===
  const openCultureDrawer = async (storeId: number, name: string) => {
    setCultureDrawerOpen(true)
    setCultureDrawerLoading(true)
    setCultureDrawerData({ name, story: "", storeId })
    try {
      const res = await CultureAPI.getStoreStory(storeId)
      setCultureDrawerData({
        name,
        story: res.data.ai_story || "Chưa có câu chuyện.",
        storeId,
      })
    } catch {
      setCultureDrawerData({
        name,
        story: "Địa điểm này chưa có dữ liệu văn hóa.",
        storeId,
      })
    } finally {
      setCultureDrawerLoading(false)
    }
  }

  const openPriceCompare = async (
    productId: number,
    storeId: number,
    productName: string,
    productPrice: number,
  ) => {
    setPriceModalOpen(true)
    setPriceLoading(true)
    setPriceCompareProduct({ name: productName, price: productPrice })
    try {
      const res = await InventoryAPI.comparePrices(productId, storeId, lat, lon)
      setPriceCompareData(res.data)
    } catch {
      setPriceCompareData([])
    } finally {
      setPriceLoading(false)
    }
  }

  const openMixMatch = async (
    productId: number,
    productName: string,
    imageUrl?: string,
  ) => {
    setMixMatchOpen(true)
    setMixMatchLoading(true)
    setMixMatchProduct({ name: productName, image_url: imageUrl })
    try {
      // Tìm sản phẩm tương tự trong catalog dùng vision API (CLIP 512D)
      const res = await VisionAPI.getProductMatches(productId)
      setMixMatchResults(res.data.matches)
    } catch {
      setMixMatchResults([])
    } finally {
      setMixMatchLoading(false)
    }
  }

  const mapPoints: [number, number][] = useMemo(() => {
    if (!result) return [[lat, lon]]
    return [
      [lat, lon],
      ...result.optimized_route.map((s) => [s.lat, s.lon] as [number, number]),
    ]
  }, [result, lat, lon])

  // GeoJSON style cho đường thực tế từ OSRM
  const geoJsonStyle = {
    color: "#06b6d4",
    weight: 6,
    opacity: 0.85,
    lineCap: "round" as const,
    lineJoin: "round" as const,
  }

  const routeGeoJson = useMemo<FeatureCollection<LineString> | null>(() => {
    if (result?.route_geometry?.geojson) {
      return {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            properties: {},
            geometry: result.route_geometry.geojson as LineString,
          },
        ],
      }
    }
    return frontendRouteGeoJson
  }, [result?.route_geometry?.geojson, frontendRouteGeoJson])

  // Lấy đường đi thực tế từ OSRM qua Frontend nếu Backend không trả về
  useEffect(() => {
    if (!result?.optimized_route || result.optimized_route.length === 0) {
      setFrontendRouteGeoJson(null)
      return
    }
    if (result?.route_geometry?.geojson) {
      setFrontendRouteGeoJson(null)
      return
    }

    const fetchFrontendRoute = async () => {
      const coords = [[lon, lat], ...result.optimized_route.map(s => [s.lon, s.lat])]
      const coordsStr = coords.map(c => `${c[0]},${c[1]}`).join(";")
      try {
        const res = await fetch(`https://router.project-osrm.org/route/v1/driving/${coordsStr}?overview=full&geometries=geojson`)
        const data = await res.json()
        if (data.code === "Ok" && data.routes?.[0]?.geometry) {
          setFrontendRouteGeoJson({
            type: "FeatureCollection",
            features: [
              {
                type: "Feature",
                properties: {},
                geometry: data.routes[0].geometry,
              },
            ],
          })
        }
      } catch (e) {
        console.error("OSRM Frontend Fetch Error:", e)
      }
    }
    fetchFrontendRoute()
  }, [result, lat, lon])

  const fmt = (n: number) =>
    new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
    }).format(n)

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] lg:h-screen overflow-hidden bg-[#FAF9F7] font-sans">
      {/* LEFT PANEL (Floating Card) */}
      <div className="absolute top-4 left-4 w-[380px] flex flex-col max-h-[calc(100vh-6rem)] bg-[#F0F7F7] rounded-2xl shadow-xl shadow-teal-900/5 border border-teal-100 z-[1000] overflow-hidden">
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">
          {/* Origin */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-bold text-[#333333]">
                Điểm xuất phát của bạn
              </label>
              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-500">Auto GPS</span>
                <button
                  onClick={handleLocate}
                  disabled={isLocating}
                  className={`w-10 h-5 rounded-full relative transition-colors ${
                    isLocating ? "bg-zinc-300" : "bg-[#008080]"
                  }`}
                >
                  <div
                    className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                      isLocating ? "translate-x-0" : "translate-x-5"
                    }`}
                  ></div>
                </button>
              </div>
            </div>
            <div className="relative">
              <MapPin className="w-4 h-4 text-[#008080] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={originText}
                onChange={(e) => setOriginText(e.target.value)}
                placeholder="VD: Khách sạn Rex"
                className="w-full bg-white border border-teal-200 rounded-lg pl-9 pr-3 py-2 text-sm text-[#333333] focus:outline-none focus:border-[#008080] focus:ring-1 focus:ring-[#008080] transition-all shadow-sm"
              />
            </div>
          </div>

          {/* Params */}
          <div className="space-y-4 pt-4 border-t border-teal-100">
            <div className="space-y-3">
              <label className="text-sm font-bold text-[#333333]">
                Nhu cầu
              </label>
              <div className="relative">
                <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="vd: cafe, lụa, nón lá..."
                  className="w-full bg-white border border-teal-200 rounded-lg pl-9 pr-3 py-2 text-sm text-[#333333] focus:outline-none focus:border-[#008080] focus:ring-1 focus:ring-[#008080] transition-all shadow-sm"
                />
              </div>
              <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar pb-1">
                {["Cafe", "Mua sắm", "Ăn uống", "Địa điểm"].map((cat) => (
                  <button
                    key={cat}
                    onClick={() =>
                      setKeywords((prev) =>
                        prev ? `${prev}, ${cat}` : cat
                      )
                    }
                    className="px-3 py-1 bg-white border border-zinc-200 text-[#555555] rounded-full text-xs font-medium hover:bg-teal-50 hover:text-[#008080] hover:border-[#008080] transition-colors whitespace-nowrap shadow-sm"
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-bold text-[#333333]">
                  Bán kính: {(radius / 1000).toFixed(1)} km
                </label>
              </div>
              <input
                type="range"
                min={500}
                max={20000}
                step={100}
                value={radius}
                onChange={(e) => setRadius(parseInt(e.target.value, 10))}
                className="w-full h-1 bg-zinc-200 rounded-lg appearance-none cursor-pointer accent-[#008080]"
              />
            </div>

            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-bold text-[#333333]">
                  Gợi ý tối đa
                </label>
                <span className="text-sm font-medium text-[#008080]">{topN} điểm</span>
              </div>
              <input
                type="range"
                min={1}
                max={10}
                step={1}
                value={topN}
                onChange={(e) => setTopN(parseInt(e.target.value, 10))}
                className="w-full h-1 bg-zinc-200 rounded-lg appearance-none cursor-pointer accent-[#008080]"
              />
            </div>
          </div>

          {/* Weights as Chips */}
          <div className="space-y-3 pt-4 border-t border-teal-100">
            <label className="text-sm font-bold text-[#333333]">
              Tiêu chí ưu tiên
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: "Ưu tiên Gần nhất", r: 0, d: 1, p: 0 },
                { label: "Đánh giá Cao nhất", r: 1, d: 0, p: 0 },
                { label: "Ngon - Bổ - Rẻ", r: 0.5, d: 0, p: 1 },
                { label: "Cân bằng nhất", r: 0.4, d: 0.3, p: 0.3 },
              ].map((chip) => {
                const isActive = wRating === chip.r && wDistance === chip.d && wPrice === chip.p;
                return (
                  <button
                    key={chip.label}
                    onClick={() => {
                      setWRating(chip.r)
                      setWDistance(chip.d)
                      setWPrice(chip.p)
                    }}
                    className={`px-3 py-2 rounded-lg text-xs font-medium transition-all shadow-sm ${
                      isActive
                        ? "bg-[#008080] text-white"
                        : "bg-white border border-zinc-200 text-[#555555] hover:bg-teal-50"
                    }`}
                  >
                    {chip.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            data-testid="itinerary-generate-button"
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-[#008080] to-[#00A3A3] hover:from-[#007070] hover:to-[#008A8A] text-white font-bold text-sm py-3.5 rounded-[20px] flex items-center justify-center gap-2 transition-all shadow-md shadow-[#008080]/30 disabled:opacity-50 disabled:cursor-not-allowed mt-4"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Đang tính toán...
              </>
            ) : (
              "TỰ ĐỘNG LÊN LỊCH"
            )}
          </button>
        </div>
      </div>

      {/* MAP */}
      <div className="absolute inset-0 z-0">
        {/* Shopping Filter Tab */}
        <div className="absolute top-4 left-[380px] right-0 z-[400] flex items-center justify-center pointer-events-none">
          <div className="bg-white/90 backdrop-blur-md border border-zinc-200 rounded-full p-1.5 flex items-center gap-1 shadow-lg pointer-events-auto">
            {["Đặc sản", "Quần áo lụa", "Đồ lưu niệm", "Tất cả"].map((cat) => (
              <button
                key={cat}
                onClick={() => handleShoppingCategory(cat)}
                disabled={loadingNearbyStores}
                className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                  selectedShoppingCategory === cat
                    ? "bg-[#2B0B3F] text-white shadow-md"
                    : "text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100"
                } disabled:opacity-50 flex items-center gap-2`}
              >
                {selectedShoppingCategory === cat && loadingNearbyStores && (
                  <Loader2 className="w-3 h-3 animate-spin" />
                )}
                {cat}
              </button>
            ))}
          </div>
        </div>

        {errorNearbyStores && (
          <div className="absolute top-20 left-1/2 -translate-x-1/2 z-[400] bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-3 py-1.5 rounded-full">
            {errorNearbyStores}
          </div>
        )}

        <MapContainer
          ref={mapRef}
          center={[lat, lon]}
          zoom={14}
          className="w-full h-full"
          zoomControl={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          />
          <FitBounds points={mapPoints} />
          <Marker position={[lat, lon]} icon={userIcon}>
            <Popup>
              <div className="text-xs font-mono p-1">
                <strong className="text-emerald-500">📍 Vị trí của bạn</strong>
                <br />
                {lat.toFixed(5)}, {lon.toFixed(5)}
              </div>
            </Popup>
          </Marker>
          <Circle
            center={[lat, lon]}
            radius={radius}
            pathOptions={{
              color: "#8b5cf6",
              fillColor: "#8b5cf6",
              fillOpacity: 0.05,
              weight: 1,
              dashArray: "5, 10",
            }}
          />
          {result?.optimized_route.map((stop: StopInRoute) => (
            <Marker
              key={stop.order}
              position={[stop.lat, stop.lon]}
              icon={getStopIcon(stop.order, stop.order === 1)}
            >
              <Popup>
                <div className="text-xs font-mono p-1 min-w-[150px]">
                  <strong className="text-violet-400 text-sm block mb-1">
                    #{stop.order} {stop.name}
                  </strong>
                  {stop.rating && (
                    <span className="text-yellow-500">⭐ {stop.rating}</span>
                  )}
                  {stop.category && (
                    <span className="text-zinc-400 ml-2">{stop.category}</span>
                  )}
                  <br />
                  <span className="text-emerald-400">
                    {stop.products.length} sản phẩm
                  </span>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* Nearby Stores Markers */}
          {nearbyStores.map((store) => (
            <Marker
              key={store.store_id}
              position={[store.lat, store.lon]}
              icon={storeIcon}
            >
              <Popup>
                <div className="text-xs font-mono p-1 min-w-[150px]">
                  <strong className="text-amber-500 text-sm block mb-1">
                    🛍️ {store.name}
                  </strong>
                  {store.category && (
                    <span className="text-zinc-400 bg-black/10 px-1 rounded block w-fit mb-1">
                      {store.category}
                    </span>
                  )}
                  {store.rating !== null && store.rating !== undefined && (
                    <span className="text-yellow-500 block mb-1">
                      ⭐ {store.rating}
                    </span>
                  )}
                  {store.distance_m !== undefined &&
                    store.distance_m !== null && (
                      <span className="text-cyan-500 font-bold block mb-2">
                        Cách đây {store.distance_m}m
                      </span>
                    )}
                  <button
                    onClick={() =>
                      openCultureDrawer(store.store_id!, store.name)
                    }
                    className="w-full bg-amber-500 text-zinc-950 font-bold rounded px-2 py-1.5 hover:bg-amber-600 transition-colors shadow-lg"
                  >
                    Xem thông tin
                  </button>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* OSRM GeoJSON — đường đi thực tế uốn theo phố */}
          {routeGeoJson && (
            <GeoJSON
              key={JSON.stringify(routeGeoJson)}
              data={routeGeoJson}
              style={geoJsonStyle}
            />
          )}
          {/* Fallback: đường chập nối thẳng khi OSRM không có geometry (cả FE & BE đều lỗi) */}
          {!routeGeoJson &&
            result?.optimized_route &&
            result.optimized_route.length > 0 &&
            (() => {
              const fallbackLine: [number, number][] = [
                [lat, lon],
                ...result.optimized_route.map(
                  (s) => [s.lat, s.lon] as [number, number],
                ),
              ]
              return (
                <Polyline
                  positions={fallbackLine}
                  pathOptions={{
                    color: "#06b6d4",
                    weight: 6,
                    opacity: 0.85,
                    lineCap: "round",
                    lineJoin: "round",
                    fill: false,
                  }}
                />
              )
            })()}
        </MapContainer>

        {/* Floating Status */}
        {isLoading && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-white rounded-2xl px-6 py-3 flex items-center gap-3 shadow-xl border border-zinc-200">
            <Loader2 className="w-5 h-5 text-[#2B0B3F] animate-spin" />
            <div>
              <p className="text-sm text-zinc-800 font-bold">
                Đang tự động tính toán lộ trình tối ưu...
              </p>
            </div>
          </div>
        )}

        {/* RIGHT SIDE PANELS */}
        {result && (
          <div className="absolute right-4 top-4 bottom-4 w-[500px] pointer-events-none flex flex-col gap-4 z-[1000]">
            {/* Weather Panel */}
            <div className="pointer-events-auto bg-white rounded-2xl shadow-xl border border-zinc-100 p-5 w-fit self-end flex items-center gap-4">
              <div>
                <p className="font-bold text-base text-zinc-800">Thời tiết</p>
                <p className="text-sm text-zinc-600">
                  {result.weather?.temperature ? `TP.HCM ${result.weather.temperature}°C, ${result.weather.condition}` : "Đang cập nhật..."}
                </p>
              </div>
              <Thermometer className="w-8 h-8 text-orange-400" />
            </div>

            {/* Suggested Itinerary Timeline */}
            <div className="pointer-events-auto bg-white rounded-2xl shadow-2xl border border-zinc-100 p-6 flex-1 overflow-hidden flex flex-col">
              <h2 className="text-lg font-bold text-zinc-800 mb-6">Lịch trình gợi ý</h2>
              <div className="relative pl-4 flex-1 overflow-y-auto custom-scrollbar pr-2">
                {/* Vertical Line */}
                <div className="absolute left-[23px] top-4 bottom-4 w-0.5 bg-[#F08080]/30" />
                
                <div className="space-y-8">
                  {result.optimized_route.map((stop: StopInRoute, idx: number) => {
                    const time = new Date(2024, 1, 1, 9, 0)
                    time.setMinutes(time.getMinutes() + idx * 45)
                    const timeStr = time.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
                    
                    return (
                    <div key={stop.order} className="relative flex items-start gap-5 group">
                      {/* Node circle */}
                      <div className={`relative z-10 w-5 h-5 rounded-full mt-1.5 shrink-0 shadow-sm outline outline-[5px] outline-white transition-transform group-hover:scale-125
                        ${idx === 0 ? "bg-[#F08080]" : "bg-white border-[4px] border-[#F08080]"}
                      `} />
                      
                      {/* Content */}
                      <div className="flex-1 min-w-0 bg-[#FAF9F7] p-4 rounded-xl shadow-sm border border-zinc-100/50">
                        <div className="flex justify-between items-start mb-1">
                          <p className="font-bold text-[#333333] text-base truncate pr-2 group-hover:text-[#008080] transition-colors">
                            {stop.order}. {stop.name}
                          </p>
                          <span className="text-sm font-bold text-[#F08080] shrink-0 mt-0.5 tabular-nums">
                            {timeStr}
                          </span>
                        </div>
                        <p className="text-sm text-[#555555] font-medium truncate mb-3">
                          {stop.category || "Địa danh"}
                        </p>
                        
                        <div className="flex items-center gap-3 mt-3">
                          <button
                            onClick={() => setExpandedStop(expandedStop === stop.order ? null : stop.order)}
                            className={`text-xs font-bold px-3 py-1.5 rounded-full border transition-colors ${expandedStop === stop.order ? "bg-[#38235D] text-white border-[#38235D]" : "bg-white text-zinc-600 border-zinc-200 hover:bg-zinc-50"}`}
                          >
                            {stop.products.length} Món đồ {expandedStop === stop.order ? "▲" : "▼"}
                          </button>
                          {stop.store_id && (
                            <button
                              onClick={() => navigate({ to: "/culture" })}
                              className="text-xs font-bold text-[#008080] hover:text-[#00A3A3] transition-colors"
                            >
                              Khám phá
                            </button>
                          )}
                        </div>

                        {/* Expanded Products */}
                        {expandedStop === stop.order && stop.products.length > 0 && (
                          <div className="mt-4 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
                            {stop.products.map(p => (
                              <div key={p.product_id} className="flex gap-4 bg-white p-3 rounded-xl border border-zinc-200 shadow-sm">
                                <div className="w-16 h-16 rounded-lg object-cover border border-zinc-100 shrink-0 overflow-hidden">
                                  <img src={p.image_url || "https://placehold.co/100x100"} alt={p.name} className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                                </div>
                                <div className="flex-1 min-w-0 flex flex-col justify-center">
                                  <p className="text-sm font-bold text-zinc-800 truncate">{p.name}</p>
                                  <p className="text-xs text-[#008080] font-bold tabular-nums mt-0.5">
                                    {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(p.price)}
                                  </p>
                                  <div className="flex flex-wrap gap-2 mt-2">
                                    <button
                                      onClick={() => openPriceCompare(p.product_id, stop.store_id!, p.name, p.price)}
                                      className="text-xs font-medium text-zinc-600 bg-zinc-50 px-2.5 py-1.5 rounded-md border border-zinc-200 hover:bg-zinc-100 transition-colors flex items-center gap-1.5 shadow-sm whitespace-nowrap"
                                    >
                                      <BarChart3 className="w-3.5 h-3.5 text-[#008080]" /> So sánh giá
                                    </button>
                                    <button
                                      onClick={() => openMixMatch(p.product_id, p.name, p.image_url)}
                                      className="text-xs font-medium text-zinc-600 bg-zinc-50 px-2.5 py-1.5 rounded-md border border-zinc-200 hover:bg-zinc-100 transition-colors flex items-center gap-1.5 shadow-sm whitespace-nowrap"
                                    >
                                      <Sparkles className="w-3.5 h-3.5 text-[#008080]" /> Phối đồ AI
                                    </button>
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleLock(p.product_id, stop.store_id)}
                                  disabled={lockingId === p.product_id}
                                  className="self-center shrink-0 bg-white border border-[#F08080] hover:bg-[#F08080] hover:text-white text-[#F08080] text-xs font-bold px-4 py-2.5 rounded-lg transition-colors disabled:opacity-50 flex flex-col items-center gap-1 shadow-sm"
                                >
                                  {lockingId === p.product_id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Lock className="w-4 h-4" />
                                  )}
                                  Giữ
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )})}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ═══ OVERLAY 1: Culture Drawer (Right Side) ═══ */}
      <Sheet open={cultureDrawerOpen} onOpenChange={setCultureDrawerOpen}>
        <SheetContent
          side="right"
          className="w-[400px] sm:max-w-[420px] overflow-y-auto"
        >
          <SheetHeader className="border-b border-white/5 pb-4">
            <SheetTitle className="flex items-center gap-2 text-amber-400">
              <BookOpen className="w-5 h-5" /> Câu chuyện văn hóa
            </SheetTitle>
            <p className="text-xs text-zinc-500 font-mono">
              {cultureDrawerData?.name}
            </p>
          </SheetHeader>
          <div className="p-5 space-y-6">
            {cultureDrawerLoading ? (
              <div className="flex flex-col items-center py-12">
                <Loader2 className="w-8 h-8 text-amber-400 animate-spin mb-3" />
                <p className="text-xs text-amber-300/70 font-mono animate-pulse">
                  Gemini AI đang viết câu chuyện...
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4">
                  <p className="text-[10px] text-amber-400 font-mono uppercase tracking-wider mb-3 flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3" /> AI Storyteller
                  </p>
                  <p className="text-sm text-zinc-200 leading-relaxed">
                    {cultureDrawerData?.story}
                  </p>
                </div>
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>

      {/* ═══ OVERLAY 2: Price Compare Modal (Bottom Sheet) ═══ */}
      <Sheet open={priceModalOpen} onOpenChange={setPriceModalOpen}>
        <SheetContent
          side="bottom"
          className="max-h-[60vh] overflow-y-auto rounded-t-3xl"
        >
          <SheetHeader className="pb-3">
            <SheetTitle className="flex items-center gap-2 text-cyan-400">
              <BarChart3 className="w-5 h-5" /> So sánh giá:{" "}
              {priceCompareProduct?.name}
            </SheetTitle>
            <p className="text-xs text-zinc-500 font-mono">
              Giá tại các cửa hàng trong bán kính 5km
            </p>
          </SheetHeader>
          <div className="px-5 pb-6">
            {priceLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
              </div>
            ) : priceCompareData.length > 0 ? (
              <div className="space-y-2">
                {priceCompareData.map((item) => (
                  <div
                    key={item.store_id}
                    className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${item.is_current ? "bg-cyan-500/10 border-cyan-500/30" : "bg-white/[0.02] border-white/5 hover:border-white/10"}`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white font-medium truncate flex items-center gap-1.5">
                        {item.is_current && (
                          <span className="text-[9px] bg-cyan-500 text-black px-1.5 py-0.5 rounded font-mono font-bold">
                            ĐANG XEM
                          </span>
                        )}
                        {item.store_name}
                      </p>
                      <p className="text-[10px] text-zinc-500 truncate">
                        {item.address}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-bold font-mono text-emerald-400">
                        {fmt(item.price)}
                      </p>
                      <p className="text-[10px] text-zinc-500 font-mono">
                        Còn {item.stock}
                      </p>
                    </div>
                    {/* Visual bar */}
                    <div className="w-20 h-2 bg-zinc-800 rounded-full overflow-hidden shrink-0">
                      <div
                        className={`h-full rounded-full ${item.is_current ? "bg-cyan-500" : "bg-violet-500"}`}
                        style={{
                          width: `${Math.min(100, (item.stock / 20) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-zinc-500 text-sm py-8">
                Không tìm thấy cửa hàng nào khác bán sản phẩm này.
              </p>
            )}
          </div>
        </SheetContent>
      </Sheet>

      {/* ═══ OVERLAY 3: AI Mix & Match (Bottom Sheet) ═══ */}
      <Sheet open={mixMatchOpen} onOpenChange={setMixMatchOpen}>
        <SheetContent
          side="bottom"
          className="max-h-[70vh] overflow-y-auto rounded-t-3xl"
        >
          <SheetHeader className="pb-3">
            <SheetTitle className="flex items-center gap-2 text-purple-400">
              <Sparkles className="w-5 h-5" /> AI Mix & Match — Phối đồ thông
              minh
            </SheetTitle>
            <p className="text-xs text-zinc-500 font-mono">
              CLIP 512D · pgvector Cosine Similarity
            </p>
          </SheetHeader>
          <div className="px-5 pb-6">
            {mixMatchProduct && (
              <div className="flex items-center gap-3 mb-4 p-3 bg-purple-500/10 border border-purple-500/20 rounded-xl">
                <div className="w-16 h-16 rounded-xl overflow-hidden bg-zinc-800 shrink-0">
                  <img
                    src={
                      mixMatchProduct.image_url ||
                      "https://via.placeholder.com/100"
                    }
                    className="w-full h-full object-cover"
                  />
                </div>
                <div>
                  <p className="text-[10px] text-purple-300 font-mono uppercase">
                    Đang phối với
                  </p>
                  <p className="text-sm text-white font-bold truncate">
                    {mixMatchProduct.name}
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-purple-400 ml-auto animate-pulse" />
              </div>
            )}

            {mixMatchLoading ? (
              <div className="flex flex-col items-center py-8">
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-3" />
                <p className="text-xs text-purple-300 font-mono">
                  Đang tìm sản phẩm tương tự...
                </p>
              </div>
            ) : mixMatchResults.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {mixMatchResults.map((prod) => (
                  <div
                    key={prod.product_id}
                    className="bg-white/[0.03] border border-white/5 rounded-2xl overflow-hidden hover:border-purple-500/30 transition-all group"
                  >
                    <div className="aspect-square bg-zinc-900 overflow-hidden">
                      <img
                        src={
                          prod.image_url || "https://via.placeholder.com/200"
                        }
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        referrerPolicy="no-referrer"
                      />
                    </div>
                    <div className="p-3 space-y-1.5">
                      <p className="text-xs text-white font-medium truncate">
                        {prod.name}
                      </p>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-emerald-400 font-mono">
                          {prod.price.toLocaleString()}₫
                        </span>
                        <span
                          className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${prod.match_score >= 85 ? "bg-purple-500/20 text-purple-300" : "bg-zinc-800 text-zinc-400"}`}
                        >
                          {prod.match_score}%
                        </span>
                      </div>
                      <button
                        onClick={() =>
                          handleLock(prod.product_id, prod.store_id)
                        }
                        className="w-full mt-1 bg-gradient-to-r from-purple-600 to-pink-600 text-white text-[9px] font-mono uppercase tracking-wider py-1.5 rounded-lg hover:shadow-[0_0_15px_rgba(168,85,247,0.5)] transition-all flex items-center justify-center gap-1"
                      >
                        <ShoppingBag className="w-3 h-3" /> Thêm vào giỏ
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-zinc-500 text-sm py-8">
                Chưa có sản phẩm matching. Cần products có vector embeddings.
              </p>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}

export default ItineraryPage
