import { createFileRoute } from "@tanstack/react-router"
import {
  ArrowRight,
  BookOpen,
  ChevronRight,
  Command,
  Compass,
  Globe,
  Flag,
  Landmark,
  Loader2,
  Lock,
  MapPin,
  Navigation,
  Send,
  ShoppingBag,
  Sparkles,
  Star,
  TrendingUp,
  X,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import {
  CultureAPI,
  SpatialAPI,
  type CultureMetadataResponse,
  type PlaceDetailWithAI,
  type PlaceResponse,
  type ProductCompactResponse,
  type ReviewResponse,
} from "@/client/aegis-api"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/culture")({
  component: CultureHeritage,
})

// Ảnh nền chất lượng cao, rõ nét
const BACKGROUND_IMAGE =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1200' height='800' viewBox='0 0 1200 800'%3E%3Crect width='1200' height='800' fill='%23050b14'/%3E%3Cg fill='none' stroke='%23d4af37' stroke-opacity='.28'%3E%3Cpath d='M140 620h920M220 620V300l380-150 380 150v320M300 620V360h600v260M390 620V410M510 620V410M630 620V410M750 620V410M870 620V410'/%3E%3C/g%3E%3Ctext x='600' y='705' text-anchor='middle' fill='%23d4af37' fill-opacity='.8' font-family='Arial' font-size='36'%3EAEGIS Heritage%3C/text%3E%3C/svg%3E"

const TRENDING_HERITAGES = [
  {
    name: "Vịnh Hạ Long",
    subtitle: "Kỳ quan thiên nhiên thế giới",
    desc: "Hòn Trống Mái, Động Thiên Cung, vẻ đẹp huyền ảo",
    query: "Vịnh Hạ Long",
  },
  {
    name: "Cố đô Huế",
    subtitle: "Kiến trúc triều Nguyễn độc đáo",
    desc: "Sự giao thoa văn hóa lịch sử",
    query: "Huế",
  },
  {
    name: "Hà Nội",
    subtitle: "Thủ đô ngàn năm văn hiến",
    desc: "Hồ Gươm, 36 phố phường",
    query: "Hà Nội",
  },
  {
    name: "Phố cổ Hội An",
    subtitle: "Di sản văn hóa thế giới",
    desc: "Đèn lồng, cổ kính, thơ mộng",
    query: "Hội An",
  },
  {
    name: "Ninh Bình",
    subtitle: "Tràng An, Tam Cốc",
    desc: "Vịnh Hạ Long trên cạn",
    query: "Ninh Bình",
  },
  {
    name: "Sapa",
    subtitle: "Thành phố trong sương",
    desc: "Ruộng bậc thang, đỉnh Fansipan",
    query: "Sapa",
    wikiTitle: "Ruộng bậc thang Sa Pa",
  },
]

type RecommendedProduct = ProductCompactResponse & {
  storeName: string
}

