import {
  createFileRoute,
  Outlet,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import {
  Bell,
  ChevronRight,
  Fingerprint,
  Loader2,
  LogOut,
  Search,
  Send,
  Settings as SettingsIcon,
} from "lucide-react"
import { type FormEvent, useEffect, useRef, useState } from "react"
import { AgentAPI } from "@/client/aegis-api"
import AppSidebar from "@/components/Sidebar/AppSidebar"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Sheet as SheetComp,
  SheetContent as SheetContentComp,
  SheetHeader as SheetHeaderComp,
  SheetTitle as SheetTitleComp,
  SheetTrigger as SheetTriggerComp,
} from "@/components/ui/sheet"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({
        to: "/login",
      })
    }
  },
})

// Typewriter Logo Component
const TypewriterLogo = () => {
  const text = "AEGIS_O2O"
  const [displayText, setDisplayText] = useState("")

  useEffect(() => {
    let currentIndex = 0
    setDisplayText("")
    const interval = setInterval(() => {
      if (currentIndex <= text.length) {
        setDisplayText(text.slice(0, currentIndex))
        currentIndex++
      } else {
        clearInterval(interval)
      }
    }, 150)
    return () => clearInterval(interval)
  }, [])

  return (
    <h1 className="text-lg font-bold tracking-widest text-zinc-700 hidden sm:block font-mono border-r-2 border-teal-600 pr-1 animate-[pulse_1s_infinite]">
      {displayText}
    </h1>
  )
}

// Chat Message Type
interface ChatMessage {
  role: "user" | "agent"
  text: string
  actions?: string[]
  timestamp: Date
}

