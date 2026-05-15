import { createFileRoute } from "@tanstack/react-router"
import {
  Activity,
  Globe,
  Lock,
  MapPin,
  Package,
  Plane,
  Radio,
  ShoppingBag,
  Sparkles,
  Store,
  TrendingUp,
  Zap,
} from "lucide-react"
import { useEffect, useState } from "react"

export const Route = createFileRoute("/_layout/")({ component: Dashboard })

const fmt = (n: number) => n.toLocaleString()
const rand = (a: number, b: number) =>
  Math.floor(Math.random() * (b - a + 1)) + a

const HUBS = [
  { name: "Hà Nội", cx: 52, cy: 18, pulse: true, count: 12 },
  { name: "Đà Nẵng", cx: 56, cy: 47, pulse: true, count: 8 },
  { name: "Hội An", cx: 57, cy: 50, pulse: false, count: 5 },
  { name: "Huế", cx: 54, cy: 43, pulse: false, count: 6 },
  { name: "Nha Trang", cx: 61, cy: 63, pulse: false, count: 4 },
  { name: "TP.HCM", cx: 48, cy: 77, pulse: true, count: 15 },
  { name: "Phú Quốc", cx: 35, cy: 82, pulse: false, count: 3 },
  { name: "Sapa", cx: 44, cy: 10, pulse: true, count: 2 },
]

const ROUTES = [
  { x1: 52, y1: 18, x2: 54, y2: 43 },
  { x1: 54, y1: 43, x2: 56, y2: 47 },
  { x1: 56, y1: 47, x2: 61, y2: 63 },
  { x1: 61, y1: 63, x2: 48, y2: 77 },
]

const STATS = [
  {
    label: "Active Travelers",
    value: 2847,
    delta: "+12.4%",
    icon: Plane,
    color: "emerald",
  },
  {
    label: "Monthly Revenue",
    value: 1260000,
    delta: "+8.1%",
    icon: TrendingUp,
    color: "cyan",
    prefix: "₫",
  },
  {
    label: "O2O Hubs Online",
    value: 34,
    delta: "3 new",
    icon: Store,
    color: "purple",
  },
  {
    label: "Active Reservations",
    value: 189,
    delta: "+23%",
    icon: Lock,
    color: "amber",
  },
] as const

const ACTIVITIES = [
  { text: "Đặt cọc Áo dài tại Hub Hội An", time: "2m", type: "lock" },
  { text: "TSP route: Đà Nẵng → Huế (34km)", time: "5m", type: "route" },
  { text: "AI Agent tư vấn Sapa 3N2Đ", time: "8m", type: "ai" },
  { text: "Hub Phú Quốc thêm 12 sản phẩm", time: "15m", type: "store" },
  { text: "Vision Scan: 3 sản phẩm tương đồng", time: "22m", type: "scan" },
  { text: "Silk Scarf reserved — Hanoi Hub", time: "30m", type: "lock" },
  { text: "Heritage story: Mỹ Sơn Sanctuary", time: "1h", type: "ai" },
]

const TRENDING = [
  { name: "Sapa", region: "Lào Cai", score: 98 },
  { name: "Hội An", region: "Quảng Nam", score: 94 },
  { name: "Cố đô Huế", region: "Thừa Thiên Huế", score: 91 },
  { name: "Vịnh Hạ Long", region: "Quảng Ninh", score: 88 },
]

const C: Record<
  string,
  { bg: string; text: string; border: string; shadow: string }
> = {
  emerald: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/20",
    shadow: "shadow-[0_0_24px_rgba(16,185,129,0.12)]",
  },
  cyan: {
    bg: "bg-cyan-500/10",
    text: "text-cyan-400",
    border: "border-cyan-500/20",
    shadow: "shadow-[0_0_24px_rgba(34,211,238,0.12)]",
  },
  purple: {
    bg: "bg-purple-500/10",
    text: "text-purple-400",
    border: "border-purple-500/20",
    shadow: "shadow-[0_0_24px_rgba(168,85,247,0.12)]",
  },
  amber: {
    bg: "bg-amber-500/10",
    text: "text-amber-400",
    border: "border-amber-500/20",
    shadow: "shadow-[0_0_24px_rgba(245,158,11,0.12)]",
  },
}

const ACT_ICONS: Record<string, typeof Zap> = {
  lock: Lock,
  route: MapPin,
  ai: Sparkles,
  store: Package,
  scan: Globe,
}

function useClock() {
  const [t, setT] = useState(new Date())
  useEffect(() => {
    const i = setInterval(() => setT(new Date()), 1000)
    return () => clearInterval(i)
  }, [])
  return t
}

