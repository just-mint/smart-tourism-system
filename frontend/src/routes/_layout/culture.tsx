import { createFileRoute } from "@tanstack/react-router"
import {
  ArrowRight,
  BookOpen,
  Calendar,
  ChevronRight,
  Clock,
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
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Star,
  Ticket,
  TrendingUp,
  Users,
  X,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import {
  CultureAPI,
  type PlaceDetailWithAI,
  type PlaceResponse,
  type ReviewResponse,
} from "@/client/aegis-api"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/culture")({
  component: CultureHeritage,
})

// Ảnh nền chất lượng cao, rõ nét
const BACKGROUND_IMAGE =
  "https://kinhtevadubao.vn/stores/news_dataimages/kinhtevadubaovn/092018/18/14/5-ve-dep-co-do-hue-tao-ne-su-hap-dan-dac-biet-khi-ghe-tham-07-.7434.jpg"

const TRENDING_HERITAGES = [
  {
    name: "Vịnh Hạ Long",
    subtitle: "Kỳ quan thiên nhiên thế giới",
    desc: "Hòn Trống Mái, Động Thiên Cung, vẻ đẹp huyền ảo",
    image:
      "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200",
    query: "Vịnh Hạ Long",
  },
  {
    name: "Cố đô Huế",
    subtitle: "Kiến trúc triều Nguyễn độc đáo",
    desc: "Sự giao thoa văn hóa lịch sử",
    image:
      "https://kinhtevadubao.vn/stores/news_dataimages/kinhtevadubaovn/092018/18/14/5-ve-dep-co-do-hue-tao-ne-su-hap-dan-dac-biet-khi-ghe-tham-08-.5606.jpg",
    query: "Huế",
  },
  {
    name: "Hà Nội",
    subtitle: "Thủ đô ngàn năm văn hiến",
    desc: "Hồ Gươm, 36 phố phường",
    image:
      "https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?auto=format&fit=crop&w=1200",
    query: "Hà Nội",
  },
  {
    name: "Phố cổ Hội An",
    subtitle: "Di sản văn hóa thế giới",
    desc: "Đèn lồng, cổ kính, thơ mộng",
    image:
      "https://images.unsplash.com/photo-1555921015-5532091f6026?auto=format&fit=crop&w=1200",
    query: "Hội An",
  },
  {
    name: "Ninh Bình",
    subtitle: "Tràng An, Tam Cốc",
    desc: "Vịnh Hạ Long trên cạn",
    image:
      "https://images.pexels.com/photos/27356566/pexels-photo-27356566.jpeg",
    query: "Ninh Bình",
  },
  {
    name: "Sapa",
    subtitle: "Thành phố trong sương",
    desc: "Ruộng bậc thang, đỉnh Fansipan",
    image:
      "https://booking.muongthanh.com/upload_images/images/H%60/dinh-nui-fansipan.jpg",
    query: "Sapa",
  },
]

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
  }, [phrases.length, phrases])

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

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setIsSearching(true)
    try {
      const res = await CultureAPI.searchPlaces(searchQuery)
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
    setSearchQuery(query)
    setTimeout(() => handleSearch(), 50)
  }

  const showEmptyState =
    places.length === 0 && !isSearching && searchQuery === ""

  const [wikiImage, setWikiImage] = useState<string | null>(null)

  useEffect(() => {
    if (selectedPlace?.name) {
      const fetchWikiImage = async () => {
        try {
          const res = await fetch(
            `https://vi.wikipedia.org/w/api.php?action=query&origin=*&titles=${encodeURIComponent(selectedPlace.name)}&prop=pageimages&format=json&pithumbsize=1200`,
          )
          const data = await res.json()
          const pages = data.query?.pages
          if (pages) {
            const pageId = Object.keys(pages)[0]
            const imgUrl = pages[pageId]?.thumbnail?.source
            if (imgUrl) {
              setWikiImage(imgUrl)
              return
            }
          }
          const searchRes = await fetch(
            `https://vi.wikipedia.org/w/api.php?action=query&origin=*&list=search&srsearch=${encodeURIComponent(selectedPlace.name)}&utf8=&format=json`,
          )
          const searchData = await searchRes.json()
          if (searchData.query?.search?.length > 0) {
            const bestTitle = searchData.query.search[0].title
            const imgRes = await fetch(
              `https://vi.wikipedia.org/w/api.php?action=query&origin=*&titles=${encodeURIComponent(bestTitle)}&prop=pageimages&format=json&pithumbsize=1200`,
            )
            const imgData = await imgRes.json()
            const pId = Object.keys(imgData.query.pages)[0]
            const iUrl = imgData.query.pages[pId]?.thumbnail?.source
            if (iUrl) setWikiImage(iUrl)
            else setWikiImage(null)
          } else {
            setWikiImage(null)
          }
        } catch {
          setWikiImage(null)
        }
      }
      fetchWikiImage()
    } else {
      setWikiImage(null)
    }
  }, [selectedPlace?.name])

  return (
    <div className="relative min-h-screen w-full bg-black overflow-hidden">
      {/* Background cố định, rõ nét, không bị che sidebar */}
      <div
        className="absolute inset-0 z-0 bg-cover bg-center bg-fixed bg-no-repeat"
        style={{ backgroundImage: `url(${BACKGROUND_IMAGE})` }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-black/80 via-black/60 to-black/80" />
        <div className="absolute inset-0 backdrop-blur-md" />
      </div>

      {/* Content - có padding để không đè sidebar */}
      <div className="relative z-10 w-full h-full px-4 md:px-6 py-8 overflow-y-auto custom-scroll">
        <div className="max-w-7xl mx-auto space-y-12">
          {/* Hero + Omnibar */}
          <div className="text-center space-y-6 animate-fade-in-up">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 shadow-xl">
              <Sparkles className="w-4 h-4 text-amber-200" />
              <span className="text-xs font-mono font-bold tracking-wider text-white/90 uppercase">
                AI Storytelling Engine
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
                    <div className="absolute inset-0 transition-transform duration-700 group-hover:scale-110">
                      <img
                        src={item.image}
                        alt={item.name}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/50 to-transparent" />
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

          {/* Thêm một số thống kê giả để tăng chiều dài */}
          {showEmptyState && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-8 pb-20">
              <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-5 text-center border border-white/10">
                <Globe className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">48</div>
                <div className="text-xs text-white/50">Di sản văn hóa</div>
              </div>
              <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-5 text-center border border-white/10">
                <Compass className="w-8 h-8 text-purple-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">120+</div>
                <div className="text-xs text-white/50">Điểm đến</div>
              </div>
              <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-5 text-center border border-white/10">
                <Calendar className="w-8 h-8 text-pink-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">2000+</div>
                <div className="text-xs text-white/50">Năm lịch sử</div>
              </div>
              <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-5 text-center border border-white/10">
                <Users className="w-8 h-8 text-amber-400 mx-auto mb-2" />
                <div className="text-2xl font-bold text-white">1M+</div>
                <div className="text-xs text-white/50">Lượt khám phá</div>
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
              src={wikiImage || BACKGROUND_IMAGE}
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
                Trải nghiệm Di sản · O2O Shopping Ecosystem
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
                <img
                  src="https://images.unsplash.com/photo-1540483761890-a1f7be05ce34?auto=format&fit=crop&w=800"
                  className="w-full h-48 object-cover rounded-2xl shadow-xl hover:scale-105 transition-transform duration-500"
                  alt="Gallery 1"
                />
                <img
                  src="https://images.unsplash.com/photo-1555921015-5532091f6026?auto=format&fit=crop&w=800"
                  className="w-full h-64 object-cover rounded-2xl shadow-xl hover:scale-105 transition-transform duration-500 -mt-8"
                  alt="Gallery 2"
                />
                <img
                  src="https://images.unsplash.com/photo-1504457047772-27faf1c00561?auto=format&fit=crop&w=800"
                  className="w-full h-64 object-cover rounded-2xl shadow-xl hover:scale-105 transition-transform duration-500"
                  alt="Gallery 3"
                />
                <img
                  src="https://images.unsplash.com/photo-1582650507323-96cb34407b46?auto=format&fit=crop&w=800"
                  className="w-full h-48 object-cover rounded-2xl shadow-xl hover:scale-105 transition-transform duration-500"
                  alt="Gallery 4"
                />
              </div>
            </div>

            {/* Visitor Info Table */}
            <div className="bg-black/40 backdrop-blur-md border border-white/10 shadow-2xl rounded-2xl overflow-hidden">
              <div className="bg-[#050B14] p-5 border-b border-white/10 flex items-center gap-3">
                <BookOpen className="w-5 h-5 text-[#D4AF37]" />
                <h3 className="font-serif text-lg text-white">
                  Thông tin Đặc quyền Tham quan
                </h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-white/10">
                <div className="p-6 space-y-2">
                  <Clock className="w-6 h-6 text-white/50 mb-4" />
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Giờ mở cửa
                  </h4>
                  <p className="text-white text-lg">08:00 - 17:30</p>
                  <p className="text-white/40 text-sm">
                    Mở cửa tất cả các ngày
                  </p>
                </div>
                <div className="p-6 space-y-2">
                  <ShieldCheck className="w-6 h-6 text-white/50 mb-4" />
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Trang phục
                  </h4>
                  <p className="text-white text-lg">Kín đáo, lịch sự</p>
                  <p className="text-white/40 text-sm">
                    Cấm quần đùi, áo sát nách
                  </p>
                </div>
                <div className="p-6 space-y-2">
                  <Ticket className="w-6 h-6 text-white/50 mb-4" />
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Vé Nội Địa
                  </h4>
                  <p className="text-white text-lg">Miễn phí</p>
                  <p className="text-white/40 text-sm">Yêu cầu CCCD</p>
                </div>
                <div className="p-6 space-y-2">
                  <Globe className="w-6 h-6 text-white/50 mb-4" />
                  <h4 className="text-xs font-mono text-white/50 uppercase tracking-widest">
                    Vé Quốc Tế
                  </h4>
                  <p className="text-white text-lg font-mono">150,000 VND</p>
                  <p className="text-white/40 text-sm">
                    Thanh toán VNPay / Thẻ
                  </p>
                </div>
              </div>
            </div>

            {/* O2O Shopping Connection */}
            <div className="bg-[#050B14]/80 backdrop-blur-xl border border-[#D4AF37]/30 shadow-[0_0_40px_rgba(212,175,55,0.05)] rounded-2xl p-8 relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-64 h-64 bg-[#D4AF37]/5 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
              <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 relative z-10">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <ShoppingBag className="w-5 h-5 text-[#D4AF37]" />
                    <span className="text-xs font-mono text-[#D4AF37] uppercase tracking-[0.2em]">
                      O2O Exclusive
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

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 relative z-10">
                {[
                  {
                    name: "Nón Lá Sen Nghệ Thuật",
                    price: "450,000",
                    image:
                      "https://images.unsplash.com/photo-1548625361-ecac45bc1164?auto=format&fit=crop&w=500",
                  },
                  {
                    name: "Lụa Tơ Tằm Bảo Lộc",
                    price: "1,200,000",
                    image:
                      "https://images.unsplash.com/photo-1583335513577-224b423126dd?auto=format&fit=crop&w=500",
                  },
                  {
                    name: "Gốm Sứ Bát Tràng Men",
                    price: "850,000",
                    image:
                      "https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=500",
                  },
                ].map((item, i) => (
                  <div
                    key={i}
                    className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-[#D4AF37]/50 transition-colors group/item"
                  >
                    <div className="h-48 overflow-hidden">
                      <img
                        src={item.image}
                        alt={item.name}
                        className="w-full h-full object-cover group-hover/item:scale-110 transition-transform duration-700"
                      />
                    </div>
                    <div className="p-5">
                      <h4 className="text-white font-serif text-lg mb-1">
                        {item.name}
                      </h4>
                      <p className="text-[#D4AF37] font-mono mb-4">
                        {item.price} ₫
                      </p>
                      <button className="w-full py-2.5 rounded-lg border border-[#D4AF37] text-[#D4AF37] font-sans text-sm font-bold tracking-widest uppercase hover:bg-[#D4AF37] hover:text-[#0B132B] transition-all shadow-[0_0_15px_rgba(212,175,55,0)] hover:shadow-[0_0_15px_rgba(212,175,55,0.4)]">
                        GIỮ HÀNG TẠI QUẦY
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Review System Magazine Style */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
              {/* Expert Quote */}
              <div className="lg:col-span-1 space-y-6">
                <div className="text-6xl text-[#D4AF37] font-serif leading-none opacity-50">
                  "
                </div>
                <h3 className="text-2xl font-serif text-white italic leading-relaxed">
                  Một kiệt tác vượt thời gian, nơi từng viên gạch kể lại hàng
                  thế kỷ lịch sử huy hoàng của Việt Nam. Không gian mua sắm O2O
                  tại đây cũng mang tính đột phá.
                </h3>
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-white/10 overflow-hidden">
                    <img
                      src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150"
                      alt="Expert"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div>
                    <p className="text-white font-bold font-sans">
                      Alexander Chen
                    </p>
                    <p className="text-white/50 text-xs font-mono uppercase tracking-widest">
                      Travel Expert
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
