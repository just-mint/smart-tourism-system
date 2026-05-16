import { createFileRoute } from "@tanstack/react-router"
import L from "leaflet"
import {
  Bot,
  CloudLightning,
  Layers,
  Loader2,
  LocateFixed,
  Map as MapIcon,
  Milestone,
  Minus,
  Navigation,
  Plus,
  Search,
  ShoppingBag,
  Sparkles,
  Store,
  X,
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
    <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-[0_0_20px_rgba(139,92,246,0.8)] bg-gradient-to-tr from-cyan-500 to-purple-500 border-2 border-white/80 animate-pulse">
      ${count}
    </div>
  `,
    40,
  )
}

const tourismIcon = createDivIcon(
  `
  <div class="relative w-6 h-6 flex items-center justify-center drop-shadow-[0_0_10px_rgba(34,211,238,0.8)] transition-transform hover:scale-125 hover:-translate-y-1">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="url(#tourismGrad)" stroke="white" stroke-width="1.5">
      <defs>
        <linearGradient id="tourismGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#2dd4bf" />
          <stop offset="100%" stop-color="#a855f7" />
        </linearGradient>
      </defs>
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" fill="white" />
    </svg>
  </div>
`,
  24,
)

const storeIcon = createDivIcon(
  `
  <div class="relative w-7 h-7 flex items-center justify-center rounded-full border-2 border-white bg-gradient-to-br from-red-500 to-orange-500 shadow-[0_0_15px_rgba(249,115,22,0.9)] animate-bounce transition-transform hover:scale-110">
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/></svg>
  </div>
`,
  28,
)
const selectedIcon = createDivIcon(
  `<div class="w-4 h-4 bg-purple-500 rounded-full border-2 border-black shadow-[0_0_15px_rgba(168,85,247,0.9)] animate-pulse"></div>`,
  16,
)
const highlightedIcon = createDivIcon(
  `
  <div class="relative w-10 h-10 flex items-center justify-center drop-shadow-[0_0_30px_rgba(250,204,21,1)] scale-125 z-50">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#facc15" stroke="white" stroke-width="1.5" class="w-10 h-10 animate-bounce">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" fill="white" />
    </svg>
    <div class="absolute w-12 h-12 rounded-full border-4 border-yellow-400/50 animate-ping"></div>
  </div>
`,
  40,
)
const userIcon = createDivIcon(
  `<div class="w-5 h-5 bg-emerald-500 rounded-full border-[3px] border-black shadow-[0_0_20px_rgba(16,185,129,1)]"></div>`,
  20,
)

const getNumberedIcon = (num: number) =>
  createDivIcon(
    `
  <div class="w-7 h-7 bg-purple-600 rounded-full border-2 border-white flex items-center justify-center text-white font-bold text-[12px] shadow-[0_0_15px_rgba(168,85,247,0.9)] scale-110">
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
    <div className="absolute top-4 right-4 z-[1000] w-[420px] max-h-[calc(100vh-2rem)] flex flex-col m-4 bg-black/40 backdrop-blur-md border border-white/10 shadow-2xl rounded-2xl overflow-hidden transition-all animate-in fade-in slide-in-from-right-8 duration-300">
      <div className="p-5 border-b border-white/5 bg-gradient-to-l from-purple-500/20 to-transparent flex justify-between items-center">
        <div>
          <h2 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400 truncate w-64 leading-tight">
            {place_info.name}
          </h2>
          <p className="text-[10px] text-zinc-400 font-mono mt-1 uppercase tracking-widest">
            <ShoppingBag className="w-3 h-3 inline mr-1 mb-0.5 text-purple-400" />
            O2O Shopping Hub
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-zinc-500 hover:text-white transition-colors bg-white/5 hover:bg-white/10 border border-white/10 p-2 rounded-full"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
        {nearby_stores.length === 0 ? (
          <p className="text-xs text-zinc-500 text-center py-6 bg-white/5 rounded-2xl border border-white/5 font-mono">
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
                    <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                      <Store className="w-4 h-4 text-cyan-400" /> {store.name}
                    </h3>
                    <p className="text-[10px] text-zinc-400 font-mono uppercase tracking-widest mt-0.5">
                      {store.category || "Retail"}
                    </p>
                  </div>
                  <button
                    onClick={() => handleAskAgent(store.name)}
                    className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 px-3 py-1.5 rounded-full text-[10px] font-mono flex items-center gap-1.5 transition-colors"
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
                    {store.products.map((p) => (
                      <div
                        key={p.product_id}
                        className="bg-white/5 border border-white/5 rounded-xl overflow-hidden group hover:bg-white/10 transition-colors flex flex-row items-center p-2 gap-3"
                      >
                        <div className="w-16 h-16 rounded-lg overflow-hidden bg-zinc-900 relative shrink-0 border border-white/5 shadow-inner">
                          <img
                            src={
                              p.image_url || "https://via.placeholder.com/150"
                            }
                            alt={p.name}
                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                          />
                        </div>
                        <div className="flex-1 flex flex-col justify-between py-0.5">
                          <p className="text-[11px] text-zinc-200 line-clamp-1 leading-relaxed font-medium">
                            {p.name}
                          </p>
                          <p className="text-[10px] font-bold text-emerald-400 font-mono my-1 mb-2">
                            {new Intl.NumberFormat("vi-VN", {
                              style: "currency",
                              currency: "VND",
                            }).format(p.price)}
                          </p>
                          <button
                            disabled={lockingProduct === p.product_id}
                            onClick={() =>
                              handleLock(p.product_id, store.store_id!)
                            }
                            className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-400 hover:to-pink-400 text-white hover:shadow-[0_0_20px_rgba(168,85,247,0.8)] shadow-[0_0_10px_rgba(168,85,247,0.4)] border border-white/10 text-[9px] font-bold font-mono uppercase tracking-widest py-1.5 rounded-lg transition-all flex justify-center items-center disabled:opacity-50"
                          >
                            {lockingProduct === p.product_id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              "Giữ Hàng"
                            )}
                          </button>
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

function AutoFitNearby({
  nearbyData,
}: {
  nearbyData: NearbySearchResponse | null
}) {
  const map = useMap()
  useEffect(() => {
    if (nearbyData?.places && nearbyData.places.length > 0) {
      const lats = nearbyData.places.map((p: PlaceResponse) => p.lat)
      const lons = nearbyData.places.map((p: PlaceResponse) => p.lon)
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
  }, [nearbyData, map])
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
    if (!nearbyData || nearbyData.places.length === 0) return
    setIsLoadingClusters(true)
    try {
      const ids = nearbyData.places.map((p: PlaceResponse) => Number(p.id))
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

  const handleLocateMe = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(pos.coords.latitude)
          setLon(pos.coords.longitude)
          setMapCenter([pos.coords.latitude, pos.coords.longitude])
          toast.success("Đã cập nhật vị trí GPS của bạn")
        },
        () => {
          toast.error("Không thể lấy vị trí GPS")
        },
      )
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
            <div className="text-xs font-mono p-1">
              <strong className="text-red-400 block mb-1">{store.name}</strong>
              <span className="text-zinc-500 uppercase tracking-widest text-[10px]">
                {store.category || "Retail"}
              </span>
            </div>
          </Popup>
        </Marker>
      )
    })
  }, [o2oContext, handleStoreClick])

  const nearbyMarkers = useMemo(() => {
    if (!nearbyData) return null
    return nearbyData.places.map((p: PlaceResponse) => {
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
          <div className="text-xs font-mono p-1 min-w-[150px]">
            <strong className="text-cyan-400 text-sm block mb-1 truncate">
              {p.name}
            </strong>
            <div className="text-zinc-400 mb-2">
              {p.category && <span>{p.category}</span>}
              {p.distance_meters && (
                <span className="block mt-0.5">
                  {Math.round(p.distance_meters)}m away
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
                  className={`w-full py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-colors text-[10px] font-mono tracking-wider ${isSelected ? "bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/20" : "bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 border border-cyan-500/20"}`}
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
    nearbyData,
    selectedNodes,
    routeData,
    toggleNodeSelection,
    highlightedPlaceId,
    handlePlaceClick,
  ])

  return (
    <div className="relative w-full h-[calc(100vh-4rem)] lg:h-screen overflow-hidden bg-zinc-950">
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
            attribution='&copy; <a href="https://osm.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
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

          <AutoFitNearby nearbyData={nearbyData} />

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
        className="absolute top-4 left-4 z-[1000] w-[380px] max-h-[calc(100vh-2rem)] flex flex-col bg-zinc-950/70 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-[0_20px_60px_rgba(0,0,0,0.6)] overflow-hidden"
        style={{ willChange: "transform, opacity" }}
      >
        {/* Header */}
        <div className="p-5 border-b border-white/5 bg-gradient-to-r from-cyan-500/10 to-transparent">
          <h2 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400 flex items-center gap-2.5 tracking-wide font-mono">
            <MapIcon className="w-6 h-6 text-cyan-400" />
            SPATIAL_OPS
          </h2>
          <p className="text-[10px] text-zinc-400 mt-1 font-mono tracking-widest uppercase">
            Intelligent Routing System
          </p>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-5 space-y-6">
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
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
                <LocateFixed className="w-3 h-3 text-emerald-400" /> Điểm Bắt
                Đầu
              </label>
              <button
                onClick={handleLocateMe}
                className="text-[10px] text-emerald-400 hover:text-emerald-300 font-mono transition-colors bg-emerald-500/10 px-2 py-1 rounded-full"
              >
                Auto GPS
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                step="any"
                value={inputLat}
                onChange={(e) => setInputLat(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500/50 transition-colors"
                placeholder="Latitude"
              />
              <input
                type="number"
                step="any"
                value={inputLon}
                onChange={(e) => setInputLon(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500/50 transition-colors"
                placeholder="Longitude"
              />
            </div>

            <div>
              <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono mb-1.5 block">
                Bán kính tìm kiếm (m)
              </label>
              <input
                type="number"
                value={inputRadius}
                onChange={(e) => setInputRadius(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500/50 transition-colors"
              />
            </div>

            <button
              onClick={() => handleFindNearby()}
              data-testid="spatial-scan-button"
              disabled={isLoadingNearby}
              className="w-full mt-2 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-white font-mono uppercase tracking-wider text-xs py-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-[0_0_20px_rgba(6,182,212,0.3)] disabled:opacity-50"
            >
              {isLoadingNearby ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              {isLoadingNearby ? "Scanning..." : "Quét Khu Vực"}
            </button>
            {/* K-Means Clustering Button */}
            {nearbyData && nearbyData.places.length > 0 && !routeData && (
              <button
                onClick={handleCluster}
                disabled={isLoadingClusters}
                className="w-full mt-2 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 text-white font-mono uppercase tracking-wider text-xs py-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)] border border-emerald-400/50 disabled:opacity-50"
              >
                {isLoadingClusters ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                {isLoadingClusters
                  ? "Analyzing..."
                  : "✨ Phân Tích Cụm (K-Means)"}
              </button>
            )}
          </div>

          {/* STEP 2: Selected Nodes & Route Plan */}
          {selectedNodes.length > 0 && (
            <div className="p-4 bg-purple-500/5 border border-purple-500/20 rounded-2xl space-y-3 animate-in slide-in-from-bottom-2">
              <h3 className="text-[10px] font-bold text-purple-400 uppercase tracking-widest font-mono flex items-center gap-1.5">
                <Milestone className="w-3.5 h-3.5" /> Điểm Dừng Đã Chọn (
                {selectedNodes.length})
              </h3>

              <div className="space-y-1.5 max-h-[150px] overflow-y-auto pr-1 custom-scrollbar">
                {selectedNodes.map((node) => (
                  <div
                    key={node.id}
                    className="flex items-center justify-between bg-black/40 border border-white/5 p-2 rounded-lg group"
                  >
                    <span className="text-xs text-zinc-300 font-mono truncate mr-2">
                      {node.name}
                    </span>
                    <button
                      onClick={() => toggleNodeSelection(node)}
                      className="text-zinc-500 hover:text-red-400 transition-colors"
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
                  className="w-full bg-gradient-to-r from-purple-600 to-fuchsia-600 hover:from-purple-500 hover:to-fuchsia-500 text-white font-mono uppercase tracking-wider text-xs py-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-[0_0_20px_rgba(168,85,247,0.4)] disabled:opacity-50"
                >
                  {isLoadingRoute ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Navigation className="w-4 h-4" />
                  )}
                  {isLoadingRoute ? "Processing TSP..." : "Tối Ưu Tuyến Đường"}
                </button>
              )}

              {/* TSP Result Box */}
              {routeData && (
                <div className="mt-4 pt-4 border-t border-purple-500/20">
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="bg-black/40 rounded-xl p-3 text-center border border-white/5">
                      <p className="text-xl font-bold text-cyan-400 font-mono">
                        {(routeData.total_distance_meters / 1000).toFixed(1)}
                      </p>
                      <p className="text-[9px] text-zinc-500 font-mono uppercase tracking-widest mt-1">
                        KM Lộ Trình
                      </p>
                    </div>
                    <div className="bg-black/40 rounded-xl p-3 text-center border border-white/5">
                      <p className="text-xl font-bold text-purple-400 font-mono">
                        {routeData.optimized_order.length}
                      </p>
                      <p className="text-[9px] text-zinc-500 font-mono uppercase tracking-widest mt-1">
                        Điểm Dừng
                      </p>
                    </div>
                  </div>

                  {routeData.weather_context?.condition &&
                    routeData.weather_context.condition !== "Unknown" && (
                      <div className="flex items-center justify-center gap-2 text-xs text-amber-400 font-mono bg-amber-500/10 p-2 rounded-lg border border-amber-500/20">
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
          {nearbyData && nearbyData.places.length > 0 && !routeData && (
            <div className="space-y-3">
              <h3 className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-cyan-500" /> Kết quả truy
                  vấn
                </span>
                <span className="bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded-full">
                  {nearbyData.total_found}
                </span>
              </h3>

              <div className="space-y-2">
                {nearbyData.places.slice(0, 30).map((p) => {
                  const isSelected = selectedNodes.some((n) => n.id === p.id)
                  return (
                    <div
                      key={p.id}
                      className={`group flex items-center justify-between p-3 rounded-xl border transition-all ${
                        isSelected
                          ? "border-purple-500/50 bg-purple-500/10"
                          : "border-white/5 bg-black/40 hover:border-white/10"
                      }`}
                    >
                      <div className="min-w-0 flex-1 pr-3">
                        <p className="text-xs font-semibold text-zinc-200 truncate">
                          {p.name}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[10px] text-cyan-400 font-mono bg-cyan-500/10 px-1.5 py-0.5 rounded">
                            {Math.round(p.distance_meters || 0)}m
                          </span>
                          {p.category && (
                            <span className="text-[10px] text-zinc-500 truncate">
                              {p.category}
                            </span>
                          )}
                        </div>
                      </div>

                      <button
                        onClick={() => toggleNodeSelection(p)}
                        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                          isSelected
                            ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                            : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white"
                        }`}
                      >
                        {isSelected ? (
                          <Minus className="w-4 h-4" />
                        ) : (
                          <Plus className="w-4 h-4" />
                        )}
                      </button>
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
