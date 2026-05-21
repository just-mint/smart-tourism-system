import { createFileRoute } from "@tanstack/react-router"
import axios from "axios"
import {
  CheckCircle2,
  Clock,
  CreditCard,
  Loader2,
  Lock,
  Package,
  ShoppingCart,
  X,
  Zap,
  ChevronRight,
} from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import {
  InventoryAPI,
  type LockResponseItem,
  type OrderCreate,
  type OrderResponse,
  type ProductResponse,
  type StoreResponse,
} from "@/client/aegis-api"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"

export const Route = createFileRoute("/_layout/inventory")({
  component: Inventory,
})

const STORE_IMAGES = [
  "https://placehold.co/400x400/f4f6f8/a1a1aa?text=Store",
]
const PRODUCT_IMAGES = [
  "https://placehold.co/400x400/f4f6f8/a1a1aa?text=Product",
]

const getApiErrorDetail = (error: unknown, fallback: string) => {
  if (!axios.isAxiosError(error)) return fallback
  const detail = error.response?.data?.detail
  return typeof detail === "string" ? detail : fallback
}

function CountdownTimer({
  expiresAt,
  ttlSeconds,
}: {
  expiresAt: string
  ttlSeconds: number
}) {
  const [remaining, setRemaining] = useState(ttlSeconds)
  useEffect(() => {
    const interval = setInterval(() => {
      const diff = Math.max(
        0,
        Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000),
      )
      setRemaining(diff)
      if (diff <= 0) clearInterval(interval)
    }, 1000)
    return () => clearInterval(interval)
  }, [expiresAt])

  const m = Math.floor(remaining / 60)
  const s = remaining % 60
  const colorClass = remaining < 120 ? "text-red-400" : "text-amber-400"

  return (
    <div
      className={`flex items-center gap-1.5 font-mono text-sm font-bold ${colorClass}`}
    >
      <Clock className="w-4 h-4" />
      {String(m).padStart(2, "0")}:{String(s).padStart(2, "0")}
    </div>
  )
}