function AnimNum({ target, prefix = "" }: { target: number; prefix?: string }) {
  const [v, setV] = useState(0)
  useEffect(() => {
    let f: number,
      s = 0
    const step = (ts: number) => {
      if (!s) s = ts
      const p = Math.min((ts - s) / 1200, 1)
      setV(Math.floor(p * target))
      if (p < 1) f = requestAnimationFrame(step)
    }
    f = requestAnimationFrame(step)
    return () => cancelAnimationFrame(f)
  }, [target])
  return (
    <>
      {prefix}
      {fmt(v)}
    </>
  )
}

function TelemetryStream() {
  const msgs = [
    "[SPATIAL] ST_DWithin: 14ms — 23 places",
    "[REDIS] Lock acquired: product_id=47",
    "[AGENT] tool_call: search_culture('Hội An')",
    "[VISION] CLIP encode: 512D / 89ms",
    "[OSRM] Route: 34.2km, 5 waypoints",
    "[CACHE] Redis HIT: 94.2%",
    "[INVENTORY] 3 expired locks swept",
  ]
  const [lines, setLines] = useState<string[]>([])
  useEffect(() => {
    const add = () =>
      setLines((p) => [
        ...p.slice(-5),
        `${new Date().toLocaleTimeString()} ${msgs[rand(0, msgs.length - 1)]}`,
      ])
    add()
    const i = setInterval(add, 2800)
    return () => clearInterval(i)
  }, [msgs.length, msgs])
  return (
    <div className="space-y-1 font-mono text-[11px]">
      {lines.map((l, i) => (
        <div
          key={i}
          className={
            i === lines.length - 1 ? "text-emerald-400" : "text-zinc-600"
          }
        >
          <span className="text-zinc-700 mr-2">{l.split(" ")[0]}</span>
          {l.split(" ").slice(1).join(" ")}
        </div>
      ))}
    </div>
  )
}

/* ─── SVG Vietnam Map ─── */
function VietnamMap() {
  return (
    <div className="relative w-full h-full bg-zinc-950 overflow-hidden">
      {/* Grid lines */}
      <svg
        className="absolute inset-0 w-full h-full opacity-10"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern
            id="grid"
            width="40"
            height="40"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 40 0 L 0 0 0 40"
              fill="none"
              stroke="rgba(34,211,238,0.4)"
              strokeWidth="0.5"
            />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>

      {/* Vietnam SVG outline */}
      <svg
        viewBox="0 0 100 120"
        className="absolute inset-0 w-full h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Simplified Vietnam shape */}
        <path
          d="M52,5 L57,8 L61,12 L62,16 L60,20 L63,24 L65,28 L63,32 L60,36 L62,40 L62,44 L60,47 L63,51 L64,55 L63,59 L65,63 L63,67 L60,70 L58,74 L55,78 L52,80 L48,80 L44,78 L40,75 L36,80 L33,84 L34,88 L36,85 L38,82 L40,79 L44,82 L46,85 L44,88 L42,86 L44,90 L42,88 L40,85 L38,88 L36,91 L38,93 L36,95 L40,92 L42,95 L40,97 L44,94 L46,97 L44,100 L48,97 L50,100 L48,80 L52,80 L56,76 L58,72 L60,68 L62,63 L64,58 L62,53 L60,48 L62,43 L61,38 L60,33 L62,28 L61,23 L59,18 L57,14 L54,10 L52,5Z"
          fill="none"
          stroke="rgba(16,185,129,0.25)"
          strokeWidth="0.8"
          className="drop-shadow-[0_0_6px_rgba(16,185,129,0.4)]"
        />
        {/* Filled land mass */}
        <path
          d="M52,5 L57,8 L61,12 L62,16 L60,20 L63,24 L65,28 L63,32 L60,36 L62,40 L62,44 L60,47 L63,51 L64,55 L63,59 L65,63 L63,67 L60,70 L58,74 L55,78 L52,80 L48,80 L44,78 L40,75 L44,82 L46,85 L44,88 L44,90 L48,97 L50,100 L48,80 L52,80 L56,76 L58,72 L60,68 L62,63 L64,58 L62,53 L60,48 L62,43 L61,38 L60,33 L62,28 L61,23 L59,18 L57,14 L54,10 L52,5Z"
          fill="rgba(16,185,129,0.04)"
        />

        {/* Route lines */}
        {ROUTES.map((r, i) => (
          <line
            key={i}
            x1={r.x1}
            y1={r.y1}
            x2={r.x2}
            y2={r.y2}
            stroke="rgba(34,211,238,0.25)"
            strokeWidth="0.4"
            strokeDasharray="2,1.5"
          />
        ))}

        {/* Hub dots */}
        {HUBS.map((h) => (
          <g key={h.name}>
            {h.pulse && (
              <circle
                cx={h.cx}
                cy={h.cy}
                r="3"
                fill="none"
                stroke="rgba(16,185,129,0.4)"
                strokeWidth="0.5"
              >
                <animate
                  attributeName="r"
                  values="2;5;2"
                  dur="2s"
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  values="0.8;0;0.8"
                  dur="2s"
                  repeatCount="indefinite"
                />
              </circle>
            )}
            <circle
              cx={h.cx}
              cy={h.cy}
              r="1.5"
              fill={h.pulse ? "rgba(16,185,129,1)" : "rgba(34,211,238,0.9)"}
              filter={h.pulse ? "url(#glow-emerald)" : "url(#glow-cyan)"}
            />
            <text
              x={h.cx + 2.5}
              y={h.cy + 0.8}
              fontSize="3"
              fill="rgba(255,255,255,0.7)"
              fontFamily="monospace"
            >
              {h.name}
            </text>
          </g>
        ))}

        {/* Glow filters */}
        <defs>
          <filter
            id="glow-emerald"
            x="-100%"
            y="-100%"
            width="300%"
            height="300%"
          >
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-cyan" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="1" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>

      {/* Ambient glow behind map */}
      <div className="absolute top-[15%] left-[45%] w-24 h-48 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-[20%] left-[40%] w-20 h-32 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
    </div>
  )
}

