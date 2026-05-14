/**
 * AEGIS Domain API Service Layer
 * Centralized API calls for Agent, Culture, Spatial, Inventory, Vision domains.
 * Uses axios with auth token interceptor.
 */
import axios from "axios"

export const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? "" : "http://localhost:8000");

const aegisClient = axios.create({
  baseURL: API_BASE ? `${API_BASE}/api/v1` : "/api/v1",
  headers: { "Content-Type": "application/json" },
})

// Attach auth token to every request
aegisClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ===================== TYPES =====================

// Agent
export interface AgentChatRequest {
  query: string
  current_lat?: number
  current_lon?: number
}
export interface AgentChatResponse {
  answer: string
  internal_actions: string[]
}

// Culture
export interface PlaceResponse {
  id: number
  place_id?: string
  name: string
  category?: string
  address?: string
  lat: number
  lon: number
  distance_meters?: number
  phone?: string
  rating?: number
  review_count?: number
  image_url?: string
}
export interface PlaceDetailWithAI extends PlaceResponse {
  ai_story?: string
}
export interface ReviewCreate {
  author_name: string
  rating: number
  text: string
}
export interface ReviewResponse {
  id: number
  place_id: string
  author_name: string
  rating: number
  text: string
  time_posted: string
}

// Spatial
export interface NearbySearchResponse {
  user_location: { lat: number; lon: number }
  search_radius_meters: number
  total_found: number
  places: PlaceResponse[]
}
export interface StoreResponse {
  store_id?: number
  place_id?: string
  name: string
  category?: string
  address?: string
  lat: number
  lon: number
  phone?: string
  rating?: number
}
export interface ClusterItem {
  cluster_id: number
  center: { lat: number; lon: number }
  places: PlaceResponse[]
  stores: StoreResponse[]
}
export interface ClusterResponse {
  clusters: ClusterItem[]
}
export interface RoutePlanResponse {
  total_distance_meters: number
  waypoints: Array<{ lat: number; lon: number; name?: string; order?: number }>
  polyline?: string
  optimized_order: number[]
  weather_context?: Record<string, unknown>
}

export interface ProductCompactResponse {
  product_id: number
  name: string
  price: number
  image_url?: string
}

export interface StoreWithProductsResponse {
  store_id: number
  place_id?: string
  name: string
  category?: string
  address?: string
  lat?: number
  lon?: number
  phone?: string
  rating?: number
  products: ProductCompactResponse[]
}

export interface O2OContextResponse {
  place_info: PlaceResponse
  nearby_stores: StoreWithProductsResponse[]
}

// Inventory
export interface ProductResponse {
  product_id: number
  name: string
  price: number
  original_price?: number
  description?: string
  image_url?: string
  stock?: number
  store_id?: number
  category?: string
}
export interface LockResponseItem {
  id: number
  product_id: number
  quantity: number
  status: string
  ttl_seconds: number
  expires_at: string
}

// Vision
export interface VisionUploadResponse {
  task_id: string
  message: string
}
export interface TaskStatus {
  task_id: string
  status: string
  image_path: string
  detected_objects?: Record<string, unknown>
  matched_product_ids?: number[]
}
export interface ClosetItemResponse {
  id: number
  user_id: number
  image_path: string
  created_at: string
}

// ===================== AGENT API =====================
export const AgentAPI = {
  chat: (data: AgentChatRequest) =>
    aegisClient.post<AgentChatResponse>("/agent/chat", data),
}

// ===================== CULTURE API =====================
export const CultureAPI = {
  searchPlaces: (q: string) =>
    aegisClient.get<PlaceResponse[]>("/culture/places/search", { params: { q } }),

  getPlaceStory: (id: number) =>
    aegisClient.get<PlaceDetailWithAI>(`/culture/places/${id}/story`),

  getPlaceReviews: (id: number) =>
    aegisClient.get<ReviewResponse[]>(`/culture/places/${id}/reviews`),

  addPlaceReview: (id: number, review: ReviewCreate) =>
    aegisClient.post<ReviewResponse>(`/culture/places/${id}/reviews`, review),
}

// ===================== SPATIAL API =====================
export const SpatialAPI = {
  searchOmni: (q: string, lat?: number, lon?: number) =>
    aegisClient.get<PlaceResponse[]>("/spatial/search", { params: { q, lat, lon } }),

  nearbyPlaces: (lat: number, lon: number, radius = 2000) =>
    aegisClient.get<NearbySearchResponse>("/spatial/nearby-places", {
      params: { lat, lon, radius },
    }),

  clusterStores: (place_ids: number[]) =>
    aegisClient.post<ClusterResponse>("/spatial/cluster-stores", { place_ids }),

  routePlan: (current_lat: number, current_lon: number, place_ids: number[]) =>
    aegisClient.post<RoutePlanResponse>("/spatial/route-plan", {
      current_lat,
      current_lon,
      place_ids,
    }),

  getPlaceO2OContext: (place_id: string, radius: number = 2000) =>
    aegisClient.get<O2OContextResponse>(`/spatial/places/${place_id}/o2o-context`, { params: { radius } }),
}