function CultureHeritage() {
  const { user: currentUser } = useAuth()
  const [searchQuery, setSearchQuery] = useState("")
  const [places, setPlaces] = useState<PlaceResponse[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [selectedPlace, setSelectedPlace] = useState<PlaceDetailWithAI | null>(
    null,
  )
  const [reviews, setReviews] = useState<ReviewResponse[]>([])
  const [isLoadingStory, setIsLoadingStory] = useState(false)
  const [_isLoadingReviews, setIsLoadingReviews] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [reviewText, setReviewText] = useState("")
  const [reviewRating, setReviewRating] = useState(5)
  const [isSubmittingReview, setIsSubmittingReview] = useState(false)
  const [cultureMetadata, setCultureMetadata] =
    useState<CultureMetadataResponse | null>(null)
  const [recommendedProducts, setRecommendedProducts] = useState<
    RecommendedProduct[]
  >([])
  const [trendingImages, setTrendingImages] = useState<Record<string, string>>(
    {},
  )
  const [isLoadingRecommendations, setIsLoadingRecommendations] =
    useState(false)
  const searchRef = useRef<HTMLInputElement>(null)
  const [typed, setTyped] = useState("")
  const phrases = [
    "tìm hiểu về Chùa Một Cột...",
    "khám phá Vịnh Hạ Long...",
    "kể chuyện Thánh địa Mỹ Sơn...",
  ]

  useEffect(() => {
    let i = 0,
      j = 0,
      forward = true
    const interval = setInterval(() => {
      if (forward) {
        if (j <= phrases[i].length) {
          setTyped(phrases[i].slice(0, j))
          j++
        } else {
          forward = false
          setTimeout(() => {}, 2000)
        }
      } else {
        if (j >= 0) {
          setTyped(phrases[i].slice(0, j))
          j--
        } else {
          forward = true
          i = (i + 1) % phrases.length
          j = 0
        }
      }
    }, 100)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    CultureAPI.getMetadata()
      .then((res) => setCultureMetadata(res.data))
      .catch(() => setCultureMetadata(null))
  }, [])

  useEffect(() => {
    let cancelled = false

    Promise.all(
      TRENDING_HERITAGES.map((item) =>
        CultureAPI.getWikiImage(item.wikiTitle ?? item.name, "di sản")
          .then((res) => [item.name, res.data.image_url || ""] as const)
          .catch(() => [item.name, ""] as const),
      ),
    ).then((entries) => {
      if (cancelled) return
      setTrendingImages(
        Object.fromEntries(entries.filter(([, imageUrl]) => imageUrl)),
      )
    })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [])

  const handleSearch = async (queryOverride?: string) => {
    const query = (queryOverride ?? searchQuery).trim()
    if (!query) return
    setSearchQuery(query)
    setIsSearching(true)
    try {
      const res = await CultureAPI.searchPlaces(query)
      setPlaces(res.data)
    } catch {
      setPlaces([])
    } finally {
      setIsSearching(false)
    }
  }

  const handleOpenPlace = async (place: PlaceResponse) => {
    setShowModal(true)
    setIsLoadingStory(true)
    setIsLoadingReviews(true)
    setSelectedPlace(null)
    setReviews([])
    try {
      const [storyRes, reviewsRes] = await Promise.all([
        CultureAPI.getPlaceStory(place.id),
        CultureAPI.getPlaceReviews(place.id),
      ])
      setSelectedPlace(storyRes.data)
      setReviews(reviewsRes.data)
    } catch {
      setSelectedPlace({ ...place, ai_story: "Không thể tải câu chuyện AI." })
    } finally {
      setIsLoadingStory(false)
      setIsLoadingReviews(false)
    }
  }

  const handleSubmitReview = async () => {
    const trimmedText = reviewText.trim()
    if (!selectedPlace) return
    if (!currentUser) {
      toast.error("Bạn cần đăng nhập để gửi đánh giá.")
      return
    }
    if (reviewRating < 1 || reviewRating > 5) {
      toast.error("Rating phải nằm trong khoảng 1-5 sao.")
      return
    }
    if (trimmedText.length < 10) {
      toast.error("Nội dung đánh giá cần ít nhất 10 ký tự.")
      return
    }
    if (trimmedText.length > 1000) {
      toast.error("Nội dung đánh giá tối đa 1000 ký tự.")
      return
    }
    setIsSubmittingReview(true)
    try {
      const res = await CultureAPI.addPlaceReview(selectedPlace.id, {
        rating: reviewRating,
        text: trimmedText,
      })
      setReviews((prev) => [res.data, ...prev])
      setReviewText("")
      setReviewRating(5)
      toast.success("Đánh giá đã gửi và đang chờ duyệt.")
    } catch (error: any) {
      if (error?.response?.status === 401) {
        toast.error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
      } else if (error?.response?.status === 422) {
        toast.error("Nội dung hoặc rating chưa hợp lệ.")
      } else {
        toast.error("Không thể gửi đánh giá lúc này.")
      }
    } finally {
      setIsSubmittingReview(false)
    }
  }

  const handleReportReview = async (reviewId: number) => {
    try {
      const res = await CultureAPI.reportReview(
        reviewId,
        "Reported from Culture review UI",
      )
      setReviews((prev) =>
        prev.map((review) => (review.id === reviewId ? res.data : review)),
      )
      toast.success("Đã gửi báo cáo để admin kiểm duyệt.")
    } catch {
      toast.error("Không thể báo cáo đánh giá này.")
    }
  }

  const handleTrendingClick = (query: string) => {
    void handleSearch(query)
  }

  const showEmptyState =
    places.length === 0 && !isSearching && searchQuery === ""

  const [wikiImage, setWikiImage] = useState<string | null>(null)
  const [wikiImageSource, setWikiImageSource] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    if (!selectedPlace?.name) {
      setWikiImage(null)
      return
    }

    CultureAPI.getWikiImage(selectedPlace.name, selectedPlace.category)
      .then((res) => {
        if (!cancelled) {
          setWikiImage(res.data.image_url || null)
          setWikiImageSource(res.data.source || null)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setWikiImage(null)
          setWikiImageSource(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedPlace?.name, selectedPlace?.category])

  const placeImages = selectedPlace
    ? [...(selectedPlace.images || []), ...(wikiImage ? [wikiImage] : [])]
    : []
  const heroImage = placeImages[0] || BACKGROUND_IMAGE
  const imageSource =
    selectedPlace?.image_source || wikiImageSource || "AEGIS placeholder"

  useEffect(() => {
    let cancelled = false
    const placeId = selectedPlace?.place_id
    if (!placeId) {
      setRecommendedProducts([])
      return
    }

    setIsLoadingRecommendations(true)
    SpatialAPI.getPlaceO2OContext(placeId, 2000)
      .then((res) => {
        const products = res.data.nearby_stores
          .flatMap((store) =>
            store.products.map((product) => ({
              ...product,
              storeName: store.name,
            })),
          )
          .slice(0, 6)
        if (!cancelled) setRecommendedProducts(products)
      })
      .catch(() => {
        if (!cancelled) setRecommendedProducts([])
      })
      .finally(() => {
        if (!cancelled) setIsLoadingRecommendations(false)
      })

    return () => {
      cancelled = true
    }
  }, [selectedPlace?.place_id])

  return (
    <div className="route-performance-budget relative min-h-screen w-full bg-black overflow-hidden">
      {/* Background cố định, rõ nét, không bị che sidebar */}
      <div
        className="absolute inset-0 z-0 bg-cover bg-center bg-fixed bg-no-repeat"
        style={{ backgroundImage: `url(${BACKGROUND_IMAGE})` }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-black/80 via-black/60 to-black/80" />
        <div className="absolute inset-0 bg-black/20" />
      </div>

      {/* Content - có padding để không đè sidebar */}
      <div className="relative z-10 w-full h-full px-4 md:px-6 py-8 overflow-y-auto custom-scroll">
        <div className="max-w-7xl mx-auto space-y-12">
          {/* Hero + Omnibar */}
          <div className="text-center space-y-6 animate-fade-in-up">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 shadow-xl">
              <Sparkles className="w-4 h-4 text-amber-200" />
              <span className="text-xs font-mono font-bold tracking-wider text-white/90 uppercase">
                Công cụ kể chuyện AI
              </span>
            </div>
            <h1 className="text-5xl md:text-7xl font-black tracking-tighter">
              <span className="text-white drop-shadow-[0_2px_10px_rgba(255,255,255,0.2)]">
                Văn hóa & Di sản
              </span>
            </h1>
            <p className="text-white/60 text-base md:text-lg max-w-2xl mx-auto">
              Khám phá chiều sâu lịch sử qua lăng kính trí tuệ nhân tạo
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSearch()
              }}
              className="max-w-3xl mx-auto mt-8"
            >
              <div className="relative group">
                <Sparkles className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-white/80 drop-shadow-lg" />
                <input
                  ref={searchRef}
                  type="text"
                  data-testid="culture-search-input"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={`${typed}`}
                  className="w-full bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl py-5 pl-14 pr-44 text-white placeholder:text-white/60 text-lg focus:outline-none focus:border-white/40 focus:ring-2 focus:ring-white/20 transition-all shadow-[0_8px_32px_0_rgba(0,0,0,0.5)]"
                />
                <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-3">
                  <kbd className="hidden md:inline-flex items-center gap-1 px-2 py-1 rounded-md bg-white/10 border border-white/20 text-white/60 text-xs font-mono">
                    <Command size={12} /> K
                  </kbd>
                  <button
                    type="submit"
                    disabled={isSearching}
                    className="bg-white/20 hover:bg-white/30 backdrop-blur-md border border-white/30 hover:scale-105 transition-all px-5 py-2 rounded-xl text-white font-semibold flex items-center gap-2 shadow-lg disabled:opacity-50"
                  >
                    {isSearching ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send size={16} />
                    )}
                    <span>Khám phá</span>
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* Results Area */}
          {places.length > 0 && (
            <div className="space-y-6 pb-20">
              <div className="flex items-center gap-2 mb-8 border-b border-white/10 pb-4">
                <MapPin className="w-5 h-5 text-cyan-400" />
                <h2 className="text-xl font-bold text-white uppercase tracking-wider">
                  Kết quả từ CSDL ({places.length})
                </h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {places.map((place) => (
                  <div
                    key={place.id}
                    className="group bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl p-6 hover:bg-white/10 hover:border-cyan-500/50 transition-all cursor-pointer shadow-lg hover:shadow-[0_8px_32px_0_rgba(34,211,238,0.2)] flex flex-col justify-between min-h-[160px]"
                    onClick={() => handleOpenPlace(place)}
                  >
                    <div>
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="text-lg font-bold text-white group-hover:text-cyan-400 transition-colors drop-shadow-md">
                          {place.name}
                        </h3>
                        <Landmark className="w-5 h-5 text-white/40 group-hover:text-cyan-400/50 transition-colors" />
                      </div>
                      <p className="text-sm text-white/60 line-clamp-2 drop-shadow-md">
                        {place.category || "Di tích văn hóa"}
                      </p>
                    </div>
                    <div className="mt-4 flex items-center justify-between text-xs border-t border-white/10 pt-3">
                      <span className="text-white/40 flex items-center gap-1 font-mono">
                        📍 {place.lat.toFixed(4)}, {place.lon.toFixed(4)}
                      </span>
                      <span className="text-cyan-400 font-medium group-hover:underline flex items-center gap-1">
                        Chi tiết{" "}
                        <ChevronRight
                          size={14}
                          className="group-hover:translate-x-1 transition-transform"
                        />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Empty State - Trending Cards 3D */}
          {showEmptyState && (
            <div className="space-y-10">
              <div className="text-center">
                <TrendingUp className="inline-block w-6 h-6 text-cyan-400 mr-2" />
                <span className="text-white/70 text-sm font-mono tracking-wider uppercase">
                  Điểm đến được quan tâm nhất
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
                {TRENDING_HERITAGES.map((item, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleTrendingClick(item.query)}
                    className="group relative overflow-hidden rounded-2xl cursor-pointer transition-all duration-500 hover:scale-105 hover:z-10 transform-gpu perspective-1000 border border-white/10 shadow-[0_8px_30px_rgb(0,0,0,0.8)] hover:border-white/30 hover:shadow-[0_8px_30px_rgba(255,255,255,0.15)]"
                  >
                    <div className="absolute inset-0 transition-transform duration-700 group-hover:scale-105 bg-[#050B14]">
                      {trendingImages[item.name] ? (
                        <img
                          src={trendingImages[item.name]}
                          alt={item.name}
                          className="h-full w-full object-cover opacity-90"
                          onError={() =>
                            setTrendingImages((prev) => {
                              const next = { ...prev }
                              delete next[item.name]
                              return next
                            })
                          }
                        />
                      ) : (
                        <div className="absolute inset-0 flex items-center justify-center">
                          <Landmark className="h-16 w-16 text-[#D4AF37]/40" />
                        </div>
                      )}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/45 to-black/15" />
                    </div>
                    <div className="relative p-6 h-72 flex flex-col justify-end">
                      <h3 className="text-2xl font-bold text-white group-hover:text-amber-200 transition drop-shadow-md">
                        {item.name}
                      </h3>
                      <p className="text-white/90 text-sm mt-1 drop-shadow-md">
                        {item.subtitle}
                      </p>
                      <p className="text-white/70 text-xs mt-2 drop-shadow-md">
                        {item.desc}
                      </p>
                      <div className="mt-5 flex items-center gap-2 text-amber-300 text-sm font-medium opacity-0 group-hover:opacity-100 transition-all translate-y-2 group-hover:translate-y-0">
                        Khám phá ngay <Navigation size={14} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Thống kê lấy từ backend */}
          {showEmptyState && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-8 pb-20">
              <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-5 text-center border border-white/10">
                <Globe className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">
                  {cultureMetadata?.total_categories.toLocaleString("vi-VN") ?? "--"}
                </div>
                <div className="text-xs text-white/50">Nhóm địa điểm</div>
              </div>
              <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-5 text-center border border-white/10">
                <Compass className="w-8 h-8 text-purple-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">
                  {cultureMetadata?.total_places.toLocaleString("vi-VN") ?? "--"}
                </div>
                <div className="text-xs text-white/50">Điểm đến</div>
              </div>
              <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-5 text-center border border-white/10">
                <ShoppingBag className="w-8 h-8 text-pink-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">
                  {cultureMetadata?.total_stores.toLocaleString("vi-VN") ?? "--"}
                </div>
                <div className="text-xs text-white/50">Cửa hàng O2O</div>
              </div>
              <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-5 text-center border border-white/10">
                <Star className="w-8 h-8 text-amber-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">
                  {cultureMetadata?.approved_reviews.toLocaleString("vi-VN") ?? "--"}
                </div>
                <div className="text-xs text-white/50">Đánh giá đã duyệt</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Premium One-Page Overlay - Changed from fixed to absolute to prevent overlaying the layout sidebar */}
      {showModal && (
        <div
          className="absolute inset-0 z-50 bg-[#0B132B] overflow-y-auto custom-scroll font-sans"
          onClick={() => setShowModal(false)}
        >
          {/* Hero Banner */}
          <div
            className="relative w-full h-[60vh] min-h-[400px]"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={heroImage}
              alt="Hero"
              className="w-full h-full object-cover opacity-50"
            />
            <div className="absolute inset-0 bg-gradient-to-b from-[#0B132B]/30 via-transparent to-[#0B132B]" />
            <button
              onClick={() => setShowModal(false)}
              className="absolute top-6 right-6 p-3 bg-black/40 backdrop-blur-md rounded-full border border-white/20 hover:bg-white/10 transition-colors z-10"
            >
              <X className="w-6 h-6 text-white" />
            </button>
            <div className="absolute bottom-0 left-0 w-full p-8 md:p-16 flex flex-col items-center justify-end text-center">
              <h2 className="text-5xl md:text-7xl font-serif text-[#D4AF37] mb-4 drop-shadow-lg tracking-wide">
                {selectedPlace?.name}
              </h2>
              <div className="w-24 h-1 bg-[#D4AF37] mb-6 shadow-[0_0_10px_#D4AF37]" />
              <p className="text-white/80 font-mono text-sm tracking-[0.2em] uppercase">
                Trải nghiệm di sản · Hệ sinh thái O2O
              </p>
              <p className="mt-3 text-xs text-white/50 font-mono">
                Nguồn ảnh: {imageSource}
              </p>
            </div>
          </div>

          <div
            className="max-w-7xl mx-auto px-4 md:px-8 py-12 space-y-16"
            onClick={(e) => e.stopPropagation()}
          >
            {/* AI Storyteller & Gallery Split */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
              {/* Left: Story */}
              <div className="space-y-6">
                <div className="flex items-center gap-3 mb-6">
                  <Sparkles className="w-5 h-5 text-[#D4AF37]" />
                  <h3 className="text-[#D4AF37] font-sans font-semibold tracking-[0.2em] uppercase text-sm">
                    Câu chuyện từ dòng thời gian
                  </h3>
                </div>
                {isLoadingStory ? (
                  <div className="animate-pulse space-y-4">
                    <div className="h-4 bg-white/10 rounded w-3/4" />
                    <div className="h-4 bg-white/10 rounded w-full" />
                    <div className="h-4 bg-white/10 rounded w-5/6" />
                  </div>
                ) : (
                  <div className="prose prose-invert max-w-none">
                    <p className="text-white/90 font-sans text-lg md:text-xl leading-relaxed font-light text-justify">
                      <span className="float-left text-7xl font-serif text-[#D4AF37] mr-3 mt-2 leading-none">
                        {(selectedPlace?.ai_story || "T")[0]}
                      </span>
                      {(selectedPlace?.ai_story || "T").substring(1)}
                    </p>
                  </div>
                )}
                <div className="pt-8 flex items-center gap-2 text-white/50 text-sm font-mono border-t border-white/10">
                  <MapPin className="w-4 h-4" /> {selectedPlace?.address}
                </div>
              </div>

              {/* Right: Gallery */}
              <div className="grid grid-cols-2 gap-4">
                {[0, 1, 2, 3].map((slot) => {
                  const image = placeImages[slot]
                  const heightClass = slot === 1 || slot === 2 ? "h-64" : "h-48"
                  const offsetClass = slot === 1 ? "-mt-8" : ""
                  return image ? (
                    <img
                      key={slot}
                      src={image}
                      className={`w-full ${heightClass} ${offsetClass} object-cover rounded-2xl shadow-xl hover:scale-105 transition-transform duration-500`}
                      alt={`${selectedPlace?.name || "Di sản"} ${slot + 1}`}
                    />
                  ) : (
                    <div
                      key={slot}
                      className={`w-full ${heightClass} ${offsetClass} rounded-2xl border border-white/10 bg-white/5 flex items-center justify-center`}
                    >
                      <Landmark className="h-10 w-10 text-white/25" />
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Visitor Info Table */}
            <div className="bg-black/40 backdrop-blur-md border border-white/10 shadow-2xl rounded-2xl overflow-hidden">
              <div className="bg-[#050B14] p-5 border-b border-white/10 flex items-center gap-3">
                <BookOpen className="w-5 h-5 text-[#D4AF37]" />
                <h3 className="font-serif text-lg text-white">
                  Thông tin từ CSDL
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-white/10">
                <div className="p-6 space-y-2">
                  <Landmark className="w-6 h-6 text-white/50 mb-4" />
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Phân loại
                  </h4>
                  <p className="text-white text-lg">
                    {selectedPlace?.category || "Chưa phân loại"}
                  </p>
                  <p className="text-white/40 text-sm">
                    Nguồn dữ liệu địa điểm
                  </p>
                </div>
                <div className="p-6 space-y-2">
                  <Star className="w-6 h-6 text-white/50 mb-4" />
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Rating
                  </h4>
                  <p className="text-white text-lg">
                    {selectedPlace?.rating ? `${selectedPlace.rating}/5` : "Chưa có"}
                  </p>
                  <p className="text-white/40 text-sm">
                    Điểm đánh giá trong CSDL
                  </p>
                </div>
                <div className="p-6 space-y-2">
                  <BookOpen className="w-6 h-6 text-white/50 mb-4" />
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Review
                  </h4>
                  <p className="text-white text-lg">
                    {selectedPlace?.review_count?.toLocaleString("vi-VN") ?? "Chưa có"}
                  </p>
                  <p className="text-white/40 text-sm">Lượt review ghi nhận</p>
                </div>
                <div className="p-6 space-y-2">
                  <Globe className="w-6 h-6 text-white/50 mb-4" />
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Địa chỉ
                  </h4>
                  <p className="text-white text-lg">
                    {selectedPlace?.address || "Chưa có địa chỉ"}
                  </p>
                  <p className="text-white/40 text-sm">
                    Tọa độ {selectedPlace?.lat.toFixed(4)}, {selectedPlace?.lon.toFixed(4)}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 border-t border-white/10">
                <div className="p-6">
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Giờ mở cửa
                  </h4>
                  <p className="mt-2 text-white">
                    {selectedPlace?.opening_hours || "Chưa có dữ liệu xác thực"}
                  </p>
                </div>
                <div className="p-6">
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Giá vé
                  </h4>
                  <p className="mt-2 text-white">
                    {selectedPlace?.ticket_price || "Chưa có dữ liệu xác thực"}
                  </p>
                </div>
                <div className="p-6">
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Quy định tham quan
                  </h4>
                  <ul className="mt-2 space-y-1 text-sm text-white/70">
                    {(selectedPlace?.rules || []).map((rule) => (
                      <li key={rule}>• {rule}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* O2O Shopping Connection */}
            <div className="bg-[#050B14]/90 border border-[#D4AF37]/30 shadow-lg rounded-2xl p-8 relative overflow-hidden group">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 relative z-10">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <ShoppingBag className="w-5 h-5 text-[#D4AF37]" />
                    <span className="text-xs font-mono text-[#D4AF37] uppercase tracking-[0.2em]">
                      Gợi ý O2O
                    </span>
                  </div>
                  <h3 className="font-serif text-3xl text-white">
                    Vật Phẩm Kỷ Niệm Đề Xuất
                  </h3>
                  <p className="text-white/60 mt-2 font-sans">
                    Được tuyển chọn từ Cửa hàng Chính Hãng AEGIS gần nhất.
                  </p>
                </div>
                <button className="hidden md:flex mt-4 md:mt-0 items-center gap-2 text-sm text-white/80 hover:text-[#D4AF37] transition-colors font-mono uppercase tracking-wider">
                  Xem tất cả <ArrowRight className="w-4 h-4" />
                </button>
              </div>

              {isLoadingRecommendations ? (
                <div className="flex items-center gap-3 text-white/60 relative z-10">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Đang lấy gợi ý O2O từ cửa hàng gần địa điểm...
                </div>
              ) : recommendedProducts.length === 0 ? (
                <div className="relative z-10 rounded-xl border border-white/10 bg-white/5 p-6 text-white/60">
                  Chưa có gợi ý O2O từ dữ liệu cửa hàng gần địa điểm này.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 relative z-10">
                  {recommendedProducts.map((item) => (
                  <div
                    key={item.product_id}
                    className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-[#D4AF37]/50 transition-colors group/item"
                  >
                    <div className="h-48 overflow-hidden">
                      <img
                        src={item.image_url || wikiImage || BACKGROUND_IMAGE}
                        alt={item.name}
                        className="w-full h-full object-cover group-hover/item:scale-110 transition-transform duration-700"
                      />
                    </div>
                    <div className="p-5">
                      <h4 className="text-white font-serif text-lg mb-1">
                        {item.name}
                      </h4>
                      <p className="text-[#D4AF37] font-mono mb-4">
                        {Number(item.price).toLocaleString("vi-VN")} ₫
                      </p>
                      <p className="text-white/40 text-xs mb-4">
                        {item.storeName}
                      </p>
                      <button className="w-full py-2.5 rounded-lg border border-[#D4AF37] text-[#D4AF37] font-sans text-sm font-bold tracking-widest uppercase hover:bg-[#D4AF37] hover:text-[#0B132B] transition-all shadow-[0_0_15px_rgba(212,175,55,0)] hover:shadow-[0_0_15px_rgba(212,175,55,0.4)]">
                        GIỮ HÀNG TẠI QUẦY
                      </button>
                    </div>
                  </div>
                  ))}
                </div>
              )}
            </div>

            {/* Review System Magazine Style */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
              {/* Expert Quote */}
              <div className="lg:col-span-1 space-y-6">
                <div className="text-6xl text-[#D4AF37] font-serif leading-none opacity-50">
                  <BookOpen className="h-12 w-12" />
                </div>
                <p className="text-2xl font-serif text-white italic leading-relaxed">
                  Nội dung ưu tiên dữ liệu thật từ hồ sơ địa điểm, nguồn ảnh có cache
                  và đánh giá đã qua kiểm duyệt. Trường chưa xác thực được hiển thị
                  rõ để tránh tạo kỳ vọng sai.
                </p>
                <h3 className="sr-only">
                  Một kiệt tác vượt thời gian, nơi từng viên gạch kể lại hàng
                  thế kỷ lịch sử huy hoàng của Việt Nam. Không gian mua sắm O2O
                  tại đây cũng mang tính đột phá.
                </h3>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-white/10 overflow-hidden">
                    <div className="w-full h-full flex items-center justify-center">
                      <BookOpen className="h-5 w-5 text-[#D4AF37]" />
                    </div>
                  </div>
                  <div>
                    <p className="text-white font-bold font-sans">
                      Nguồn dữ liệu
                    </p>
                    <p className="text-white/50 text-xs font-mono uppercase tracking-widest">
                      AEGIS dataset · Moderated reviews
                    </p>
                  </div>
                </div>
              </div>

              {/* User Reviews */}
              <div className="lg:col-span-2 space-y-6">
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <h3 className="font-sans font-semibold text-white uppercase tracking-wider">
                    Đánh giá từ Du khách ({reviews.length})
                  </h3>
                  <button className="text-sm text-[#D4AF37] font-mono border border-[#D4AF37]/30 px-4 py-1.5 rounded-full hover:bg-[#D4AF37]/10 transition-colors">
                    Viết trải nghiệm
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {reviews.length > 0 ? (
                    reviews.map((r, i) => (
                      <div
                        key={r.id || i}
                        className="p-5 bg-white/5 border border-white/10 rounded-xl"
                      >
                        <div className="flex justify-between items-start mb-3">
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#D4AF37] to-amber-200 text-[#0B132B] flex items-center justify-center font-bold text-xs uppercase">
                              {r.author_name.charAt(0)}
                            </div>
                            <div>
                              <p className="text-white text-sm font-bold">
                                {r.author_name}
                              </p>
                              <span className="text-[10px] text-white/40 font-mono block">
                                {r.time_posted}
                              </span>
                              {r.status !== "approved" && (
                                <span className="mt-1 inline-flex rounded-full border border-amber-400/40 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider text-amber-200">
                                  {r.status === "pending" ? "Chờ duyệt" : "Đã từ chối"}
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex">
                            {Array(5)
                              .fill(0)
                              .map((_, idx) => (
                                <Star
                                  key={idx}
                                  className={`w-3 h-3 ${idx < r.rating ? "fill-[#D4AF37] text-[#D4AF37]" : "text-white/20"}`}
                                />
                              ))}
                          </div>
                        </div>
                        <p className="text-white/70 text-sm font-sans line-clamp-4">
                          {r.text}
                        </p>
                        {r.status === "approved" && (
                          <button
                            type="button"
                            onClick={() => handleReportReview(r.id)}
                            className="mt-4 inline-flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wider text-white/35 hover:text-amber-300"
                          >
                            <Flag className="w-3 h-3" />
                            Báo cáo
                          </button>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="col-span-2 py-8 text-center text-white/50 font-sans border border-dashed border-white/20 rounded-xl">
                      Hãy là người đầu tiên để lại ấn tượng về nơi này.
                    </div>
                  )}
                </div>

                {/* Review Form - Expandable */}
                <div className="mt-8 p-6 bg-[#050B14] border border-white/10 rounded-xl">
                  <div className="mb-4 flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-xs font-mono uppercase tracking-[0.2em] text-white/40">
                        Người đánh giá
                      </p>
                      <p className="mt-1 truncate text-sm font-semibold text-white">
                        {currentUser?.full_name || currentUser?.email || "Chưa đăng nhập"}
                      </p>
                      <p className="mt-1 text-xs text-white/40">
                        Đánh giá mới sẽ ở trạng thái chờ duyệt trước khi hiển thị công khai.
                      </p>
                    </div>
                    <div className="flex items-center gap-2 px-2">
                      <span className="text-sm text-white/50 font-sans">
                        Đánh giá:
                      </span>
                      {[1, 2, 3, 4, 5].map((s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => setReviewRating(s)}
                        >
                          <Star
                            className={`w-4 h-4 transition-colors ${s <= reviewRating ? "fill-[#D4AF37] text-[#D4AF37]" : "text-white/20 hover:text-white/40"}`}
                          />
                        </button>
                      ))}
                    </div>
                  </div>
                  <textarea
                    rows={3}
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    maxLength={1000}
                    placeholder="Trải nghiệm của bạn, tối thiểu 10 ký tự..."
                    className="w-full bg-transparent border-b border-white/20 px-2 py-2 text-white font-sans placeholder:text-white/30 focus:outline-none focus:border-[#D4AF37] resize-none mb-6"
                  />
                  <div className="mb-4 flex items-center justify-between text-xs font-mono text-white/40">
                    <span className="inline-flex items-center gap-1.5">
                      <Lock className="h-3 w-3" />
                      Authenticated review · Audit by user account
                    </span>
                    <span>{reviewText.trim().length}/1000</span>
                  </div>
                  <button
                    onClick={handleSubmitReview}
                    disabled={
                      isSubmittingReview ||
                      !currentUser ||
                      reviewText.trim().length < 10 ||
                      reviewText.trim().length > 1000
                    }
                    className="px-8 py-3 bg-white text-[#0B132B] font-bold font-sans text-sm rounded hover:bg-[#D4AF37] transition-colors disabled:opacity-50 disabled:hover:bg-white flex items-center justify-center gap-2 float-right"
                  >
                    {isSubmittingReview ? (
                      <Loader2 className="animate-spin w-4 h-4" />
                    ) : (
                      <Send size={14} />
                    )}{" "}
                    Đăng Tải
                  </button>
                  <div className="clear-both" />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(40px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in-up {
          animation: fadeInUp 0.7s cubic-bezier(0.2, 0.9, 0.4, 1.1) forwards;
        }
        .custom-scroll::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scroll::-webkit-scrollbar-track {
          background: #1a1a1a;
        }
        .custom-scroll::-webkit-scrollbar-thumb {
          background: #06b6d4;
          border-radius: 10px;
        }
        .stagger-children > * {
          opacity: 0;
          animation: fadeInUp 0.5s ease-out forwards;
        }
        .perspective-1000 {
          perspective: 1000px;
        }
      `}</style>
    </div>
  )
}