/* ─── Dashboard ─── */
export default function Dashboard() {
  const now = useClock()
  const greeting =
    now.getHours() < 12
      ? "Good Morning"
      : now.getHours() < 18
        ? "Good Afternoon"
        : "Good Evening"

  return (
    <div className="relative min-h-screen w-full bg-zinc-950 overflow-x-hidden">
      {/* Background glows */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-5%] w-[45%] h-[45%] bg-emerald-500/[0.06] rounded-full blur-[130px]" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[40%] h-[40%] bg-cyan-500/[0.05] rounded-full blur-[120px]" />
        <div className="absolute top-[45%] right-[25%] w-[20%] h-[20%] bg-purple-500/[0.03] rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-[1600px] mx-auto px-6 py-8 space-y-7">
        {/* HEADER */}
        <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-3">
              <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
              <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-widest">
                All Systems Operational
              </span>
            </div>
            <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
              AEGIS{" "}
              <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                Trung tâm điều phối
              </span>
            </h1>
            <p className="text-zinc-400 mt-1 text-sm">
              {greeting}, Commander ·{" "}
              {now.toLocaleDateString("vi-VN", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-2xl font-mono font-bold text-white tabular-nums">
                {now.toLocaleTimeString("vi-VN")}
              </p>
              <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-widest">
                Asia/Ho_Chi_Minh
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Activity className="w-5 h-5 text-emerald-400" />
            </div>
          </div>
        </header>

        {/* STATS */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STATS.map((s) => {
            const c = C[s.color]
            return (
              <div
                key={s.label}
                className={`bg-zinc-900/40 backdrop-blur-md border border-white/[0.08] rounded-2xl p-5 hover:border-white/15 transition-all duration-500 ${c.shadow}`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div
                    className={`p-2.5 rounded-xl ${c.bg} border ${c.border}`}
                  >
                    <s.icon className={`w-4 h-4 ${c.text}`} />
                  </div>
                  <span
                    className={`text-[10px] font-mono ${c.text} bg-zinc-950/50 px-2 py-0.5 rounded-full`}
                  >
                    {s.delta}
                  </span>
                </div>
                <p className={`text-2xl font-bold font-mono ${c.text}`}>
                  <AnimNum
                    target={s.value}
                    prefix={"prefix" in s ? s.prefix : ""}
                  />
                </p>
                <p className="text-xs text-zinc-400 mt-1">{s.label}</p>
              </div>
            )
          })}
        </div>

        {/* MAIN GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* MAP PANEL */}
          <div className="lg:col-span-2 bg-zinc-900/40 backdrop-blur-md border border-white/[0.08] rounded-2xl overflow-hidden flex flex-col">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/5">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-widest">
                  Vietnam O2O Network
                </span>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(16,185,129,0.8)]" />
                  <span className="text-[10px] text-zinc-400 font-mono">
                    Major Hub
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.8)]" />
                  <span className="text-[10px] text-zinc-400 font-mono">
                    Station
                  </span>
                </div>
                <div className="flex items-center gap-1.5 ml-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-[10px] text-zinc-400 font-mono">
                    LIVE
                  </span>
                </div>
              </div>
            </div>

            <div className="flex-1 relative" style={{ minHeight: 420 }}>
              <VietnamMap />
              {/* Bottom overlay */}
              <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-zinc-950/90 to-transparent">
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { l: "Active Routes", v: "12" },
                    { l: "Hubs Online", v: "34" },
                    { l: "Coverage", v: "89%" },
                  ].map((s) => (
                    <div
                      key={s.l}
                      className="bg-zinc-950/60 backdrop-blur-md rounded-xl px-3 py-2.5 border border-white/5 text-center"
                    >
                      <p className="text-lg font-bold text-emerald-400 font-mono">
                        {s.v}
                      </p>
                      <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider">
                        {s.l}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN */}
          <div className="space-y-5">
            {/* Activity Feed */}
            <div className="bg-zinc-900/40 backdrop-blur-md border border-white/[0.08] rounded-2xl overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3.5 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold text-white uppercase tracking-wider">
                    Live Activity
                  </span>
                </div>
                <span className="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded-full">
                  {ACTIVITIES.length} events
                </span>
              </div>
              <div className="p-3 space-y-0.5 max-h-72 overflow-y-auto">
                {ACTIVITIES.map((a, i) => {
                  const Icon = ACT_ICONS[a.type] || Zap
                  return (
                    <div
                      key={i}
                      className="flex items-start gap-3 px-2.5 py-2 rounded-xl hover:bg-white/[0.03] transition-colors"
                    >
                      <div className="mt-0.5 p-1.5 rounded-lg bg-white/[0.04] border border-white/5 shrink-0">
                        <Icon className="w-3 h-3 text-zinc-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-zinc-300 leading-relaxed">
                          {a.text}
                        </p>
                        <p className="text-[10px] text-zinc-600 font-mono">
                          {a.time} ago
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Trending Destinations */}
            <div className="bg-zinc-900/40 backdrop-blur-md border border-white/[0.08] rounded-2xl overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-3.5 border-b border-white/5">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                <span className="text-xs font-bold text-white uppercase tracking-wider">
                  Trending Destinations
                </span>
              </div>
              <div className="p-3 space-y-2">
                {TRENDING.map((t, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 px-2.5 py-2.5 rounded-xl hover:bg-white/[0.04] transition-colors cursor-pointer"
                  >
                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-emerald-500/20 to-cyan-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
                      <span className="text-[10px] font-bold text-emerald-400 font-mono">
                        #{i + 1}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white">
                        {t.name}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <p className="text-[10px] text-zinc-500 flex items-center gap-1">
                          <MapPin className="w-2.5 h-2.5" />
                          {t.region}
                        </p>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="flex items-center gap-1">
                        <div className="w-12 h-1 rounded-full bg-zinc-800 overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full"
                            style={{ width: `${t.score}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-emerald-400 font-mono">
                          {t.score}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* BOTTOM ROW */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-zinc-900/40 backdrop-blur-md border border-white/[0.08] rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <Activity className="w-4 h-4 text-emerald-400" />
              </div>
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                System Telemetry
              </span>
              <span className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <TelemetryStream />
          </div>

          <div className="bg-zinc-900/40 backdrop-blur-md border border-white/[0.08] rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                <Zap className="w-4 h-4 text-cyan-400" />
              </div>
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                Quick Actions
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                {
                  icon: MapPin,
                  label: "Spatial Scan",
                  desc: "Find nearby places",
                  color: "emerald",
                },
                {
                  icon: ShoppingBag,
                  label: "Lock Inventory",
                  desc: "Reserve O2O items",
                  color: "cyan",
                },
                {
                  icon: Sparkles,
                  label: "AI Agent",
                  desc: "Ask anything",
                  color: "purple",
                },
                {
                  icon: Globe,
                  label: "Vision Scan",
                  desc: "Tìm bằng hình ảnh",
                  color: "amber",
                },
              ].map((a) => {
                const c = C[a.color]
                return (
                  <button
                    key={a.label}
                    className="text-left p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] hover:border-white/10 transition-all duration-300 group"
                  >
                    <div
                      className={`p-2 rounded-lg ${c.bg} border ${c.border} w-fit mb-3 group-hover:scale-110 transition-transform`}
                    >
                      <a.icon className={`w-4 h-4 ${c.text}`} />
                    </div>
                    <p className="text-sm font-semibold text-white mb-0.5">
                      {a.label}
                    </p>
                    <p className="text-[11px] text-zinc-500">{a.desc}</p>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
