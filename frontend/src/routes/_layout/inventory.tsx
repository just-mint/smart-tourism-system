import { createFileRoute } from "@tanstack/react-router"
import axios from "axios"
import {
  CheckCircle2,
  Clock,
  CreditCard,
  Loader2,
  Lock,
  MapPin,
  Package,
  PackageOpen,
  ScanLine,
  Search,
  ShoppingCart,
  Store,
  X,
  Zap,
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
  "https://images.unsplash.com/photo-1550650222-6b94dbba2211?q=80&w=800",
  "https://images.unsplash.com/photo-1559592413-7ceecea18501?q=80&w=800",
  "https://images.unsplash.com/photo-1555921015-5532091f6026?q=80&w=800",
]
const PRODUCT_IMAGES = [
  "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?q=80&w=600",
  "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?q=80&w=600",
  "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=600",
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?q=80&w=600",
  "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=600",
]

const isUsableImageUrl = (url?: string | null) =>
  !!url &&
  !url.includes("via.placeholder.com") &&
  !url.includes("placeholder.com")

const getProductImage = (product: ProductResponse & { imageIndex?: number }) =>
  isUsableImageUrl(product.image_url)
    ? product.image_url
    : PRODUCT_IMAGES[(product.imageIndex || 0) % PRODUCT_IMAGES.length]

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
    setLockingId(product.product_id)
    try {
      const res = await InventoryAPI.createLock(product.product_id, 1)
      setNotification(`✅ ${res.data.message}`)
      loadLocks()
      // Open checkout modal
      setCheckoutProduct(product)
      setOrderForm({
        ...orderForm,
        product_id: product.product_id,
        store_id: product.store_id,
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

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200 selection:bg-amber-500/30 font-sans pb-20">
      {/* 1. STICKY HEADER & SEARCH */}
      <header className="sticky top-0 z-40 bg-zinc-950/80 backdrop-blur-xl border-b border-white/5 shadow-2xl">
        <div className="max-w-[1600px] mx-auto px-6 h-20 flex items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-zinc-950">
              <PackageOpen className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white hidden md:block">
              O2O Market
            </h1>
          </div>

          <div className="flex-1 max-w-2xl relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search hubs, brands, apparels..."
              className="w-full bg-zinc-900/50 border-white/10 h-12 pl-12 rounded-2xl text-white placeholder:text-zinc-500 focus-visible:ring-amber-500/50 focus-visible:border-amber-500/50 transition-all text-base"
            />
            {isLoading && (
              <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-amber-500 animate-spin" />
            )}
          </div>

          <button
            onClick={() => setIsCartOpen(true)}
            className="relative p-3 rounded-xl hover:bg-zinc-800 transition-colors"
          >
            <ShoppingCart className="w-6 h-6 text-zinc-300 hover:text-white" />
            {locks.length > 0 && (
              <span className="absolute top-1 right-1 w-5 h-5 rounded-full bg-amber-500 text-zinc-950 text-[10px] font-bold flex items-center justify-center shadow-[0_0_15px_rgba(245,158,11,0.5)]">
                {locks.length}
              </span>
            )}
          </button>
        </div>
      </header>

      {/* NOTIFICATION */}
      {notification && (
        <div className="fixed top-24 left-1/2 -translate-x-1/2 z-50 bg-zinc-900 border border-white/10 rounded-full px-6 py-3 shadow-2xl flex items-center gap-2 animate-in slide-in-from-top-4">
          <span className="text-sm font-medium">{notification}</span>
        </div>
      )}

      <main className="max-w-[1600px] mx-auto px-6 py-8 flex flex-col lg:flex-row gap-8">
        {/* 2. LEFT COL: HUB LIST */}
        <aside className="w-full lg:w-[350px] shrink-0 space-y-4">
          <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-widest flex items-center gap-2 mb-6">
            <Store className="w-4 h-4" /> Nearby Hubs
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-4">
            {stores.map((store, idx) => {
              const isActive = activeStoreId === store.store_id
              return (
                <div
                  key={store.store_id}
                  onClick={() => handleStoreClick(store.store_id!)}
                  className={`group flex items-center gap-4 p-3 rounded-2xl cursor-pointer transition-all duration-300 border bg-zinc-900/30 ${isActive ? "border-amber-500/50 bg-amber-500/5 shadow-[0_0_30px_rgba(245,158,11,0.1)]" : "border-white/5 hover:border-white/20 hover:bg-zinc-800/50"}`}
                >
                  <img
                    src={STORE_IMAGES[idx % STORE_IMAGES.length]}
                    alt={store.name}
                    className="w-20 h-20 rounded-xl object-cover"
                  />
                  <div className="flex-1 overflow-hidden">
                    <h3
                      className={`font-bold text-base truncate transition-colors ${isActive ? "text-amber-400" : "text-white"}`}
                    >
                      {store.name}
                    </h3>
                    <p className="text-xs text-zinc-500 truncate flex items-center gap-1 mt-1">
                      <MapPin className="w-3 h-3" />
                      {store.address || "Location pending"}
                    </p>
                    <p className="text-xs text-zinc-400 mt-1.5 flex items-center gap-1 font-medium">
                      ⭐ {store.rating || 4.5}{" "}
                      <span className="text-zinc-600">
                        ({Math.floor(Math.random() * 100 + 20)})
                      </span>
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </aside>

        {/* 3. RIGHT COL: PRODUCT GRID */}
        <section className="flex-1">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <ScanLine className="w-6 h-6 text-amber-500" />
              {searchQuery ? "Search Results" : "Inventory Catalog"}
            </h2>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-80 bg-zinc-900/50 rounded-3xl animate-pulse"
                />
              ))}
            </div>
          ) : products.length === 0 ? (
            <div className="h-80 flex flex-col items-center justify-center border border-dashed border-zinc-800 rounded-3xl">
              <Package className="w-12 h-12 text-zinc-700 mb-2" />
              <p className="text-zinc-500">No products found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
              {products.map((p) => {
                const img = getProductImage(p)
                const stock = p.stock ?? 0
                const isOut = stock === 0
                return (
                  <div
                    key={p.product_id}
                    className={`group bg-zinc-900/40 rounded-3xl overflow-hidden border transition-all duration-500 hover:-translate-y-1 hover:shadow-2xl flex flex-col ${isOut ? "border-zinc-800 opacity-60" : "border-white/5 hover:border-amber-500/30"}`}
                  >
                    {/* Image Box */}
                    <div className="relative aspect-[4/5] overflow-hidden bg-zinc-950">
                      <img
                        src={img}
                        alt={p.name}
                        onError={(e) =>
                          (e.currentTarget.src = PRODUCT_IMAGES[0])
                        }
                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                        referrerPolicy="no-referrer"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-transparent to-transparent opacity-80" />

                      {/* Badges */}
                      <div className="absolute top-3 left-3 flex flex-col gap-2">
                        {stock > 0 && stock <= 5 && (
                          <span className="bg-red-500/90 text-white text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wider backdrop-blur-md">
                            Almost Gone
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Info */}
                    <div className="p-5 flex flex-col flex-1 justify-between bg-gradient-to-b from-zinc-900/80 to-zinc-950">
                      <div>
                        <h3 className="text-sm font-bold text-white line-clamp-2 leading-snug mb-2 group-hover:text-amber-400 transition-colors">
                          {p.name}
                        </h3>
                        <div className="text-lg font-mono font-bold text-zinc-100">
                          {p.price.toLocaleString("vi-VN")} đ
                        </div>
                      </div>

                      <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
                        <div className="flex flex-col">
                          <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-semibold mb-1">
                            Stock
                          </span>
                          <span
                            className={`text-xs font-mono font-bold ${isOut ? "text-zinc-600" : "text-emerald-400"}`}
                          >
                            {stock} left
                          </span>
                        </div>
                        <button
                          disabled={isOut || lockingId === p.product_id}
                          onClick={() => handleReserveClick(p)}
                          data-testid="reserve-button"
                          className="bg-zinc-800 hover:bg-amber-500 text-zinc-300 hover:text-zinc-950 w-10 h-10 rounded-full flex items-center justify-center transition-all disabled:opacity-50"
                        >
                          {lockingId === p.product_id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Lock className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>
      </main>

      {/* 4. CHECKOUT OVERLAY (VietQR) */}
      <Dialog
        open={!!checkoutProduct}
        onOpenChange={(open) => !open && closeCheckout()}
      >
        <DialogContent className="!max-w-[min(900px,calc(100vw-2rem))] p-0 bg-zinc-950/90 backdrop-blur-2xl border-white/10 shadow-2xl overflow-hidden max-h-[calc(100vh-2rem)]">
          {checkoutProduct && (
            <div className="flex flex-col md:flex-row h-[min(600px,calc(100vh-2rem))]">
              {/* Left: Product Recap */}
              <div className="w-full md:w-[400px] shrink-0 bg-zinc-900 p-8 flex flex-col justify-between border-r border-white/5">
                <div>
                  <h2 className="text-xs font-bold text-amber-500 uppercase tracking-widest mb-6">
                    Order Summary
                  </h2>
                  <img
                    src={getProductImage(checkoutProduct)}
                    onError={(e) => (e.currentTarget.src = PRODUCT_IMAGES[0])}
                    className="w-full h-48 object-cover rounded-2xl mb-6 shadow-xl"
                    referrerPolicy="no-referrer"
                  />
                  <h3 className="text-xl font-bold text-white mb-2">
                    {checkoutProduct.name}
                  </h3>
                  <p className="text-3xl font-mono font-bold text-zinc-200 mb-6">
                    {checkoutProduct.price.toLocaleString("vi-VN")} đ
                  </p>

                  <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                    <Clock className="w-5 h-5 text-amber-500" />
                    <p className="text-sm text-amber-500/90 leading-relaxed font-medium">
                      Item is locked for 15 minutes. Please complete your
                      checkout.
                    </p>
                  </div>
                </div>
              </div>

              {/* Right: Payment & Form */}
              <div className="flex-1 min-w-0 p-8 overflow-y-auto">
                {orderResult ? (
                  // SUCCESS & VIETQR
                  <div className="flex flex-col items-center text-center h-full justify-center animate-in zoom-in-95 duration-500">
                    <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6">
                      <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">
                      Order Created!
                    </h2>
                    <p className="text-zinc-400 mb-8 font-mono">
                      Code:{" "}
                      <span className="text-white font-bold">
                        {orderResult.order_code}
                      </span>
                    </p>

                    <div className="p-4 bg-white rounded-2xl shadow-2xl mb-6">
                      <img
                        src={orderResult.vietqr_url}
                        alt="VietQR"
                        className="w-48 h-48 object-contain"
                      />
                    </div>
                    <p className="text-sm text-zinc-500 max-w-xs">
                      Scan with any banking app to complete payment. Your order
                      will be shipped soon.
                    </p>

                    <button
                      onClick={closeCheckout}
                      className="mt-8 px-8 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-xl font-bold text-white transition-colors"
                    >
                      Continue Shopping
                    </button>
                  </div>
                ) : (
                  // FORM
                  <form
                    onSubmit={handleFinalizeOrder}
                    className="flex flex-col h-full"
                  >
                    <h2 className="text-2xl font-bold text-white mb-8 flex items-center gap-2">
                      <CreditCard className="w-6 h-6 text-amber-500" /> Shipping
                      Details
                    </h2>

                    <div className="space-y-5 flex-1">
                      <div>
                        <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2">
                          Full Name
                        </label>
                        <Input
                          required
                          value={orderForm.full_name}
                          onChange={(e) =>
                            setOrderForm({
                              ...orderForm,
                              full_name: e.target.value,
                            })
                          }
                          className="bg-zinc-900/50 border-white/10 text-white h-12 rounded-xl"
                          placeholder="John Doe"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2">
                          Phone Number
                        </label>
                        <Input
                          required
                          type="tel"
                          value={orderForm.phone}
                          onChange={(e) =>
                            setOrderForm({
                              ...orderForm,
                              phone: e.target.value,
                            })
                          }
                          className="bg-zinc-900/50 border-white/10 text-white h-12 rounded-xl"
                          placeholder="0912345678"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2">
                          Delivery Address
                        </label>
                        <textarea
                          required
                          value={orderForm.address}
                          onChange={(e) =>
                            setOrderForm({
                              ...orderForm,
                              address: e.target.value,
                            })
                          }
                          className="w-full bg-zinc-900/50 border border-white/10 text-white p-4 rounded-xl min-h-[100px] resize-none focus:outline-none focus:border-amber-500/50"
                          placeholder="123 Main St..."
                        />
                      </div>
                    </div>

                    <button
                      disabled={isOrdering}
                      type="submit"
                      className="w-full mt-8 py-4 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-zinc-950 font-bold text-lg flex items-center justify-center gap-2 shadow-[0_10px_30px_rgba(245,158,11,0.3)] transition-all disabled:opacity-50"
                    >
                      {isOrdering ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <Zap className="w-5 h-5" />
                      )}
                      {isOrdering ? "Processing..." : "Place Order via VietQR"}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 5. SIDEBAR CART */}
      {isCartOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-zinc-950/80 backdrop-blur-sm"
            onClick={() => setIsCartOpen(false)}
          />
          <div className="relative w-full max-w-md bg-zinc-900 border-l border-white/5 shadow-2xl flex flex-col animate-in slide-in-from-right">
            <div className="p-6 border-b border-white/5 flex justify-between items-center bg-zinc-950">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Lock className="w-5 h-5 text-amber-500" /> Active Locks (
                {locks.length})
              </h2>
              <button
                onClick={() => setIsCartOpen(false)}
                className="p-2 hover:bg-white/10 rounded-full"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {locks.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                  <ShoppingCart className="w-16 h-16 mb-4 opacity-50" />
                  <p>No active reservations.</p>
                </div>
              ) : (
                locks.map((lock) => (
                  <div
                    key={lock.id}
                    className="p-4 rounded-2xl bg-zinc-950 border border-white/5"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <p className="text-white font-bold mb-1">
                          Product #{lock.product_id}
                        </p>
                        <p className="text-xs text-zinc-500 font-mono">
                          Qty: {lock.quantity} • Lock: {lock.id}
                        </p>
                      </div>
                      <CountdownTimer
                        expiresAt={lock.expires_at}
                        ttlSeconds={lock.ttl_seconds}
                      />
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