function Inventory() {
  // Data states
  const [stores, setStores] = useState<StoreResponse[]>([])
  const [products, setProducts] = useState<
    (ProductResponse & { imageIndex?: number })[]
  >([])
  const [locks, setLocks] = useState<LockResponseItem[]>([])

  // UI states
  const [searchQuery, setSearchQuery] = useState("")
  const [activeStoreId, setActiveStoreId] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isCartOpen, setIsCartOpen] = useState(false)
  const [notification, setNotification] = useState("")
  const [lockingId, setLockingId] = useState<number | null>(null)

  // Checkout flow
  const [checkoutProduct, setCheckoutProduct] = useState<
    (ProductResponse & { imageIndex?: number }) | null
  >(null)
  const [orderForm, setOrderForm] = useState<OrderCreate>({
    product_id: 0,
    store_id: 0,
    lock_id: 0,
    quantity: 1,
    full_name: "",
    phone: "",
    address: "",
  })
  const [orderResult, setOrderResult] = useState<OrderResponse | null>(null)
  const [isOrdering, setIsOrdering] = useState(false)

  const loadData = useCallback(async () => {
    setIsLoading(true)
    try {
      if (searchQuery.trim().length > 0) {
        const res = await InventoryAPI.search(searchQuery)
        setStores(res.data.stores)
        setProducts(res.data.products.map((p, i) => ({ ...p, imageIndex: i })))
        setActiveStoreId(null)
      } else {
        const storeRes = await InventoryAPI.getStores()
        setStores(storeRes.data)
        if (storeRes.data.length > 0) {
          const firstStoreId = storeRes.data[0].store_id
          setActiveStoreId(firstStoreId ?? null)
          const prodRes = await InventoryAPI.getStoreProducts(firstStoreId!)
          setProducts(prodRes.data.map((p, i) => ({ ...p, imageIndex: i })))
        }
      }
    } catch (e) {
      console.error(e)
    } finally {
      setIsLoading(false)
    }
  }, [searchQuery])

  useEffect(() => {
    const delay = setTimeout(() => {
      loadData()
    }, 500)
    return () => clearTimeout(delay)
  }, [loadData])

  const loadLocks = useCallback(async () => {
    try {
      const res = await InventoryAPI.getMyLocks()
      setLocks(res.data)
    } catch (_e) {}
  }, [])

  useEffect(() => {
    loadLocks()
  }, [loadLocks])

  useEffect(() => {
    if (locks.length === 0) return
    const interval = window.setInterval(loadLocks, 30_000)
    return () => window.clearInterval(interval)
  }, [loadLocks, locks.length])

  const handleStoreClick = async (storeId: number) => {
    setActiveStoreId(storeId)
    setSearchQuery("")
    setIsLoading(true)
    try {
      const res = await InventoryAPI.getStoreProducts(storeId)
      setProducts(res.data.map((p, i) => ({ ...p, imageIndex: i })))
    } catch (_e) {
    } finally {
      setIsLoading(false)
    }
  }

  const handleReserveClick = async (product: ProductResponse) => {
    const storeId = product.store_id ?? activeStoreId
    if (!storeId) {
      setNotification("Vui lòng chọn cửa hàng trước khi giữ hàng")
      setTimeout(() => setNotification(""), 3000)
      return
    }
    setLockingId(product.product_id)
    try {
      const res = await InventoryAPI.createLock(product.product_id, 1, storeId)
      setNotification(res.data.message)
      loadLocks()
      // Open checkout modal
      setCheckoutProduct(product)
      setOrderForm({
        ...orderForm,
        product_id: product.product_id,
        store_id: storeId,
        lock_id: res.data.lock_id,
      })
      setTimeout(() => setNotification(""), 3000)
    } catch (err: unknown) {
      setNotification(`❌ ${getApiErrorDetail(err, "Lỗi giữ hàng")}`)
      setTimeout(() => setNotification(""), 3000)
    } finally {
      setLockingId(null)
    }
  }

  const handleFinalizeOrder = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsOrdering(true)
    try {
      const res = await InventoryAPI.createOrder(orderForm)
      setOrderResult(res.data)
      loadLocks()
    } catch (err: unknown) {
      setNotification(`❌ ${getApiErrorDetail(err, "Lỗi tạo đơn")}`)
      setTimeout(() => setNotification(""), 3000)
    } finally {
      setIsOrdering(false)
    }
  }

  const closeCheckout = () => {
    setCheckoutProduct(null)
    setOrderResult(null)
  }

  const handleCheckoutLock = (lock: LockResponseItem) => {
    setCheckoutProduct({
      product_id: lock.product_id,
      store_id: lock.store_id,
      name: lock.product_name || `Product #${lock.product_id}`,
      price: lock.unit_price || 0,
      image_url: lock.image_url,
      stock: 1,
    })
    setOrderForm((prev) => ({
      ...prev,
      product_id: lock.product_id,
      store_id: lock.store_id,
      lock_id: lock.id,
      quantity: lock.quantity,
    }))
    setIsCartOpen(false)
  }

  const handleCancelLock = async (lockId: number) => {
    try {
      await InventoryAPI.cancelLock(lockId)
      await loadLocks()
      setNotification("Đã hủy giữ hàng")
    } catch (err: unknown) {
      setNotification(getApiErrorDetail(err, "Không hủy được giữ hàng"))
    } finally {
      setTimeout(() => setNotification(""), 3000)
    }
  }

  return (
    <div className="relative min-h-screen bg-[#F4F6F8] text-zinc-900 selection:bg-teal-500/30 font-sans pb-20">
      {/* Floating Cart Button for Light Theme */}
      <button
        onClick={() => setIsCartOpen(true)}
        className="fixed top-20 right-6 z-40 p-3 rounded-full bg-white shadow-md hover:shadow-lg hover:-translate-y-1 transition-all border border-zinc-100 group"
      >
        <ShoppingCart className="w-6 h-6 text-zinc-600 group-hover:text-teal-600 transition-colors" />
        {locks.length > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-teal-600 text-white text-[10px] font-bold flex items-center justify-center shadow-md animate-bounce">
            {locks.length}
          </span>
        )}
      </button>

      {/* NOTIFICATION */}
      {notification && (
        <div className="fixed top-24 left-1/2 -translate-x-1/2 z-50 bg-white border border-zinc-200 text-zinc-800 rounded-full px-6 py-3 shadow-2xl flex items-center gap-2 animate-in slide-in-from-top-4">
          <span className="text-sm font-medium">{notification}</span>
        </div>
      )}

      {/* ================= TOP SECTION (White Background) ================= */}
      <div className="bg-white rounded-b-[3rem] shadow-sm pb-12 mb-8">
        <main className="max-w-[1600px] mx-auto px-4 sm:px-6 pt-8 flex flex-col gap-12">
        
        {/* ================= TOP SECTION (NEW UI) ================= */}
        
        {/* HERO BANNER */}
        <section>
          <div className="relative w-full h-[320px] md:h-[400px] rounded-[2rem] overflow-hidden bg-[#F2EDE4] flex items-center p-8 md:p-16 shadow-sm border border-[#E8E1D5]">
            <div className="relative z-10 max-w-xl space-y-4">
              <h2 className="text-3xl md:text-5xl font-bold text-zinc-900 leading-tight font-serif">KHÁM PHÁ THẾ GIỚI SANG TRỌNG</h2>
              <p className="text-zinc-700 text-lg md:text-xl font-medium">Dịch vụ và sản phẩm O2O cao cấp dành cho bạn</p>
              <button className="mt-4 bg-[#312E81] text-white px-8 py-3.5 rounded-full text-sm font-bold hover:bg-indigo-900 transition-colors shadow-lg flex items-center gap-2">
                Khám Phá Ngay <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            <div className="absolute right-0 top-0 h-full w-2/3 pointer-events-none" style={{ background: 'linear-gradient(to right, #F2EDE4 0%, transparent 40%)', zIndex: 5 }}></div>
            <img src="https://images.unsplash.com/photo-1555529771-835f59fc5efe?q=80&w=1200" className="absolute right-0 top-0 h-full w-2/3 object-cover object-left" alt="Banner" />
          </div>
        </section>

        {/* TOP PRODUCT GRID */}
        <section>
          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                <div key={i} className="h-64 bg-zinc-100 rounded-3xl animate-pulse" />
              ))}
            </div>
          ) : products.length === 0 ? (
            <div className="h-48 flex flex-col items-center justify-center border border-dashed border-zinc-300 rounded-3xl bg-white p-6 text-center">
              <Package className="w-12 h-12 text-zinc-300 mb-4" />
              <p className="text-zinc-500 font-medium">Hiện chưa có sản phẩm nào trong khu vực của bạn.</p>
            </div>
          ) : (
            <div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {products.map((p) => {
                  const img = p.image_url || PRODUCT_IMAGES[(p.imageIndex || 0) % PRODUCT_IMAGES.length]
                  const stock = p.stock ?? 0
                  const isOut = stock === 0
                  return (
                    <div key={`top-${p.product_id}`} className={`group bg-white rounded-3xl overflow-hidden shadow-sm border border-zinc-100 hover:shadow-lg transition-all duration-300 flex flex-col ${isOut ? "opacity-60 grayscale" : ""}`}>
                      <div className="relative h-40 overflow-hidden bg-zinc-50">
                        <img 
                          src={img} 
                          alt={p.name} 
                          onError={(e) => {
                             if (e.currentTarget.src !== PRODUCT_IMAGES[0]) {
                               e.currentTarget.src = PRODUCT_IMAGES[0]
                             }
                          }} 
                          className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500" 
                        />
                      </div>
                      
                      <div className="p-4 flex flex-col flex-1">
                        <h3 className="text-sm font-bold text-zinc-800 line-clamp-1 mb-1">{p.name}</h3>
                        <div className="text-sm font-extrabold text-zinc-900 mb-4">{p.price.toLocaleString("vi-VN")} đ</div>
                        
                        <div className="mt-auto flex items-center gap-3">
                          <div className="flex-1 h-1.5 bg-zinc-100 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${stock < 10 ? 'bg-red-500' : 'bg-[#D4AF37]'}`} style={{ width: `${Math.min(100, (stock / 500) * 100)}%` }}></div>
                          </div>
                          
                          <button
                            disabled={isOut || lockingId === p.product_id}
                            onClick={() => handleReserveClick(p)}
                            className="w-8 h-8 rounded-full bg-[#D4AF37] hover:bg-amber-500 text-white flex items-center justify-center transition-colors disabled:opacity-50 shrink-0 shadow-sm"
                          >
                            {lockingId === p.product_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <span className="text-lg font-medium leading-none mb-0.5">+</span>}
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="flex justify-center items-center gap-2 mt-10 text-sm font-bold">
                <span className="text-zinc-500 mr-2">Trang</span>
                <button className="w-8 h-8 rounded-full bg-zinc-900 text-white flex items-center justify-center shadow-md">1</button>
                <button className="w-8 h-8 rounded-full hover:bg-zinc-100 text-zinc-600 flex items-center justify-center transition-colors">2</button>
                <button className="w-8 h-8 rounded-full hover:bg-zinc-100 text-zinc-600 flex items-center justify-center transition-colors">3</button>
                <button className="px-4 h-8 rounded-full hover:bg-zinc-100 text-zinc-600 flex items-center justify-center ml-2 transition-colors">Tiếp</button>
              </div>
            </div>
          )}
        </section>
        </main>
      </div>

      {/* ================= BOTTOM SECTION (Gray Background) ================= */}
      
      <main className="max-w-[1600px] mx-auto px-4 sm:px-6 flex flex-col xl:flex-row gap-8">
        {/* LEFT COL */}
        <aside className="w-full xl:w-[320px] shrink-0 space-y-8">
          
          {/* Nearby Hubs Map Placeholder */}
          <div className="space-y-4">
            <h2 className="text-sm font-bold text-zinc-900 flex items-center gap-2">
              Nearby Hubs
            </h2>
            <div className="relative w-full h-48 bg-zinc-100 rounded-[2rem] overflow-hidden border border-zinc-200 shadow-sm">
              <img src="https://images.unsplash.com/photo-1524661135-423995f22d0b?q=80&w=800" alt="Map" className="w-full h-full object-cover opacity-60 mix-blend-luminosity grayscale" />
              {/* Dynamic Map Pins */}
              {stores.length > 0 && (
                <div className="absolute top-8 left-8 w-max max-w-[140px] bg-white rounded-full p-1.5 flex items-center gap-2 shadow-lg text-[10px] font-bold border border-zinc-100">
                  <img src={`https://ui-avatars.com/api/?name=${encodeURIComponent(stores[0].name)}&background=0D9488&color=fff`} className="w-5 h-5 rounded-full" />
                  <span className="truncate pr-2 text-zinc-800">{stores[0].name}</span>
                </div>
              )}
              {stores.length > 1 && (
                <div className="absolute bottom-10 right-4 w-max max-w-[140px] bg-white rounded-full p-1.5 flex items-center gap-2 shadow-lg text-[10px] font-bold border border-zinc-100">
                  <div className="w-5 h-5 rounded-full bg-teal-600 flex items-center justify-center text-white text-[8px]">{stores[1].name.charAt(0)}</div>
                  <span className="truncate pr-2 text-zinc-800">{stores[1].name}</span>
                </div>
              )}
              {/* User location dot */}
              <div className="absolute top-1/2 left-1/2 w-4 h-4 bg-teal-600 rounded-full border-2 border-white shadow-xl -translate-x-1/2 -translate-y-1/2">
                <div className="absolute inset-0 bg-teal-600 rounded-full animate-ping opacity-50"></div>
              </div>
            </div>
          </div>

          {/* Trending Now */}
          <div className="space-y-4">
            <h2 className="text-sm font-bold text-zinc-900 flex items-center gap-2">
              Trending Now
            </h2>
            {/* Pills */}
            <div className="flex gap-2 overflow-x-auto pb-2 custom-scrollbar">
              <button className="px-4 py-1.5 bg-teal-600 text-white text-xs font-bold rounded-full whitespace-nowrap shadow-sm">Siêu Sale</button>
              <button className="px-4 py-1.5 bg-white border border-zinc-200 text-zinc-600 hover:bg-zinc-50 text-xs font-bold rounded-full whitespace-nowrap shadow-sm">Đồ Ăn Gần Đây</button>
              <button className="px-4 py-1.5 bg-white border border-zinc-200 text-zinc-600 hover:bg-zinc-50 text-xs font-bold rounded-full whitespace-nowrap shadow-sm">Bán Chạy</button>
            </div>

            {/* List */}
            <div className="flex flex-col gap-3">
              {stores.slice(0, 4).map((store, idx) => {
                const isActive = activeStoreId === store.store_id
                // Use a stable dummy count based on store ID if rating is present, else standard
                const reviewCount = store.store_id ? (store.store_id * 7 % 150) + 10 : 50
                const storeImg = `https://ui-avatars.com/api/?name=${encodeURIComponent(store.name)}&background=random&size=128`
                return (
                  <div
                    key={store.store_id}
                    onClick={() => handleStoreClick(store.store_id!)}
                    className={`group flex items-center gap-4 p-3 rounded-[1.5rem] cursor-pointer transition-all duration-300 bg-white border ${isActive ? "border-teal-200 shadow-md ring-1 ring-teal-50" : "border-zinc-100 hover:border-zinc-300 hover:shadow-sm shadow-sm"}`}
                  >
                    <img
                      src={storeImg}
                      alt={store.name}
                      onError={(e) => (e.currentTarget.src = STORE_IMAGES[idx % STORE_IMAGES.length])}
                      className="w-16 h-16 rounded-[1rem] object-cover object-center shadow-sm"
                    />
                    <div className="flex-1 overflow-hidden">
                      <h3
                        className={`font-bold text-sm truncate transition-colors ${isActive ? "text-teal-700" : "text-zinc-900"}`}
                      >
                        {store.name}
                      </h3>
                      <p className="text-[11px] text-zinc-500 truncate mt-0.5">
                        {store.address || "Đang cập nhật địa chỉ"}
                      </p>
                      <p className="text-[11px] text-zinc-600 mt-1 flex items-center gap-1 font-medium">
                        <span className="text-teal-500">⭐</span> {store.rating || 5.0}{" "}
                        <span className="text-zinc-400 font-normal">
                          ({reviewCount})
                        </span>
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </aside>

        {/* RIGHT COL */}
        <section className="flex-1 min-w-0 space-y-8">
          
          {/* Brand Spotlight Banner */}
          <div className="relative w-full h-48 md:h-56 rounded-[2rem] overflow-hidden bg-[#F2EDE4] flex items-center p-8 md:p-12 shadow-sm border border-[#E8E1D5]">
            <div className="relative z-10 max-w-md space-y-4">
              <h4 className="text-sm font-bold text-zinc-600">Brand Spotlight</h4>
              <h2 className="text-2xl md:text-3xl font-bold text-zinc-900 leading-tight">KHÁM PHÁ PHONG CÁCH SỐNG ĐẲNG CẤP</h2>
              <button className="bg-zinc-900 text-white px-6 py-2.5 rounded-full text-sm font-bold hover:bg-zinc-800 transition-colors shadow-md">
                Xem Bộ Sưu Tập
              </button>
            </div>
            {/* Background image fade trick */}
            <div className="absolute right-0 top-0 h-full w-2/3 pointer-events-none" style={{ background: 'linear-gradient(to right, #F2EDE4 0%, transparent 40%)', zIndex: 5 }}></div>
            <img src="https://images.unsplash.com/photo-1555529771-835f59fc5efe?q=80&w=1200" className="absolute right-0 top-0 h-full w-2/3 object-cover object-left" alt="Banner" />
          </div>

          {/* Merchant Selection */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-zinc-900">Merchant Selection</h2>
              <div className="flex gap-2">
                <button className="w-8 h-8 rounded-full border border-zinc-200 flex items-center justify-center hover:bg-zinc-50 bg-white shadow-sm"><ChevronRight className="w-4 h-4 rotate-180 text-zinc-400" /></button>
                <button className="w-8 h-8 rounded-full border border-zinc-200 flex items-center justify-center hover:bg-zinc-50 bg-white shadow-sm"><ChevronRight className="w-4 h-4 text-zinc-600" /></button>
              </div>
            </div>
            <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar">
              {stores.map((store, idx) => {
                const isActive = activeStoreId === store.store_id
                const storeImg = `https://ui-avatars.com/api/?name=${encodeURIComponent(store.name)}&background=random&size=128`
                return (
                  <div
                    key={store.store_id}
                    onClick={() => handleStoreClick(store.store_id!)}
                    className={`flex items-center gap-3 p-2 pr-6 rounded-2xl cursor-pointer transition-all min-w-[200px] border bg-white ${isActive ? "border-teal-200 shadow-md ring-1 ring-teal-50" : "border-zinc-100 hover:border-zinc-300 shadow-sm"}`}
                  >
                    <img 
                      src={storeImg} 
                      onError={(e) => (e.currentTarget.src = STORE_IMAGES[idx % STORE_IMAGES.length])}
                      className="w-12 h-12 rounded-xl object-cover object-center shadow-sm shrink-0" 
                    />
                    <div className="overflow-hidden">
                      <h4 className={`font-bold text-xs truncate w-32 ${isActive ? "text-teal-700" : "text-zinc-900"}`}>{store.name}</h4>
                      <div className="text-[10px] text-zinc-500 flex items-center gap-1 mt-0.5"><span className="text-teal-500">⭐</span> {store.rating || 5.0}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Product Grid */}
          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-80 bg-zinc-100 rounded-3xl animate-pulse" />
              ))}
            </div>
          ) : products.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center border border-dashed border-zinc-300 rounded-3xl bg-white p-6 text-center">
              <Package className="w-12 h-12 text-zinc-300 mb-4" />
              <p className="text-zinc-500 font-medium">Hiện chưa có sản phẩm nào trong khu vực của bạn.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {products.map((p) => {
                const img = p.image_url || PRODUCT_IMAGES[(p.imageIndex || 0) % PRODUCT_IMAGES.length]
                const stock = p.stock ?? 0
                const isOut = stock === 0
                return (
                  <div key={p.product_id} className={`group bg-white rounded-2xl overflow-hidden border border-zinc-100 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col ${isOut ? "opacity-60 grayscale" : ""}`}>
                    <div className="relative aspect-square overflow-hidden flex items-center justify-center bg-zinc-50">
                      <img 
                        src={img} 
                        alt={p.name} 
                        onError={(e) => {
                           if (e.currentTarget.src !== PRODUCT_IMAGES[0]) {
                             e.currentTarget.src = PRODUCT_IMAGES[0]
                           }
                        }} 
                        className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500" 
                      />
                    </div>
                    
                    <div className="p-4 flex flex-col flex-1">
                      <h3 className="text-xs font-bold text-zinc-700 line-clamp-2 leading-snug mb-1">{p.name}</h3>
                      <div className="text-lg font-bold text-teal-700 mb-4">{p.price.toLocaleString("vi-VN")} đ</div>
                      
                      <div className="mt-auto">
                        <div className="flex justify-between items-end mb-1.5">
                          <span className="text-[10px] text-zinc-500 font-medium">Kho hàng</span>
                          <span className="text-[10px] text-zinc-800 font-bold">Còn {stock}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-1.5 bg-zinc-100 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${stock < 10 ? 'bg-red-500' : 'bg-teal-500'}`} style={{ width: `${Math.min(100, (stock / 500) * 100)}%` }}></div>
                          </div>
                          
                          <button
                            disabled={isOut || lockingId === p.product_id}
                            onClick={() => handleReserveClick(p)}
                            className="w-8 h-8 rounded-full bg-teal-600 hover:bg-teal-700 text-white flex items-center justify-center transition-colors disabled:opacity-50 shrink-0 shadow-sm"
                          >
                            {lockingId === p.product_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <span className="text-lg font-medium leading-none mb-0.5">+</span>}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
          {/* Bottom Product Grid */}
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-zinc-900">Sản Phẩm Từ Cửa Hàng</h2>
            {isLoading ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-64 bg-zinc-100/50 rounded-3xl animate-pulse border border-zinc-200/50" />
                ))}
              </div>
            ) : products.length === 0 ? (
              <div className="h-48 flex flex-col items-center justify-center border border-dashed border-zinc-300 rounded-3xl bg-transparent p-6 text-center">
                <Package className="w-12 h-12 text-zinc-300 mb-4" />
                <p className="text-zinc-500 font-medium">Hiện chưa có sản phẩm nào trong khu vực của bạn.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {products.map((p) => {
                  const img = p.image_url || PRODUCT_IMAGES[(p.imageIndex || 0) % PRODUCT_IMAGES.length]
                  const stock = p.stock ?? 0
                  const isOut = stock === 0
                  return (
                    <div key={`bottom-${p.product_id}`} className={`group bg-white rounded-3xl overflow-hidden shadow-sm border border-zinc-100 hover:shadow-md transition-all duration-300 flex flex-col ${isOut ? "opacity-60 grayscale" : ""}`}>
                      <div className="relative h-40 overflow-hidden bg-zinc-50">
                        <img 
                          src={img} 
                          alt={p.name} 
                          onError={(e) => {
                             if (e.currentTarget.src !== PRODUCT_IMAGES[0]) {
                               e.currentTarget.src = PRODUCT_IMAGES[0]
                             }
                          }} 
                          className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500" 
                        />
                      </div>
                      
                      <div className="p-4 flex flex-col flex-1">
                        <h3 className="text-sm font-bold text-zinc-800 line-clamp-1 mb-1">{p.name}</h3>
                        <div className="text-sm font-extrabold text-zinc-900 mb-4">{p.price.toLocaleString("vi-VN")} đ</div>
                        
                        <div className="mt-auto flex items-center gap-3">
                          <div className="flex-1 h-1.5 bg-zinc-100 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${stock < 10 ? 'bg-red-500' : 'bg-teal-500'}`} style={{ width: `${Math.min(100, (stock / 500) * 100)}%` }}></div>
                          </div>
                          
                          <button
                            disabled={isOut || lockingId === p.product_id}
                            onClick={() => handleReserveClick(p)}
                            className="w-8 h-8 rounded-full bg-teal-600 hover:bg-teal-700 text-white flex items-center justify-center transition-colors disabled:opacity-50 shrink-0 shadow-sm"
                          >
                            {lockingId === p.product_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <span className="text-lg font-medium leading-none mb-0.5">+</span>}
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </section>
      </main>

      {/* CHECKOUT OVERLAY (Updated to Light Theme) */}
      <Dialog open={!!checkoutProduct} onOpenChange={(open) => !open && closeCheckout()}>
        <DialogContent className="max-w-[900px] p-0 bg-white border-zinc-200 shadow-2xl overflow-hidden rounded-[2rem]">
          {checkoutProduct && (
            <div className="flex flex-col md:flex-row h-full md:h-[600px]">
              {/* Left: Product Recap */}
              <div className="w-full md:w-[400px] bg-zinc-50 p-8 flex flex-col justify-between border-r border-zinc-200">
                <div>
                  <h2 className="text-xs font-bold text-amber-600 uppercase tracking-widest mb-6">Order Summary</h2>
                  <img
                    src={checkoutProduct.image_url || PRODUCT_IMAGES[(checkoutProduct.imageIndex || 0) % 2]}
                    onError={(e) => (e.currentTarget.src = PRODUCT_IMAGES[0])}
                    className="w-full h-48 object-cover rounded-2xl mb-6 shadow-md"
                    referrerPolicy="no-referrer"
                  />
                  <h3 className="text-lg font-bold text-zinc-900 mb-2">{checkoutProduct.name}</h3>
                  <p className="text-3xl font-mono font-bold text-zinc-800 mb-6">{checkoutProduct.price.toLocaleString("vi-VN")} đ</p>

                  <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800">
                    <Clock className="w-5 h-5 shrink-0" />
                    <p className="text-sm leading-relaxed font-medium">Item is locked for 15 minutes. Please complete your checkout.</p>
                  </div>
                </div>
              </div>

              {/* Right: Payment & Form */}
              <div className="flex-1 p-8 overflow-y-auto">
                {orderResult ? (
                  // SUCCESS & VIETQR
                  <div className="flex flex-col items-center text-center h-full justify-center animate-in zoom-in-95 duration-500">
                    <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mb-6">
                      <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-zinc-900 mb-2">Đơn đã tạo, chờ thanh toán</h2>
                    <p className="text-zinc-500 mb-8 font-mono">Code: <span className="text-zinc-900 font-bold">{orderResult.order_code}</span></p>

                    <div className="p-4 bg-white rounded-2xl shadow-xl border border-zinc-100 mb-6">
                      <img src={orderResult.vietqr_url} alt="VietQR" className="w-48 h-48 object-contain" />
                    </div>
                    <p className="text-sm text-zinc-500 max-w-xs">Quét mã bằng ứng dụng ngân hàng để thanh toán. Đơn chỉ chuyển sang xử lý sau khi webhook xác nhận đã nhận tiền.</p>

                    <button onClick={closeCheckout} className="mt-8 px-8 py-3 bg-zinc-900 hover:bg-zinc-800 rounded-full font-bold text-white transition-colors">
                      Continue Shopping
                    </button>
                  </div>
                ) : (
                  // FORM
                  <form onSubmit={handleFinalizeOrder} className="flex flex-col h-full">
                    <h2 className="text-2xl font-bold text-zinc-900 mb-8 flex items-center gap-2"><CreditCard className="w-6 h-6 text-amber-500" /> Shipping Details</h2>

                    <div className="space-y-5 flex-1">
                      <div>
                        <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest mb-2">Full Name</label>
                        <Input
                          required value={orderForm.full_name} onChange={(e) => setOrderForm({ ...orderForm, full_name: e.target.value })}
                          className="bg-white border-zinc-200 text-zinc-900 h-12 rounded-xl focus-visible:ring-purple-500" placeholder="John Doe"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest mb-2">Phone Number</label>
                        <Input
                          required type="tel" value={orderForm.phone} onChange={(e) => setOrderForm({ ...orderForm, phone: e.target.value })}
                          className="bg-white border-zinc-200 text-zinc-900 h-12 rounded-xl focus-visible:ring-purple-500" placeholder="0912345678"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest mb-2">Delivery Address</label>
                        <textarea
                          required value={orderForm.address} onChange={(e) => setOrderForm({ ...orderForm, address: e.target.value })}
                          className="w-full bg-white border border-zinc-200 text-zinc-900 p-4 rounded-xl min-h-[100px] resize-none focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500" placeholder="123 Main St..."
                        />
                      </div>
                    </div>

                    <button disabled={isOrdering} type="submit" className="w-full mt-8 py-4 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-white font-bold text-lg flex items-center justify-center gap-2 shadow-xl transition-all disabled:opacity-50">
                      {isOrdering ? <Loader2 className="w-5 h-5 animate-spin" /> : <Zap className="w-5 h-5 text-amber-400" />}
                      {isOrdering ? "Đang tạo..." : "Tạo đơn chờ thanh toán"}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* SIDEBAR CART (Updated to Light Theme) */}
      {isCartOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setIsCartOpen(false)} />
          <div className="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-in slide-in-from-right">
            <div className="p-6 border-b border-zinc-100 flex justify-between items-center bg-zinc-50">
              <h2 className="text-xl font-bold text-zinc-900 flex items-center gap-2">
                <Lock className="w-5 h-5 text-teal-600" /> Active Locks ({locks.length})
              </h2>
              <button onClick={() => setIsCartOpen(false)} className="p-2 hover:bg-zinc-200 rounded-full text-zinc-500"><X className="w-5 h-5" /></button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-[#F4F6F8]">
              {locks.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-zinc-400">
                  <ShoppingCart className="w-16 h-16 mb-4 opacity-50" />
                  <p>No active reservations.</p>
                </div>
              ) : (
                locks.map((lock) => (
                  <div key={lock.id} className="p-4 rounded-xl bg-white border border-zinc-100 shadow-sm">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className="text-zinc-900 font-bold mb-1">{lock.product_name || `Product #${lock.product_id}`}</p>
                        <p className="text-[11px] text-zinc-500 font-mono">{lock.store_name || `Store #${lock.store_id}`} • Qty: {lock.quantity} • Lock: {lock.id}</p>
                        {lock.unit_price !== undefined && <p className="text-xs text-teal-600 font-bold mt-1">{lock.unit_price.toLocaleString("vi-VN")} đ</p>}
                      </div>
                      <CountdownTimer expiresAt={lock.expires_at} ttlSeconds={lock.ttl_seconds} />
                    </div>
                    <div className="flex gap-2 mt-4">
                      <button onClick={() => handleCheckoutLock(lock)} className="flex-1 rounded-xl bg-teal-600 px-3 py-2 text-xs font-bold text-white hover:bg-teal-700 shadow-sm">Thanh toán</button>
                      <button onClick={() => handleCancelLock(lock.id)} className="rounded-xl border border-zinc-200 px-4 py-2 text-xs text-zinc-600 hover:bg-zinc-50 bg-white shadow-sm">Hủy</button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
