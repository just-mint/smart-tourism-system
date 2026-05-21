import { createFileRoute } from "@tanstack/react-router"
import axios from "axios"
import {
  CheckCircle2,
  Clock,
  CreditCard,
  Eye,
  Image,
  Loader2,
  Lock,
  RefreshCw,
  ScanFace,
  Shirt,
  Sparkles,
  UploadCloud,
  XCircle,
  Zap,
} from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import {
  API_BASE,
  type ClosetItemResponse,
  InventoryAPI,
  type MixMatchProduct,
  type OrderCreate,
  type OrderResponse,
  type TaskStatus,
  VisionAPI,
} from "@/client/aegis-api"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

// Local types to avoid breaking generated sdk
interface AvailableStore {
  store_id: number
  name: string
  lat: number
  lon: number
  stock: number
  address?: string
  rating?: number
  category?: string
}

interface ExtendedMixMatchProduct extends MixMatchProduct {
  available_stores?: AvailableStore[]
}

const getApiErrorDetail = (error: unknown, fallback: string) => {
  if (!axios.isAxiosError(error)) return fallback
  const detail = error.response?.data?.detail
  return typeof detail === "string" ? detail : fallback
}

export const Route = createFileRoute("/_layout/vision")({
  component: VisionCloset,
})

function VisionCloset() {
  const [activeTab, setActiveTab] = useState<"scan" | "closet">("scan")
  // Scan
  const [scanFile, setScanFile] = useState<File | null>(null)
  const [scanPreview, setScanPreview] = useState("")
  const [isUploading, setIsUploading] = useState(false)
  const [taskId, setTaskId] = useState("")
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  // Cleanup Object URL for memory management
  useEffect(() => {
    return () => {
      if (scanPreview) URL.revokeObjectURL(scanPreview)
    }
  }, [scanPreview])

  // Closet
  const [closetItems, setClosetItems] = useState<ClosetItemResponse[]>([])
  const [isLoadingCloset, setIsLoadingCloset] = useState(false)
  const [closetFile, setClosetFile] = useState<File | null>(null)
  const [isUploadingCloset, setIsUploadingCloset] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [selectedClosetItem, setSelectedClosetItem] =
    useState<ClosetItemResponse | null>(null)
  const [isMixMatchOpen, setIsMixMatchOpen] = useState(false)
  const [mixMatchResults, setMixMatchResults] = useState<MixMatchProduct[]>([])
  const [isLoadingMixMatch, setIsLoadingMixMatch] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const closetFileRef = useRef<HTMLInputElement>(null)

  // O2O Checkout states
  const [selectedStores, setSelectedStores] = useState<Record<number, number>>(
    {},
  )
  const [checkoutProduct, setCheckoutProduct] =
    useState<ExtendedMixMatchProduct | null>(null)
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
  const [notification, setNotification] = useState("")
  const [lockingId, setLockingId] = useState<number | null>(null)

  const handleStoreSelect = (productId: number, storeId: number) => {
    setSelectedStores((prev) => ({ ...prev, [productId]: storeId }))
  }

  const handleReserveClick = async (product: ExtendedMixMatchProduct) => {
    const storeId = selectedStores[product.product_id]
    if (!storeId) {
      setNotification("⚠️ Vui lòng chọn một cửa hàng trước khi mua!")
      setTimeout(() => setNotification(""), 3000)
      return
    }

    setLockingId(product.product_id)
    try {
      const res = await InventoryAPI.createLock(product.product_id, 1, storeId)
      setNotification(`✅ ${res.data.message}`)
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

  // Handle Scan Upload
  const handleScanUpload = async () => {
    if (!scanFile) return
    setIsUploading(true)
    setTaskStatus(null)
    try {
      const res = await VisionAPI.uploadScan(scanFile)
      setTaskId(res.data.task_id)
      setIsPolling(true)
    } catch {
      setTaskId("")
    } finally {
      setIsUploading(false)
    }
  }

  // Poll Task Status
  useEffect(() => {
    if (!isPolling || !taskId) return
    const interval = setInterval(async () => {
      try {
        const res = await VisionAPI.checkTask(taskId)
        setTaskStatus(res.data)
        if (res.data.status !== "processing") {
          setIsPolling(false)
          clearInterval(interval)
        }
      } catch {
        setIsPolling(false)
        clearInterval(interval)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [isPolling, taskId])

  // Load Closet
  const loadCloset = useCallback(async () => {
    setIsLoadingCloset(true)
    try {
      const res = await VisionAPI.getMyCloset()
      setClosetItems(res.data)
    } catch {
      setClosetItems([])
    } finally {
      setIsLoadingCloset(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab === "closet") loadCloset()
  }, [activeTab, loadCloset])

  // Handle closet upload
  const handleClosetUpload = async () => {
    if (!closetFile) return
    setIsUploadingCloset(true)
    try {
      await VisionAPI.addToCloset(closetFile)
      setClosetFile(null)
      loadCloset()
    } catch {
      // silent
    } finally {
      setIsUploadingCloset(false)
    }
  }

  // [v2] Auto-fetch Mix & Match khi mở sheet
  useEffect(() => {
    if (!isMixMatchOpen || !selectedClosetItem) return
    const fetchMatches = async () => {
      setIsLoadingMixMatch(true)
      try {
        const res = await VisionAPI.getMixMatch(selectedClosetItem.id)
        setMixMatchResults(res.data.matches)
      } catch {
        setMixMatchResults([])
      } finally {
        setIsLoadingMixMatch(false)
      }
    }
    fetchMatches()
  }, [isMixMatchOpen, selectedClosetItem])

  // Drag & Drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }
  const handleDragLeave = () => setIsDragging(false)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file?.type.startsWith("image/")) {
      if (activeTab === "scan") {
        setScanFile(file)
        setScanPreview(URL.createObjectURL(file))
      } else {
        setClosetFile(file)
      }
    }
  }

  const handleFileSelect = (
    e: React.ChangeEvent<HTMLInputElement>,
    target: "scan" | "closet",
  ) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (target === "scan") {
      setScanFile(file)
      setScanPreview(URL.createObjectURL(file))
    } else {
      setClosetFile(file)
    }
  }

  return (
    <div className="p-6 md:p-10 w-full min-h-screen bg-gradient-to-br from-[#FDFBF7] via-[#FFF8F0] to-[#FFF3E0] mx-auto flex flex-col gap-10 animate-in fade-in duration-700 relative z-10 font-sans text-zinc-900 selection:bg-amber-500/30">
      {/* NOTIFICATION */}
      {notification && (
        <div className="fixed top-24 left-1/2 -translate-x-1/2 z-50 bg-white border border-amber-200/50 rounded-full px-6 py-3 shadow-xl flex items-center gap-2 animate-in slide-in-from-top-4">
          <span className="text-sm font-medium text-zinc-800">{notification}</span>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 max-w-[1800px] mx-auto w-full">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-2xl bg-gradient-to-br from-[#F4E3C5] to-[#D4AF37] border border-[#D4AF37]/30 shadow-md flex items-center justify-center">
            <span className="font-bold text-white text-lg tracking-widest relative">
              <ScanFace className="absolute -inset-1 opacity-20 w-8 h-8 -top-0.5 -left-1" />
              AI
            </span>
          </div>
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-zinc-900 font-serif" style={{ background: 'linear-gradient(90deg, #5c4b37, #8e7343)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              AI Vision & Virtual Closet
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveTab("scan")}
            className={`px-6 py-3 rounded-full text-sm font-bold transition-all flex items-center gap-2 shadow-sm ${activeTab === "scan" ? "bg-gradient-to-r from-[#F2E0C8] to-[#D4AF37] text-zinc-900 ring-2 ring-amber-200 ring-offset-2 ring-offset-[#FFF8F0]" : "bg-white border border-zinc-200 text-zinc-600 hover:bg-zinc-50"}`}
          >
            <Eye className="w-4 h-4" /> AI Scan
          </button>
          <button
            onClick={() => setActiveTab("closet")}
            className={`px-6 py-3 rounded-full text-sm font-bold transition-all flex items-center gap-2 shadow-sm ${activeTab === "closet" ? "bg-[#312E81] text-white ring-2 ring-indigo-200 ring-offset-2 ring-offset-[#FFF8F0]" : "bg-[#312E81] text-white hover:bg-indigo-900"}`}
          >
            <Shirt className="w-4 h-4" /> Virtual Closet
          </button>
        </div>
      </div>

      <div className="max-w-[1800px] mx-auto w-full flex flex-col gap-10">
      {activeTab === "scan" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Upload Zone */}
          <div className="bg-white/80 backdrop-blur-xl rounded-[2rem] p-8 shadow-sm border border-white/50 flex flex-col">
            <h3 className="text-sm font-bold text-zinc-800 mb-6 flex items-center gap-2">
              <UploadCloud className="w-5 h-5 text-[#D4AF37]" /> Tải ảnh lên cho AI quét
            </h3>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
              data-testid="vision-upload-zone"
              className={`flex-1 min-h-[400px] border-2 border-dashed rounded-[2rem] flex flex-col items-center justify-center cursor-pointer transition-all duration-500 ${
                isDragging
                  ? "border-[#D4AF37] bg-amber-50/50 scale-[1.01]"
                  : scanPreview
                    ? "border-transparent bg-transparent"
                    : "border-[#D4AF37]/40 bg-zinc-50/50 hover:border-[#D4AF37] hover:bg-amber-50/30"
              }`}
            >
              {scanPreview ? (
                <img
                  src={scanPreview}
                  alt="Preview"
                  className="max-h-[360px] rounded-[1.5rem] object-contain shadow-lg"
                />
              ) : (
                <div className="flex flex-col items-center text-center">
                  <div className="relative mb-8 group">
                    <div className="w-32 h-32 rounded-3xl bg-white shadow-xl border border-zinc-100 flex items-center justify-center transform group-hover:-translate-y-2 transition-transform duration-500">
                      <Shirt className="w-16 h-16 text-zinc-300 transition-colors duration-500 group-hover:text-[#D4AF37]" strokeWidth={1} />
                    </div>
                    {/* Glowing aura */}
                    <div className="absolute -inset-4 bg-amber-400/20 blur-2xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
                  </div>
                  <h4 className="text-xl font-bold text-zinc-800 mb-2 font-serif">
                    Tải ảnh lên để phân tích AI
                  </h4>
                  <p className="text-sm text-zinc-500">
                    Hỗ trợ JPEG, PNG, WebP • Tối đa 10MB
                  </p>
                </div>
              )}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => handleFileSelect(e, "scan")}
            />

            {scanFile && (
              <div className="mt-6 flex items-center justify-between p-4 bg-zinc-50 rounded-2xl border border-zinc-100">
                <div className="flex items-center gap-3 text-sm text-zinc-600">
                  <div className="p-2 bg-white rounded-lg shadow-sm">
                    <Image className="w-4 h-4 text-[#D4AF37]" />
                  </div>
                  <span className="truncate max-w-[200px] font-medium">
                    {scanFile.name}
                  </span>
                  <span className="text-zinc-400 text-xs">
                    ({(scanFile.size / 1024).toFixed(0)} KB)
                  </span>
                </div>
                <button
                  onClick={handleScanUpload}
                  disabled={isUploading}
                  className="bg-[#312E81] hover:bg-indigo-900 text-white px-6 py-2.5 rounded-full text-sm font-bold flex items-center gap-2 transition-colors disabled:opacity-50 shadow-md"
                >
                  {isUploading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ScanFace className="w-4 h-4" />
                  )}
                  {isUploading ? "Đang tải lên..." : "Bắt đầu quét AI"}
                </button>
              </div>
            )}
          </div>

          {/* Results Panel */}
          <div className="bg-white/80 backdrop-blur-xl rounded-[2rem] p-8 shadow-sm border border-white/50 flex flex-col relative overflow-hidden">
            <h3 className="text-sm font-bold text-zinc-800 mb-6 flex items-center gap-2 relative z-10">
              <Eye className="w-5 h-5 text-[#312E81]" /> Kết quả quét
            </h3>

            {/* Subtle background glow for the right panel */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-50/50 rounded-full blur-3xl pointer-events-none" />

            {!taskId && !taskStatus && (
              <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 relative z-10">
                <div className="relative w-32 h-32 mb-8 flex items-center justify-center opacity-30 grayscale">
                  <Shirt className="w-20 h-20 text-zinc-400" strokeWidth={0.5} />
                </div>
                <p className="text-sm font-medium">Chưa có ảnh nào được phân tích</p>
              </div>
            )}

            {isPolling && (
              <div className="flex-1 flex flex-col items-center justify-center relative z-10">
                <div className="relative w-48 h-48 mb-8">
                  {/* Elegant scanning animation */}
                  <div className="absolute inset-0 bg-[#F2EDE4] rounded-full blur-3xl animate-pulse" />
                  <div className="absolute inset-4 rounded-full border border-indigo-200/50 animate-[spin_8s_linear_infinite]" />
                  <div className="absolute inset-8 rounded-full border border-dashed border-[#D4AF37]/40 animate-[spin_12s_linear_infinite_reverse]" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Shirt className="w-16 h-16 text-[#312E81] drop-shadow-[0_0_15px_rgba(49,46,129,0.3)] animate-pulse" strokeWidth={1} />
                  </div>
                  {/* Hologram scan line */}
                  <div className="absolute w-full h-1 bg-gradient-to-r from-transparent via-[#D4AF37] to-transparent animate-[scanline_3s_ease-in-out_infinite] blur-[1px]" />
                </div>
                <p className="text-xl font-bold text-zinc-800 font-serif mb-6">
                  Đang quét và phân tích hình ảnh...
                </p>
                <div className="flex gap-3">
                  <span className="px-4 py-1.5 bg-white border border-zinc-200 rounded-full text-xs font-medium text-zinc-600 shadow-sm">Màu sắc</span>
                  <span className="px-4 py-1.5 bg-white border border-zinc-200 rounded-full text-xs font-medium text-zinc-600 shadow-sm">Chất liệu</span>
                  <span className="px-4 py-1.5 bg-white border border-zinc-200 rounded-full text-xs font-medium text-zinc-600 shadow-sm">Kiểu dáng</span>
                </div>
              </div>
            )}

            {taskStatus && !isPolling && (
              <div className="space-y-6 relative z-10 flex-1 flex flex-col">
                {/* Status Badge */}
                <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
                  <span
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${taskStatus.status === "completed" ? "bg-emerald-100 text-emerald-700" : taskStatus.status === "failed" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}`}
                  >
                    {taskStatus.status === "completed" ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5" />
                    )}
                    {taskStatus.status === "completed" ? "Hoàn tất" : taskStatus.status}
                  </span>
                  <span className="text-[10px] text-zinc-400 font-mono">
                    ID: {taskStatus.task_id}
                  </span>
                </div>

                {/* Similar Items Grid */}
                {taskStatus.detected_objects?.similar_items && (
                  <div className="flex-1 flex flex-col">
                    <h4 className="text-sm font-bold text-zinc-800 mb-4 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#D4AF37]" /> Sản phẩm tương tự
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 custom-scrollbar overflow-y-auto pr-2 pb-4">
                      {taskStatus.detected_objects.similar_items.map(
                        (prod: MixMatchProduct) => (
                          <div
                            key={prod.product_id}
                            className="bg-white border border-zinc-100 rounded-2xl overflow-hidden flex flex-col shadow-sm hover:shadow-md transition-shadow group"
                          >
                            <div className="w-full h-[180px] bg-zinc-50 relative overflow-hidden">
                              <img
                                src={
                                  prod.image_url ||
                                  "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?q=80&w=200"
                                }
                                alt={prod.name}
                                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                referrerPolicy="no-referrer"
                              />
                              <div className="absolute top-2 right-2 bg-white/90 backdrop-blur border border-zinc-100 text-[#D4AF37] text-[10px] px-2.5 py-1 rounded-full font-bold shadow-sm">
                                {prod.match_score}% Độ tương đồng
                              </div>
                            </div>
                            <div className="p-4 flex flex-col justify-between flex-1">
                              <div>
                                <h5 className="text-zinc-800 text-sm font-bold line-clamp-2 leading-snug mb-3">
                                  {prod.name}
                                </h5>
                              </div>

                              {/* --- STORE DROPDOWN --- */}
                              <div className="mt-auto">
                                {(prod as ExtendedMixMatchProduct)
                                  .available_stores &&
                                (prod as ExtendedMixMatchProduct)
                                  .available_stores!.length > 0 ? (
                                  <select
                                    className="w-full bg-zinc-50 border border-zinc-200 text-xs text-zinc-700 p-2.5 rounded-xl focus:outline-none focus:border-[#D4AF37] focus:ring-1 focus:ring-[#D4AF37] mb-3"
                                    value={
                                      selectedStores[prod.product_id] || ""
                                    }
                                    onChange={(e) =>
                                      handleStoreSelect(
                                        prod.product_id,
                                        parseInt(e.target.value, 10),
                                      )
                                    }
                                  >
                                    <option value="" disabled>
                                      -- Chọn cửa hàng gần bạn --
                                    </option>
                                    {(
                                      prod as ExtendedMixMatchProduct
                                    ).available_stores!.map((s) => (
                                      <option
                                        key={s.store_id}
                                        value={s.store_id}
                                      >
                                        {s.name} (Còn {s.stock})
                                      </option>
                                    ))}
                                  </select>
                                ) : (
                                  <div className="w-full bg-red-50 border border-red-100 text-[10px] text-red-600 p-2.5 rounded-xl text-center font-medium mb-3">
                                    Chưa có cửa hàng còn hàng
                                  </div>
                                )}

                                <div className="flex items-center justify-between">
                                  <span className="text-lg text-zinc-900 font-bold">
                                    {prod.price.toLocaleString()} đ
                                  </span>
                                  <button
                                    onClick={() =>
                                      handleReserveClick(
                                        prod as ExtendedMixMatchProduct,
                                      )
                                    }
                                    disabled={
                                      !(prod as ExtendedMixMatchProduct)
                                        .available_stores?.length ||
                                      lockingId === prod.product_id
                                    }
                                    className="px-4 py-2 text-xs bg-[#D4AF37] hover:bg-amber-500 text-white font-bold rounded-full flex items-center gap-2 shadow-md transition-all disabled:opacity-50"
                                  >
                                    {lockingId === prod.product_id ? (
                                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    ) : (
                                      <Lock className="w-3.5 h-3.5" />
                                    )}{" "}
                                    Giữ hàng
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "closet" && (
        <div className="flex flex-col gap-8">
          {/* Upload to Closet */}
          <div className="bg-white rounded-[2rem] p-6 shadow-sm border border-zinc-100 flex flex-col md:flex-row items-center gap-4 justify-between">
            <div className="flex items-center gap-4 w-full md:w-auto">
              <button
                onClick={() => closetFileRef.current?.click()}
                className="bg-zinc-100 hover:bg-zinc-200 text-zinc-700 px-6 py-3 rounded-full text-sm font-bold flex items-center gap-2 transition-colors"
              >
                <UploadCloud className="w-4 h-4" /> Chọn ảnh
              </button>
              <input
                ref={closetFileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(e) => handleFileSelect(e, "closet")}
              />
              {closetFile && (
                <span className="text-sm text-zinc-500 font-medium truncate max-w-[200px]">
                  {closetFile.name}
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-3 w-full md:w-auto">
              <button
                onClick={handleClosetUpload}
                disabled={!closetFile || isUploadingCloset}
                className="flex-1 md:flex-none bg-[#312E81] hover:bg-indigo-900 text-white px-8 py-3 rounded-full text-sm font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-50 shadow-md"
              >
                {isUploadingCloset ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Shirt className="w-4 h-4" />
                )}
                Thêm vào tủ đồ
              </button>
              <button
                onClick={loadCloset}
                className="p-3 bg-white border border-zinc-200 text-zinc-600 hover:bg-zinc-50 rounded-full shadow-sm transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Closet Grid */}
          {isLoadingCloset ? (
            <div className="bg-white/50 backdrop-blur-md rounded-[2rem] p-24 text-center border border-white/50">
              <Loader2 className="w-10 h-10 text-[#D4AF37] animate-spin mx-auto" />
            </div>
          ) : closetItems.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
              {closetItems.map((item) => (
                <div key={item.id} className="bg-white rounded-[2rem] p-3 shadow-sm border border-zinc-100 group hover:shadow-xl transition-all duration-300">
                  <div className="aspect-square rounded-[1.5rem] bg-zinc-50 relative overflow-hidden mb-4">
                    <img
                      src={`${API_BASE}/${item.image_path}`}
                      alt={`Closet item ${item.id}`}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                      referrerPolicy="no-referrer"
                      onError={(e) => {
                        ;(e.target as HTMLImageElement).style.display = "none"
                      }}
                    />
                  </div>
                  <div className="px-2 pb-2">
                    <div className="flex justify-between items-center mb-4">
                      <div>
                        <p className="text-[10px] text-zinc-400 font-mono font-medium uppercase tracking-wider mb-0.5">
                          Mã: {item.id}
                        </p>
                        <p className="text-xs text-zinc-800 font-bold">
                          {new Date(item.created_at).toLocaleDateString("vi-VN")}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setSelectedClosetItem(item)
                        setIsMixMatchOpen(true)
                      }}
                      className="w-full bg-[#F4F6F8] hover:bg-[#D4AF37] text-zinc-700 hover:text-white font-bold text-xs py-3 rounded-xl flex justify-center items-center gap-2 transition-colors shadow-sm"
                    >
                      <Sparkles className="w-4 h-4" /> AI Mix & Match
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div
              className="bg-white/80 backdrop-blur-xl rounded-[2rem] border-2 border-dashed border-zinc-200 p-24 text-center"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="w-24 h-24 bg-zinc-50 rounded-full flex items-center justify-center mx-auto mb-6">
                <Shirt className="w-12 h-12 text-zinc-300" strokeWidth={1} />
              </div>
              <p className="text-xl font-bold text-zinc-700 font-serif mb-2">
                Tủ đồ ảo trống
              </p>
              <p className="text-sm text-zinc-500">
                Kéo thả ảnh trang phục vào đây để bắt đầu.
              </p>
            </div>
          )}
        </div>
      )}
      </div>
      {/* AI Mix & Match Sheet — REAL API */}
      <Sheet
        open={isMixMatchOpen}
        onOpenChange={(open) => {
          setIsMixMatchOpen(open)
          if (!open) setMixMatchResults([])
        }}
      >
        <SheetContent className="w-[400px] sm:w-[500px] border-l border-zinc-200 bg-white/95 backdrop-blur-2xl text-zinc-900 p-0 shadow-2xl overflow-y-auto custom-scrollbar">
          <SheetHeader className="p-8 border-b border-zinc-100 bg-white/80 sticky top-0 z-10 backdrop-blur-xl">
            <SheetTitle className="flex items-center gap-3 text-zinc-900 text-2xl font-bold font-serif">
              <Sparkles className="w-6 h-6 text-[#D4AF37]" />{" "}
              AI Style Matcher
            </SheetTitle>
            <p className="text-xs text-zinc-500 font-medium mt-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-sm animate-pulse" />
              pgvector Cosine Similarity · CLIP 512D
            </p>
          </SheetHeader>

          <div className="p-8 space-y-10">
            {selectedClosetItem && (
              <div className="flex flex-col items-center">
                <div className="relative w-40 h-40 rounded-[2rem] overflow-hidden border-4 border-white shadow-xl mb-4 bg-zinc-50">
                  <img
                    src={`${API_BASE}/${selectedClosetItem.image_path}`}
                    className="w-full h-full object-cover"
                    referrerPolicy="no-referrer"
                  />
                  <div className="absolute bottom-2 w-full text-center">
                    <span className="bg-white/90 backdrop-blur px-3 py-1 rounded-full text-[10px] font-bold text-zinc-800 shadow-sm uppercase tracking-wider">
                      Trang phục gốc
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div>
              <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-wider mb-6 flex items-center gap-2">
                <Shirt className="w-4 h-4 text-[#312E81]" /> Đề xuất phối đồ
              </h3>

              <div className="space-y-4">
                {isLoadingMixMatch ? (
                  <div className="flex flex-col items-center py-16 bg-zinc-50 rounded-3xl border border-zinc-100">
                    <Loader2 className="w-8 h-8 text-[#D4AF37] animate-spin mb-4" />
                    <p className="text-sm text-zinc-600 font-medium">
                      AI đang tìm kiếm các lựa chọn phù hợp nhất...
                    </p>
                  </div>
                ) : mixMatchResults.length > 0 ? (
                  mixMatchResults.map((prod) => (
                    <div
                      key={prod.product_id}
                      className="flex gap-4 p-4 rounded-3xl bg-white border border-zinc-100 hover:border-[#D4AF37]/50 hover:shadow-lg transition-all duration-300 group"
                    >
                      <div className="w-28 h-28 rounded-2xl overflow-hidden shrink-0 bg-zinc-50">
                        <img
                          src={
                            prod.image_url ||
                            "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?q=80&w=200"
                          }
                          alt={prod.name}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                          referrerPolicy="no-referrer"
                        />
                      </div>
                      <div className="flex-1 flex flex-col justify-between min-w-0 py-1">
                        <div>
                          <h4 className="font-bold text-zinc-800 text-sm line-clamp-1 mb-1">
                            {prod.name}
                          </h4>
                          <div className="inline-block bg-amber-50 text-amber-700 text-[10px] px-2 py-0.5 rounded font-bold mb-2">
                            {prod.match_score}% Phù hợp
                          </div>
                        </div>

                        {/* --- STORE DROPDOWN --- */}
                        <div className="mb-3">
                          {(prod as ExtendedMixMatchProduct).available_stores &&
                          (prod as ExtendedMixMatchProduct).available_stores!
                            .length > 0 ? (
                            <select
                              className="w-full bg-zinc-50 border border-zinc-200 text-xs text-zinc-700 p-2 rounded-xl focus:outline-none focus:border-[#D4AF37]"
                              value={selectedStores[prod.product_id] || ""}
                              onChange={(e) =>
                                handleStoreSelect(
                                  prod.product_id,
                                  parseInt(e.target.value, 10),
                                )
                              }
                            >
                              <option value="" disabled>
                                -- Chọn cửa hàng --
                              </option>
                              {(
                                prod as ExtendedMixMatchProduct
                              ).available_stores!.map((s) => (
                                <option key={s.store_id} value={s.store_id}>
                                  {s.name} (Còn {s.stock})
                                </option>
                              ))}
                            </select>
                          ) : (
                            <div className="inline-block bg-red-50 border border-red-100 text-[10px] text-red-600 px-2.5 py-1 rounded-lg font-medium">
                              Chưa có cửa hàng còn hàng
                            </div>
                          )}
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-lg font-bold text-zinc-900">
                            {prod.price.toLocaleString()} đ
                          </span>
                          <button
                            onClick={() =>
                              handleReserveClick(
                                prod as ExtendedMixMatchProduct,
                              )
                            }
                            disabled={
                              !(prod as ExtendedMixMatchProduct)
                                .available_stores?.length ||
                              lockingId === prod.product_id
                            }
                            className="w-8 h-8 rounded-full bg-[#D4AF37] hover:bg-amber-500 text-white flex items-center justify-center transition-colors shadow-sm disabled:opacity-50 shrink-0"
                          >
                            {lockingId === prod.product_id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Lock className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12 text-zinc-500">
                    Không tìm thấy sản phẩm phù hợp.
                  </div>
                )}
              </div>
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* CHECKOUT MODAL (VietQR) */}
      <Dialog
        open={!!checkoutProduct}
        onOpenChange={(open) => !open && closeCheckout()}
      >
        <DialogContent className="max-w-[900px] p-0 bg-zinc-950/90 backdrop-blur-2xl border-white/10 shadow-2xl overflow-hidden">
          {checkoutProduct && (
            <div className="flex flex-col md:flex-row h-full md:h-[600px]">
              {/* Left: Product Recap */}
              <div className="w-full md:w-[400px] bg-zinc-900 p-8 flex flex-col justify-between border-r border-white/5">
                <div>
                  <h2 className="text-xs font-bold text-amber-500 uppercase tracking-widest mb-6">
                    Order Summary
                  </h2>
                  <img
                    src={
                      checkoutProduct.image_url ||
                      "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?q=80&w=600"
                    }
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
                      Đã khóa kho 15 phút. Vui lòng thanh toán để hoàn tất.
                    </p>
                  </div>
                </div>
              </div>

              {/* Right: Payment & Form */}
              <div className="flex-1 p-8 overflow-y-auto">
                {orderResult ? (
                  // SUCCESS & VIETQR
                  <div className="flex flex-col items-center text-center h-full justify-center animate-in zoom-in-95 duration-500">
                    <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6">
                      <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">
                      Đã tạo đơn hàng!
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
                      Quét mã bằng ứng dụng ngân hàng bất kỳ để thanh toán. Đơn
                      hàng sẽ được chuyển sau khi nhận thanh toán.
                    </p>

                    <button
                      onClick={closeCheckout}
                      className="mt-8 px-8 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-xl font-bold text-white transition-colors"
                    >
                      Tiếp tục mua sắm
                    </button>
                  </div>
                ) : (
                  // FORM
                  <form
                    onSubmit={handleFinalizeOrder}
                    className="flex flex-col h-full"
                  >
                    <h2 className="text-2xl font-bold text-white mb-8 flex items-center gap-2">
                      <CreditCard className="w-6 h-6 text-amber-500" /> Thông
                      tin nhận hàng
                    </h2>

                    <div className="space-y-5 flex-1">
                      <div>
                        <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2">
                          Họ và tên
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
                          placeholder="Nguyễn Văn A"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold text-zinc-400 uppercase tracking-widest mb-2">
                          Số điện thoại
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
                          Địa chỉ giao hàng (O2O)
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
                          placeholder="123 Đường số 1..."
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
                      {isOrdering ? "Đang tạo..." : "Tạo đơn chờ thanh toán"}
                    </button>
                  </form>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
