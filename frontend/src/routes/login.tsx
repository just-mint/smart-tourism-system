import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { ArrowRight, Fingerprint, Shield, Sparkles, Zap } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

const BACKGROUND_IMAGES = [
  "https://images.unsplash.com/photo-1528181304800-259b08848526?q=90&w=2500&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1559592413-7ceecea18501?q=90&w=2500&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1504214208698-ea1916a2195a?q=90&w=2500&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1583417319070-4a69db38a482?q=90&w=2500&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1550650222-6b94dbba2211?q=90&w=2500&auto=format&fit=crop",
]

const GRID_ROWS = 8
const GRID_COLS = 12

const formSchema = z.object({
  username: z.email({ message: "Vui lòng nhập email hợp lệ" }),
  password: z
    .string()
    .min(1, { message: "Vui lòng nhập mật khẩu" })
    .min(8, { message: "Ít nhất 8 ký tự" }),
}) satisfies z.ZodType<AccessToken>

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) throw redirect({ to: "/" })
  },
  head: () => ({ meta: [{ title: "AEGIS O2O | Premium Access" }] }),
})

function Login() {
  const { loginMutation } = useAuth()
  const [baseIndex, setBaseIndex] = useState(0)
  const [gridIndex, setGridIndex] = useState(1)
  const [isGridVisible, setIsGridVisible] = useState(false)
  const [isReady, setIsReady] = useState(false)

  const preloadedImages = useRef<HTMLImageElement[]>([])
  const gridIndexRef = useRef(1)
  const transitionTimer = useRef<NodeJS.Timeout | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  // Preload tất cả ảnh
  useEffect(() => {
    let loaded = 0
    BACKGROUND_IMAGES.forEach((src, idx) => {
      const img = new Image()
      img.src = src
      img
        .decode()
        .then(() => {
          preloadedImages.current[idx] = img
          loaded++
          console.log(`✅ Decoded ${idx} - ${src.slice(0, 50)}`)
          if (loaded === BACKGROUND_IMAGES.length) {
            console.log("🎯 All images ready")
            setIsReady(true)
          }
        })
        .catch((err) => {
          console.error(`❌ Failed to decode ${idx}:`, err)
          loaded++
          if (loaded === BACKGROUND_IMAGES.length) setIsReady(true) // vẫn đánh dấu ready để fallback
        })
    })
  }, [])

  // Hàm chuyển ảnh chính
  const performTransition = () => {
    if (!isReady) {
      console.log("⏳ Not ready yet, waiting...")
      return
    }

    console.log("🚀 Starting transition")
    setIsGridVisible(true)

    // Sau 1.8 giây (đủ để animation assemble hoàn thành), đổi ảnh đáy
    const timeout = setTimeout(() => {
      const nextIndex = gridIndexRef.current
      console.log(`🔄 Changing base to index ${nextIndex}`)

      // Đảm bảo ảnh đã decode (nếu chưa thì decode lại)
      const nextImg = preloadedImages.current[nextIndex]
      if (nextImg) {
        Promise.resolve(nextImg.decode())
          .then(() => {
            setBaseIndex(nextIndex)
            // Chờ 2 frame để trình duyệt render
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                setIsGridVisible(false)
                // Cập nhật ảnh cho lần lưới kế tiếp
                gridIndexRef.current =
                  (gridIndexRef.current + 1) % BACKGROUND_IMAGES.length
                setGridIndex(gridIndexRef.current)
                console.log(
                  `✅ Transition done. Next grid index = ${gridIndexRef.current}`,
                )
              })
            })
          })
          .catch(() => {
            // Fallback: vẫn đổi ảnh
            setBaseIndex(nextIndex)
            requestAnimationFrame(() => {
              setIsGridVisible(false)
              gridIndexRef.current =
                (gridIndexRef.current + 1) % BACKGROUND_IMAGES.length
              setGridIndex(gridIndexRef.current)
            })
          })
      } else {
        // Fallback khi ảnh chưa có trong preload (hiếm)
        setBaseIndex(nextIndex)
        requestAnimationFrame(() => {
          setIsGridVisible(false)
          gridIndexRef.current =
            (gridIndexRef.current + 1) % BACKGROUND_IMAGES.length
          setGridIndex(gridIndexRef.current)
        })
      }
    }, 1800)

    transitionTimer.current = timeout
  }

  // Khởi tạo interval khi isReady = true
  useEffect(() => {
    if (!isReady) return

    // Chạy transition lần đầu tiên sau 1 giây (để mọi thứ ổn định)
    const startDelay = setTimeout(() => {
      performTransition()
      // Sau đó lặp lại mỗi 6 giây
      intervalRef.current = setInterval(performTransition, 6000)
    }, 1000)

    return () => {
      clearTimeout(startDelay)
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (transitionTimer.current) clearTimeout(transitionTimer.current)
    }
  }, [isReady, performTransition]) // performTransition phụ thuộc isReady nhưng isReady ổn định, ta có thể dùng ref để gọi

  // Grid cells
  const gridCells = useMemo(() => {
    const cells = []
    for (let r = 0; r < GRID_ROWS; r++) {
      for (let c = 0; c < GRID_COLS; c++) {
        cells.push({
          id: `${r}-${c}`,
          r,
          c,
          delay: r * 0.03 + c * 0.02,
          tx: (Math.random() - 0.5) * 400,
          ty: (Math.random() - 0.5) * 400,
          rot: (Math.random() - 0.5) * 120,
        })
      }
    }
    return cells
  }, [])

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: { username: "", password: "" },
  })

  const onSubmit = (data: FormData) => {
    if (loginMutation.isPending) return
    loginMutation.mutate(data)
  }

  return (
    <div className="relative flex min-h-screen w-full font-sans bg-black overflow-hidden">
      {/* Hidden preload images for cache */}
      <div className="absolute w-0 h-0 opacity-0 overflow-hidden pointer-events-none">
        {BACKGROUND_IMAGES.map((src) => (
          <img key={src} src={src} alt="" />
        ))}
      </div>

      {/* ========== SHATTER ENGINE ========== */}
      <div className="absolute inset-0 z-0 w-full h-full bg-black">
        {/* BASE LAYER */}
        {BACKGROUND_IMAGES.map((src, index) => (
          <img
            key={`base-${src}`}
            src={src}
            className="absolute inset-0 w-full h-full object-cover transition-opacity duration-300"
            style={{
              opacity: index === baseIndex ? 1 : 0,
              zIndex: index === baseIndex ? 0 : -1,
            }}
            alt=""
          />
        ))}

        {/* GRID LAYER */}
        {isGridVisible && (
          <div
            className="absolute inset-0 z-10 grid"
            style={{
              gridTemplateRows: `repeat(${GRID_ROWS}, 1fr)`,
              gridTemplateColumns: `repeat(${GRID_COLS}, 1fr)`,
            }}
          >
            {gridCells.map((cell) => (
              <div
                key={cell.id}
                className="relative overflow-hidden will-change-transform"
                style={
                  {
                    animation: `assembleIn 0.9s cubic-bezier(0.23, 1, 0.32, 1) ${cell.delay}s both`,
                    "--tx": `${cell.tx}px`,
                    "--ty": `${cell.ty}px`,
                    "--rot": `${cell.rot}deg`,
                  } as React.CSSProperties
                }
              >
                <div
                  className="absolute w-[100vw] h-[100vh] bg-cover bg-center"
                  style={{
                    backgroundImage: `url(${BACKGROUND_IMAGES[gridIndex]})`,
                    left: `-${cell.c * 100}%`,
                    top: `-${cell.r * 100}%`,
                  }}
                />
              </div>
            ))}
          </div>
        )}

        <style>{`
          @keyframes assembleIn {
            0% { opacity: 0; transform: translate(var(--tx), var(--ty)) scale(1.3) rotate(var(--rot)); filter: blur(12px); }
            100% { opacity: 1; transform: translate(0, 0) scale(1) rotate(0deg); filter: blur(0px); }
          }
        `}</style>

        {/* Gradient overlay */}
        <div className="absolute inset-0 z-20 bg-gradient-to-r from-black/70 via-black/30 to-transparent lg:to-black/40 pointer-events-none" />
      </div>

      {/* ========== LEFT CONTENT ========== */}
      <div className="relative z-30 hidden lg:flex flex-col justify-center px-16 xl:px-24 w-1/2 h-screen">
        <div className="animate-fade-in-up">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-md border border-white/20 shadow-lg mb-10">
            <Sparkles className="w-4 h-4 text-amber-300" />
            <span className="text-xs font-bold text-white/90 tracking-[0.2em] uppercase">
              Giới hạn · 2025
            </span>
          </div>

          <h1 className="text-6xl xl:text-7xl font-bold text-white mb-8 leading-[1.1] tracking-tight">
            Kết nối
            <br />
            <span className="bg-gradient-to-r from-amber-200 via-emerald-300 to-cyan-400 bg-clip-text text-transparent">
              Tinh hoa & Nhịp sống
            </span>
          </h1>

          <p className="text-lg text-zinc-200/80 max-w-md leading-relaxed font-light mb-12 drop-shadow-md">
            Nền tảng O2O thế hệ mới – nơi văn hóa gặp gỡ thương mại. Trải nghiệm
            liền mạch, đặc quyền riêng biệt.
          </p>

          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3 text-white/70">
              <Shield className="w-5 h-5 text-emerald-400" />
              <span className="text-sm font-medium">
                Bảo mật chuẩn ngân hàng
              </span>
            </div>
            <div className="flex items-center gap-3 text-white/70">
              <Zap className="w-5 h-5 text-amber-400" />
              <span className="text-sm font-medium">
                Xác thực vân tay & Face ID
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ========== LOGIN PANEL ========== */}
      <div className="relative z-30 w-full lg:w-1/2 h-screen flex items-center justify-center lg:justify-end lg:pr-16 xl:pr-24 p-6">
        <div className="w-full max-w-[440px] p-8 rounded-3xl bg-white/5 backdrop-blur-2xl border border-white/20 shadow-2xl transition-all duration-500 hover:shadow-emerald-500/10">
          <div className="mb-8 text-center">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-white to-gray-200 flex items-center justify-center shadow-[0_8px_20px_rgba(0,0,0,0.3)] mb-5">
              <Fingerprint className="w-7 h-7 text-gray-900" />
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Chào mừng trở lại
            </h2>
            <p className="text-sm text-white/50 mt-1">
              Đăng nhập để truy cập hệ sinh thái AEGIS
            </p>
          </div>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-white/70 text-xs font-semibold tracking-wider uppercase">
                      Email
                    </FormLabel>
                    <FormControl>
                      <Input
                        data-testid="email-input"
                        placeholder="admin@aegis.com"
                        type="email"
                        className="bg-black/30 border-white/15 text-white placeholder:text-white/30 focus:border-emerald-400/60 focus:ring-0 h-11 rounded-xl"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-rose-300 text-xs" />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <div className="flex justify-between items-center">
                      <FormLabel className="text-white/70 text-xs font-semibold tracking-wider uppercase">
                        Mật khẩu
                      </FormLabel>
                      <RouterLink
                        to="/recover-password"
                        className="text-xs text-white/40 hover:text-white transition"
                      >
                        Quên?
                      </RouterLink>
                    </div>
                    <FormControl>
                      <PasswordInput
                        data-testid="password-input"
                        placeholder="••••••••"
                        className="bg-black/30 border-white/15 text-white placeholder:text-white/30 focus:border-emerald-400/60 focus:ring-0 h-11 rounded-xl"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-rose-300 text-xs" />
                  </FormItem>
                )}
              />

              <LoadingButton
                type="submit"
                loading={loginMutation.isPending}
                data-testid="login-button"
                className="w-full mt-6 h-11 bg-white text-gray-900 hover:bg-gray-100 font-semibold rounded-xl transition-all shadow-md hover:shadow-xl flex items-center justify-center gap-2 group"
              >
                Đăng nhập{" "}
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
              </LoadingButton>

              <div className="text-center text-sm text-white/40 mt-6">
                Chưa có tài khoản?{" "}
                <RouterLink
                  to="/signup"
                  className="text-white hover:text-emerald-300 transition"
                >
                  Đăng ký ngay
                </RouterLink>
              </div>
            </form>
          </Form>
        </div>
      </div>

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade-in-up {
          animation: fadeInUp 0.6s ease-out forwards;
        }
      `}</style>
    </div>
  )
}