// Agent Chat Panel
const AgentChatPanel = ({ initialMessage }: { initialMessage?: string }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (initialMessage) {
      setInput(initialMessage)
    }
  }, [initialMessage])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    const query = input.trim()
    if (!query || isLoading) return

    const userMsg: ChatMessage = {
      role: "user",
      text: query,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setIsLoading(true)

    try {
      const res = await AgentAPI.chat({ query })
      const data = res.data
      const agentMsg: ChatMessage = {
        role: "agent",
        text: data.answer,
        actions: data.internal_actions,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, agentMsg])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text: "⚠ Không thể kết nối tới AEGIS Agent. Kiểm tra backend.",
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <div className="flex-1 p-4 overflow-y-auto custom-scrollbar space-y-4 relative">
        {/* Background Glow */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(34,211,238,0.03),transparent_70%)] pointer-events-none"></div>

        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-zinc-500 relative">
            <div className="relative w-24 h-24 flex items-center justify-center mb-8">
              <div className="absolute inset-0 rounded-full border border-cyan-500/20 animate-[spin_4s_linear_infinite]"></div>
              <div className="absolute inset-2 rounded-full border border-dashed border-cyan-500/40 animate-[spin_6s_linear_infinite_reverse]"></div>
              <div className="absolute inset-4 rounded-full border border-cyan-500/60 shadow-[0_0_15px_rgba(34,211,238,0.3)] animate-pulse"></div>
              <Fingerprint className="w-8 h-8 text-cyan-300 drop-shadow-[0_0_10px_rgba(34,211,238,0.8)]" />
            </div>
            <p className="font-mono text-sm tracking-widest uppercase animate-pulse text-cyan-500/70">
              AEGIS Agent Ready
            </p>
            <p className="text-xs text-zinc-600 mt-2 max-w-[250px] text-center">
              Hỏi về địa danh, thời tiết, gợi ý mua sắm...
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-slide-up`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-cyan-600/20 border border-cyan-500/30 text-cyan-100 rounded-br-md"
                  : "bg-white/5 border border-white/10 text-zinc-200 rounded-bl-md"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>
              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-3 pt-2 border-t border-white/10">
                  <p className="text-[10px] text-zinc-500 font-mono uppercase tracking-wider mb-1">
                    Internal Actions
                  </p>
                  {msg.actions.map((action, j) => (
                    <div
                      key={j}
                      className="text-[11px] text-cyan-400/70 font-mono flex items-center gap-1"
                    >
                      <ChevronRight className="w-3 h-3" /> {action}
                    </div>
                  ))}
                </div>
              )}
              <p className="text-[10px] text-zinc-600 mt-1 font-mono">
                {msg.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start animate-slide-up">
            <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-2">
              <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
              <span className="text-xs text-zinc-400 font-mono animate-pulse">
                Processing...
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/10 bg-black/60 backdrop-blur-xl">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Hỏi AEGIS Agent..."
            className="aegis-input flex-1 text-sm"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="aegis-btn aegis-btn-primary px-4 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </>
  )
}

function Layout() {
  const { user: currentUser, logout } = useAuth()

  const [isChatOpen, setIsChatOpen] = useState(false)
  const [initialChatMessage, setInitialChatMessage] = useState("")
  const [globalQuery, setGlobalQuery] = useState("")

  useEffect(() => {
    const handleOpenChatEvent = (e: Event) => {
      const customEvent = e as CustomEvent<{ message?: string }>
      setIsChatOpen(true)
      if (customEvent.detail?.message) {
        setInitialChatMessage(customEvent.detail.message)
      }
    }
    document.addEventListener("open-agent-chat", handleOpenChatEvent)
    return () =>
      document.removeEventListener("open-agent-chat", handleOpenChatEvent)
  }, [])

  const initials = currentUser?.full_name
    ? currentUser.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .substring(0, 2)
        .toUpperCase()
    : currentUser?.email?.substring(0, 2).toUpperCase() || "AL"

  const handleGlobalSearch = (e: FormEvent) => {
    e.preventDefault()
    const query = globalQuery.trim()
    if (!query) return
    setInitialChatMessage(query)
    setIsChatOpen(true)
    setGlobalQuery("")
  }

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-800 font-sans relative overflow-hidden z-0">

      <SidebarProvider>
        <AppSidebar />
        <SidebarInset className="bg-transparent flex flex-col h-screen overflow-hidden relative">
          {/* Light Navbar */}
          <header className="flex h-16 shrink-0 items-center justify-between border-b border-zinc-200 bg-white/95 backdrop-blur-xl px-4 sm:px-6 relative z-20 shadow-sm">
            <div className="flex items-center gap-4">
              <SidebarTrigger className="-ml-2 text-zinc-500 hover:text-teal-600 transition-colors" />
              <div className="h-4 w-px bg-zinc-200 hidden sm:block"></div>
              <TypewriterLogo />
            </div>

            <div className="flex items-center gap-4 sm:gap-6">
              <form
                onSubmit={handleGlobalSearch}
                className="hidden md:flex relative group"
              >
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400 group-focus-within:text-teal-600 transition-colors" />
                <input
                  type="text"
                  value={globalQuery}
                  onChange={(e) => setGlobalQuery(e.target.value)}
                  placeholder="Tìm kiếm..."
                  className="w-64 pl-10 pr-12 py-1.5 bg-zinc-100 border border-zinc-200 rounded-full text-sm text-zinc-800 outline-none focus:border-teal-500 focus:bg-white transition-all placeholder:text-zinc-400"
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
                  <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded bg-zinc-100 px-1.5 font-mono text-[10px] font-medium text-zinc-500 border border-zinc-200">
                    ⌘K
                  </kbd>
                </div>
              </form>

              <div className="flex items-center gap-3">
                <button className="relative p-2 text-zinc-500 hover:text-teal-600 transition-colors rounded-full hover:bg-zinc-100">
                  <Bell className="w-5 h-5" />
                </button>

                <div className="h-6 w-px bg-zinc-200 hidden sm:block"></div>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <div className="p-0.5 rounded-full bg-gradient-to-tr from-teal-500 to-emerald-500 hover:scale-110 transition-transform">
                      <Avatar className="h-8 w-8 cursor-pointer border-2 border-white rounded-full">
                        <AvatarImage
                          src=""
                          alt={currentUser?.full_name || "User"}
                          className="rounded-full"
                        />
                        <AvatarFallback className="bg-white text-zinc-700 text-xs font-medium rounded-full">
                          {initials}
                        </AvatarFallback>
                      </Avatar>
                    </div>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    className="w-56 bg-white border border-zinc-200 text-zinc-700 mt-2 shadow-lg"
                    align="end"
                  >
                    <DropdownMenuLabel className="font-medium text-zinc-800">
                      {currentUser?.full_name || currentUser?.email || "User"}
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator className="bg-zinc-100" />
                    <RouterLink to="/settings">
                      <DropdownMenuItem className="cursor-pointer hover:bg-zinc-50 focus:bg-zinc-50">
                        <SettingsIcon className="mr-2 h-4 w-4" />
                        <span>Cài đặt</span>
                      </DropdownMenuItem>
                    </RouterLink>
                    <DropdownMenuItem
                      className="cursor-pointer text-red-600 hover:bg-red-50 hover:text-red-700 focus:bg-red-50 focus:text-red-700"
                      onClick={() => logout()}
                    >
                      <LogOut className="mr-2 h-4 w-4" />
                      <span>Đăng xuất</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 overflow-auto bg-transparent relative z-10 custom-scrollbar">
            <Outlet />
          </main>

          {/* FAB Executive Agent */}
          <SheetComp open={isChatOpen} onOpenChange={setIsChatOpen}>
            <SheetTriggerComp asChild>
              <button className="fixed bottom-8 right-8 z-50 p-4 bg-black/60 hover:bg-black backdrop-blur-xl border border-cyan-500/50 text-cyan-400 rounded-full shadow-[0_0_30px_rgba(34,211,238,0.3)] hover:shadow-[0_0_40px_rgba(34,211,238,0.6)] transition-all duration-300 hover:scale-110 active:scale-95 group">
                <div className="absolute inset-0 rounded-full border border-cyan-400/30 animate-ping"></div>
                <Fingerprint className="w-6 h-6 group-hover:text-cyan-300 transition-colors" />
              </button>
            </SheetTriggerComp>
            <SheetContentComp className="w-[400px] sm:w-[450px] border-l border-white/10 bg-black/40 backdrop-blur-3xl text-zinc-100 p-0 flex flex-col shadow-[-20px_0_50px_rgba(0,0,0,0.8)]">
              <SheetHeaderComp className="p-6 border-b border-white/10 bg-gradient-to-b from-cyan-950/20 to-transparent">
                <SheetTitleComp className="flex items-center gap-3 text-zinc-100 text-xl font-bold tracking-wide font-mono">
                  <Fingerprint className="w-6 h-6 text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]" />{" "}
                  AEGIS_AGENT
                </SheetTitleComp>
                <p className="text-xs text-cyan-400 font-mono mt-1 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(34,211,238,0.8)] animate-pulse"></span>
                  LINK SECURED // GEMINI ACTIVE
                </p>
              </SheetHeaderComp>
              <AgentChatPanel initialMessage={initialChatMessage} />
            </SheetContentComp>
          </SheetComp>
        </SidebarInset>
      </SidebarProvider>
    </div>
  )
}

export default Layout
