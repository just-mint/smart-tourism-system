import { createFileRoute } from "@tanstack/react-router"
import L from "leaflet"
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Clock,
  Info,
  Loader2,
  LocateFixed,
  Lock,
  MapPin,
  Navigation2,
  Package,
  Route as RouteIcon,
  Search,
  ShoppingBag,
  Sparkles,
  Star,
  Thermometer,
  Zap,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"
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
  PlannerAPI,
  type PlannerResponse,
  type PriceComparison,
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
  `<div class="w-5 h-5 bg-emerald-500 rounded-full border-[3px] border-black shadow-[0_0_20px_rgba(16,185,129,1)]"></div>`,
  20,
)
const getStopIcon = (num: number) =>
  createDivIcon(
    `
  <div class="w-8 h-8 bg-gradient-to-br from-violet-600 to-fuchsia-500 rounded-full border-2 border-white flex items-center justify-center text-white font-bold text-sm shadow-[0_0_20px_rgba(139,92,246,0.9)]">${num}</div>
`,
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
  const [radius, setRadius] = useState(3000)
  const [keywords, setKeywords] = useState("")
  const [topN, setTopN] = useState(5)
  const [wRating, setWRating] = useState(0.4)
  const [wDistance, setWDistance] = useState(0.3)
  const [wPrice, setWPrice] = useState(0.3)
  const [maxBudget, setMaxBudget] = useState<number | "">("")
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<PlannerResponse | null>(null)
  const [expandedStop, setExpandedStop] = useState<number | null>(null)
  const [lockingId, setLockingId] = useState<number | null>(null)
  const [isTracking, setIsTracking] = useState(false)

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
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(pos.coords.latitude)
          setLon(pos.coords.longitude)
          toast.success("Đã cập nhật GPS")
        },
        () => toast.error("Không lấy được GPS"),
      )
    }
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
<<<<<<< HEAD
=======
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

