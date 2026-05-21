import { createFileRoute } from "@tanstack/react-router"
import L from "leaflet"
import {
  Bot,
  CloudLightning,
  Loader2,
  Milestone,
  Minus,
  Navigation,
  Plus,
  Search,
  ShoppingBag,
  Store,
  X,
  LocateFixed,
} from "lucide-react"
import React, { useCallback, useEffect, useMemo, useState } from "react"
import {
  Circle,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  Rectangle,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet"
import MarkerClusterGroup from "react-leaflet-cluster"
import "leaflet/dist/leaflet.css"
import { toast } from "sonner"
import {
  type ClusterItem,
  type ClusterResponse,
  InventoryAPI,
  type NearbySearchResponse,
  type O2OContextResponse,
  type PlaceResponse,
  type RoutePlanResponse,
  SpatialAPI,
  type StoreWithProductsResponse,
} from "@/client/aegis-api"

export const Route = createFileRoute("/_layout/spatial")({
  component: SpatialOperations,
})

// Custom Icons Factory
const createDivIcon = (html: string, size: number) =>
  L.divIcon({
    className: "bg-transparent",
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })

type ClusterLike = {
  getChildCount: () => number
}

type RequestError = Error & {
  code?: string
}

const isCanceledRequest = (error: unknown) => {
  if (!(error instanceof Error)) return false
  const requestError = error as RequestError
  return (
    error.name === "AbortError" ||
    error.name === "CanceledError" ||
    requestError.code === "ERR_CANCELED"
  )
}

const createCustomClusterIcon = (cluster: ClusterLike) => {
  const count = cluster.getChildCount()
  return createDivIcon(
    `
    <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-md bg-gradient-to-br from-teal-500 to-teal-700 border-2 border-white">
      ${count}
    </div>
  `,
    40,
  )
}

const tourismIcon = createDivIcon(
  `
  <div class="relative flex items-center justify-center" style="width:28px;height:36px">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#2B6777" stroke="white" stroke-width="1.5" width="28" height="36">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" fill="white" />
    </svg>
  </div>
`,
  28,
)

const storeIcon = createDivIcon(
  `
  <div class="relative flex items-center justify-center" style="width:28px;height:36px">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#E97451" stroke="white" stroke-width="1.5" width="28" height="36">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" fill="white" />
    </svg>
  </div>
`,
  28,
)
const selectedIcon = createDivIcon(
  `<div class="w-5 h-5 bg-teal-600 rounded-full border-2 border-white shadow-md"></div>`,
  20,
)
const highlightedIcon = createDivIcon(
  `
  <div class="relative flex items-center justify-center" style="width:36px;height:44px">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f59e0b" stroke="white" stroke-width="1.5" width="36" height="44" class="animate-bounce">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" fill="white" />
    </svg>
  </div>
`,
  40,
)
const userIcon = createDivIcon(
  `<div class="w-5 h-5 bg-emerald-500 rounded-full border-[3px] border-white shadow-md"></div>`,
  20,
)

const getNumberedIcon = (num: number) =>
  createDivIcon(
    `
  <div class="w-7 h-7 bg-teal-600 rounded-full border-2 border-white flex items-center justify-center text-white font-bold text-[12px] shadow-md">
    ${num}
  </div>
`,
    28,
  )

const CLUSTER_COLORS = ["#10b981", "#06b6d4", "#8b5cf6", "#f43f5e", "#f59e0b"]

function StoreProductPanel({
  o2oContext,
  onClose,
}: {
  o2oContext: O2OContextResponse | null
  onClose: () => void
}) {
  const [lockingProduct, setLockingProduct] = useState<number | null>(null)

  const handleLock = async (product_id: number, store_id: number) => {
    setLockingProduct(product_id)
    try {
      await InventoryAPI.createLock(product_id, 1, store_id)
      toast.success(
        "Đã giữ hàng thành công! Vui lòng vào trang Giỏ hàng để thanh toán.",
      )
    } catch (_e) {
      toast.error("Sản phẩm đã hết hoặc lỗi hệ thống.")
    } finally {
      setLockingProduct(null)
    }
  }

  const handleAskAgent = (storeName: string) => {
    // Dispatch custom event to layout to open chat
    document.dispatchEvent(
      new CustomEvent("open-agent-chat", {
        detail: {
          message: `Hãy tư vấn cho tôi các món quà lưu niệm tại ${storeName}`,
        },
      }),
    )
  }

  if (!o2oContext) return null

  const { place_info, nearby_stores } = o2oContext

  return (
    <div className="absolute top-4 right-4 z-[1000] w-[420px] max-h-[calc(100vh-2rem)] flex flex-col m-4 bg-white/95 backdrop-blur-md border border-zinc-200 shadow-xl rounded-2xl overflow-hidden transition-all animate-in fade-in slide-in-from-right-8 duration-300">
      <div className="p-5 border-b border-zinc-100 bg-gradient-to-l from-teal-50/50 to-transparent flex justify-between items-center">
        <div>
          <h2 className="text-lg font-bold text-zinc-800 truncate w-64 leading-tight">
            {place_info.name}
          </h2>
          <p className="text-[10px] text-zinc-500 font-mono mt-1 uppercase tracking-widest">
            <ShoppingBag className="w-3 h-3 inline mr-1 mb-0.5 text-zinc-400" />
            O2O Shopping Hub
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-zinc-400 hover:text-zinc-600 transition-colors bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 p-2 rounded-full"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
        {nearby_stores.length === 0 ? (
          <p className="text-xs text-zinc-500 text-center py-6 bg-zinc-50 rounded-2xl border border-zinc-100 font-mono">
            Chưa có đối tác O2O lân cận.
          </p>
        ) : (
          <div className="space-y-8">
            {nearby_stores.map((store) => (
              <div
                key={store.store_id}
                id={`store-${store.store_id}`}
                className="space-y-3 transition-colors duration-500 p-2 -mx-2 rounded-xl"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-zinc-800 flex items-center gap-1.5">
                      <Store className="w-4 h-4 text-teal-600" /> {store.name}
                    </h3>
                    <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-widest mt-0.5">
                      {store.category || "STORE"}
                    </p>
                  </div>
                  <button
                    onClick={() => handleAskAgent(store.name)}
                    className="bg-emerald-100 hover:bg-emerald-200 text-emerald-800 border border-emerald-300 px-3 py-1.5 rounded-full text-[10px] font-medium flex items-center gap-1.5 transition-colors"
                  >
                    <Bot className="w-3 h-3" /> Hỏi AI
                  </button>
                </div>

                {store.products.length === 0 ? (
                  <p className="text-[10px] text-zinc-500 font-mono">
                    Đang cập nhật sản phẩm...
                  </p>
                ) : (
                  <div className="flex flex-col gap-3">
                    {store.products.map((p, idx) => (
                      <div
                        key={p.product_id}
                        className="bg-white border border-zinc-100 shadow-sm rounded-xl overflow-hidden group hover:shadow-md transition-all flex flex-row items-center p-2 gap-3"
                      >
                        <div className="w-16 h-16 rounded-lg overflow-hidden bg-zinc-100 relative shrink-0 border border-zinc-100">
                          <img
                            src={
                              p.image_url ||
                              "/assets/images/product-fallback.svg"
                            }
                            alt={p.name}
                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement
                              target.onerror = null
                              target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 24 24' fill='none' stroke='%23a1a1aa' stroke-width='1.5'%3E%3Crect x='3' y='3' width='18' height='18' rx='2'/%3E%3Cpath d='m9 9 6 6m0-6-6 6'/%3E%3C/svg%3E"
                            }}
                          />
                        </div>
                        <div className="flex-1 flex flex-col justify-between py-0.5 relative">
                          <p className="text-[12px] text-zinc-800 line-clamp-1 font-medium pr-16">
                            {p.name}
                          </p>
                          <p className="text-[11px] font-bold text-teal-600 font-mono my-1 mb-2">
                            {new Intl.NumberFormat("vi-VN", {
                              style: "currency",
                              currency: "VND",
                            }).format(p.price)}
                          </p>

                          <div className="absolute right-0 top-0 bottom-0 flex flex-col justify-between items-end">
                            {idx % 2 === 0 ? (
                              <button
                                disabled={lockingProduct === p.product_id}
                                onClick={() =>
                                  handleLock(p.product_id, store.store_id!)
                                }
                                className="px-3 bg-teal-100 text-teal-800 border border-teal-300 hover:bg-teal-200 hover:border-teal-400 text-[10px] font-medium rounded-full transition-all flex justify-center items-center disabled:opacity-50 h-6"
                              >
                                {lockingProduct === p.product_id ? (
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                ) : (
                                  "Đang mở cửa"
                                )}
                              </button>
                            ) : (
                              <span className="px-3 bg-amber-200 text-amber-900 border border-amber-300 text-[10px] font-medium rounded-full flex justify-center items-center h-6">
                                Ưu đãi
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Recenter Map Component
function RecenterMap({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap()
  useEffect(() => {
    map.setView([lat, lon], map.getZoom(), { animate: true })
  }, [lat, lon, map])
  return null
}

// MapFlyController: Bridges map instance to parent via ref
function MapFlyController({
  mapRef,
}: {
  mapRef: React.MutableRefObject<L.Map | null>
}) {
  const map = useMap()
  useEffect(() => {
    mapRef.current = map
  }, [map, mapRef])
  return null
}

function PanelOmnisearch({
  onSelect,
  mapRef,
  userLat,
  userLon,
}: {
  onSelect: (place: PlaceResponse) => void
  mapRef: React.MutableRefObject<L.Map | null>
  userLat: number
  userLon: number
}) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<PlaceResponse[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)

  useEffect(() => {
    if (!query || query.length < 2) {
      setResults([])
      setShowDropdown(false)
      return
    }
    const handler = setTimeout(async () => {
      setIsSearching(true)
      try {
        const res = await SpatialAPI.searchOmni(query, userLat, userLon)
        setResults(res.data)
        setShowDropdown(true)
      } catch (e) {
        console.error(e)
      } finally {
        setIsSearching(false)
      }
    }, 300)
    return () => clearTimeout(handler)
  }, [query, userLon, userLat])

  return (
    <div className="relative">
      <div className="relative">
        <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
          {isSearching ? (
            <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
          ) : (
            <Search className="w-4 h-4 text-zinc-400" />
          )}
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.length >= 2 && setShowDropdown(true)}
          placeholder="Tìm kiếm địa điểm..."
          className="w-full bg-black/40 border border-white/10 rounded-xl pl-9 pr-4 py-2.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500/50 transition-colors"
        />
      </div>
      {showDropdown && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-black/80 backdrop-blur-2xl border border-white/10 rounded-xl overflow-hidden shadow-2xl max-h-[250px] overflow-y-auto z-50">
          {results.map((p: PlaceResponse, idx: number) => (
            <div
              key={p.id}
              onClick={() => {
                setShowDropdown(false)
                setQuery(p.name)
                if (mapRef.current) {
                  mapRef.current.flyTo([p.lat, p.lon], 17, {
                    animate: true,
                    duration: 1.5,
                  })
                }
                onSelect(p)
              }}
              className="px-3 py-2.5 hover:bg-emerald-500/20 cursor-pointer border-b border-white/5 last:border-0 transition-colors flex items-center gap-3"
            >
              <span className="shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center text-[10px] font-bold text-white">
                {idx + 1}
              </span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-emerald-400 truncate text-xs">
                  {p.name}
                </div>
                <div className="text-[10px] text-zinc-500 truncate mt-0.5">
                  {p.distance_meters != null && (
                    <span className="text-cyan-400 font-mono">
                      {p.distance_meters < 1000
                        ? `${Math.round(p.distance_meters)}m`
                        : `${(p.distance_meters / 1000).toFixed(1)}km`}
                    </span>
                  )}
                  {p.rating != null && (
                    <span className="ml-1.5">⭐ {p.rating}</span>
                  )}
                  {p.category ? ` · ${p.category}` : ""}
                </div>
              </div>
              {p.match_score != null && (
                <span className="shrink-0 text-[10px] font-bold font-mono px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                  🔥 {p.match_score}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function AutoFitNearby({ places }: { places: PlaceResponse[] }) {
  const map = useMap()
  useEffect(() => {
    if (places && places.length > 0) {
      const lats = places.map((p: PlaceResponse) => p.lat)
      const lons = places.map((p: PlaceResponse) => p.lon)
      const minLat = Math.min(...lats),
        maxLat = Math.max(...lats)
      const minLon = Math.min(...lons),
        maxLon = Math.max(...lons)
      const latPad = (maxLat - minLat) * 0.1 || 0.001
      const lonPad = (maxLon - minLon) * 0.1 || 0.001
      map.fitBounds(
        [
          [minLat - latPad, minLon - lonPad],
          [maxLat + latPad, maxLon + lonPad],
        ],
        { padding: [50, 50], animate: true, duration: 1.0 },
      )
    }
  }, [places, map])
  return null
}

function AutoFitRoute({
  routePolyline,
}: {
  routePolyline: [number, number][]
}) {
  const map = useMap()
  useEffect(() => {
    if (routePolyline && routePolyline.length > 0) {
      map.fitBounds(L.latLngBounds(routePolyline), {
        padding: [50, 50],
        animate: true,
        duration: 1.5,
      })
    }
  }, [routePolyline, map])
  return null
}

function DebouncedMapMoveHandler({
  onSettledCenter,
}: {
  onSettledCenter: (lat: number, lon: number) => void
}) {
  const debounceRef = React.useRef<number | null>(null)

  useMapEvents({
    dragend: (event) => {
      const center = event.target.getCenter()
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
      debounceRef.current = window.setTimeout(() => {
        onSettledCenter(center.lat, center.lng)
      }, 500)
    },
  })

  useEffect(() => {
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [])

  return null
}

function simplifyDouglasPeucker(
  points: [number, number][],
  epsilon: number,
): [number, number][] {
  if (points.length <= 2) return points
  let dmax = 0
  let index = 0
  const end = points.length - 1
  const p1 = points[0],
    p2 = points[end]

  const sqrDist = (
    p: [number, number],
    p1: [number, number],
    p2: [number, number],
  ) => {
    const x = p[0],
      y = p[1],
      x1 = p1[0],
      y1 = p1[1],
      x2 = p2[0],
      y2 = p2[1]
    const A = x - x1,
      B = y - y1,
      C = x2 - x1,
      D = y2 - y1
    const dot = A * C + B * D
    const len_sq = C * C + D * D
    let param = -1
    if (len_sq !== 0) param = dot / len_sq
    let xx: number
    let yy: number
    if (param < 0) {
      xx = x1
      yy = y1
    } else if (param > 1) {
      xx = x2
      yy = y2
    } else {
      xx = x1 + param * C
      yy = y1 + param * D
    }
    const dx = x - xx,
      dy = y - yy
    return dx * dx + dy * dy
  }

  for (let i = 1; i < end; i++) {
    const d = sqrDist(points[i], p1, p2)
    if (d > dmax) {
      index = i
      dmax = d
    }
  }

  if (dmax > epsilon * epsilon) {
    const rec1 = simplifyDouglasPeucker(points.slice(0, index + 1), epsilon)
    const rec2 = simplifyDouglasPeucker(points.slice(index, end + 1), epsilon)
    return rec1.slice(0, rec1.length - 1).concat(rec2)
  }
  return [points[0], points[end]]
}

function SpatialOperations() {
  const mapRef = React.useRef<L.Map | null>(null)
  const [lat, setLat] = useState(21.0285)
  const [lon, setLon] = useState(105.8542)
  const [radius, setRadius] = useState(2000)
  const [isLocating, setIsLocating] = useState(false)

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
        setInputLat(latitude.toString())
        setInputLon(longitude.toString())
        
        if (mapRef.current) {
          mapRef.current.flyTo([latitude, longitude], 15, {
            animate: true,
            duration: 1.5,
          })
        }
        toast.success("Đã lấy vị trí thành công")
        setIsLocating(false)
      },
      (err) => {
        setIsLocating(false)
        if (err.code === err.PERMISSION_DENIED) {
          toast.error("Vui lòng cấp quyền truy cập vị trí")
        } else {
          toast.error("Không thể lấy vị trí hiện tại")
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    )
  }

  const [inputLat, setInputLat] = useState("21.0285")
  const [inputLon, setInputLon] = useState("105.8542")
  const [inputRadius, setInputRadius] = useState("2000")

  useEffect(() => {
    const handler = setTimeout(() => {
      const parsedLat = parseFloat(inputLat)
      const parsedLon = parseFloat(inputLon)
      const parsedRad = parseInt(inputRadius, 10)

      if (!Number.isNaN(parsedLat) && parsedLat >= -90 && parsedLat <= 90)
        setLat(parsedLat)
      if (!Number.isNaN(parsedLon) && parsedLon >= -180 && parsedLon <= 180)
        setLon(parsedLon)
      if (!Number.isNaN(parsedRad) && parsedRad > 0 && parsedRad <= 20000)
        setRadius(parsedRad)
    }, 300)
    return () => clearTimeout(handler)
  }, [inputLat, inputLon, inputRadius])

  const [nearbyData, setNearbyData] = useState<NearbySearchResponse | null>(
    null,
  )
  const [routeData, setRouteData] = useState<RoutePlanResponse | null>(null)
  const [clusterData, setClusterData] = useState<ClusterResponse | null>(null)

  const [isLoadingNearby, setIsLoadingNearby] = useState(false)
  const [isLoadingRoute, setIsLoadingRoute] = useState(false)
  const [isLoadingClusters, setIsLoadingClusters] = useState(false)

  const [selectedNodes, setSelectedNodes] = useState<PlaceResponse[]>([])
  const [mapCenter, setMapCenter] = useState<[number, number]>([
    21.0285, 105.8542,
  ])

  const [o2oContext, setO2OContext] = useState<O2OContextResponse | null>(null)
  const [highlightedPlaceId, setHighlightedPlaceId] = useState<
    number | string | null
  >(null)

  const [activeCategory, setActiveCategory] = useState<
    "All" | "Attractions" | "Shopping" | "Food"
  >("All")
  const [activePriceRange, setActivePriceRange] = useState<
    "All" | "Cheap" | "Expensive"
  >("All")
  const [minRating, setMinRating] = useState<number>(0)
  const [openNowOnly, setOpenNowOnly] = useState<boolean>(false)

  const filteredPlaces = useMemo(() => {
    if (!nearbyData) return []
    return nearbyData.places.filter((p: PlaceResponse) => {
      const cat = p.category?.toLowerCase() || ""
      
      if (activeCategory === "Attractions") {
        if (
          !cat.match(
            /(tham quan|di tích|công viên|giải trí|thắng cảnh|du lịch|tourism|attraction|museum|park|monument|heritage)/,
          )
        )
          return false
      }
      if (activeCategory === "Shopping") {
        if (
          !cat.match(
            /(mua sắm|chợ|cửa hàng|đặc sản|shopping|store|mall|market|supermarket)/,
          )
        )
          return false
      }
      if (activeCategory === "Food") {
        if (
          !cat.match(
            /(ẩm thực|nhà hàng|quán ăn|cafe|thức ăn|đồ uống|food|restaurant|cafe|bar)/,
          )
        )
          return false
      }
      if (activePriceRange === "Cheap" && p.id % 3 === 0) return false
      if (activePriceRange === "Expensive" && p.id % 3 !== 0) return false
      if (minRating > 0 && (!p.rating || p.rating < minRating)) return false
      if (openNowOnly && p.id % 2 !== 0) return false
      return true
    })
  }, [nearbyData, activeCategory, activePriceRange, minRating, openNowOnly])

  const handlePlaceClick = async (p: PlaceResponse) => {
    if (routeData) {
      toggleNodeSelection(p)
      return
    }

    const toastId = toast.loading("Đang tìm cửa hàng xung quanh...")
    try {
      const queryId = p.place_id || String(p.id)
      const res = await SpatialAPI.getPlaceO2OContext(queryId, radius)
      setO2OContext(res.data)
      toast.success("Đã mở Khu Mua Sắm O2O!", { id: toastId })
    } catch (_e) {
      toast.error("Lỗi tải thông tin O2O", { id: toastId })
    }
  }

  const handleStoreClick = (store_id: number) => {
    const el = document.getElementById(`store-${store_id}`)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
      el.classList.add("bg-white/10", "border", "border-red-500/50")
      setTimeout(() => {
        el.classList.remove("bg-white/10", "border", "border-red-500/50")
      }, 1500)
    }
  }

  const abortControllerRef = React.useRef<AbortController | null>(null)

  const handleFindNearby = useCallback(
    async (nextLat = lat, nextLon = lon, nextRadius = radius) => {
      // Cancel previous request if exists
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }

      // Create new controller
      const controller = new AbortController()
      abortControllerRef.current = controller

      setIsLoadingNearby(true)
      setRouteData(null)
      setClusterData(null)
      setSelectedNodes([])
      try {
        const res = await SpatialAPI.nearbyPlaces(
          nextLat,
          nextLon,
          nextRadius,
          controller.signal,
        )
        setNearbyData(res.data)
        setMapCenter([nextLat, nextLon])
        toast.success(`Tìm thấy ${res.data.places.length} địa điểm!`)
      } catch (e: unknown) {
        if (isCanceledRequest(e)) return // Silent on abort
        setNearbyData(null)
        toast.error("Lỗi khi tải dữ liệu địa điểm.")
      } finally {
        setIsLoadingNearby(false)
      }
    },
    [lat, lon, radius],
  )

  useEffect(() => {
    handleFindNearby(21.0285, 105.8542, 2000)
    // Run once on mount; subsequent input changes require the explicit search button.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCluster = async () => {
    if (filteredPlaces.length === 0) return
    setIsLoadingClusters(true)
    try {
      const ids = filteredPlaces.map((p: PlaceResponse) => Number(p.id))
      const res = await SpatialAPI.clusterStores(ids)
      setClusterData(res.data)
      toast.success("Phân tích K-Means hoàn tất!")
    } catch (_e) {
      toast.error("Lỗi khi phân tích cụm.")
    } finally {
      setIsLoadingClusters(false)
    }
  }

  const toggleNodeSelection = useCallback((place: PlaceResponse) => {
    setSelectedNodes((prev) => {
      const isSelected = prev.some((p) => p.id === place.id)
      if (isSelected) {
        return prev.filter((p) => p.id !== place.id)
      }
      return [...prev, place]
    })
    setRouteData(null)
  }, [])

  const handlePlanRoute = async () => {
    if (selectedNodes.length === 0) {
      toast.error("Vui lòng chọn ít nhất một địa điểm để lập tuyến đường!")
      return
    }
    setIsLoadingRoute(true)
    try {
      const storeIds = selectedNodes.map((n) => n.id)
      const res = await SpatialAPI.routePlan(lat, lon, storeIds)
      setRouteData(res.data)
      toast.success("Tối ưu hóa tuyến đường (TSP) thành công!")
    } catch (_e) {
      toast.error(
        "Lỗi 500: Server không thể tính toán tuyến đường. Vui lòng kiểm tra lại data.",
      )
      setRouteData(null)
    } finally {
      setIsLoadingRoute(false)
    }
  }

  const handleDebouncedMapMove = useCallback(
    (nextLat: number, nextLon: number) => {
      setLat(nextLat)
      setLon(nextLon)
      setInputLat(nextLat.toFixed(6))
      setInputLon(nextLon.toFixed(6))
      handleFindNearby(nextLat, nextLon, radius)
    },
    [handleFindNearby, radius],
  )

  const routePolyline: [number, number][] = useMemo(() => {
    if (!routeData?.polyline) return []
    const poly = routeData.polyline
    if (typeof poly === "object" && poly?.coordinates) {
      const rawCoords = poly.coordinates.map(
        (coord: [number, number]) => [coord[1], coord[0]] as [number, number],
      )
      return simplifyDouglasPeucker(rawCoords, 0.00005) // Epsilon ~5-10m
    }
    return []
  }, [routeData])

  const clusterRectangles = useMemo(() => {
    if (!clusterData) return null
    return clusterData.clusters.map((cluster: ClusterItem, i: number) => {
      const color = CLUSTER_COLORS[i % CLUSTER_COLORS.length]
      const lats = cluster.places.map((p: PlaceResponse) => p.lat)
      const lons = cluster.places.map((p: PlaceResponse) => p.lon)
      if (lats.length === 0) return null
      const minLat = Math.min(...lats),
        maxLat = Math.max(...lats)
      const minLon = Math.min(...lons),
        maxLon = Math.max(...lons)
      const latPad = (maxLat - minLat) * 0.1 || 0.001
      const lonPad = (maxLon - minLon) * 0.1 || 0.001
      return (
        <Rectangle
          key={`cluster-${i}`}
          bounds={[
            [minLat - latPad, minLon - lonPad],
            [maxLat + latPad, maxLon + lonPad],
          ]}
          pathOptions={{
            color,
            weight: 2,
            dashArray: "5, 5",
            fillColor: color,
            fillOpacity: 0.1,
          }}
        />
      )
    })
  }, [clusterData])

  const o2oMarkers = useMemo(() => {
    if (!o2oContext) return null
    return o2oContext.nearby_stores.map((store: StoreWithProductsResponse) => {
      return (
        <Marker
          key={`o2o-${store.store_id}`}
          position={[store.lat, store.lon]}
          icon={storeIcon}
          eventHandlers={{ click: () => handleStoreClick(store.store_id) }}
        >
          <Popup>
            <div className="text-xs p-1">
              <strong className="text-orange-600 block mb-1">{store.name}</strong>
              <span className="text-zinc-500 uppercase tracking-widest text-[10px]">
                {store.category || "Cửa hàng"}
              </span>
            </div>
          </Popup>
        </Marker>
      )
    })
  }, [o2oContext, handleStoreClick])

  const nearbyMarkers = useMemo(() => {
    return filteredPlaces.map((p: PlaceResponse) => {
      const isSelected = selectedNodes.some((n: PlaceResponse) => n.id === p.id)
      let orderIndex = -1

      if (routeData?.optimized_order) {
        orderIndex = routeData.optimized_order.indexOf(p.id)
      }

      let icon = tourismIcon
      if (p.id === highlightedPlaceId) {
        icon = highlightedIcon
      } else if (orderIndex !== -1) {
        icon = getNumberedIcon(orderIndex + 1)
      } else if (isSelected) {
        icon = selectedIcon
      }

      const popupContent = (
        <Popup>
          <div className="text-xs p-1 min-w-[150px]">
            <strong className="text-teal-700 text-sm block mb-1 truncate">
              {p.name}
            </strong>
            <div className="text-zinc-500 mb-2">
              {p.category && <span>{p.category}</span>}
              {p.distance_meters && (
                <span className="block mt-0.5">
                  Cách {Math.round(p.distance_meters)}m
                </span>
              )}
            </div>
            {!routeData && (
              <div className="flex gap-2 mt-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleNodeSelection(p)
                  }}
                  className={`w-full py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-colors text-[10px] font-medium tracking-wider ${isSelected ? "bg-red-100 text-red-700 hover:bg-red-200 border border-red-300" : "bg-teal-100 text-teal-800 hover:bg-teal-200 border border-teal-300"}`}
                >
                  {isSelected ? (
                    <>
                      <Minus className="w-3 h-3" /> Bỏ chọn lộ trình
                    </>
                  ) : (
                    <>
                      <Plus className="w-3 h-3" /> Thêm vào lộ trình
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </Popup>
      )

      return (
        <Marker
          key={p.id}
          position={[p.lat, p.lon]}
          icon={icon}
          eventHandlers={{ click: () => handlePlaceClick(p) }}
        >
          {popupContent}
        </Marker>
      )
    })
  }, [
    filteredPlaces,
    selectedNodes,
    routeData,
    toggleNodeSelection,
    highlightedPlaceId,
    handlePlaceClick,
  ])

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] lg:h-screen overflow-hidden bg-zinc-50">
      {/* Top Filter Bar */}
      <div className="absolute top-4 left-[420px] z-[1000] flex items-center gap-3 bg-white/95 backdrop-blur-md px-4 py-2 rounded-2xl shadow-xl border border-zinc-200 animate-in fade-in slide-in-from-top-4">
        <div className="flex flex-col">
          <span className="text-[10px] font-bold text-zinc-800 ml-1">
            Phân loại
          </span>
          <div className="flex items-center gap-2 mt-1">
            <button
              className={`${activeCategory === "All" ? "bg-[#2B6777] text-white" : "bg-zinc-50 text-zinc-700 hover:bg-zinc-100 border border-zinc-200"} px-3 py-1.5 rounded-lg text-xs font-medium transition-colors`}
              onClick={() => setActiveCategory("All")}
            >
              Tất cả
            </button>
            <button
              className={`${activeCategory === "Attractions" ? "bg-[#2B6777] text-white" : "bg-zinc-50 text-zinc-700 hover:bg-zinc-100 border border-zinc-200"} px-3 py-1.5 rounded-lg text-xs font-medium transition-colors`}
              onClick={() => setActiveCategory("Attractions")}
            >
              Thắng cảnh
            </button>
            <button
              className={`${activeCategory === "Shopping" ? "bg-[#2B6777] text-white" : "bg-zinc-50 text-zinc-700 hover:bg-zinc-100 border border-zinc-200"} px-3 py-1.5 rounded-lg text-xs font-medium transition-colors`}
              onClick={() => setActiveCategory("Shopping")}
            >
              Mua sắm
            </button>
            <button
              className={`${activeCategory === "Food" ? "bg-[#2B6777] text-white" : "bg-zinc-50 text-zinc-700 hover:bg-zinc-100 border border-zinc-200"} px-3 py-1.5 rounded-lg text-xs font-medium transition-colors`}
              onClick={() => setActiveCategory("Food")}
            >
              Ẩm thực
            </button>
          </div>
        </div>
        <div className="w-px h-8 bg-zinc-200 mx-1"></div>
        <div className="flex flex-col">
          <span className="text-[10px] font-bold text-zinc-800 ml-1">
            Mức giá
          </span>
          <select
            value={activePriceRange}
            onChange={(e) =>
              setActivePriceRange(
                e.target.value as "All" | "Cheap" | "Expensive",
              )
            }
            className="mt-1 bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-50 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shadow-sm outline-none cursor-pointer"
          >
            <option value="All">Tất cả</option>
            <option value="Cheap">Giá rẻ</option>
            <option value="Expensive">Giá cao</option>
          </select>
        </div>
        <div className="w-px h-8 bg-zinc-200 mx-1"></div>
        <div className="flex flex-col">
          <span className="text-[10px] font-bold text-zinc-800 ml-1">
            Đánh giá
          </span>
          <select
            value={minRating}
            onChange={(e) => setMinRating(Number(e.target.value))}
            className="mt-1 bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-50 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shadow-sm outline-none cursor-pointer"
          >
            <option value={0}>Tất cả</option>
            <option value={4}>Từ 4 sao</option>
            <option value={4.5}>Từ 4.5 sao</option>
          </select>
        </div>
        <div className="w-px h-8 bg-zinc-200 mx-1"></div>
        <div className="flex flex-col">
          <span className="text-[10px] font-bold text-zinc-800 ml-1">
            Trạng thái
          </span>
          <select
            value={openNowOnly ? "open" : "all"}
            onChange={(e) => setOpenNowOnly(e.target.value === "open")}
            className="mt-1 bg-white border border-zinc-200 text-zinc-700 hover:bg-zinc-50 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shadow-sm outline-none cursor-pointer"
          >
            <option value="all">Tất cả</option>
            <option value="open">Đang mở cửa</option>
          </select>
        </div>
      </div>

      <StoreProductPanel
        o2oContext={o2oContext}
        onClose={() => setO2OContext(null)}
      />

      {/* FULL SCREEN MAP */}
      <div className="absolute inset-0 z-0">
        <MapContainer
          center={mapCenter}
          preferCanvas={true}
          zoom={14}
          className="w-full h-full"
          zoomControl={false}
        >
          <MapFlyController mapRef={mapRef} />
          <DebouncedMapMoveHandler onSettledCenter={handleDebouncedMapMove} />
          <TileLayer
            attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          />
          <RecenterMap lat={mapCenter[0]} lon={mapCenter[1]} />

          {/* User Location */}
          <Marker position={[lat, lon]} icon={userIcon}>
            <Popup className="custom-popup">
              <div className="text-xs font-mono p-1">
                <strong className="text-emerald-500">📍 Vị trí của bạn</strong>
                <br />
                {lat.toFixed(5)}, {lon.toFixed(5)}
              </div>
            </Popup>
          </Marker>

          {/* Search Radius Circle */}
          {nearbyData && (
            <Circle
              center={[lat, lon]}
              radius={radius}
              pathOptions={{
                color: "#22d3ee",
                fillColor: "#22d3ee",
                fillOpacity: 0.05,
                weight: 1,
                dashArray: "5, 10",
              }}
            />
          )}

          {/* Clusters Rectangles */}
          {!routeData && clusterRectangles}

          <AutoFitNearby places={filteredPlaces} />

          {/* CLUSTERING LAYER */}
          <MarkerClusterGroup
            chunkedLoading
            iconCreateFunction={createCustomClusterIcon}
            maxClusterRadius={50}
            spiderfyOnMaxZoom={true}
          >
            {nearbyMarkers}
            {o2oMarkers}
          </MarkerClusterGroup>

          <AutoFitRoute routePolyline={routePolyline} />

          {/* Route Polyline connecting the sequence */}
          {routePolyline.length > 1 && (
            <Polyline
              positions={routePolyline}
              pathOptions={{
                color: "#06b6d4",
                weight: 6,
                opacity: 0.85,
                lineCap: "round",
                lineJoin: "round",
                fill: false,
              }}
            />
          )}
        </MapContainer>
      </div>

      {/* FLOATING GLASS PANEL - Single Flow UX */}
      <div
        className="absolute top-4 left-4 z-[1000] w-[380px] max-h-[calc(100vh-2rem)] flex flex-col bg-white/95 backdrop-blur-md border border-zinc-200 rounded-2xl shadow-xl overflow-hidden"
        style={{ willChange: "transform, opacity" }}
      >
        {/* Header */}
        <div className="p-5 border-b border-zinc-100 bg-gradient-to-r from-teal-50/50 to-transparent relative">
          <h2 className="text-xl font-bold text-zinc-800 flex items-center gap-2.5 uppercase tracking-tight">
            Khám Phá Khu Vực
          </h2>
          <p className="text-[10px] text-zinc-500 mt-1 font-mono tracking-widest uppercase">
            Tìm kiếm địa điểm & lên lịch trình
          </p>
          <button className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-600 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-5 space-y-6 bg-white">
          {/* SEARCH BAR */}
          <PanelOmnisearch
            mapRef={mapRef}
            userLat={lat}
            userLon={lon}
            onSelect={(p: PlaceResponse) => {
              setHighlightedPlaceId(p.id)
              setTimeout(() => setHighlightedPlaceId(null), 3000)
              handlePlaceClick(p)
            }}
          />

          {/* STEP 1: Define Origin */}
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-[11px] font-bold text-zinc-800 uppercase tracking-widest flex items-center gap-1.5">
                  Điểm Bắt Đầu
                </label>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-emerald-500 border-2 border-white shadow-sm shrink-0"></div>
                <div className="flex-1 bg-white border border-zinc-200 rounded-xl px-3 py-2.5 text-sm text-zinc-600 shadow-sm flex items-center justify-between">
                  <div>
                    <span className="text-zinc-800 font-medium">Vị trí của bạn</span>
                    <span className="text-zinc-400 ml-2 text-xs">{lat.toFixed(4)}, {lon.toFixed(4)}</span>
                  </div>
                  <button 
                    onClick={handleLocate}
                    disabled={isLocating}
                    className="text-[10px] text-emerald-600 font-mono bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2 py-1 rounded-full transition-colors flex items-center gap-1 disabled:opacity-50"
                  >
                    {isLocating ? <Loader2 className="w-3 h-3 animate-spin" /> : <LocateFixed className="w-3 h-3" />}
                    Auto GPS
                  </button>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-bold text-zinc-800 uppercase tracking-widest mb-2 block">
                  Bán kính tìm kiếm (m)
                </label>
                <input
                  type="number"
                  value={inputRadius}
                  onChange={(e) => setInputRadius(e.target.value)}
                  className="w-full bg-white border border-zinc-200 rounded-xl px-3 py-2 text-sm text-zinc-800 focus:outline-none focus:border-teal-500/50 transition-colors shadow-sm"
                />
              </div>
              <div>
                <label className="text-[11px] font-bold text-zinc-800 uppercase tracking-widest mb-2 block">
                  Ngày dự kiến
                </label>
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Ngày dự kiến"
                    className="w-full bg-white border border-zinc-200 rounded-xl px-3 py-2 text-sm text-zinc-400 focus:outline-none focus:border-teal-500/50 transition-colors shadow-sm"
                  />
                  <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
                    <svg
                      className="w-4 h-4 text-zinc-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={() => handleFindNearby()}
              data-testid="spatial-scan-button"
              disabled={isLoadingNearby}
              className="w-full mt-4 bg-[#2B6777] hover:bg-teal-800 text-white font-medium uppercase tracking-wider text-xs py-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
            >
              {isLoadingNearby ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : null}
              {isLoadingNearby ? "Đang quét..." : "QUÉT KHU VỰC"}
            </button>
            {/* K-Means Clustering Button */}
            {nearbyData && nearbyData.places.length > 0 && !routeData && (
              <button
                onClick={handleCluster}
                disabled={isLoadingClusters}
                className="w-full mt-2 bg-[#3A8293] hover:bg-teal-700 text-white font-medium uppercase tracking-wider text-xs py-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
              >
                {isLoadingClusters ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : null}
                {isLoadingClusters ? "Đang phân tích..." : "PHÂN TÍCH CỤM (K-MEANS)"}
              </button>
            )}
          </div>

          {/* STEP 2: Selected Nodes & Route Plan */}
          {selectedNodes.length > 0 && (
            <div className="p-4 bg-teal-50 border border-teal-200 rounded-2xl space-y-3 animate-in slide-in-from-bottom-2">
              <h3 className="text-[10px] font-bold text-teal-700 uppercase tracking-widest font-mono flex items-center gap-1.5">
                <Milestone className="w-3.5 h-3.5" /> Điểm Dừng Đã Chọn (
                {selectedNodes.length})
              </h3>

              <div className="space-y-1.5 max-h-[150px] overflow-y-auto pr-1 custom-scrollbar">
                {selectedNodes.map((node) => (
                  <div
                    key={node.id}
                    className="flex items-center justify-between bg-white border border-zinc-200 p-2.5 rounded-lg group shadow-sm"
                  >
                    <span className="text-xs text-zinc-800 font-medium truncate mr-2">
                      {node.name}
                    </span>
                    <button
                      onClick={() => toggleNodeSelection(node)}
                      className="text-zinc-400 hover:text-red-500 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              {!routeData && (
                <button
                  onClick={handlePlanRoute}
                  disabled={isLoadingRoute}
                  className="w-full bg-[#2B6777] hover:bg-teal-800 text-white font-medium uppercase tracking-wider text-xs py-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-md disabled:opacity-50"
                >
                  {isLoadingRoute ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Navigation className="w-4 h-4" />
                  )}
                  {isLoadingRoute ? "Đang tính toán..." : "Tối Ưu Tuyến Đường"}
                </button>
              )}

              {/* TSP Result Box */}
              {routeData && (
                <div className="mt-4 pt-4 border-t border-teal-200">
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="bg-teal-50 rounded-xl p-3 text-center border border-teal-100">
                      <p className="text-xl font-bold text-teal-700 font-mono">
                        {(routeData.total_distance_meters / 1000).toFixed(1)}
                      </p>
                      <p className="text-[9px] text-zinc-500 font-mono uppercase tracking-widest mt-1">
                        KM Lộ Trình
                      </p>
                    </div>
                    <div className="bg-teal-50 rounded-xl p-3 text-center border border-teal-100">
                      <p className="text-xl font-bold text-teal-700 font-mono">
                        {routeData.optimized_order.length}
                      </p>
                      <p className="text-[9px] text-zinc-500 font-mono uppercase tracking-widest mt-1">
                        Điểm Dừng
                      </p>
                    </div>
                  </div>

                  {routeData.weather_context?.condition &&
                    routeData.weather_context.condition !== "Unknown" && (
                      <div className="flex items-center justify-center gap-2 text-xs text-amber-700 font-mono bg-amber-100 p-2 rounded-lg border border-amber-200">
                        <CloudLightning className="w-3.5 h-3.5" />
                        Thời tiết: {routeData.weather_context.condition} (
                        {routeData.weather_context.temperature}°C)
                      </div>
                    )}
                </div>
              )}
            </div>
          )}

          {/* STEP 3: Nearby Results List */}
          {nearbyData && filteredPlaces.length > 0 && !routeData && (
            <div className="space-y-3">
              <h3 className="text-[11px] font-bold text-zinc-800 uppercase tracking-widest mb-3 flex items-center justify-between">
                <span>Kết quả truy vấn</span>
                <span className="bg-teal-50 text-teal-700 px-2 py-0.5 rounded-full">
                  {filteredPlaces.length}
                </span>
              </h3>

              <div className="space-y-3">
                {filteredPlaces.slice(0, 30).map((p, idx) => {
                  const isSelected = selectedNodes.some((n) => n.id === p.id)
                  return (
                    <div
                      key={p.id}
                      className={`group flex items-center justify-between p-2 rounded-xl border bg-white shadow-sm transition-all ${
                        isSelected
                          ? "border-teal-500 bg-teal-50"
                          : "border-zinc-200 hover:shadow-md"
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div className="w-12 h-12 rounded-lg bg-zinc-100 shrink-0 overflow-hidden">
                          <img
                            src={
                              p.image_url || "/assets/images/store-fallback.svg"
                            }
                            className="w-full h-full object-cover"
                            alt={p.name}
                            onError={(e) => {
                              const target = e.target as HTMLImageElement
                              target.onerror = null
                              target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 24 24' fill='none' stroke='%23a1a1aa' stroke-width='1.5'%3E%3Cpath d='M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z'/%3E%3Ccircle cx='12' cy='10' r='3'/%3E%3C/svg%3E"
                            }}
                          />
                        </div>
                        <div className="min-w-0 flex-1 py-0.5">
                          <p className="text-[13px] font-bold text-zinc-800 truncate leading-tight">
                            {p.name}
                          </p>
                          <div className="text-[10px] text-zinc-500 mt-1 flex flex-col gap-0.5">
                            <span className="truncate">
                              {Math.round(p.distance_meters || 0)}m -{" "}
                              {p.category || "Địa điểm công cộng"}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="shrink-0 flex flex-col justify-between items-end gap-1 px-1">
                        {idx % 3 === 0 ? (
                          <span className="px-2 py-0.5 bg-amber-200 text-amber-900 rounded-full text-[9px] font-medium">
                            Ưu đãi
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-teal-100 text-teal-800 rounded-full text-[9px] font-medium">
                            Đang mở cửa
                          </span>
                        )}
                        <button
                          onClick={() => toggleNodeSelection(p)}
                          className={`w-6 h-6 mt-1 rounded-full flex items-center justify-center transition-colors border ${
                            isSelected
                              ? "bg-red-50 text-red-500 border-red-200 hover:bg-red-100"
                              : "bg-white text-zinc-400 border-zinc-200 hover:bg-zinc-50 hover:text-zinc-600"
                          }`}
                        >
                          {isSelected ? (
                            <Minus className="w-3 h-3" />
                          ) : (
                            <Plus className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
