import { createFileRoute } from "@tanstack/react-router"
import {
  ChevronRight,
  Clock,
  Globe,
  Landmark,
  Loader2,
  MapPin,
  Search,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Ticket,
  X,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import {
  AgentAPI,
  CultureAPI,
  SpatialAPI,
  type PlaceDetailWithAI,
  type PlaceResponse,
  type ReviewResponse,
  type StoreWithProductsResponse,
} from "@/client/aegis-api"

export const Route = createFileRoute("/_layout/culture")({
  component: CultureHeritage,
})

// Ảnh nền chất lượng cao, rõ nét
const BACKGROUND_IMAGE =
  "https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?auto=format&fit=crop&w=1600"

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
      "https://images.unsplash.com/photo-1504457047772-27faf1c00561?auto=format&fit=crop&w=1200",
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
  const [o2oStores, setO2oStores] = useState<StoreWithProductsResponse[]>([])
  const [isLoadingO2O, setIsLoadingO2O] = useState(false)
  const searchRef = useRef<HTMLInputElement>(null)

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
    setIsLoadingO2O(true)
    setSelectedPlace(null)
    setReviews([])
    setO2oStores([])

    try {
      // Bắt đầu gọi API đồng thời
      const reviewsPromise = CultureAPI.getPlaceReviews(place.id).catch(() => ({ data: [] }))
      const aiStoryPromise = AgentAPI.chat({
        query: `Kể một câu chuyện lịch sử chi tiết, phong phú (khoảng 2-3 đoạn văn dài) giới thiệu về địa danh ${place.name}. Nhấn mạnh vào văn hóa và ý nghĩa lịch sử. Hãy trình bày tự nhiên, không cần tiêu đề dư thừa.`,
      }).catch(() => ({ data: { answer: "Không thể kết nối đến Trợ lý AI kể chuyện lúc này." } }))
      
      const o2oPromise = place.place_id 
        ? SpatialAPI.getPlaceO2OContext(place.place_id, 3000).catch(() => ({ data: { nearby_stores: [] } }))
        : Promise.resolve({ data: { nearby_stores: [] } })

      const [reviewsRes, aiRes, o2oRes] = await Promise.all([
        reviewsPromise,
        aiStoryPromise,
        o2oPromise
      ])

      setSelectedPlace({ ...place, ai_story: aiRes.data.answer })
      setReviews(reviewsRes.data)
      setO2oStores(o2oRes.data.nearby_stores)
    } catch {
      setSelectedPlace({ ...place, ai_story: "Đã xảy ra lỗi khi tải dữ liệu." })
    } finally {
      setIsLoadingStory(false)
      setIsLoadingReviews(false)
      setIsLoadingO2O(false)
    }
  }

  const handleTrendingClick = (query: string) => {
    setSearchQuery(query)
    handleSearch(query)
  }

  const showEmptyState =
    places.length === 0 && !isSearching && searchQuery === ""

  const [wikiImage, setWikiImage] = useState<string | null>(null)
  const [galleryImages, setGalleryImages] = useState<string[]>([])

  useEffect(() => {
    if (selectedPlace?.name) {
      const fetchPlaceImages = async () => {
        try {
          // Get hero image
          const res = await CultureAPI.getPlaceImage(selectedPlace.id)
          setWikiImage(res.data.image_url)

          // Fetch multiple images from Wikipedia for the gallery
          const wikiUrl = `https://vi.wikipedia.org/w/api.php?action=query&generator=images&titles=${encodeURIComponent(
            selectedPlace.name
          )}&prop=imageinfo&iiprop=url&format=json&origin=*`
          const wikiRes = await fetch(wikiUrl)
          const wikiData = await wikiRes.json()
          
          if (wikiData?.query?.pages) {
            const pages = Object.values(wikiData.query.pages) as any[]
            // Filter out SVGs and icons
            const validImages = pages
              .map((p) => p.imageinfo?.[0]?.url)
              .filter(
                (url) =>
                  url &&
                  !url.toLowerCase().endsWith(".svg") &&
                  !url.toLowerCase().includes("logo") &&
                  !url.toLowerCase().includes("icon")
              )
            setGalleryImages(validImages.slice(0, 3))
          } else {
            setGalleryImages([])
          }
        } catch {
          setWikiImage(null)
          setGalleryImages([])
        }
      }
      fetchPlaceImages()
    } else {
      setWikiImage(null)
      setGalleryImages([])
    }
  }, [selectedPlace?.name])

  return (
    <div className="relative min-h-screen w-full bg-[#F3F4F6] font-sans p-4 md:p-6 overflow-hidden">
      {/* White Card Container */}
      <div className="relative z-10 w-full h-full bg-white rounded-[2rem] shadow-sm border border-zinc-100 p-4 md:p-8 overflow-y-auto custom-scroll">
        <div className="max-w-[1300px] mx-auto space-y-10 pb-20">
          
          {/* Hero Banner */}
          <div className="relative w-full h-[320px] md:h-[400px] rounded-[2rem] overflow-hidden shadow-md flex flex-col items-center justify-center">
            {/* Background Image */}
            <div
              className="absolute inset-0 bg-cover bg-center"
              style={{ backgroundImage: `url(${BACKGROUND_IMAGE})` }}
            />
            {/* Gradient Overlay */}
            <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-black/30 to-black/80" />
            
            {/* Badge AI */}
            <div className="absolute top-6 left-6 md:top-8 md:left-8 inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-[#D4AF37] to-amber-200 shadow-xl z-10">
              <Sparkles className="w-4 h-4 text-[#0B132B]" />
              <span className="text-[11px] font-bold tracking-widest text-[#0B132B] uppercase">
                Trợ Lý Kể Chuyện AI
              </span>
            </div>

            {/* Title & Subtitle */}
            <div className="relative z-10 text-center mt-8 px-4 animate-fade-in-up">
              <h1 className="text-5xl md:text-7xl font-serif font-bold text-white mb-4 drop-shadow-xl">
                Văn hóa & Di sản
              </h1>
              <p className="text-white/95 text-base md:text-lg drop-shadow-md max-w-2xl mx-auto font-medium">
                Khám phá chiều sâu lịch sử qua lăng kính trí tuệ nhân tạo
              </p>
            </div>

            {/* Search Bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSearch()
              }}
              className="relative z-10 w-full max-w-2xl mx-auto mt-10 px-4"
            >
              <div className="relative group shadow-2xl rounded-full">
                <Search className="absolute left-6 top-1/2 -translate-y-1/2 w-5 h-5 text-white/70" />
                <input
                  ref={searchRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Tìm kiếm di sản..."
                  className="w-full bg-white/20 backdrop-blur-md border border-white/40 rounded-full py-4 pl-14 pr-36 text-white placeholder:text-white/80 text-lg focus:outline-none focus:bg-white/30 transition-all shadow-[0_8px_30px_rgb(0,0,0,0.2)]"
                />
                <button
                  type="submit"
                  disabled={isSearching}
                  className="absolute right-2 top-1/2 -translate-y-1/2 bg-gradient-to-r from-[#D4AF37] to-amber-200 hover:from-amber-200 hover:to-[#D4AF37] text-[#0B132B] font-bold rounded-full px-8 py-2.5 transition-all shadow-md disabled:opacity-50"
                >
                  {isSearching ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : "Khám phá"}
                </button>
              </div>
            </form>
          </div>

          {/* Results Area */}
          {places.length > 0 && (
            <div className="space-y-6">
              <div className="flex items-center gap-2 mb-6 ml-2">
                <MapPin className="w-5 h-5 text-[#D4AF37]" />
                <h2 className="text-xl font-bold text-zinc-800 uppercase tracking-wider">
                  Kết quả từ CSDL ({places.length})
                </h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {places.map((place) => (
                  <div
                    key={place.id}
                    className="group bg-white border border-zinc-200 rounded-2xl p-6 hover:border-[#D4AF37] transition-all cursor-pointer shadow-sm hover:shadow-lg flex flex-col justify-between min-h-[160px]"
                    onClick={() => handleOpenPlace(place)}
                  >
                    <div>
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="text-lg font-bold text-zinc-800 group-hover:text-[#D4AF37] transition-colors">
                          {place.name}
                        </h3>
                        <Landmark className="w-5 h-5 text-zinc-400 group-hover:text-[#D4AF37] transition-colors" />
                      </div>
                      <p className="text-sm text-zinc-500 line-clamp-2">
                        {place.category || "Di tích văn hóa"}
                      </p>
                    </div>
                    <div className="mt-4 flex items-center justify-between text-xs border-t border-zinc-100 pt-3">
                      <span className="text-zinc-400 flex items-center gap-1 font-mono">
                        📍 {place.lat.toFixed(4)}, {place.lon.toFixed(4)}
                      </span>
                      <span className="text-[#D4AF37] font-medium group-hover:underline flex items-center gap-1">
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

          {/* Empty State - Trending Cards */}
          {showEmptyState && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {TRENDING_HERITAGES.map((item, idx) => (
                <div
                  key={idx}
                  onClick={() => handleTrendingClick(item.query)}
                  className="group relative overflow-hidden rounded-[1.5rem] cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:shadow-xl border border-zinc-200 h-56 shadow-sm"
                >
                  <img
                    src={item.image}
                    alt={item.name}
                    className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />
                  
                  <div className="absolute inset-0 p-6 flex flex-col justify-end">
                    <h3 className="text-xl md:text-2xl font-bold text-white drop-shadow-md group-hover:text-[#D4AF37] transition-colors">
                      {item.name}
                    </h3>
                    <p className="text-white/80 text-xs md:text-sm mt-1 drop-shadow-md line-clamp-2">
                      {item.subtitle}: {item.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Statistics */}
          {showEmptyState && (
            <div className="mt-8">
              <h3 className="text-zinc-500 font-bold uppercase tracking-widest text-sm mb-4 ml-2">Thống kê nổi bật</h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white rounded-2xl p-5 border border-zinc-100 shadow-sm flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-[#2B0B3F] flex items-center justify-center shrink-0">
                    <Landmark className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="text-2xl font-black text-[#2B0B3F]">48</div>
                    <div className="text-[10px] sm:text-xs font-bold text-zinc-500 uppercase">Di sản văn hóa<br/><span className="font-normal normal-case opacity-70">(Đã cập nhật)</span></div>
                  </div>
                </div>
                
                <div className="bg-white rounded-2xl p-5 border border-zinc-100 shadow-sm flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-[#2B0B3F] flex items-center justify-center shrink-0">
                    <MapPin className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="text-2xl font-black text-[#2B0B3F]">120+</div>
                    <div className="text-[10px] sm:text-xs font-bold text-zinc-500 uppercase">Điểm đến<br/><span className="font-normal normal-case opacity-70">(Toàn quốc)</span></div>
                  </div>
                </div>

                <div className="bg-white rounded-2xl p-5 border border-zinc-100 shadow-sm flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-[#2B0B3F] flex items-center justify-center shrink-0">
                    <Clock className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="text-2xl font-black text-[#2B0B3F]">2000+</div>
                    <div className="text-[10px] sm:text-xs font-bold text-zinc-500 uppercase">Năm lịch sử<br/><span className="font-normal normal-case opacity-70">(Đã số hóa)</span></div>
                  </div>
                </div>

                <div className="bg-white rounded-2xl p-5 border border-zinc-100 shadow-sm flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-[#2B0B3F] flex items-center justify-center shrink-0">
                    <Globe className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <div className="text-2xl font-black text-[#2B0B3F]">1M+</div>
                    <div className="text-[10px] sm:text-xs font-bold text-zinc-500 uppercase">Lượt khám phá<br/><span className="font-normal normal-case opacity-70">(Toàn cầu)</span></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modal Light Theme Overhaul */}
      {showModal && (
        <div
          className="absolute inset-0 z-50 bg-[#F3F4F6] overflow-y-auto custom-scroll font-sans"
          onClick={() => setShowModal(false)}
        >
          {/* Main White Canvas inside Modal */}
          <div className="bg-white min-h-screen pb-20 relative shadow-2xl" onClick={(e) => e.stopPropagation()}>
            {/* Hero Banner Area */}
            <div className="relative w-full h-[50vh] min-h-[400px] mb-16">
              <img
                src={wikiImage || BACKGROUND_IMAGE}
                alt="Hero"
                className="w-full h-full object-cover rounded-b-[2.5rem] shadow-sm"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-black/40 rounded-b-[2.5rem]" />
              
              <button
                onClick={() => setShowModal(false)}
                className="absolute top-6 left-6 p-3 bg-white/20 backdrop-blur-md rounded-full border border-white/40 hover:bg-white/40 transition-colors z-30"
              >
                <X className="w-6 h-6 text-white" />
              </button>

              <div className="absolute bottom-16 left-8 md:left-16 z-20 text-white max-w-3xl">
                <h2 className="text-5xl md:text-6xl font-serif text-[#D4AF37] mb-3 drop-shadow-md">
                  {selectedPlace?.name}
                </h2>
                <p className="text-white/90 font-mono text-sm tracking-[0.2em] uppercase">
                  Trải nghiệm Di sản · O2O Shopping Ecosystem
                </p>
              </div>

              {/* Floating AI Story Box (Right side overlapping) */}
              <div className="absolute -bottom-12 right-8 md:right-16 w-[90%] md:w-[700px] bg-black/50 backdrop-blur-3xl border border-white/20 shadow-2xl rounded-[2rem] p-8 z-30 text-white transition-all">
                <div className="flex items-start gap-6">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#D4AF37] to-amber-200 flex items-center justify-center shrink-0 shadow-[0_0_20px_rgba(212,175,55,0.5)]">
                    <Sparkles className="w-8 h-8 text-[#0B132B]" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-base uppercase tracking-widest mb-3 text-[#D4AF37]">CÂU CHUYỆN TỪ DÒNG THỜI GIAN</h3>
                    {isLoadingStory ? (
                      <div className="animate-pulse space-y-3 mt-3">
                        <div className="h-4 bg-white/20 rounded w-full" />
                        <div className="h-4 bg-white/20 rounded w-full" />
                        <div className="h-4 bg-white/20 rounded w-5/6" />
                        <div className="h-4 bg-white/20 rounded w-4/5" />
                      </div>
                    ) : (
                      <div className="max-h-64 overflow-y-auto custom-scroll pr-4 pb-2">
                        <p className="text-white/95 text-base md:text-lg leading-relaxed text-justify">
                          <span className="font-bold text-[#D4AF37] text-xl mr-2">AI:</span>
                          {selectedPlace?.ai_story}
                        </p>
                      </div>
                    )}
                    <div className="flex items-center gap-3 mt-6 text-white/60 text-sm font-medium border-t border-white/10 pt-4">
                      <MapPin className="w-4 h-4" />
                      <span className="truncate">{selectedPlace?.address}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Content 2 Columns */}
            <div className="max-w-[1300px] mx-auto px-4 md:px-8 grid grid-cols-1 lg:grid-cols-12 gap-12 relative z-10">
              
              {/* Left Column (5/12) */}
              <div className="lg:col-span-5 space-y-12">
                {/* 3 Portrait Images */}
                <div className="grid grid-cols-3 gap-4">
                  {galleryImages.length >= 3 ? (
                    <>
                      <img src={galleryImages[0]} className="w-full h-48 md:h-64 object-cover rounded-2xl shadow-md hover:scale-[1.02] transition-transform" alt="Gallery 1" />
                      <img src={galleryImages[1]} className="w-full h-48 md:h-64 object-cover rounded-2xl shadow-md mt-6 hover:scale-[1.02] transition-transform" alt="Gallery 2" />
                      <img src={galleryImages[2]} className="w-full h-48 md:h-64 object-cover rounded-2xl shadow-md hover:scale-[1.02] transition-transform" alt="Gallery 3" />
                    </>
                  ) : (
                    <>
                      <img src={galleryImages[0] || wikiImage || "https://images.unsplash.com/photo-1540483761890-a1f7be05ce34?auto=format&fit=crop&w=400&h=600"} className="w-full h-48 md:h-64 object-cover rounded-2xl shadow-md hover:scale-[1.02] transition-transform" alt="Gallery 1" />
                      <img src={galleryImages[1] || wikiImage || "https://images.unsplash.com/photo-1555921015-5532091f6026?auto=format&fit=crop&w=400&h=600"} className="w-full h-48 md:h-64 object-cover rounded-2xl shadow-md mt-6 hover:scale-[1.02] transition-transform" alt="Gallery 2" />
                      <img src="https://images.unsplash.com/photo-1504457047772-27faf1c00561?auto=format&fit=crop&w=400&h=600" className="w-full h-48 md:h-64 object-cover rounded-2xl shadow-md hover:scale-[1.02] transition-transform" alt="Gallery 3" />
                    </>
                  )}
                </div>

                {/* O2O Exclusive */}
                <div>
                  <h3 className="font-serif text-2xl text-zinc-800 mb-1">Vật Phẩm Kỷ Niệm Đề Xuất</h3>
                  <p className="text-zinc-500 text-sm font-mono tracking-widest uppercase mb-6">O2O EXCLUSIVE</p>
                  
                  {isLoadingO2O ? (
                    <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-[#D4AF37]" /></div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {o2oStores.flatMap(s => s.products).slice(0, 3).length > 0 ? (
                        o2oStores.flatMap(s => s.products).slice(0, 3).map((item, i) => (
                          <div key={i} className="bg-white border border-zinc-200 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow group flex flex-col">
                            <div className="relative h-32 overflow-hidden bg-zinc-100">
                              {item.image_url ? (
                                <img src={item.image_url} alt={item.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-zinc-400"><ShoppingBag className="w-8 h-8 opacity-20" /></div>
                              )}
                            </div>
                            <div className="p-4 flex flex-col flex-1 justify-between gap-3">
                              <div>
                                <h4 className="text-sm font-bold text-zinc-800 line-clamp-2">{item.name}</h4>
                                <p className="text-sm font-bold text-zinc-800 mt-1">{item.price.toLocaleString()} ₫</p>
                              </div>
                              <button className="w-full py-2 bg-[#CFA356] text-white rounded-lg text-[10px] font-bold tracking-widest uppercase hover:bg-[#B8860B] transition-colors mt-auto">
                                GIỮ HÀNG TẠI QUẦY
                              </button>
                            </div>
                          </div>
                        ))
                      ) : (
                        // Mock 3 products if empty to match screenshot exactly
                        [
                          { name: "Nón Lá Sen Nghệ Thuật", price: "450,000", image: "https://images.unsplash.com/photo-1548625361-ecac45bc1164?auto=format&fit=crop&w=500" },
                          { name: "Lụa Tơ Tằm Bảo Lộc", price: "1,200,000", image: "https://images.unsplash.com/photo-1583335513577-224b423126dd?auto=format&fit=crop&w=500" },
                          { name: "Gốm Sứ Bát Tràng Men", price: "850,000", image: "https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=500" }
                        ].map((item, i) => (
                          <div key={i} className="bg-white border border-zinc-200 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col">
                            <img src={item.image} alt={item.name} className="w-full h-32 object-cover bg-zinc-100" />
                            <div className="p-4 flex flex-col flex-1 justify-between gap-3">
                              <div>
                                <h4 className="text-sm font-bold text-zinc-800 line-clamp-2 leading-tight">{item.name}</h4>
                                <p className="text-sm font-bold text-zinc-800 mt-1">{item.price} ₫</p>
                              </div>
                              <button className="w-full py-2 bg-[#CFA356] text-white rounded-lg text-[10px] font-bold tracking-[0.1em] uppercase hover:bg-[#B8860B] transition-colors mt-auto">
                                GIỮ HÀNG TẠI QUẦY
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column (7/12) */}
              <div className="lg:col-span-7 space-y-10 lg:mt-8">
                
                {/* Visitor Info Card */}
                <div>
                  <div className="flex items-center gap-4 mb-6 relative">
                    <div className="h-px bg-zinc-200 flex-1"></div>
                    <h3 className="font-serif text-xl text-zinc-800 px-4">Thông tin Đặc quyền Tham quan</h3>
                    <div className="h-px bg-zinc-200 flex-1"></div>
                  </div>

                  <div className="bg-white border border-[#D4AF37]/40 rounded-3xl p-6 shadow-[0_10px_40px_rgba(212,175,55,0.08)]">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 divide-x divide-zinc-100 text-center">
                      <div className="space-y-3 px-2">
                        <Clock className="w-6 h-6 text-[#D4AF37] mx-auto" />
                        <h4 className="text-[11px] font-bold text-zinc-800 uppercase tracking-widest">GIỜ MỞ CỬA</h4>
                        <p className="text-zinc-800 font-bold text-sm">08:00 - 17:30</p>
                        <p className="text-zinc-500 text-[11px]">Mở cửa tất cả các ngày</p>
                      </div>
                      <div className="space-y-3 px-2">
                        <ShieldCheck className="w-6 h-6 text-[#D4AF37] mx-auto" />
                        <h4 className="text-[11px] font-bold text-zinc-800 uppercase tracking-widest">TRANG PHỤC</h4>
                        <p className="text-zinc-800 font-bold text-sm">Kín đáo, lịch sự</p>
                        <p className="text-zinc-500 text-[11px]">Cấm quần đùi, áo sát nách</p>
                      </div>
                      <div className="space-y-3 px-2">
                        <Ticket className="w-6 h-6 text-[#D4AF37] mx-auto" />
                        <h4 className="text-[11px] font-bold text-zinc-800 uppercase tracking-widest">VÉ NỘI ĐỊA</h4>
                        <p className="text-zinc-800 font-bold text-sm">Miễn phí</p>
                        <p className="text-zinc-500 text-[11px]">Yêu cầu CCCD</p>
                      </div>
                      <div className="space-y-3 px-2">
                        <Globe className="w-6 h-6 text-[#D4AF37] mx-auto" />
                        <h4 className="text-[11px] font-bold text-zinc-800 uppercase tracking-widest">VÉ QUỐC TẾ</h4>
                        <p className="text-zinc-800 font-bold text-sm">150,000 VND</p>
                        <p className="text-zinc-500 text-[11px]">Thanh toán VNPay / Thẻ</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Reviews */}
                <div className="bg-white border border-zinc-200 rounded-3xl p-6 shadow-sm">
                  <div className="flex justify-between items-center mb-6 border-b border-zinc-100 pb-4">
                    <h3 className="font-bold text-zinc-800 uppercase tracking-widest text-sm flex items-center gap-2">
                      <span className="text-2xl text-[#D4AF37] font-serif leading-none mt-2">“</span>
                      ĐÁNH GIÁ TỪ DU KHÁCH ({reviews.length})
                    </h3>
                    <button className="px-4 py-2 border border-zinc-300 rounded-lg text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors">
                      Viết trải nghiệm
                    </button>
                  </div>
                  
                  {reviews.length > 0 ? (
                    <div className="space-y-4">
                      {reviews.map((r, i) => (
                        <div key={r.id || i} className="flex gap-4 p-4 rounded-2xl bg-[#F8F9FA] border border-zinc-100">
                          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#D4AF37] to-amber-200 text-[#0B132B] flex items-center justify-center font-bold text-lg uppercase shrink-0">
                            {r.author_name.charAt(0)}
                          </div>
                          <div className="flex-1">
                            <p className="text-zinc-800 text-sm italic mb-2 line-clamp-3">{r.text}</p>
                            <p className="text-zinc-900 font-bold text-sm">{r.author_name}, <span className="text-zinc-500 font-normal uppercase text-[10px] tracking-widest">{r.time_posted}</span></p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    // Show Expert review as fallback for empty
                    <div className="flex gap-4 p-4 rounded-2xl bg-[#F8F9FA] border border-zinc-100">
                      <img src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150" alt="Expert" className="w-16 h-16 rounded-xl object-cover shrink-0" />
                      <div>
                        <p className="text-zinc-800 text-sm italic mb-2">Một kiệt tác vượt thời gian, nơi từng viên gạch kể lại hàng thế kỷ lịch sử huy hoàng của Việt Nam. Không gian mua sắm O2O tại đây cũng mang tính đột phá.</p>
                        <p className="text-zinc-900 font-bold text-sm">Alexander Chen, <span className="text-zinc-500 font-normal uppercase text-[10px] tracking-widest">TRAVEL EXPERT</span></p>
                      </div>
                    </div>
                  )}
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