// ===================== INVENTORY API =====================
export interface OrderCreate {
  product_id: number
  store_id?: number
  quantity: number
  full_name: string
  phone: string
  address: string
}

export interface OrderResponse {
  order_id: number
  order_code: string
  status: string
  total_amount: number
  product_name: string
  vietqr_url: string
}

export interface SearchResult {
  stores: StoreResponse[]
  products: ProductResponse[]
}

export const InventoryAPI = {
  getStores: (place_id?: string) =>
    aegisClient.get<StoreResponse[]>("/inventory/stores", { params: { place_id } }),

  getProduct: (id: number) =>
    aegisClient.get<ProductResponse>(`/inventory/products/${id}`),

  getStoreProducts: (storeId: number) =>
    aegisClient.get<ProductResponse[]>(`/inventory/stores/${storeId}/products`),

  search: (q: string) =>
    aegisClient.get<SearchResult>("/inventory/search", { params: { q } }),

  createLock: (product_id: number, quantity = 1) =>
    aegisClient.post<{ message: string; lock_id: number; expires_at: string }>(
      "/inventory/lock",
      { product_id, quantity }
    ),

  getMyLocks: () =>
    aegisClient.get<LockResponseItem[]>("/inventory/locks"),

  triggerRelease: () =>
    aegisClient.post<{ message: string }>("/inventory/trigger-release"),

  comparePrices: (productId: number, storeId: number, lat?: number, lon?: number) =>
    aegisClient.get<PriceComparison[]>(`/inventory/products/${productId}/compare`, {
      params: { store_id: storeId, lat, lon },
    }),

  createOrder: (data: OrderCreate) =>
    aegisClient.post<OrderResponse>("/inventory/orders", data),
}

export interface PriceComparison {
  store_id: number
  store_name: string
  address: string | null
  price: number
  stock: number
  is_current: boolean
  category: string | null
}

// ===================== VISION API =====================
export const VisionAPI = {
  uploadScan: (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    return aegisClient.post<VisionUploadResponse>("/vision/scan", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  },

  checkTask: (taskId: string) =>
    aegisClient.get<TaskStatus>(`/vision/tasks/${taskId}`),

  addToCloset: (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    return aegisClient.post<ClosetItemResponse>("/vision/closet", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
  },

  getMyCloset: () =>
    aegisClient.get<ClosetItemResponse[]>("/vision/closet"),

  getMixMatch: (closetItemId: number) =>
    aegisClient.get<MixMatchResponse>(`/vision/closet/${closetItemId}/matches`),
}

export interface MixMatchProduct {
  product_id: number
  name: string
  description?: string
  price: number
  original_price?: number
  image_url?: string
  match_score: number
  stock: number
  store_id?: number
}

export interface MixMatchResponse {
  closet_item_id: number
  matches: MixMatchProduct[]
  total_matches: number
}

export interface TelemetryStats {
  active_users: number
  total_places: number
  total_stores: number
  active_locks: number
}

export const TelemetryAPI = {
  getStats: () => aegisClient.get<TelemetryStats>("/utils/telemetry/"),
}

// ===================== PLANNER API =====================
export interface PlannerWeightConfig {
  rating: number
  distance: number
  price: number
}

export interface PlannerRequest {
  current_lat: number
  current_lon: number
  radius: number
  keywords: string
  weights: PlannerWeightConfig
  top_n: number
  local_hour?: number
  max_budget?: number
}

export interface ProductInRoute {
  product_id: number
  name: string
  price: number
  image_url?: string
}

export interface StopInRoute {
  order: number
  store_id?: number
  name: string
  category?: string
  address?: string
  lat: number
  lon: number
  rating?: number
  distance_km?: number
  final_score?: number
  products: ProductInRoute[]
}

export interface RouteMetrics {
  total_price: number
  total_distance_km: number
  routing_fallback_used: boolean
}

export interface WeatherInfo {
  temperature?: number
  condition?: string
  code?: number
}

export interface RouteGeometry {
  geojson: {
    type: "LineString"
    coordinates: [number, number][]  // [lon, lat] pairs — OSRM format
  }
  duration_minutes?: number
}

export interface ContextInfo {
  time_slot: string
  time_description: string
  weather_condition: string
  weather_reason: string
  hour_used: number
}

export interface PlannerResponse {
  status: string
  optimized_route: StopInRoute[]
  metrics: RouteMetrics
  route_geometry?: RouteGeometry
  weather?: WeatherInfo
  context_applied?: ContextInfo
  total_candidates: number
}

export const PlannerAPI = {
  generate: (data: PlannerRequest) =>
    aegisClient.post<PlannerResponse>("/planner/generate", data),
}

export default aegisClient