>>>>>>> origin/main
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
        max_budget: maxBudget === "" ? undefined : maxBudget,
      })
      setResult(res.data)
      if (res.data.optimized_route.length > 0)
        toast.success(`Đã tối ưu ${res.data.optimized_route.length} điểm dừng!`)
      else toast.warning("Không tìm thấy cửa hàng phù hợp trong bán kính")
    } catch {
      toast.error("Lỗi kết nối Backend / Optimization Service")
    } finally {
      setIsLoading(false)
    }
  }

  const handleLock = async (productId: number) => {
    setLockingId(productId)
    try {
      await InventoryAPI.createLock(productId, 1)
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
      const res = await CultureAPI.getPlaceStory(storeId)
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
      const res = await VisionAPI.getMixMatch(productId)
      setMixMatchResults(res.data.matches)
    } catch {
      setMixMatchResults([])
    } finally {
      setMixMatchLoading(false)
    }
  }

  const mapPoints: [number, number][] = useMemo(() => {
    if (!result) return [[lat, lon]]
<<<<<<< HEAD
    const pts: [number, number][] = [[lat, lon]]
    result.optimized_route.forEach((s) => pts.push([s.lat, s.lon]))
    return pts
=======
    return [
      [lat, lon],
      ...result.optimized_route.map((s) => [s.lat, s.lon] as [number, number]),
    ]
>>>>>>> origin/main
  }, [result, lat, lon])

  // GeoJSON style cho đường thực tế từ OSRM
  const geoJsonStyle = {
    color: "#3b82f6",
    weight: 5,
    opacity: 0.7,
    lineCap: "round" as const,
    lineJoin: "round" as const,
  }

  const fmt = (n: number) =>
    new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
    }).format(n)

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] overflow-hidden bg-zinc-950 flex">
      {/* LEFT PANEL */}
      <div className="w-[420px] shrink-0 flex flex-col h-full border-r border-white/5 bg-black/60 backdrop-blur-2xl z-20">
        {/* Header */}
        <div className="p-5 border-b border-white/5 bg-gradient-to-r from-violet-500/10 to-fuchsia-500/10">
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-400 to-fuchsia-400 flex items-center gap-2 font-mono tracking-wide">
            <Zap className="w-6 h-6 text-violet-400" /> SMART_PLANNER
          </h1>
          <p className="text-[10px] text-zinc-500 font-mono mt-1 uppercase tracking-widest">
            O2O 6-Step Orchestrator Engine
          </p>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-5 space-y-5">
          {/* Origin */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1">
                <LocateFixed className="w-3 h-3 text-emerald-400" /> Vị trí xuất
                phát
              </label>
              <button
                onClick={handleLocate}
                className="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-2 py-1 rounded-full hover:bg-emerald-500/20 transition-colors"
              >
                Auto GPS
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                step="any"
                value={lat}
                onChange={(e) => setLat(parseFloat(e.target.value) || 0)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-violet-500/50"
                placeholder="Latitude"
              />
              <input
                type="number"
                step="any"
                value={lon}
                onChange={(e) => setLon(parseFloat(e.target.value) || 0)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-violet-500/50"
                placeholder="Longitude"
              />
            </div>
          </div>

          {/* Params */}
          <div className="space-y-2">
            <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1">
              <Search className="w-3 h-3 text-cyan-400" /> Nhu cầu
            </label>
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="vd: cafe, lụa, nón lá, quà lưu niệm"
              className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2.5 text-xs font-mono text-white focus:outline-none focus:border-violet-500/50"
            />
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-zinc-500 font-mono block mb-1">
                  Bán kính (m)
                </label>
                <input
                  type="number"
                  value={radius}
                  onChange={(e) =>
                    setRadius(parseInt(e.target.value, 10) || 2000)
                  }
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-violet-500/50"
                />
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 font-mono block mb-1">
                  Top N điểm
                </label>
                <input
                  type="number"
                  value={topN}
                  min={1}
                  max={10}
                  onChange={(e) => setTopN(parseInt(e.target.value, 10) || 5)}
                  className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-violet-500/50"
                />
              </div>
            </div>
            <div>
              <label className="text-[10px] text-zinc-500 font-mono block mb-1">
                💰 Ngân sách tối đa (VNĐ)
              </label>
              <input
                type="number"
                value={maxBudget}
                onChange={(e) =>
                  setMaxBudget(
                    e.target.value === ""
                      ? ""
                      : parseInt(e.target.value, 10) || 0,
                  )
                }
                placeholder="Không giới hạn"
                className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-violet-500/50"
              />
            </div>
          </div>

          {/* Weights */}
          <div className="space-y-2 p-3 bg-white/[0.02] border border-white/5 rounded-xl">
            <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1">
              <Star className="w-3 h-3 text-yellow-400" /> Trọng số ưu tiên
            </label>
            {[
              {
                label: "Rating",
                val: wRating,
                set: setWRating,
                color: "text-yellow-400",
              },
              {
                label: "Khoảng cách",
                val: wDistance,
                set: setWDistance,
                color: "text-cyan-400",
              },
              {
                label: "Giá cả",
                val: wPrice,
                set: setWPrice,
                color: "text-emerald-400",
              },
            ].map((w) => (
              <div key={w.label} className="flex items-center gap-2">
                <span className={`text-[10px] font-mono w-20 ${w.color}`}>
                  {w.label}
                </span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={w.val}
                  onChange={(e) => w.set(parseFloat(e.target.value))}
                  className="flex-1 h-1 accent-violet-500"
                />
                <span className="text-[10px] font-mono text-zinc-400 w-8 text-right">
                  {w.val}
                </span>
              </div>
            ))}
          </div>

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
<<<<<<< HEAD
=======
            data-testid="itinerary-generate-button"
>>>>>>> origin/main
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-mono uppercase tracking-wider text-xs py-3.5 rounded-xl flex items-center justify-center gap-2 transition-all shadow-[0_0_30px_rgba(139,92,246,0.4)] hover:shadow-[0_0_40px_rgba(139,92,246,0.6)] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Đang tối ưu hóa...
              </>
            ) : (
              <>
                <RouteIcon className="w-4 h-4" /> Tự động lên lịch
              </>
            )}
          </button>

          {/* RESULTS */}
          {result && (
            <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
              {/* Metrics */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  {
                    icon: <MapPin className="w-3.5 h-3.5" />,
                    label: "Điểm dừng",
                    value: `${result.optimized_route.length}`,
                    color: "text-violet-400",
                    bg: "bg-violet-500/10 border-violet-500/20",
                  },
                  {
                    icon: <Navigation2 className="w-3.5 h-3.5" />,
                    label: "Quãng đường",
                    value: `${result.metrics.total_distance_km}km`,
                    color: "text-cyan-400",
                    bg: "bg-cyan-500/10 border-cyan-500/20",
                  },
                  {
                    icon: <Package className="w-3.5 h-3.5" />,
                    label: "Tổng giá",
                    value: fmt(result.metrics.total_price),
                    color: "text-emerald-400",
                    bg: "bg-emerald-500/10 border-emerald-500/20",
                  },
                ].map((m, i) => (
                  <div
                    key={i}
                    className={`p-2.5 rounded-xl border ${m.bg} text-center`}
                  >
                    <div
                      className={`flex items-center justify-center gap-1 ${m.color} mb-1`}
                    >
                      {m.icon}
                    </div>
                    <p className="text-[10px] text-zinc-500 font-mono">
                      {m.label}
                    </p>
                    <p className={`text-xs font-bold font-mono ${m.color}`}>
                      {m.value}
                    </p>
                  </div>
                ))}
              </div>

              {result.weather && (
                <div className="flex items-center gap-2 p-2.5 bg-white/[0.03] border border-white/5 rounded-xl">
                  <Thermometer className="w-4 h-4 text-orange-400" />
                  <span className="text-xs font-mono text-zinc-300">
                    {result.weather.temperature}°C
                  </span>
                  <span className="text-[10px] text-zinc-500">·</span>
                  <span className="text-xs font-mono text-zinc-400">
                    {result.weather.condition}
                  </span>
                </div>
              )}

              {/* [v2] Context Awareness Badges */}
              {result.context_applied && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                    <Clock className="w-4 h-4 text-amber-400" />
                    <div>
                      <p className="text-[10px] text-amber-300/70 font-mono uppercase tracking-tighter">
                        AI Time-Aware
                      </p>
                      <p className="text-xs text-amber-200 font-medium">
                        {result.context_applied.time_description}
                      </p>
                    </div>
                  </div>

                  {result.context_applied.weather_condition !== "Clear" &&
                    result.context_applied.weather_condition !== "Unknown" && (
                      <div className="flex items-center gap-2 p-2.5 bg-sky-500/10 border border-sky-500/20 rounded-xl">
                        <Info className="w-4 h-4 text-sky-400" />
                        <p className="text-xs text-sky-200">
                          {result.context_applied.weather_reason}
                        </p>
                      </div>
                    )}
                </div>
              )}

              {/* Duration từ OSRM */}
              {result.route_geometry?.duration_minutes && (
                <div className="flex items-center gap-2 p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                  <Clock className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-mono text-blue-300">
                    Thời gian ước tính:
                  </span>
                  <span className="text-xs font-bold font-mono text-blue-400">
                    {result.route_geometry.duration_minutes} phút
                  </span>
                </div>
              )}

              {result.metrics.routing_fallback_used && (
                <div className="flex items-center gap-2 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded-xl">
                  <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
                  <span className="text-[10px] text-yellow-400 font-mono">
                    OSRM không khả dụng — hiển thị đường chim bay
                  </span>
                </div>
              )}

              {/* [v2] Bước 6: Realtime Tracking Toggle */}
              <button
                onClick={() => {
                  setIsTracking(!isTracking)
                  toast.info(
                    isTracking
                      ? "Đã tắt theo dõi GPS"
                      : "Bắt đầu theo dõi vị trí realtime",
                  )
                }}
                className={`w-full flex items-center justify-center gap-2 p-2.5 rounded-xl text-xs font-mono transition-all ${
                  isTracking
                    ? "bg-emerald-500/20 border border-emerald-500/30 text-emerald-400"
                    : "bg-white/[0.03] border border-white/5 text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <LocateFixed
                  className={`w-4 h-4 ${isTracking ? "animate-pulse" : ""}`}
                />
                {isTracking
                  ? "🔴 Đang theo dõi GPS Realtime"
                  : "Bật theo dõi vị trí Realtime"}
              </button>

              {/* Stops */}
              <div className="space-y-2">
                <h3 className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
                  <RouteIcon className="w-3.5 h-3.5 text-violet-400" /> Lộ trình
                  tối ưu ({result.optimized_route.length} điểm)
                </h3>
                {result.optimized_route.map((stop: StopInRoute) => (
                  <div
                    key={stop.order}
                    className="bg-white/[0.03] border border-white/5 rounded-xl overflow-hidden hover:border-violet-500/30 transition-colors"
                  >
                    <button
                      onClick={() =>
                        setExpandedStop(
                          expandedStop === stop.order ? null : stop.order,
                        )
                      }
                      className="w-full p-3 flex items-center gap-3 text-left"
                    >
                      <div className="w-7 h-7 bg-gradient-to-br from-violet-600 to-fuchsia-500 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0">
                        {stop.order}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">
                          {stop.name}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          {stop.rating && (
                            <span className="text-[10px] text-yellow-400 font-mono">
                              ⭐{stop.rating}
                            </span>
                          )}
                          {stop.category && (
                            <span className="text-[10px] text-zinc-500">
                              {stop.category}
                            </span>
                          )}
                          {stop.final_score && (
                            <span className="text-[10px] text-violet-400 font-mono">
                              Score: {stop.final_score}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-zinc-500 font-mono">
                          {stop.products.length} SP
                        </span>
                        {expandedStop === stop.order ? (
                          <ChevronUp className="w-4 h-4 text-zinc-500" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-zinc-500" />
                        )}
                      </div>
                    </button>
                    {expandedStop === stop.order &&
                      stop.products.length > 0 && (
                        <div className="border-t border-white/5 p-3 space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
                          {stop.products.map((p) => (
                            <div
                              key={p.product_id}
                              className="p-2.5 bg-black/30 rounded-xl space-y-2"
                            >
                              <div className="flex items-center gap-3">
                                <div className="w-12 h-12 rounded-lg overflow-hidden bg-zinc-900 shrink-0 border border-white/5">
                                  <img
                                    src={
                                      p.image_url ||
                                      "https://via.placeholder.com/80"
                                    }
                                    alt={p.name}
                                    className="w-full h-full object-cover"
<<<<<<< HEAD
=======
                                    referrerPolicy="no-referrer"
>>>>>>> origin/main
                                  />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="text-[11px] text-zinc-200 truncate">
                                    {p.name}
                                  </p>
                                  <p className="text-[10px] font-bold text-emerald-400 font-mono">
                                    {fmt(p.price)}
                                  </p>
                                </div>
                                <button
                                  onClick={() => handleLock(p.product_id)}
                                  disabled={lockingId === p.product_id}
                                  className="bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white text-[9px] font-mono uppercase tracking-wider px-2.5 py-1.5 rounded-lg hover:shadow-[0_0_15px_rgba(139,92,246,0.6)] transition-all disabled:opacity-50 flex items-center gap-1 shrink-0"
                                >
                                  {lockingId === p.product_id ? (
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                  ) : (
                                    <Lock className="w-3 h-3" />
                                  )}
                                  Giữ
                                </button>
                              </div>
                              {/* Action Buttons Row */}
                              <div className="flex gap-1.5">
                                <button
                                  onClick={() =>
                                    openPriceCompare(
                                      p.product_id,
                                      stop.store_id!,
                                      p.name,
                                      p.price,
                                    )
                                  }
                                  className="flex-1 flex items-center justify-center gap-1 text-[9px] font-mono text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 rounded-lg py-1.5 hover:bg-cyan-500/20 transition-all"
                                >
                                  <BarChart3 className="w-3 h-3" /> So sánh giá
                                </button>
                                <button
                                  onClick={() =>
                                    openMixMatch(
                                      p.product_id,
                                      p.name,
                                      p.image_url,
                                    )
                                  }
                                  className="flex-1 flex items-center justify-center gap-1 text-[9px] font-mono text-purple-400 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20 rounded-lg py-1.5 hover:from-purple-500/20 hover:to-pink-500/20 transition-all"
                                >
                                  <Sparkles className="w-3 h-3" /> Phối đồ AI
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    {/* Culture Drawer Trigger */}
                    {expandedStop === stop.order && stop.store_id && (
                      <div className="border-t border-white/5 p-3">
                        <button
                          onClick={() =>
                            openCultureDrawer(stop.store_id!, stop.name)
                          }
                          className="w-full flex items-center justify-center gap-2 text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-xl py-2 hover:bg-amber-500/20 font-mono transition-all"
                        >
                          <BookOpen className="w-3.5 h-3.5" /> 📖 Xem câu chuyện
                          văn hóa & Reviews
                        </button>
                      </div>
                    )}{" "}
                  </div>
                ))}
              </div>

              <p className="text-[10px] text-zinc-600 font-mono text-center">
                Đã quét {result.total_candidates} ứng viên · Bước 2→4 hoàn tất
              </p>
            </div>
          )}
        </div>
      </div>

      {/* MAP */}
      <div className="flex-1 relative z-0">
        <MapContainer
          center={[lat, lon]}
          zoom={14}
          className="w-full h-full"
          zoomControl={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://osm.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
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
              icon={getStopIcon(stop.order)}
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
          {/* OSRM GeoJSON — đường đi thực tế uốn theo phố */}
          {result?.route_geometry?.geojson && (
            <GeoJSON
              key={JSON.stringify(result.route_geometry.geojson)}
<<<<<<< HEAD
              data={result.route_geometry.geojson as any}
=======
              data={{
                type: "FeatureCollection",
                features: [
                  {
                    type: "Feature",
                    properties: {},
                    geometry: result.route_geometry.geojson as any,
                  },
                ],
              }}
>>>>>>> origin/main
              style={geoJsonStyle}
            />
          )}
          {/* Fallback: đường chập nối thẳng khi OSRM không có geometry */}
          {!result?.route_geometry?.geojson &&
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
                    color: "#f59e0b",
                    weight: 3,
                    opacity: 0.6,
                    dashArray: "8, 6",
                  }}
                />
              )
            })()}
        </MapContainer>

        {/* Floating Status */}
        {isLoading && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-black/70 backdrop-blur-xl border border-violet-500/30 rounded-2xl px-6 py-3 flex items-center gap-3 shadow-[0_0_30px_rgba(139,92,246,0.3)]">
            <Loader2 className="w-5 h-5 text-violet-400 animate-spin" />
            <div>
              <p className="text-xs text-white font-mono font-bold">
                Orchestrator đang xử lý...
              </p>
              <p className="text-[10px] text-zinc-400 font-mono">
                PostGIS → Ranking → TSP → Products
              </p>
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
<<<<<<< HEAD
=======
                        referrerPolicy="no-referrer"
>>>>>>> origin/main
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
                        onClick={() => handleLock(prod.product_id)}
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
