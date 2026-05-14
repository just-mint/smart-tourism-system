import { createFileRoute } from "@tanstack/react-router"
import {
  CheckCircle2,
  Eye,
  Image,
  Loader2,
  RefreshCw,
  ScanFace,
  Shirt,
  Sparkles,
  UploadCloud,
  XCircle,
} from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import {
  type ClosetItemResponse,
  type MixMatchProduct,
  type TaskStatus,
  VisionAPI,
  API_BASE,
} from "@/client/aegis-api"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

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
    <div className="p-6 md:p-8 w-full max-w-[1800px] mx-auto flex flex-col gap-6 animate-in fade-in duration-700 relative z-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 glow-emerald">
            <ScanFace className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Vision & Closet
            </h1>
            <p className="text-sm text-emerald-400/70 font-mono mt-0.5 tracking-widest uppercase">
              AI Scan · Vector Embedding · pgvector
            </p>
          </div>
        </div>

        <div className="flex bg-white/5 rounded-xl border border-white/10 overflow-hidden">
          <button
            onClick={() => setActiveTab("scan")}
            className={`px-5 py-2 text-xs font-mono tracking-wider uppercase transition-all flex items-center gap-2 ${activeTab === "scan" ? "bg-emerald-500/10 text-emerald-400 border-b-2 border-emerald-400" : "text-zinc-500 hover:text-zinc-300"}`}
          >
            <Eye className="w-3.5 h-3.5" /> AI Scan
          </button>
          <button
            onClick={() => setActiveTab("closet")}
            className={`px-5 py-2 text-xs font-mono tracking-wider uppercase transition-all flex items-center gap-2 ${activeTab === "closet" ? "bg-purple-500/10 text-purple-400 border-b-2 border-purple-400" : "text-zinc-500 hover:text-zinc-300"}`}
          >
            <Shirt className="w-3.5 h-3.5" /> Virtual Closet
          </button>
        </div>
      </div>

      {activeTab === "scan" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upload Zone */}
          <div className="glass-card p-6 flex flex-col">
            <h3 className="text-xs font-mono text-emerald-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <UploadCloud className="w-4 h-4" /> Upload for AI Scan
            </h3>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
              className={`flex-1 min-h-[280px] border-2 border-dashed rounded-2xl flex flex-col items-center justify-center cursor-pointer transition-all duration-300 ${isDragging
                  ? "border-emerald-400 bg-emerald-500/10 scale-[1.02]"
                  : scanPreview
                    ? "border-white/10 bg-transparent"
                    : "border-white/10 bg-white/[0.02] hover:border-emerald-400/30 hover:bg-white/[0.04]"
                }`}
            >
              {scanPreview ? (
                <img
                  src={scanPreview}
                  alt="Preview"
                  className="max-h-[260px] rounded-xl object-contain"
                />
              ) : (
                <>
                  <div className="relative mb-6">
                    <div className="w-20 h-20 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                      <UploadCloud className="w-8 h-8 text-emerald-400" />
                    </div>
                    {/* Scan animation */}
                    <div className="absolute inset-0 rounded-2xl overflow-hidden">
                      <div className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-emerald-400 to-transparent animate-[scanline_2s_ease-in-out_infinite]" />
                    </div>
                  </div>
                  <p className="text-sm text-zinc-400 mb-1">
                    Kéo thả ảnh hoặc click để chọn
                  </p>
                  <p className="text-[10px] text-zinc-600 font-mono">
                    JPEG, PNG, WebP • Max 10MB
                  </p>
                </>
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
              <div className="mt-4 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-zinc-400">
                  <Image className="w-3.5 h-3.5" />
                  <span className="truncate max-w-[200px]">
                    {scanFile.name}
                  </span>
                  <span className="text-zinc-600">
                    ({(scanFile.size / 1024).toFixed(0)} KB)
                  </span>
                </div>
                <button
                  onClick={handleScanUpload}
                  disabled={isUploading}
                  className="aegis-btn aegis-btn-primary text-xs"
                >
                  {isUploading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <ScanFace className="w-3.5 h-3.5" />
                  )}
                  {isUploading ? "Uploading..." : "Start AI Scan"}
                </button>
              </div>
            )}
          </div>

          {/* Results Panel */}
          <div className="glass-card p-6 flex flex-col">
            <h3 className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Eye className="w-4 h-4" /> Scan Results
            </h3>

            {!taskId && !taskStatus && (
              <div className="flex-1 flex flex-col items-center justify-center text-zinc-600">
                <div className="relative w-24 h-24 mb-6">
                  <div className="absolute inset-0 rounded-full border border-emerald-500/20 animate-[spin_4s_linear_infinite]" />
                  <div className="absolute inset-3 rounded-full border border-dashed border-emerald-500/30 animate-[spin_6s_linear_infinite_reverse]" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <ScanFace className="w-8 h-8 text-emerald-500/30" />
                  </div>
                </div>
                <p className="text-sm font-mono">Awaiting image input...</p>
              </div>
            )}

            {isPolling && (
              <div className="flex-1 flex flex-col items-center justify-center">
                <div className="relative w-24 h-24 mb-6">
                  <div className="absolute inset-0 rounded-full border-2 border-emerald-500/40 animate-ping" />
                  <div className="absolute inset-0 rounded-full border border-emerald-500/60 animate-[spin_2s_linear_infinite]" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
                  </div>
                </div>
                <p className="text-sm text-emerald-400 font-mono animate-pulse">
                  AI Processing...
                </p>
                <p className="text-[10px] text-zinc-600 font-mono mt-1">
                  Task: {taskId}
                </p>
              </div>
            )}

            {taskStatus && !isPolling && (
              <div className="space-y-4">
                {/* Status Badge */}
                <div className="flex items-center justify-between">
                  <span
                    className={`status-badge ${taskStatus.status === "completed" ? "status-badge-active" : taskStatus.status === "failed" ? "status-badge-danger" : "status-badge-warning"}`}
                  >
                    {taskStatus.status === "completed" ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                    {taskStatus.status as string}
                  </span>
                  <span className="text-[10px] text-zinc-600 font-mono">
                    ID: {taskStatus.task_id}
                  </span>
                </div>

                {/* Similar Items Grid */}
                {(taskStatus.detected_objects as any)?.similar_items && (
                  <div className="glass-card p-4">
                    <h4 className="text-[10px] font-mono text-purple-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                      <Sparkles className="w-4 h-4" /> Recommended Matches
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {((taskStatus.detected_objects as any).similar_items as any[]).map(
                        (prod: any) => (
                          <div
                            key={prod.product_id}
                            className="bg-white/5 border border-white/10 rounded-xl overflow-hidden flex flex-col transition-transform hover:scale-[1.02]"
                          >
                            <div className="w-full h-[150px] bg-zinc-800 relative">
                              <img
                                src={
                                  prod.image_url ||
                                  "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?q=80&w=200"
                                }
                                alt={prod.name}
                                className="w-full h-full object-cover"
                              />
                              <div className="absolute top-2 right-2 bg-purple-500/80 backdrop-blur text-white text-[10px] px-2 py-1 rounded font-bold">
                                {prod.match_score}% Match
                              </div>
                            </div>
                            <div className="p-3 flex flex-col justify-between flex-1">
                              <div>
                                <h5 className="text-white text-sm font-bold line-clamp-1">
                                  {prod.name}
                                </h5>
                              </div>
                              <div className="flex items-center justify-between mt-3">
                                <span className="text-emerald-400 font-mono font-bold">
                                  {prod.price.toLocaleString()}₫
                                </span>
                                <button className="px-3 py-1.5 text-[10px] bg-purple-500 hover:bg-purple-600 text-white font-bold rounded flex items-center gap-1 shadow-[0_0_10px_rgba(168,85,247,0.4)] transition-all">
                                  <Shirt className="w-3 h-3" /> Thêm tủ đồ
                                </button>
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
        <>
          {/* Upload to Closet */}
          <div className="glass-card p-5 flex items-center gap-4">
            <div className="flex-1 flex items-center gap-3">
              <button
                onClick={() => closetFileRef.current?.click()}
                className="aegis-btn aegis-btn-ghost text-xs"
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
                <span className="text-xs text-zinc-400 truncate">
                  {closetFile.name}
                </span>
              )}
            </div>
            <button
              onClick={handleClosetUpload}
              disabled={!closetFile || isUploadingCloset}
              className="aegis-btn aegis-btn-primary text-xs disabled:opacity-30"
            >
              {isUploadingCloset ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Shirt className="w-3.5 h-3.5" />
              )}
              Add to Closet
            </button>
            <button
              onClick={loadCloset}
              className="aegis-btn aegis-btn-ghost text-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Closet Grid */}
          {isLoadingCloset ? (
            <div className="glass-card p-12 text-center">
              <Loader2 className="w-8 h-8 text-purple-400 animate-spin mx-auto" />
            </div>
          ) : closetItems.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 stagger-children">
              {closetItems.map((item) => (
                <div key={item.id} className="glass-card overflow-hidden group">
                  <div className="aspect-square bg-white/[0.02] relative overflow-hidden">
                    <img
                      src={`${API_BASE}/${item.image_path}`}
                      alt={`Closet item ${item.id}`}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                      onError={(e) => {
                        ; (e.target as HTMLImageElement).style.display = "none"
                      }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <div className="p-3">
                    <div className="flex justify-between items-center mb-2">
                      <div>
                        <p className="text-[10px] text-zinc-500 font-mono">
                          ID: {item.id}
                        </p>
                        <p className="text-[10px] text-zinc-600 font-mono">
                          {new Date(item.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setSelectedClosetItem(item)
                        setIsMixMatchOpen(true)
                      }}
                      className="w-full mt-1 bg-gradient-to-r from-purple-600/20 to-cyan-600/20 hover:from-purple-500/40 hover:to-cyan-500/40 border border-purple-500/30 text-purple-300 hover:text-white font-mono text-[10px] uppercase tracking-wider py-1.5 rounded flex justify-center items-center gap-1.5 transition-all"
                    >
                      <Sparkles className="w-3 h-3" /> AI Mix & Match
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div
              className="glass-card p-12 text-center"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <Shirt className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
              <p className="text-zinc-500">
                Tủ đồ ảo trống. Kéo thả ảnh trang phục vào đây!
              </p>
            </div>
          )}
        </>
      )}
      {/* AI Mix & Match Sheet — REAL API */}
      <Sheet
        open={isMixMatchOpen}
        onOpenChange={(open) => {
          setIsMixMatchOpen(open)
          if (!open) setMixMatchResults([])
        }}
      >
        <SheetContent className="w-[400px] sm:w-[500px] border-l border-white/10 bg-black/80 backdrop-blur-3xl text-zinc-100 p-0 shadow-[-20px_0_50px_rgba(0,0,0,0.8)] overflow-y-auto custom-scrollbar">
          <SheetHeader className="p-6 border-b border-white/10 bg-gradient-to-b from-purple-900/20 to-transparent sticky top-0 z-10 backdrop-blur-md">
            <SheetTitle className="flex items-center gap-3 text-white text-xl font-bold tracking-wide">
              <Sparkles className="w-6 h-6 text-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)]" />{" "}
              AI Style Matcher
            </SheetTitle>
            <p className="text-xs text-purple-400 font-mono mt-1 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.8)] animate-pulse" />
              pgvector Cosine Similarity · CLIP 512D
            </p>
          </SheetHeader>

          <div className="p-6 space-y-8">
            {selectedClosetItem && (
              <div className="flex flex-col items-center">
                <div className="relative w-32 h-32 rounded-2xl overflow-hidden border-2 border-purple-500/50 shadow-[0_0_30px_rgba(168,85,247,0.3)] mb-4">
                  <img
                    src={`${API_BASE}/${selectedClosetItem.image_path}`}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                  <div className="absolute bottom-2 w-full text-center text-[10px] font-mono text-purple-300">
                    Target Vector
                  </div>
                </div>
                <div className="w-full h-px bg-gradient-to-r from-transparent via-purple-500/50 to-transparent" />
              </div>
            )}

            <div>
              <h3 className="text-sm font-bold text-zinc-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Shirt className="w-4 h-4 text-cyan-400" /> Recommended Matches
              </h3>

              <div className="space-y-4">
                {isLoadingMixMatch ? (
                  <div className="flex flex-col items-center py-12">
                    <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-3" />
                    <p className="text-xs text-purple-300 font-mono animate-pulse">
                      Đang tìm kiếm sản phẩm tương tự...
                    </p>
                  </div>
                ) : mixMatchResults.length > 0 ? (
                  mixMatchResults.map((prod) => (
                    <div
                      key={prod.product_id}
                      className="flex gap-4 p-4 rounded-2xl bg-white/5 border border-white/10 hover:border-purple-500/50 hover:bg-white/10 transition-all cursor-pointer"
                    >
                      <div className="w-24 h-24 rounded-xl overflow-hidden shrink-0 bg-zinc-800">
                        <img
                          src={
                            prod.image_url ||
                            "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?q=80&w=200"
                          }
                          alt={prod.name}
                          className="w-full h-full object-cover"
                        />
                      </div>
                      <div className="flex-1 flex flex-col justify-between min-w-0">
                        <div>
                          <h4 className="font-bold text-white text-sm truncate">
                            {prod.name}
                          </h4>
                          <p className="text-[10px] text-zinc-400 mt-1 line-clamp-2">
                            {prod.description}
                          </p>
                        </div>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-emerald-400 font-mono font-bold text-sm">
                            {prod.price.toLocaleString()}₫
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${prod.match_score >= 90
                                ? "bg-purple-500/20 text-purple-300 border-purple-500/30"
                                : prod.match_score >= 70
                                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
                                  : "bg-blue-500/20 text-blue-300 border-blue-500/30"
                              }`}
                          >
                            Match: {prod.match_score}%
                          </span>
                        </div>
                        {prod.stock <= 0 && (
                          <p className="text-[10px] text-red-400 font-mono mt-1">
                            ⚠ Hết hàng
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12">
                    <Sparkles className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
                    <p className="text-sm text-zinc-500">
                      Chưa có kết quả. Cần products có vector embeddings.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
